"""
Test Tradeable Calculations: Verify B-entry model formulas

PURPOSE:
- Validates risk/reward calculations using B-entry model
- Tests target price calculations with RR
- Verifies realized RR formulas from cost_model.py

CRITICAL:
- Risk = abs(entry - stop) NOT ORB size
- Target = entry +/- RR * risk
- Realized RR uses CANONICAL formulas (CANONICAL_LOGIC.txt lines 76-98)
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


class TestTradeableCalculations:
    """Test suite for tradeable calculations (B-entry model)"""

    @pytest.fixture
    def db_connection(self):
        """Create database connection"""
        conn = duckdb.connect(DB_PATH)
        yield conn
        conn.close()

    def test_risk_equals_entry_minus_stop(self, db_connection):
        """Verify risk = abs(entry - stop) for all trades"""
        rows = db_connection.execute("""
            SELECT
                date_local,
                orb_1000_tradeable_entry_price,
                orb_1000_tradeable_stop_price,
                orb_1000_tradeable_risk_points
            FROM daily_features
            WHERE orb_1000_tradeable_entry_price IS NOT NULL
            AND orb_1000_tradeable_risk_points IS NOT NULL
            LIMIT 50
        """).fetchall()

        if not rows:
            pytest.skip("No tradeable data found")

        for date_local, entry, stop, risk_points in rows:
            expected_risk = abs(entry - stop)

            # Allow 0.01 tolerance for floating point
            assert abs(risk_points - expected_risk) < 0.01, \
                f"Risk {risk_points} != abs(entry {entry} - stop {stop}) = {expected_risk} on {date_local}"

    def test_target_equals_entry_plus_rr_times_risk(self, db_connection):
        """Verify target = entry +/- RR * risk"""
        # Get RR from validated_setups
        rr_row = db_connection.execute("""
            SELECT rr
            FROM validated_setups
            WHERE instrument = 'MGC' AND orb_time = '1000'
            LIMIT 1
        """).fetchone()

        if not rr_row:
            pytest.skip("No 1000 ORB strategy in validated_setups")

        expected_rr = rr_row[0]

        # Get tradeable data
        rows = db_connection.execute("""
            SELECT
                date_local,
                orb_1000_break_dir,
                orb_1000_tradeable_entry_price,
                orb_1000_tradeable_risk_points,
                orb_1000_tradeable_target_price
            FROM daily_features
            WHERE orb_1000_tradeable_entry_price IS NOT NULL
            AND orb_1000_tradeable_target_price IS NOT NULL
            AND orb_1000_break_dir != 'NONE'
            LIMIT 20
        """).fetchall()

        if not rows:
            pytest.skip("No tradeable data with targets")

        for date_local, direction, entry, risk, target in rows:
            if direction == 'UP':
                expected_target = entry + (expected_rr * risk)
            elif direction == 'DOWN':
                expected_target = entry - (expected_rr * risk)
            else:
                continue

            # Allow 20% tolerance for cost adjustments in realized_rr
            tolerance = 0.20
            target_distance = abs(target - entry)
            expected_distance = expected_rr * risk

            assert abs(target_distance - expected_distance) / expected_distance < tolerance, \
                f"Target distance {target_distance:.2f} != RR {expected_rr} * risk {risk:.2f} = {expected_distance:.2f} on {date_local}"

    def test_realized_rr_columns_exist(self, db_connection):
        """Verify realized RR columns exist for all ORBs"""
        for orb in ['0900', '1000', '1100', '1800', '2300', '0030']:
            col_name = f'orb_{orb}_tradeable_realized_rr'

            cols = db_connection.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'daily_features'
                AND column_name = '{col_name}'
            """).fetchall()

            assert len(cols) == 1, f"Missing column: {col_name}"

    def test_realized_rr_less_than_theoretical(self, db_connection):
        """Verify realized RR < theoretical RR (due to costs)"""
        # Get theoretical RR from validated_setups
        rr_row = db_connection.execute("""
            SELECT rr
            FROM validated_setups
            WHERE instrument = 'MGC' AND orb_time = '1000'
            LIMIT 1
        """).fetchone()

        if not rr_row:
            pytest.skip("No 1000 ORB strategy in validated_setups")

        theoretical_rr = rr_row[0]

        # Get realized RR from daily_features
        rows = db_connection.execute("""
            SELECT
                date_local,
                orb_1000_tradeable_realized_rr
            FROM daily_features
            WHERE orb_1000_tradeable_realized_rr IS NOT NULL
            LIMIT 50
        """).fetchall()

        if not rows:
            pytest.skip("No realized RR data found")

        for date_local, realized_rr in rows:
            # Realized RR should be less than theoretical (costs reduce it)
            assert realized_rr < theoretical_rr, \
                f"Realized RR {realized_rr:.3f} >= theoretical RR {theoretical_rr} on {date_local} (costs not embedded)"

    def test_realized_risk_dollars_calculation(self, db_connection):
        """Verify realized risk = (stop distance * $10) + friction"""
        # Get cost model parameters
        from pipeline.cost_model import COST_MODELS

        mgc_costs = COST_MODELS['MGC']
        total_friction = mgc_costs['total_friction']  # $8.40 for MGC
        point_value = mgc_costs['point_value']  # $10 per point

        # Get data
        rows = db_connection.execute("""
            SELECT
                date_local,
                orb_1000_tradeable_risk_points,
                orb_1000_tradeable_realized_risk_dollars
            FROM daily_features
            WHERE orb_1000_tradeable_risk_points IS NOT NULL
            AND orb_1000_tradeable_realized_risk_dollars IS NOT NULL
            LIMIT 20
        """).fetchall()

        if not rows:
            pytest.skip("No realized risk data found")

        for date_local, risk_points, realized_risk_dollars in rows:
            # CANONICAL: Realized_Risk_$ = (stop_points × PointValue) + TotalFriction
            expected_risk_dollars = (risk_points * point_value) + total_friction

            # Allow 0.10 tolerance
            assert abs(realized_risk_dollars - expected_risk_dollars) < 0.10, \
                f"Realized risk ${realized_risk_dollars:.2f} != (risk {risk_points:.2f} * $10) + ${total_friction:.2f} = ${expected_risk_dollars:.2f} on {date_local}"

    def test_realized_reward_dollars_calculation(self, db_connection):
        """Verify realized reward = (target distance * $10) - friction"""
        # Get cost model parameters
        from pipeline.cost_model import COST_MODELS

        mgc_costs = COST_MODELS['MGC']
        total_friction = mgc_costs['total_friction']  # $8.40
        point_value = mgc_costs['point_value']  # $10

        # Get RR from validated_setups
        rr_row = db_connection.execute("""
            SELECT rr
            FROM validated_setups
            WHERE instrument = 'MGC' AND orb_time = '1000'
            LIMIT 1
        """).fetchone()

        if not rr_row:
            pytest.skip("No 1000 ORB strategy")

        theoretical_rr = rr_row[0]

        # Get data
        rows = db_connection.execute("""
            SELECT
                date_local,
                orb_1000_tradeable_risk_points,
                orb_1000_tradeable_realized_reward_dollars
            FROM daily_features
            WHERE orb_1000_tradeable_risk_points IS NOT NULL
            AND orb_1000_tradeable_realized_reward_dollars IS NOT NULL
            LIMIT 20
        """).fetchall()

        if not rows:
            pytest.skip("No realized reward data found")

        for date_local, risk_points, realized_reward_dollars in rows:
            # CANONICAL: Realized_Reward_$ = (target_points × PointValue) - TotalFriction
            # Target_points = RR × risk_points
            target_points = theoretical_rr * risk_points
            expected_reward_dollars = (target_points * point_value) - total_friction

            # Allow 0.10 tolerance
            assert abs(realized_reward_dollars - expected_reward_dollars) < 0.10, \
                f"Realized reward ${realized_reward_dollars:.2f} != (target {target_points:.2f} * $10) - ${total_friction:.2f} = ${expected_reward_dollars:.2f} on {date_local}"

    def test_realized_rr_formula(self, db_connection):
        """Verify realized_rr = realized_reward / realized_risk"""
        rows = db_connection.execute("""
            SELECT
                date_local,
                orb_1000_tradeable_realized_rr,
                orb_1000_tradeable_realized_risk_dollars,
                orb_1000_tradeable_realized_reward_dollars
            FROM daily_features
            WHERE orb_1000_tradeable_realized_rr IS NOT NULL
            AND orb_1000_tradeable_realized_risk_dollars IS NOT NULL
            AND orb_1000_tradeable_realized_reward_dollars IS NOT NULL
            LIMIT 20
        """).fetchall()

        if not rows:
            pytest.skip("No complete realized RR data found")

        for date_local, realized_rr, realized_risk, realized_reward in rows:
            # CANONICAL: Realized_RR = Realized_Reward_$ / Realized_Risk_$
            expected_realized_rr = realized_reward / realized_risk

            # Allow 0.001 tolerance
            assert abs(realized_rr - expected_realized_rr) < 0.001, \
                f"Realized RR {realized_rr:.3f} != reward ${realized_reward:.2f} / risk ${realized_risk:.2f} = {expected_realized_rr:.3f} on {date_local}"

    def test_stop_placement_full_vs_half(self, db_connection):
        """Verify stop placement logic (full vs half mode)"""
        # Get strategies with different sl_modes
        strategies = db_connection.execute("""
            SELECT orb_time, sl_mode
            FROM validated_setups
            WHERE instrument = 'MGC'
        """).fetchall()

        for orb_time, sl_mode in strategies:
            orb_code = orb_time.replace(':', '')

            # Get sample trade
            row = db_connection.execute(f"""
                SELECT
                    date_local,
                    orb_{orb_code}_break_dir,
                    orb_{orb_code}_high,
                    orb_{orb_code}_low,
                    orb_{orb_code}_tradeable_stop_price
                FROM daily_features
                WHERE orb_{orb_code}_tradeable_stop_price IS NOT NULL
                AND orb_{orb_code}_break_dir != 'NONE'
                LIMIT 1
            """).fetchone()

            if not row:
                continue

            date_local, direction, orb_high, orb_low, stop_price = row

            if sl_mode.lower() == 'full':
                # Full stop: opposite ORB edge
                if direction == 'UP':
                    expected_stop = orb_low
                elif direction == 'DOWN':
                    expected_stop = orb_high
                else:
                    continue

                assert abs(stop_price - expected_stop) < 0.01, \
                    f"Full stop {stop_price} != opposite ORB edge {expected_stop} on {date_local} for ORB {orb_time}"

            elif sl_mode.lower() == 'half':
                # Half stop: ORB midpoint (clamped to edge)
                orb_mid = (orb_high + orb_low) / 2.0

                if direction == 'UP':
                    expected_stop = max(orb_low, orb_mid)
                elif direction == 'DOWN':
                    expected_stop = min(orb_high, orb_mid)
                else:
                    continue

                assert abs(stop_price - expected_stop) < 0.01, \
                    f"Half stop {stop_price} != midpoint {expected_stop} on {date_local} for ORB {orb_time}"

    def test_no_null_risk_for_valid_trades(self, db_connection):
        """Verify risk is not NULL when entry and stop exist"""
        null_risk_rows = db_connection.execute("""
            SELECT date_local
            FROM daily_features
            WHERE orb_1000_tradeable_entry_price IS NOT NULL
            AND orb_1000_tradeable_stop_price IS NOT NULL
            AND orb_1000_tradeable_risk_points IS NULL
        """).fetchall()

        assert len(null_risk_rows) == 0, \
            f"Found {len(null_risk_rows)} trades with NULL risk despite having entry/stop"

    def test_risk_is_positive(self, db_connection):
        """Verify all risk values are positive"""
        negative_risk_rows = db_connection.execute("""
            SELECT date_local, orb_1000_tradeable_risk_points
            FROM daily_features
            WHERE orb_1000_tradeable_risk_points < 0
        """).fetchall()

        assert len(negative_risk_rows) == 0, \
            f"Found {len(negative_risk_rows)} trades with negative risk (data corruption)"

    def test_realized_risk_greater_than_theoretical(self, db_connection):
        """Verify realized risk $ > theoretical risk $ (costs add to risk)"""
        from pipeline.cost_model import COST_MODELS

        point_value = COST_MODELS['MGC']['point_value']

        rows = db_connection.execute("""
            SELECT
                date_local,
                orb_1000_tradeable_risk_points,
                orb_1000_tradeable_realized_risk_dollars
            FROM daily_features
            WHERE orb_1000_tradeable_risk_points IS NOT NULL
            AND orb_1000_tradeable_realized_risk_dollars IS NOT NULL
            LIMIT 20
        """).fetchall()

        if not rows:
            pytest.skip("No realized risk data")

        for date_local, risk_points, realized_risk_dollars in rows:
            theoretical_risk_dollars = risk_points * point_value

            # Realized risk should be greater (costs added)
            assert realized_risk_dollars > theoretical_risk_dollars, \
                f"Realized risk ${realized_risk_dollars:.2f} <= theoretical ${theoretical_risk_dollars:.2f} on {date_local} (costs not added)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
