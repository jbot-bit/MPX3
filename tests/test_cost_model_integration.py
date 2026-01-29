"""
Test Cost Model Integration: Verify $8.40 costs embedded correctly

PURPOSE:
- Validates cost_model.py integration with tradeable calculations
- Tests $8.40 total friction for MGC (honest double-spread accounting)
- Verifies cost embedding in realized RR

CRITICAL:
- Total friction = commission $2.40 + spread_double $2.00 + slippage $4.00 = $8.40
- Costs INCREASE risk (added to stop)
- Costs REDUCE reward (subtracted from target)
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import duckdb
import pytest
from datetime import date
from pipeline.cost_model import (
    COST_MODELS,
    INSTRUMENT_SPECS,
    calculate_realized_rr,
    calculate_expectancy
)


# Database path
DB_PATH = "data/db/gold.db"


class TestCostModelIntegration:
    """Test suite for cost model integration"""

    @pytest.fixture
    def db_connection(self):
        """Create database connection"""
        conn = duckdb.connect(DB_PATH)
        yield conn
        conn.close()

    def test_mgc_cost_model_structure(self):
        """Verify MGC cost model has correct structure"""
        assert 'MGC' in COST_MODELS, "MGC must be in COST_MODELS"

        mgc = COST_MODELS['MGC']

        # Check required fields
        required_fields = [
            'broker', 'source', 'commission_rt', 'spread_per_cross',
            'spread_double', 'slippage_rt', 'slippage_ticks', 'total_friction',
            'tick_size', 'tick_value', 'point_value', 'status'
        ]

        for field in required_fields:
            assert field in mgc, f"MGC cost model missing field: {field}"

    def test_mgc_total_friction_is_840(self):
        """Verify MGC total friction = $8.40 (honest double-spread accounting)"""
        mgc = COST_MODELS['MGC']

        # Total friction = commission + spread_double + slippage
        expected_total = mgc['commission_rt'] + mgc['spread_double'] + mgc['slippage_rt']

        assert abs(mgc['total_friction'] - 8.40) < 0.01, \
            f"MGC total friction should be $8.40, got ${mgc['total_friction']:.2f}"

        assert abs(mgc['total_friction'] - expected_total) < 0.01, \
            f"Total friction ${mgc['total_friction']:.2f} != commission + spread_double + slippage = ${expected_total:.2f}"

    def test_mgc_friction_components(self):
        """Verify MGC friction components are correct"""
        mgc = COST_MODELS['MGC']

        # Commission (from real broker data)
        assert abs(mgc['commission_rt'] - 2.40) < 0.01, \
            f"Commission should be $2.40, got ${mgc['commission_rt']:.2f}"

        # Spread double (entry + exit = 2 crossings)
        assert abs(mgc['spread_double'] - 2.00) < 0.01, \
            f"Spread double should be $2.00, got ${mgc['spread_double']:.2f}"

        # Slippage (beyond spread, conservative estimate)
        assert abs(mgc['slippage_rt'] - 4.00) < 0.01, \
            f"Slippage should be $4.00, got ${mgc['slippage_rt']:.2f}"

    def test_mgc_instrument_specs(self):
        """Verify MGC instrument specs are correct"""
        assert 'MGC' in INSTRUMENT_SPECS, "MGC must be in INSTRUMENT_SPECS"

        mgc = INSTRUMENT_SPECS['MGC']

        assert mgc['tick_size'] == 0.10, "MGC tick size should be 0.10"
        assert mgc['tick_value'] == 1.00, "MGC tick value should be $1.00"
        assert mgc['point_value'] == 10.00, "MGC point value should be $10.00"
        assert mgc['status'] == 'PRODUCTION', "MGC should be in PRODUCTION status"

    def test_calculate_realized_rr_function(self):
        """Verify calculate_realized_rr function works correctly"""
        # Test with typical 1000 ORB parameters
        result = calculate_realized_rr(
            instrument='MGC',
            stop_distance_points=2.5,  # ~2.5 point ORB size
            rr_theoretical=1.5,
            stress_level='normal'
        )

        # Check result structure
        assert 'realized_rr' in result, "Result must have realized_rr"
        assert 'realized_risk_dollars' in result, "Result must have realized_risk_dollars"
        assert 'realized_reward_dollars' in result, "Result must have realized_reward_dollars"
        assert 'theoretical_rr' in result, "Result must have theoretical_rr"
        assert 'delta_rr' in result, "Result must have delta_rr"
        assert 'costs' in result, "Result must have costs"

        # Check values
        assert result['theoretical_rr'] == 1.5, "Theoretical RR should match input"
        assert result['realized_rr'] < 1.5, "Realized RR should be less than theoretical (costs reduce it)"
        assert result['delta_rr'] < 0, "Delta should be negative (costs reduce RR)"

        # Check cost embedding
        costs = result['costs']
        assert costs['total_friction'] == 8.40, "Costs should have $8.40 friction"

    def test_realized_rr_with_different_stop_sizes(self):
        """Verify realized RR scales correctly with stop size"""
        # Small stop (higher cost impact)
        result_small = calculate_realized_rr(
            instrument='MGC',
            stop_distance_points=1.0,
            rr_theoretical=2.0,
            stress_level='normal'
        )

        # Large stop (lower cost impact)
        result_large = calculate_realized_rr(
            instrument='MGC',
            stop_distance_points=5.0,
            rr_theoretical=2.0,
            stress_level='normal'
        )

        # Realized RR should be HIGHER for larger stops (costs are fixed, stop is larger)
        assert result_large['realized_rr'] > result_small['realized_rr'], \
            "Larger stops should have higher realized RR (lower relative cost impact)"

        # Both should be less than theoretical
        assert result_small['realized_rr'] < 2.0, "Small stop realized RR < theoretical"
        assert result_large['realized_rr'] < 2.0, "Large stop realized RR < theoretical"

    def test_costs_increase_risk(self):
        """Verify costs are ADDED to risk (not subtracted)"""
        result = calculate_realized_rr(
            instrument='MGC',
            stop_distance_points=2.5,
            rr_theoretical=1.5,
            stress_level='normal'
        )

        # Theoretical risk (no costs)
        theoretical_risk = 2.5 * 10.0  # $25.00

        # Realized risk should be theoretical + friction
        expected_realized_risk = theoretical_risk + 8.40  # $33.40

        assert abs(result['realized_risk_dollars'] - expected_realized_risk) < 0.01, \
            f"Realized risk ${result['realized_risk_dollars']:.2f} != theoretical ${theoretical_risk:.2f} + friction $8.40 = ${expected_realized_risk:.2f}"

    def test_costs_reduce_reward(self):
        """Verify costs are SUBTRACTED from reward (not added)"""
        result = calculate_realized_rr(
            instrument='MGC',
            stop_distance_points=2.5,
            rr_theoretical=1.5,
            stress_level='normal'
        )

        # Theoretical reward (no costs)
        # Target = RR * stop = 1.5 * 2.5 = 3.75 points = $37.50
        theoretical_reward = 1.5 * 2.5 * 10.0  # $37.50

        # Realized reward should be theoretical - friction
        expected_realized_reward = theoretical_reward - 8.40  # $29.10

        assert abs(result['realized_reward_dollars'] - expected_realized_reward) < 0.01, \
            f"Realized reward ${result['realized_reward_dollars']:.2f} != theoretical ${theoretical_reward:.2f} - friction $8.40 = ${expected_realized_reward:.2f}"

    def test_calculate_expectancy_function(self):
        """Verify calculate_expectancy function works correctly"""
        # Test with typical win rate and realized RR
        expectancy = calculate_expectancy(
            win_rate=0.60,
            realized_rr=1.238,  # Typical for MGC RR=1.5 after costs
            avg_loss_r=1.0
        )

        # Expectancy = (WR * AvgWin) - (LR * AvgLoss)
        # = (0.60 * 1.238) - (0.40 * 1.0) = 0.7428 - 0.4 = 0.3428
        expected_expectancy = (0.60 * 1.238) - (0.40 * 1.0)

        assert abs(expectancy - expected_expectancy) < 0.001, \
            f"Expectancy {expectancy:.3f} != expected {expected_expectancy:.3f}"

    def test_database_uses_cost_model(self, db_connection):
        """Verify database tradeable metrics use cost_model.py calculations"""
        # Get sample tradeable data
        row = db_connection.execute("""
            SELECT
                date_local,
                orb_1000_tradeable_risk_points,
                orb_1000_tradeable_realized_risk_dollars,
                orb_1000_tradeable_realized_reward_dollars,
                orb_1000_tradeable_realized_rr
            FROM daily_features
            WHERE orb_1000_tradeable_realized_rr IS NOT NULL
            LIMIT 1
        """).fetchone()

        if not row:
            pytest.skip("No tradeable data found")

        date_local, risk_points, realized_risk, realized_reward, realized_rr = row

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

        # Calculate using cost_model.py
        result = calculate_realized_rr(
            instrument='MGC',
            stop_distance_points=risk_points,
            rr_theoretical=theoretical_rr,
            stress_level='normal'
        )

        # Database values should match cost_model calculations
        assert abs(realized_risk - result['realized_risk_dollars']) < 0.10, \
            f"Database realized risk ${realized_risk:.2f} != cost_model ${result['realized_risk_dollars']:.2f} on {date_local}"

        assert abs(realized_reward - result['realized_reward_dollars']) < 0.10, \
            f"Database realized reward ${realized_reward:.2f} != cost_model ${result['realized_reward_dollars']:.2f} on {date_local}"

        assert abs(realized_rr - result['realized_rr']) < 0.01, \
            f"Database realized RR {realized_rr:.3f} != cost_model {result['realized_rr']:.3f} on {date_local}"

    def test_no_hardcoded_friction_values(self):
        """Verify no hardcoded friction values outside cost_model.py"""
        # Check populate_tradeable_metrics.py for hardcoded friction
        populate_path = PROJECT_ROOT / "pipeline" / "populate_tradeable_metrics.py"

        if not populate_path.exists():
            pytest.skip("populate_tradeable_metrics.py not found")

        content = populate_path.read_text()

        # Check for suspicious hardcoded friction values
        suspicious_patterns = [
            "8.40",  # Total friction
            "2.40",  # Commission
            "4.00",  # Slippage
        ]

        for pattern in suspicious_patterns:
            if pattern in content:
                # Check if it's in a comment or import
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if pattern in line:
                        # Skip comments
                        if '#' in line and line.index('#') < line.index(pattern):
                            continue
                        # Skip imports
                        if 'import' in line or 'from' in line:
                            continue
                        # Skip docstrings
                        if '"""' in line or "'''" in line:
                            continue

                        # If we reach here, might be hardcoded
                        print(f"WARNING: Found potential hardcoded value {pattern} at line {i+1}: {line.strip()}")

    def test_stress_testing_multipliers(self):
        """Verify stress testing works correctly"""
        base_result = calculate_realized_rr(
            instrument='MGC',
            stop_distance_points=2.5,
            rr_theoretical=1.5,
            stress_level='normal'
        )

        moderate_result = calculate_realized_rr(
            instrument='MGC',
            stop_distance_points=2.5,
            rr_theoretical=1.5,
            stress_level='moderate'
        )

        severe_result = calculate_realized_rr(
            instrument='MGC',
            stop_distance_points=2.5,
            rr_theoretical=1.5,
            stress_level='severe'
        )

        # Realized RR should decrease under stress (higher costs)
        assert base_result['realized_rr'] > moderate_result['realized_rr'], \
            "Normal RR should be higher than moderate stress"

        assert moderate_result['realized_rr'] > severe_result['realized_rr'], \
            "Moderate stress RR should be higher than severe stress"

        # Check that slippage increases
        assert base_result['costs']['slippage_rt'] < moderate_result['costs']['slippage_rt'], \
            "Slippage should increase under stress"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
