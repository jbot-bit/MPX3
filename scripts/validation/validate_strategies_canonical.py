"""
CANONICAL STRATEGY VALIDATION

Uses ONLY StrategyDiscovery for backtesting.
NEVER reads outcomes directly from daily_features.

This script exists because validation scripts that bypass StrategyDiscovery
have caused bugs where RR=1.0 outcomes were incorrectly scaled to RR=4.0.

Usage:
    python scripts/validation/validate_strategies_canonical.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from trading_app.strategy_discovery import StrategyDiscovery, DiscoveryConfig


def validate_strategy(discovery: StrategyDiscovery, config: DiscoveryConfig, name: str = "") -> dict:
    """
    Validate a strategy using the CANONICAL StrategyDiscovery pipeline.

    This is the ONLY correct way to backtest strategies.
    DO NOT use direct SQL queries on daily_features for backtesting.
    """
    print(f"\n{'='*60}")
    print(f"VALIDATING: {name or config.orb_time}")
    print(f"{'='*60}")
    print(f"Config:")
    print(f"  Instrument: {config.instrument}")
    print(f"  ORB Time: {config.orb_time}")
    print(f"  RR: {config.rr}")
    print(f"  SL Mode: {config.sl_mode}")
    print(f"  ORB Size Filter: {config.orb_size_filter}")

    result = discovery.backtest_configuration(config)

    print(f"\nResults:")
    print(f"  Expected R: {result.avg_r:+.4f}R")
    print(f"  Win Rate: {result.win_rate:.1f}%")
    print(f"  Wins/Losses: {result.wins}/{result.losses}")
    print(f"  Total Trades: {result.total_trades}")
    print(f"  Total R: {result.total_r:+.2f}R")

    # Verdict
    print(f"\nVerdict:")
    if result.total_trades < 30:
        print(f"  REJECTED - Insufficient sample size (N={result.total_trades})")
        verdict = "REJECTED"
    elif result.avg_r >= 0.15:
        print(f"  TRADEABLE - ExpR >= +0.15R")
        verdict = "TRADEABLE"
    elif result.avg_r >= 0.05:
        print(f"  MARGINAL - ExpR between 0.05-0.15R")
        verdict = "MARGINAL"
    else:
        print(f"  REJECTED - ExpR < +0.05R")
        verdict = "REJECTED"

    return {
        'name': name,
        'config': config,
        'result': result,
        'verdict': verdict
    }


def run_stress_test(discovery: StrategyDiscovery, config: DiscoveryConfig, name: str = "") -> dict:
    """
    Run stress tests at +25% and +50% cost levels.

    NOTE: StrategyDiscovery doesn't have built-in stress test mode,
    so this is informational only. For proper stress testing,
    use the stress_test functionality in strategy_discovery if available.
    """
    print(f"\n{'='*60}")
    print(f"STRESS TEST: {name or config.orb_time}")
    print(f"{'='*60}")

    baseline = discovery.backtest_configuration(config)

    print(f"\nBaseline ($8.40): ExpR {baseline.avg_r:+.4f}R")

    # Note: Cannot easily run stress tests without modifying cost model
    # This would need to be done through the BacktestResult.survives_stress field
    if hasattr(baseline, 'survives_stress') and baseline.survives_stress is not None:
        print(f"Survives Stress: {baseline.survives_stress}")
    else:
        print(f"Stress test: Not available in current result")

    return {'baseline': baseline}


def main():
    print("\n" + "#" * 70)
    print("# CANONICAL STRATEGY VALIDATION")
    print("# Using StrategyDiscovery only - no SQL shortcuts!")
    print("#" * 70)

    discovery = StrategyDiscovery()

    # Strategies to validate
    strategies = [
        # 0900 ORB strategies
        DiscoveryConfig(
            instrument='MGC',
            orb_time='0900',
            rr=4.0,
            sl_mode='HALF',
            orb_size_filter=None
        ),
        DiscoveryConfig(
            instrument='MGC',
            orb_time='0900',
            rr=4.0,
            sl_mode='HALF',
            orb_size_filter=0.18
        ),
        # 1000 ORB strategies
        DiscoveryConfig(
            instrument='MGC',
            orb_time='1000',
            rr=4.0,
            sl_mode='HALF',
            orb_size_filter=None
        ),
        DiscoveryConfig(
            instrument='MGC',
            orb_time='1000',
            rr=4.0,
            sl_mode='HALF',
            orb_size_filter=0.14
        ),
    ]

    names = [
        "0900 Baseline",
        "0900 with ORB filter 0.18",
        "1000 Baseline",
        "1000 with ORB filter 0.14 (Optuna best)",
    ]

    results = []
    for config, name in zip(strategies, names):
        result = validate_strategy(discovery, config, name)
        results.append(result)

    # Summary
    print("\n\n" + "#" * 70)
    print("# SUMMARY")
    print("#" * 70)

    tradeable = [r for r in results if r['verdict'] == 'TRADEABLE']
    marginal = [r for r in results if r['verdict'] == 'MARGINAL']
    rejected = [r for r in results if r['verdict'] == 'REJECTED']

    print(f"\nTRADEABLE ({len(tradeable)}):")
    for r in tradeable:
        print(f"  - {r['name']}: {r['result'].avg_r:+.4f}R")

    print(f"\nMARGINAL ({len(marginal)}):")
    for r in marginal:
        print(f"  - {r['name']}: {r['result'].avg_r:+.4f}R")

    print(f"\nREJECTED ({len(rejected)}):")
    for r in rejected:
        print(f"  - {r['name']}: {r['result'].avg_r:+.4f}R")

    print("\n" + "#" * 70)
    print("# IMPORTANT NOTES")
    print("#" * 70)
    print("""
1. These results use the CANONICAL StrategyDiscovery pipeline.
2. RR is correctly simulated (price must actually hit RR target).
3. Costs are correctly applied ($8.40 RT friction).
4. Do NOT trust any validation that bypasses StrategyDiscovery!

For advanced filters (RSI, travel, asia range):
- These require extending StrategyDiscovery to support them
- OR using execution_engine with date-filtered data
- Never just query daily_features outcomes directly!
""")


if __name__ == "__main__":
    main()
