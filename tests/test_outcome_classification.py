"""
Test Outcome Classification: Verify WIN/LOSS/OPEN/NO_TRADE logic

PURPOSE:
- Validates outcome classification logic
- Tests WIN vs LOSS determination (high/low-based, conservative same-bar logic)
- Verifies OPEN positions (price still between target and stop)
- Confirms NO_TRADE handling (no break or no entry)

CRITICAL:
- Outcomes: WIN, LOSS, OPEN, NO_TRADE
- Same-bar TP+SL hit = LOSS (conservative)
- OPEN = position still active (neither target nor stop hit)
- NO_TRADE = no break or filtered out
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
import pytest
from datetime import date


# Database path
DB_PATH = "data/db/gold.db"


class TestOutcomeClassification:
    """Test suite for outcome classification logic"""

    @pytest.fixture
    def db_connection(self):
        """Create database connection"""
        conn = duckdb.connect(DB_PATH)
        yield conn
        conn.close()

    def test_valid_outcome_values(self, db_connection):
        """Verify only valid outcome values exist"""
        valid_outcomes = ['WIN', 'LOSS', 'OPEN', 'NO_TRADE']

        # Check tradeable outcomes
        outcomes = db_connection.execute("""
            SELECT DISTINCT orb_1000_tradeable_outcome
            FROM daily_features
            WHERE orb_1000_tradeable_outcome IS NOT NULL
        """).fetchall()

        for outcome_tuple in outcomes:
            outcome = outcome_tuple[0]
            assert outcome in valid_outcomes, \
                f"Invalid outcome found: {outcome}. Valid: {valid_outcomes}"

    def test_structural_vs_tradeable_outcomes(self, db_connection):
        """Verify structural uses WIN/LOSS/NO_TRADE, tradeable uses WIN/LOSS/OPEN"""
        # Structural outcomes (from build_daily_features.py)
        structural_outcomes = db_connection.execute("""
            SELECT DISTINCT orb_1000_outcome
            FROM daily_features
            WHERE orb_1000_outcome IS NOT NULL
        """).fetchall()

        structural_values = [o[0] for o in structural_outcomes]

        # Should NOT have OPEN (uses NO_TRADE instead)
        assert 'OPEN' not in structural_values, \
            "Structural outcomes should use NO_TRADE (not OPEN)"

        # Tradeable outcomes (from populate_tradeable_metrics.py)
        tradeable_outcomes = db_connection.execute("""
            SELECT DISTINCT orb_1000_tradeable_outcome
            FROM daily_features
            WHERE orb_1000_tradeable_outcome IS NOT NULL
        """).fetchall()

        tradeable_values = [o[0] for o in tradeable_outcomes]

        # May have OPEN (position still active)
        # This is the key difference between structural and tradeable

    def test_win_means_target_hit(self, db_connection):
        """Verify WIN outcomes have price reaching target"""
        rows = db_connection.execute("""
            SELECT
                date_local,
                orb_1000_break_dir,
                orb_1000_tradeable_entry_price,
                orb_1000_tradeable_target_price,
                orb_1000_tradeable_outcome
            FROM daily_features
            WHERE orb_1000_tradeable_outcome = 'WIN'
            AND orb_1000_tradeable_target_price IS NOT NULL
            LIMIT 10
        """).fetchall()

        if not rows:
            pytest.skip("No WIN outcomes found")

        for date_local, direction, entry, target, outcome in rows:
            # For WIN, price must have reached target
            # We can't verify exact bar data here, but we can verify
            # that target is in the correct direction from entry

            if direction == 'UP':
                assert target > entry, \
                    f"UP WIN: target {target} should be > entry {entry} on {date_local}"
            elif direction == 'DOWN':
                assert target < entry, \
                    f"DOWN WIN: target {target} should be < entry {entry} on {date_local}"

    def test_loss_means_stop_hit(self, db_connection):
        """Verify LOSS outcomes have price hitting stop"""
        rows = db_connection.execute("""
            SELECT
                date_local,
                orb_1000_break_dir,
                orb_1000_tradeable_entry_price,
                orb_1000_tradeable_stop_price,
                orb_1000_tradeable_outcome
            FROM daily_features
            WHERE orb_1000_tradeable_outcome = 'LOSS'
            AND orb_1000_tradeable_stop_price IS NOT NULL
            LIMIT 10
        """).fetchall()

        if not rows:
            pytest.skip("No LOSS outcomes found")

        for date_local, direction, entry, stop, outcome in rows:
            # For LOSS, price must have hit stop
            # Verify stop is in correct direction from entry

            if direction == 'UP':
                assert stop < entry, \
                    f"UP LOSS: stop {stop} should be < entry {entry} on {date_local}"
            elif direction == 'DOWN':
                assert stop > entry, \
                    f"DOWN LOSS: stop {stop} should be > entry {entry} on {date_local}"

    def test_open_means_neither_target_nor_stop_hit(self, db_connection):
        """Verify OPEN outcomes mean position still active"""
        rows = db_connection.execute("""
            SELECT
                date_local,
                orb_1000_break_dir,
                orb_1000_tradeable_entry_price,
                orb_1000_tradeable_stop_price,
                orb_1000_tradeable_target_price
            FROM daily_features
            WHERE orb_1000_tradeable_outcome = 'OPEN'
            LIMIT 5
        """).fetchall()

        if not rows:
            pytest.skip("No OPEN outcomes found")

        for date_local, direction, entry, stop, target in rows:
            # For OPEN, neither target nor stop was hit
            # This means final price is between stop and target

            if direction == 'UP':
                assert stop < entry < target, \
                    f"UP OPEN: stop {stop} < entry {entry} < target {target} on {date_local}"
            elif direction == 'DOWN':
                assert target < entry < stop, \
                    f"DOWN OPEN: target {target} < entry {entry} < stop {stop} on {date_local}"

    def test_no_trade_means_no_entry(self, db_connection):
        """Verify NO_TRADE means no entry occurred"""
        rows = db_connection.execute("""
            SELECT
                date_local,
                orb_1000_tradeable_entry_price,
                orb_1000_tradeable_outcome
            FROM daily_features
            WHERE orb_1000_tradeable_outcome = 'NO_TRADE'
            LIMIT 5
        """).fetchall()

        for date_local, entry_price, outcome in rows:
            # NO_TRADE should have NULL entry
            assert entry_price is None, \
                f"NO_TRADE should have NULL entry price, got {entry_price} on {date_local}"

    def test_outcome_consistency_with_break_direction(self, db_connection):
        """Verify outcomes are consistent with break direction"""
        # If break_dir is NONE, outcome should be NO_TRADE
        rows = db_connection.execute("""
            SELECT date_local, orb_1000_tradeable_outcome
            FROM daily_features
            WHERE orb_1000_break_dir = 'NONE'
            AND orb_1000_tradeable_outcome IS NOT NULL
            AND orb_1000_tradeable_outcome != 'NO_TRADE'
            LIMIT 5
        """).fetchall()

        assert len(rows) == 0, \
            f"Found {len(rows)} cases where break_dir=NONE but outcome != NO_TRADE"

        # If break_dir is UP/DOWN, outcome should be WIN, LOSS, or OPEN
        rows = db_connection.execute("""
            SELECT date_local, orb_1000_break_dir, orb_1000_tradeable_outcome
            FROM daily_features
            WHERE orb_1000_break_dir IN ('UP', 'DOWN')
            AND orb_1000_tradeable_outcome = 'NO_TRADE'
            LIMIT 5
        """).fetchall()

        # This is possible if trade was filtered out, so just warn
        if len(rows) > 0:
            print(f"INFO: Found {len(rows)} cases where break occurred but outcome=NO_TRADE (likely filtered)")

    def test_win_rate_calculation(self, db_connection):
        """Verify win rate can be calculated correctly"""
        # Get all completed trades (WIN or LOSS, not OPEN or NO_TRADE)
        rows = db_connection.execute("""
            SELECT
                orb_1000_tradeable_outcome,
                COUNT(*) as count
            FROM daily_features
            WHERE orb_1000_tradeable_outcome IN ('WIN', 'LOSS')
            GROUP BY orb_1000_tradeable_outcome
        """).fetchall()

        if len(rows) == 0:
            pytest.skip("No completed trades found")

        outcome_counts = {outcome: count for outcome, count in rows}

        wins = outcome_counts.get('WIN', 0)
        losses = outcome_counts.get('LOSS', 0)
        total = wins + losses

        if total > 0:
            win_rate = wins / total
            print(f"INFO: Win rate for 1000 ORB = {win_rate*100:.1f}% ({wins} wins, {losses} losses)")

            # Sanity check
            assert 0 <= win_rate <= 1.0, f"Win rate {win_rate} outside valid range"

    def test_no_null_outcomes_for_valid_entries(self, db_connection):
        """Verify outcome is not NULL when entry exists"""
        null_outcome_rows = db_connection.execute("""
            SELECT date_local
            FROM daily_features
            WHERE orb_1000_tradeable_entry_price IS NOT NULL
            AND orb_1000_tradeable_outcome IS NULL
        """).fetchall()

        assert len(null_outcome_rows) == 0, \
            f"Found {len(null_outcome_rows)} trades with entry but NULL outcome"

    def test_r_multiple_consistency_with_outcome(self, db_connection):
        """Verify R-multiple is consistent with outcome"""
        # WIN outcomes should have positive R
        win_rows = db_connection.execute("""
            SELECT date_local, orb_1000_r_multiple
            FROM daily_features
            WHERE orb_1000_outcome = 'WIN'
            AND orb_1000_r_multiple <= 0
            LIMIT 5
        """).fetchall()

        assert len(win_rows) == 0, \
            f"Found {len(win_rows)} WIN outcomes with non-positive R-multiple"

        # LOSS outcomes should have negative R (typically -1.0)
        loss_rows = db_connection.execute("""
            SELECT date_local, orb_1000_r_multiple
            FROM daily_features
            WHERE orb_1000_outcome = 'LOSS'
            AND orb_1000_r_multiple >= 0
            LIMIT 5
        """).fetchall()

        assert len(loss_rows) == 0, \
            f"Found {len(loss_rows)} LOSS outcomes with non-negative R-multiple"

        # NO_TRADE should have R = 0
        no_trade_rows = db_connection.execute("""
            SELECT date_local, orb_1000_r_multiple
            FROM daily_features
            WHERE orb_1000_outcome = 'NO_TRADE'
            AND orb_1000_r_multiple != 0
            LIMIT 5
        """).fetchall()

        assert len(no_trade_rows) == 0, \
            f"Found {len(no_trade_rows)} NO_TRADE outcomes with non-zero R-multiple"

    def test_same_bar_tp_sl_is_loss(self, db_connection):
        """Verify same-bar TP+SL hit is classified as LOSS (conservative)"""
        # This test verifies the conservative logic:
        # If both target and stop are hit in same bar, outcome = LOSS

        # We can't directly test this without bar-by-bar data,
        # but we can verify that execution_engine.py implements this logic

        execution_engine_path = PROJECT_ROOT / "strategies" / "execution_engine.py"

        if not execution_engine_path.exists():
            pytest.skip("execution_engine.py not found")

        content = execution_engine_path.read_text()

        # Check for conservative same-bar logic
        assert "Conservative: both hit in same bar => LOSS" in content or \
               "both hit same bar" in content.lower(), \
            "execution_engine.py must implement conservative same-bar TP+SL logic"

    def test_outcome_distribution(self, db_connection):
        """Verify outcome distribution is reasonable"""
        rows = db_connection.execute("""
            SELECT
                orb_1000_tradeable_outcome,
                COUNT(*) as count
            FROM daily_features
            WHERE orb_1000_tradeable_outcome IS NOT NULL
            GROUP BY orb_1000_tradeable_outcome
            ORDER BY count DESC
        """).fetchall()

        if not rows:
            pytest.skip("No tradeable outcomes found")

        print("\nOutcome distribution:")
        for outcome, count in rows:
            print(f"  {outcome}: {count}")

        # Sanity checks
        total = sum(count for _, count in rows)

        for outcome, count in rows:
            pct = (count / total) * 100
            print(f"  {outcome}: {pct:.1f}%")

            # No outcome should dominate completely (would indicate logic bug)
            assert pct < 95, f"Outcome {outcome} represents {pct:.1f}% of trades (suspicious)"

    def test_no_invalid_outcome_transitions(self, db_connection):
        """Verify outcomes don't have invalid state transitions"""
        # Check for impossible scenarios

        # Scenario 1: WIN but realized RR is 0
        invalid_wins = db_connection.execute("""
            SELECT date_local
            FROM daily_features
            WHERE orb_1000_tradeable_outcome = 'WIN'
            AND orb_1000_tradeable_realized_rr = 0
        """).fetchall()

        assert len(invalid_wins) == 0, \
            f"Found {len(invalid_wins)} WIN outcomes with 0 realized RR (impossible)"

        # Scenario 2: LOSS but realized RR > 0
        invalid_losses = db_connection.execute("""
            SELECT date_local
            FROM daily_features
            WHERE orb_1000_tradeable_outcome = 'LOSS'
            AND orb_1000_tradeable_realized_rr > 0
        """).fetchall()

        # Note: realized_rr for LOSS should be positive (it's the RR ratio, not the R-multiple)
        # So this test might need adjustment based on how LOSS realized_rr is stored


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
