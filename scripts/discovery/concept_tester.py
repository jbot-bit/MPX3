"""
Stage 1: Concept Testing (Held-Out Validation Data)

Tests if edge CONCEPT works BEFORE optimizing parameters.

CRITICAL: This runs on VALIDATION data (held-out, never used for optimization).
Uses DEFAULT parameters (RR=1.5, no filter, FULL SL).

If concept fails here, DON'T waste time optimizing - the idea doesn't work.
"""

import sys
sys.path.append('.')

import duckdb
from typing import Dict, List
from dataclasses import dataclass

from strategies.execution_engine import simulate_orb_trade
from pipeline.walkforward_config import (
    get_simple_split,
    filter_by_strategy_family,
    THRESHOLDS,
    COST_MODELS
)


@dataclass
class ConceptTestResult:
    """Stage 1 output"""
    stage: str
    orb_time: str
    instrument: str

    # Test parameters
    validation_dates: List[str]
    test_rr: float
    test_sl_mode: str
    test_filter: float

    # Results
    valid: bool
    validation_expr: float
    validation_wr: float
    validation_sample: int

    # Diagnostics
    wins: int
    losses: int
    verdict: str
    reason: str


def test_concept(
    con: duckdb.DuckDBPyConnection,
    orb_time: str,
    instrument: str = 'MGC',
    use_family_filter: bool = True
) -> ConceptTestResult:
    """
    Stage 1: Test if concept works on held-out validation data

    Args:
        con: Database connection
        orb_time: '0900', '1000', '1100', '1800', etc.
        instrument: 'MGC', 'NQ', 'MPL'
        use_family_filter: If True, filter dates by strategy family rules

    Returns:
        ConceptTestResult with pass/fail verdict

    Process:
        1. Get validation dates (20% held-out, never used for optimization)
        2. Filter by strategy family if applicable
        3. Run trades with DEFAULT parameters (not optimized)
        4. Calculate ExpR, win rate, sample size
        5. Check against Stage 1 thresholds

    Gates:
        - ExpR >= +0.10R on validation data
        - Sample size >= 20 trades
        - Win rate >= 10%
    """
    print(f"\n{'='*60}")
    print(f"STAGE 1: CONCEPT TESTING")
    print(f"{'='*60}")
    print(f"ORB: {orb_time} | Instrument: {instrument}")
    print(f"Testing concept on HELD-OUT validation data (never used for optimization)")
    print(f"{'='*60}\n")

    # Get data splits
    splits = get_simple_split(con, instrument)
    validation_dates = splits['validation']

    print(f"Validation dates: {len(validation_dates)} days ({validation_dates[0]} to {validation_dates[-1]})")

    # Apply strategy family filter if requested
    if use_family_filter:
        original_count = len(validation_dates)
        validation_dates = filter_by_strategy_family(con, validation_dates, orb_time, instrument)
        print(f"Strategy family filter: {len(validation_dates)} / {original_count} dates pass")

    if len(validation_dates) == 0:
        return ConceptTestResult(
            stage='concept_test',
            orb_time=orb_time,
            instrument=instrument,
            validation_dates=[],
            test_rr=1.5,
            test_sl_mode='full',
            test_filter=None,
            valid=False,
            validation_expr=0.0,
            validation_wr=0.0,
            validation_sample=0,
            wins=0,
            losses=0,
            verdict='FAIL',
            reason='No dates pass strategy family filter'
        )

    # Default parameters (NOT optimized)
    test_rr = 1.5
    test_sl_mode = 'full'
    test_filter = None

    print(f"\nTesting with DEFAULT parameters (not optimized):")
    print(f"  RR: {test_rr}")
    print(f"  SL Mode: {test_sl_mode}")
    print(f"  Filter: {test_filter}")
    print(f"\nRunning backtest on {len(validation_dates)} validation dates...")

    # Get cost model
    friction = COST_MODELS[instrument]['base_friction']

    # Run backtest
    results = []
    for date in validation_dates:
        try:
            result = simulate_orb_trade(
                con=con,
                date_local=date,
                orb=orb_time,
                mode='1m',
                rr=test_rr,
                sl_mode=test_sl_mode,
                orb_size_filter=test_filter,
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
        return ConceptTestResult(
            stage='concept_test',
            orb_time=orb_time,
            instrument=instrument,
            validation_dates=validation_dates,
            test_rr=test_rr,
            test_sl_mode=test_sl_mode,
            test_filter=test_filter,
            valid=False,
            validation_expr=0.0,
            validation_wr=0.0,
            validation_sample=0,
            wins=0,
            losses=0,
            verdict='FAIL',
            reason='No valid trades generated'
        )

    wins = sum(1 for r in results if r.outcome == 'WIN')
    losses = len(results) - wins
    validation_wr = wins / len(results)
    validation_expr = sum(r.r_multiple for r in results) / len(results)

    print(f"\n{'='*60}")
    print("CONCEPT TEST RESULTS")
    print(f"{'='*60}")
    print(f"Sample:   {len(results)} trades (W:{wins} / L:{losses})")
    print(f"Win Rate: {validation_wr:.1%}")
    print(f"ExpR:     {validation_expr:+.3f}R")
    print(f"{'='*60}")

    # Check gates
    thresholds = THRESHOLDS['stage_1_concept']

    checks = {
        'expr': validation_expr >= thresholds['min_expr'],
        'sample': len(results) >= thresholds['min_sample'],
        'wr': validation_wr >= thresholds['min_wr']
    }

    print(f"\nGate Checks:")
    print(f"  ExpR >= {thresholds['min_expr']:+.2f}R: {'✅' if checks['expr'] else '❌'} ({validation_expr:+.3f}R)")
    print(f"  Sample >= {thresholds['min_sample']}: {'✅' if checks['sample'] else '❌'} ({len(results)})")
    print(f"  WR >= {thresholds['min_wr']:.0%}: {'✅' if checks['wr'] else '❌'} ({validation_wr:.1%})")

    passed = all(checks.values())

    if passed:
        verdict = 'PASS'
        reason = f"Concept valid on held-out data (ExpR: {validation_expr:+.3f}R)"
        print(f"\n✅ STAGE 1: {verdict}")
        print(f"Concept works on validation data - proceed to Stage 2 (optimization)")
    else:
        verdict = 'FAIL'
        failed_checks = [k for k, v in checks.items() if not v]
        reason = f"Failed checks: {', '.join(failed_checks)}"
        print(f"\n❌ STAGE 1: {verdict}")
        print(f"Concept doesn't work on held-out data - don't waste time optimizing")
        print(f"Reason: {reason}")

    print(f"{'='*60}\n")

    return ConceptTestResult(
        stage='concept_test',
        orb_time=orb_time,
        instrument=instrument,
        validation_dates=validation_dates,
        test_rr=test_rr,
        test_sl_mode=test_sl_mode,
        test_filter=test_filter,
        valid=passed,
        validation_expr=validation_expr,
        validation_wr=validation_wr,
        validation_sample=len(results),
        wins=wins,
        losses=losses,
        verdict=verdict,
        reason=reason
    )


if __name__ == '__main__':
    """CLI for concept testing"""
    import argparse

    parser = argparse.ArgumentParser(description='Stage 1: Test concept on held-out validation data')
    parser.add_argument('--orb', required=True, choices=['0900', '1000', '1100', '1800', '2300', '0030'],
                        help='ORB time to test')
    parser.add_argument('--instrument', default='MGC', choices=['MGC', 'NQ', 'MPL'],
                        help='Instrument to test')
    parser.add_argument('--no-family-filter', action='store_true',
                        help='Disable strategy family filtering')

    args = parser.parse_args()

    con = duckdb.connect('gold.db')

    result = test_concept(
        con=con,
        orb_time=args.orb,
        instrument=args.instrument,
        use_family_filter=not args.no_family_filter
    )

    con.close()

    # Exit with appropriate code
    sys.exit(0 if result.valid else 1)
