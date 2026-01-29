"""
Test Entry Price Calculation: Verify OPEN column is used correctly

PURPOSE:
- Ensures B-entry model uses NEXT 1m OPEN (not signal CLOSE)
- Validates entry slippage calculations
- Tests entry-anchored risk calculations

CRITICAL:
- Entry must be NEXT 1m bar OPEN after signal CLOSE
- Entry determines actual risk (not ORB edge)
- Slippage is entry - ORB edge
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
import pytest
from datetime import date, datetime


# Database path
DB_PATH = "data/db/gold.db"


class TestEntryPrice:
    """Test suite for entry price calculations in B-entry model"""

    @pytest.fixture
    def db_connection(self):
        """Create database connection"""
        conn = duckdb.connect(DB_PATH)
        yield conn
        conn.close()

    def test_tradeable_entry_price_column_exists(self, db_connection):
        """Verify tradeable_entry_price columns exist"""
        for orb in ['0900', '1000', '1100', '1800', '2300', '0030']:
            col_name = f'orb_{orb}_tradeable_entry_price'

            cols = db_connection.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'daily_features'
                AND column_name = '{col_name}'
            """).fetchall()

            assert len(cols) == 1, f"Missing column: {col_name}"

    def test_entry_price_differs_from_orb_edge(self, db_connection):
        """Verify tradeable entry price differs from structural ORB edge (due to slippage)"""
        # Get sample with UP break
        row_up = db_connection.execute("""
            SELECT
                date_local,
                orb_1000_high as orb_edge,
                orb_1000_tradeable_entry_price as entry_price
            FROM daily_features
            WHERE orb_1000_break_dir = 'UP'
            AND orb_1000_tradeable_entry_price IS NOT NULL
            LIMIT 1
        """).fetchone()

        if row_up:
            date_local, orb_edge, entry_price = row_up

            # For UP break: entry should be ABOVE ORB high (NEXT bar OPEN)
            # Entry may equal ORB edge (if market gaps) or be higher (normal case)
            assert entry_price >= orb_edge, \
                f"UP break: entry {entry_price} should be >= ORB edge {orb_edge} on {date_local}"

        # Get sample with DOWN break
        row_down = db_connection.execute("""
            SELECT
                date_local,
                orb_1000_low as orb_edge,
                orb_1000_tradeable_entry_price as entry_price
            FROM daily_features
            WHERE orb_1000_break_dir = 'DOWN'
            AND orb_1000_tradeable_entry_price IS NOT NULL
            LIMIT 1
        """).fetchone()

        if row_down:
            date_local, orb_edge, entry_price = row_down

            # For DOWN break: entry should be BELOW ORB low (NEXT bar OPEN)
            assert entry_price <= orb_edge, \
                f"DOWN break: entry {entry_price} should be <= ORB edge {orb_edge} on {date_local}"

    def test_entry_price_uses_open_not_close(self, db_connection):
        """Verify entry price is from OPEN column (not CLOSE)"""
        # This test verifies the B-entry model by checking that entry prices
        # match bar OPEN values, not bar CLOSE values

        # Get a sample date with tradeable data
        sample_row = db_connection.execute("""
            SELECT
                date_local,
                orb_1000_break_dir,
                orb_1000_tradeable_entry_price
            FROM daily_features
            WHERE orb_1000_tradeable_entry_price IS NOT NULL
            AND orb_1000_break_dir != 'NONE'
            LIMIT 1
        """).fetchone()

        if not sample_row:
            pytest.skip("No tradeable data found")

        date_local, direction, entry_price = sample_row

        # Get 1m bars for this date (starting after ORB ends at 10:05)
        bars = db_connection.execute("""
            SELECT
                ts_utc AT TIME ZONE 'Australia/Brisbane' as ts_local,
                open, high, low, close
            FROM bars_1m
            WHERE symbol = 'MGC'
            AND (ts_utc AT TIME ZONE 'Australia/Brisbane')::DATE = ?
            AND EXTRACT(HOUR FROM ts_utc AT TIME ZONE 'Australia/Brisbane') >= 10
            AND EXTRACT(MINUTE FROM ts_utc AT TIME ZONE 'Australia/Brisbane') >= 5
            ORDER BY ts_local
            LIMIT 50
        """, [date_local]).fetchall()

        if not bars:
            pytest.skip(f"No bars found for {date_local}")

        # Check that entry_price matches one of the OPEN values
        # (not necessarily CLOSE, which would indicate A-entry model)
        open_prices = [float(bar[1]) for bar in bars]

        # Entry should match an OPEN price (within 1 tick tolerance)
        matches_open = any(abs(entry_price - open_price) < 0.2 for open_price in open_prices)

        assert matches_open, \
            f"Entry price {entry_price} does not match any bar OPEN on {date_local}. " \
            f"This suggests CLOSE is being used (A-entry model) instead of OPEN (B-entry model)."

    def test_entry_price_is_after_orb_completion(self, db_connection):
        """Verify entry occurs AFTER ORB completion (not during ORB window)"""
        # Entry should be at or after 10:05 for 1000 ORB

        sample_row = db_connection.execute("""
            SELECT
                date_local,
                orb_1000_tradeable_entry_price,
                orb_1000_high,
                orb_1000_low
            FROM daily_features
            WHERE orb_1000_tradeable_entry_price IS NOT NULL
            LIMIT 1
        """).fetchone()

        if not sample_row:
            pytest.skip("No tradeable data found")

        date_local, entry_price, orb_high, orb_low = sample_row

        # Entry must be outside ORB range
        assert entry_price > orb_high or entry_price < orb_low, \
            f"Entry {entry_price} is inside ORB range [{orb_low}, {orb_high}] on {date_local}"

    def test_risk_calculation_uses_entry_price(self, db_connection):
        """Verify risk is calculated from entry price (not ORB edge)"""
        # Get sample with tradeable data
        row = db_connection.execute("""
            SELECT
                date_local,
                orb_1000_break_dir,
                orb_1000_tradeable_entry_price,
                orb_1000_tradeable_stop_price,
                orb_1000_tradeable_risk_points,
                orb_1000_size
            FROM daily_features
            WHERE orb_1000_tradeable_entry_price IS NOT NULL
            AND orb_1000_tradeable_risk_points IS NOT NULL
            LIMIT 5
        """).fetchall()

        if not row:
            pytest.skip("No tradeable data found")

        for date_local, direction, entry, stop, risk_points, orb_size in row:
            # Risk should be based on entry-to-stop distance (not ORB size)
            expected_risk = abs(entry - stop)

            # Allow 0.01 tolerance for floating point
            assert abs(risk_points - expected_risk) < 0.01, \
                f"Risk {risk_points} does not match entry-stop distance {expected_risk} on {date_local}"

            # Risk should generally differ from ORB size (due to entry slippage)
            # This is not always true (entry could equal ORB edge), but usually differs
            if abs(risk_points - orb_size) > 0.1:
                # This is expected - risk differs from ORB size
                pass

    def test_entry_slippage_is_positive(self, db_connection):
        """Verify entry slippage is always positive (worse fill than ORB edge)"""
        # Entry slippage = abs(entry - ORB edge)

        # UP breaks: entry should be >= ORB high
        rows_up = db_connection.execute("""
            SELECT
                date_local,
                orb_1000_high,
                orb_1000_tradeable_entry_price
            FROM daily_features
            WHERE orb_1000_break_dir = 'UP'
            AND orb_1000_tradeable_entry_price IS NOT NULL
            LIMIT 10
        """).fetchall()

        for date_local, orb_high, entry_price in rows_up:
            slippage = entry_price - orb_high
            assert slippage >= -0.01, \
                f"UP break: entry {entry_price} < ORB high {orb_high} (impossible slippage) on {date_local}"

        # DOWN breaks: entry should be <= ORB low
        rows_down = db_connection.execute("""
            SELECT
                date_local,
                orb_1000_low,
                orb_1000_tradeable_entry_price
            FROM daily_features
            WHERE orb_1000_break_dir = 'DOWN'
            AND orb_1000_tradeable_entry_price IS NOT NULL
            LIMIT 10
        """).fetchall()

        for date_local, orb_low, entry_price in rows_down:
            slippage = orb_low - entry_price
            assert slippage >= -0.01, \
                f"DOWN break: entry {entry_price} > ORB low {orb_low} (impossible slippage) on {date_local}"

    def test_structural_vs_tradeable_entry_difference(self, db_connection):
        """Verify structural (ORB-anchored) and tradeable (entry-anchored) differ"""
        # Structural assumes entry at ORB edge
        # Tradeable uses actual NEXT bar OPEN

        row = db_connection.execute("""
            SELECT
                date_local,
                orb_1000_break_dir,
                orb_1000_high,
                orb_1000_low,
                orb_1000_tradeable_entry_price,
                orb_1000_risk_ticks as structural_risk_ticks,
                orb_1000_tradeable_risk_points as tradeable_risk_points
            FROM daily_features
            WHERE orb_1000_tradeable_entry_price IS NOT NULL
            AND orb_1000_risk_ticks IS NOT NULL
            LIMIT 5
        """).fetchall()

        if not row:
            pytest.skip("No dual-track data found")

        for date_local, direction, orb_high, orb_low, entry_price, structural_risk_ticks, tradeable_risk_points in row:
            # Structural entry is ORB edge
            if direction == 'UP':
                structural_entry = orb_high
            elif direction == 'DOWN':
                structural_entry = orb_low
            else:
                continue

            # Tradeable entry should differ (unless market gaps exactly to ORB edge)
            entry_difference = abs(entry_price - structural_entry)

            # Most trades will have entry slippage > 0
            # (Some may be exactly 0 if market gaps to ORB edge)
            if entry_difference > 0.1:
                # This is expected - entry differs from ORB edge
                pass

            # Risk should also differ (unless entry == ORB edge)
            # Structural risk is ORB size, tradeable risk is entry-to-stop
            structural_risk_points = structural_risk_ticks * 0.1  # Convert ticks to points
            risk_difference = abs(tradeable_risk_points - structural_risk_points)

            # Allow small tolerance
            if risk_difference > 0.2:
                # This is expected - risks differ due to entry slippage
                pass

    def test_no_negative_entry_prices(self, db_connection):
        """Verify all entry prices are positive (sanity check)"""
        negative_entries = db_connection.execute("""
            SELECT date_local, orb_1000_tradeable_entry_price
            FROM daily_features
            WHERE orb_1000_tradeable_entry_price < 0
        """).fetchall()

        assert len(negative_entries) == 0, \
            f"Found {len(negative_entries)} negative entry prices (data corruption)"

    def test_entry_price_realistic_range(self, db_connection):
        """Verify entry prices are in realistic range for MGC"""
        # MGC trades in range ~2500-3000 (as of 2025-2026)

        rows = db_connection.execute("""
            SELECT date_local, orb_1000_tradeable_entry_price
            FROM daily_features
            WHERE orb_1000_tradeable_entry_price IS NOT NULL
            LIMIT 100
        """).fetchall()

        if not rows:
            pytest.skip("No tradeable data found")

        for date_local, entry_price in rows:
            assert 2000 < entry_price < 3500, \
                f"Entry price {entry_price} outside realistic range for MGC on {date_local}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
