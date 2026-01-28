"""
Stage 3: Out-of-Sample Verification (Test Data - UNSEEN)

Tests optimized parameters on UNSEEN test data.

CRITICAL: This runs on TEST data (last 20%, NEVER seen before).
Parameters from Stage 2 are tested here WITHOUT modification.

This is the key anti-curve-fitting gate.
"""

import sys
sys.path.append('.')

import duckdb
from typing import Dict, List, Optional
from dataclasses import dataclass

from strategies.execution_engine import simulate_orb_trade
from pipeline.walkforward_config import (
    get_simple_split,
    filter_by_strategy_family,
    THRESHOLDS,
    COST_MODELS
)


@dataclass
class OutOfSampleResult:
    """Stage 3 output"""
    stage: str
    orb_time: str
    instrument: str

    # Test details
    test_dates: List[str]
    test_rr: float
    test_filter: Optional[float]
    test_sl_mode: str

    # Test performance
    test_expr: float
    test_wr: float
    test_sample: int
    test_wins: int
    test_losses: int

    # Comparison to training
    train_expr: float
    degradation: float  # (train - test) / train

    # Verdict
    passed: bool
    verdict: str
    reason: str


def verify_out_of_sample(
    con: duckdb.DuckDBPyConnection,
    orb_time: str,
    optimal_rr: float,
    optimal_filter: Optional[float],
    optimal_sl_mode: str,
    train_expr: float,
    instrument: str = 'MGC',
    use_family_filter: bool = True
) -> OutOfSampleResult:
    """
    Stage 3: Test optimized parameters on UNSEEN test data

    Args:
        con: Database connection
        orb_time: '0900', '1000', etc.
        optimal_rr: Best RR from Stage 2
        optimal_filter: Best filter from Stage 2
        optimal_sl_mode: Best SL mode from Stage 2
        train_expr: Training ExpR from Stage 2 (for degradation calc)
        instrument: 'MGC', 'NQ', 'MPL'
        use_family_filter: Apply strategy family filtering

    Returns:
        OutOfSampleResult with pass/fail verdict

    Process:
        1. Get test dates (last 20% of data, NEVER used before)
        2. Filter by strategy family
        3. Run backtest with optimal parameters (NO changes)
        4. Calculate test ExpR, win rate
        5. Calculate degradation vs training
        6. Check against Stage 3 gates

    Gates:
        - Test ExpR >= +0.15R (profitability)
        - Degradation < 50% (test >= 50% of train)
        - Sample size >= 30 trades

    This is the CRITICAL anti-curve-fitting gate.
    """
    print(f"\n{'='*60}")
    print(f"STAGE 3: OUT-OF-SAMPLE VERIFICATION")
    print(f"{'='*60}")
    print(f"ORB: {orb_time} | Instrument: {instrument}")
    print(f"Testing optimized parameters on UNSEEN test data")
    print(f"{'='*60}\n")

    # Get data splits
    splits = get_simple_split(con, instrument)
    test_dates = splits['test']

    print(f"Test dates: {len(test_dates)} days ({test_dates[0]} to {test_dates[-1]})")
    print(f"CRITICAL: This data was NEVER used for optimization")

    # Apply strategy family filter
    if use_family_filter:
        original_count = len(test_dates)
        test_dates = filter_by_strategy_family(con, test_dates, orb_time, instrument)
        print(f"Strategy family filter: {len(test_dates)} / {original_count} dates pass")

    if len(test_dates) == 0:
        return OutOfSampleResult(
            stage='out_of_sample_verification',
            orb_time=orb_time,
            instrument=instrument,
            test_dates=[],
            test_rr=optimal_rr,
            test_filter=optimal_filter,
            test_sl_mode=optimal_sl_mode,
            test_expr=0.0,
            test_wr=0.0,
            test_sample=0,
            test_wins=0,
            test_losses=0,
            train_expr=train_expr,
            degradation=1.0,
            passed=False,
            verdict='FAIL',
            reason='No test dates pass strategy family filter'
        )

    print(f"\nTesting with OPTIMIZED parameters from Stage 2:")
    print(f"  RR: {optimal_rr}")
    print(f"  Filter: {optimal_filter}")
    print(f"  SL Mode: {optimal_sl_mode}")
    print(f"\nRunning backtest on {len(test_dates)} test dates...")

    # Get cost model
    friction = COST_MODELS[instrument]['base_friction']

    # Run backtest
    results = []
    for date in test_dates:
        try:
            result = simulate_orb_trade(
                con=con,
                date_local=date,
                orb=orb_time,
                mode='1m',
                rr=optimal_rr,
                sl_mode=optimal_sl_mode,
                orb_size_filter=optimal_filter,
                slippage_ticks=1.5,
                commission_per_contract=1.0,
                instrument=instrument
            )

            if result.outcome in ['WIN', 'LOSS']:
                results.append(result)

        except Exception as e:
            print(f"  Error on {date}: {e}")
            continue

    # Calculate metrics
    if len(results) == 0:
        return OutOfSampleResult(
            stage='out_of_sample_verification',
            orb_time=orb_time,
            instrument=instrument,
            test_dates=test_dates,
            test_rr=optimal_rr,
            test_filter=optimal_filter,
            test_sl_mode=optimal_sl_mode,
            test_expr=0.0,
            test_wr=0.0,
            test_sample=0,
            test_wins=0,
            test_losses=0,
            train_expr=train_expr,
            degradation=1.0,
            passed=False,
            verdict='FAIL',
            reason='No valid trades generated on test data'
        )

    test_wins = sum(1 for r in results if r.outcome == 'WIN')
    test_losses = len(results) - test_wins
    test_wr = test_wins / len(results)
    test_expr = sum(r.r_multiple for r in results) / len(results)

    # Calculate degradation
    if train_expr > 0:
        degradation = (train_expr - test_expr) / train_expr
    else:
        degradation = 1.0 if test_expr < 0 else 0.0

    print(f"\n{'='*60}")
    print("OUT-OF-SAMPLE RESULTS")
    print(f"{'='*60}")
    print(f"Test performance:")
    print(f"  Sample:   {len(results)} trades (W:{test_wins} / L:{test_losses})")
    print(f"  Win Rate: {test_wr:.1%}")
    print(f"  ExpR:     {test_expr:+.3f}R")
    print(f"\nComparison to training:")
    print(f"  Train ExpR: {train_expr:+.3f}R")
    print(f"  Test ExpR:  {test_expr:+.3f}R")
    print(f"  Degradation: {degradation:.1%}")
    print(f"{'='*60}")

    # Check gates
    thresholds = THRESHOLDS['stage_3_out_of_sample']

    checks = {
        'expr': test_expr >= thresholds['min_expr'],
        'degradation': degradation < thresholds['max_degradation'],
        'sample': len(results) >= thresholds['min_sample']
    }

    print(f"\nGate Checks:")
    print(f"  Test ExpR >= {thresholds['min_expr']:+.2f}R: {'✅' if checks['expr'] else '❌'} ({test_expr:+.3f}R)")
    print(f"  Degradation < {thresholds['max_degradation']:.0%}: {'✅' if checks['degradation'] else '❌'} ({degradation:.1%})")
    print(f"  Sample >= {thresholds['min_sample']}: {'✅' if checks['sample'] else '❌'} ({len(results)})")

    passed = all(checks.values())

    if passed:
        verdict = 'PASS'
        reason = f"Edge survives on unseen data (Test ExpR: {test_expr:+.3f}R, Degradation: {degradation:.1%})"
        print(f"\n✅ STAGE 3: {verdict}")
        print(f"Optimized parameters work on unseen data - proceed to Stage 4 (stress testing)")
        print(f"\nThis is STRONG evidence the edge is NOT curve-fit.")
    else:
        verdict = 'FAIL'
        failed_checks = [k for k, v in checks.items() if not v]
        reason = f"Failed checks: {', '.join(failed_checks)}"
        print(f"\n❌ STAGE 3: {verdict}")
        print(f"Edge fails on unseen data - LIKELY CURVE-FIT")
        print(f"Reason: {reason}")
        print(f"\nDo NOT promote this edge. It was optimized on training data but doesn't generalize.")

    print(f"{'='*60}\n")

    return OutOfSampleResult(
        stage='out_of_sample_verification',
        orb_time=orb_time,
        instrument=instrument,
        test_dates=test_dates,
        test_rr=optimal_rr,
        test_filter=optimal_filter,
        test_sl_mode=optimal_sl_mode,
        test_expr=test_expr,
        test_wr=test_wr,
        test_sample=len(results),
        test_wins=test_wins,
        test_losses=test_losses,
        train_expr=train_expr,
        degradation=degradation,
        passed=passed,
        verdict=verdict,
        reason=reason
    )


