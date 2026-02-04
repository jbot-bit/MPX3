"""
TEST: R-Multiple Calculation Integrity

Ensures that any validation/backtest correctly handles different RR values.
Prevents bugs where RR=1.0 outcomes are incorrectly scaled to RR=4.0.

This test exists because of a bug found on 2026-02-04 where validation scripts
read WIN/LOSS from daily_features (at RR=1.0) and incorrectly applied RR=4.0
R-multiples, inflating Expected R from +0.08R to +0.55R.

Run with: python -m pytest tests/test_rr_calculation_integrity.py -v
"""

import sys
from pathlib import Path
from pipeline.paths import GOLD_DB_PATH

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
import duckdb

DB_PATH = PROJECT_ROOT / "data" / "db" / GOLD_DB_PATH


class TestRRIntegrity:
    """Tests to prevent R-multiple calculation bugs"""

    def test_daily_features_uses_rr_1(self):
        """
        Verify that daily_features outcomes are calculated at RR=1.0.

        This is a CRITICAL assumption. If someone changes it, tests will fail
        and prevent bugs in downstream validation scripts.
        """
        conn = duckdb.connect(str(DB_PATH), read_only=True)

        try:
            # Get average WIN r_multiple
            result = conn.execute("""
                SELECT AVG(orb_0900_r_multiple) as avg_win_r
                FROM daily_features
                WHERE orb_0900_outcome = 'WIN'
                LIMIT 1
            """).fetchone()

            avg_win_r = result[0]

            # WIN at RR=1.0 should have r_mult close to +1.0
            assert avg_win_r is not None, "No WIN trades found"
            assert 0.9 <= avg_win_r <= 1.1, (
                f"daily_features WIN r_multiple = {avg_win_r:.4f}, expected ~1.0. "
                f"If this changed, ALL validation scripts may be broken!"
            )

            # Get average LOSS r_multiple
            result = conn.execute("""
                SELECT AVG(orb_0900_r_multiple) as avg_loss_r
                FROM daily_features
                WHERE orb_0900_outcome = 'LOSS'
                LIMIT 1
            """).fetchone()

            avg_loss_r = result[0]

            # LOSS should have r_mult close to -1.0
            assert avg_loss_r is not None, "No LOSS trades found"
            assert -1.1 <= avg_loss_r <= -0.9, (
                f"daily_features LOSS r_multiple = {avg_loss_r:.4f}, expected ~-1.0. "
                f"If this changed, ALL validation scripts may be broken!"
            )

        finally:
            conn.close()

    def test_strategy_discovery_respects_rr(self):
        """
        Verify that StrategyDiscovery correctly calculates at specified RR.

        At RR=1.0, win rate should be higher than at RR=4.0
        (easier to hit 1R target than 4R target).
        """
        from trading_app.strategy_discovery import StrategyDiscovery, DiscoveryConfig

        discovery = StrategyDiscovery()

        # Test at RR=1.0
        config_rr1 = DiscoveryConfig(
            instrument='MGC',
            orb_time='0900',
            rr=1.0,
            sl_mode='FULL',
            orb_size_filter=None
        )
        result_rr1 = discovery.backtest_configuration(config_rr1)

        # Test at RR=4.0
        config_rr4 = DiscoveryConfig(
            instrument='MGC',
            orb_time='0900',
            rr=4.0,
            sl_mode='FULL',
            orb_size_filter=None
        )
        result_rr4 = discovery.backtest_configuration(config_rr4)

        # Win rate at RR=4.0 should be LOWER than at RR=1.0
        # (harder to hit 4R target than 1R target)
        assert result_rr4.win_rate < result_rr1.win_rate, (
            f"Win rate at RR=4.0 ({result_rr4.win_rate:.1f}%) should be lower than "
            f"at RR=1.0 ({result_rr1.win_rate:.1f}%). "
            f"This suggests RR is not being respected in simulation!"
        )

        # Sanity check: RR=4.0 should have much lower win rate
        # (typically 20-30% vs 50-60% for RR=1.0)
        assert result_rr4.win_rate < 40, (
            f"Win rate at RR=4.0 is {result_rr4.win_rate:.1f}%, expected <40%. "
            f"Something may be wrong with RR calculation."
        )

    def test_cannot_directly_use_daily_features_for_high_rr(self):
        """
        This test documents that you CANNOT use daily_features outcomes
        directly for RR > 1.0 without re-simulation.

        If you query daily_features outcomes and multiply by RR, you get WRONG answers.
        """
        conn = duckdb.connect(str(DB_PATH), read_only=True)

        try:
            # The WRONG way (what the buggy scripts did)
            result = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN orb_0900_outcome = 'WIN' THEN 1 ELSE 0 END) as wins
                FROM daily_features
                WHERE orb_0900_outcome IN ('WIN', 'LOSS')
            """).fetchone()

            total = result[0]
            wins = result[1]
            win_rate = wins / total

            # The WRONG calculation: multiply wins by RR=4.0
            rr = 4.0
            wrong_expected_r = (win_rate * rr) + ((1 - win_rate) * -1.0)

            # This gives inflated numbers!
            # Real Expected R at RR=4.0 is around +0.08R
            # Wrong calculation gives ~+0.55R

            assert wrong_expected_r > 0.4, (
                f"If this test fails, someone fixed the inflation bug? "
                f"Wrong calc gives {wrong_expected_r:.4f}R, expected >0.4R (inflated)"
            )

            # Document that this is WRONG
            # The correct way is to use StrategyDiscovery
            from trading_app.strategy_discovery import StrategyDiscovery, DiscoveryConfig
            discovery = StrategyDiscovery()

            config = DiscoveryConfig(
                instrument='MGC',
                orb_time='0900',
                rr=4.0,
                sl_mode='HALF',
                orb_size_filter=None
            )
            correct_result = discovery.backtest_configuration(config)

            # Correct result should be much lower
            assert correct_result.avg_r < 0.2, (
                f"StrategyDiscovery gives {correct_result.avg_r:.4f}R, expected <0.2R"
            )

            # Prove the wrong way is inflated
            assert wrong_expected_r > correct_result.avg_r * 2, (
                f"Wrong calculation ({wrong_expected_r:.4f}R) should be >2x higher than "
                f"correct calculation ({correct_result.avg_r:.4f}R)"
            )

        finally:
            conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