if __name__ == '__main__':
    """CLI for out-of-sample verification"""
    import argparse

    parser = argparse.ArgumentParser(description='Stage 3: Verify optimized parameters on unseen test data')
    parser.add_argument('--orb', required=True, choices=['0900', '1000', '1100', '1800', '2300', '0030'],
                        help='ORB time to verify')
    parser.add_argument('--instrument', default='MGC', choices=['MGC', 'NQ', 'MPL'],
                        help='Instrument to verify')
    parser.add_argument('--rr', type=float, required=True, help='Optimal RR from Stage 2')
    parser.add_argument('--filter', type=float, help='Optimal filter from Stage 2 (optional)')
    parser.add_argument('--sl-mode', required=True, choices=['full', 'half'], help='Optimal SL mode from Stage 2')
    parser.add_argument('--train-expr', type=float, required=True, help='Training ExpR from Stage 2')
    parser.add_argument('--no-family-filter', action='store_true',
                        help='Disable strategy family filtering')

    args = parser.parse_args()

    con = duckdb.connect('gold.db')

    result = verify_out_of_sample(
        con=con,
        orb_time=args.orb,
        optimal_rr=args.rr,
        optimal_filter=args.filter,
        optimal_sl_mode=args.sl_mode,
        train_expr=args.train_expr,
        instrument=args.instrument,
        use_family_filter=not args.no_family_filter
    )

    con.close()

    # Exit with appropriate code
    sys.exit(0 if result.passed else 1)
