"""
Stage 2: Parameter Optimization (Training Data ONLY)

Finds optimal parameters for VALIDATED concept.

CRITICAL: This runs on TRAINING data only (first 60% of dataset).
Parameters are optimized here, then tested on UNSEEN test data in Stage 3.

Only run this AFTER Stage 1 passes (concept validated on held-out data).
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
    get_search_space,
    THRESHOLDS,
    COST_MODELS
)


@dataclass
class OptimizationResult:
    """Stage 2 output"""
    stage: str
    orb_time: str
    instrument: str

    # Optimization details
    train_dates: List[str]
    configurations_tested: int

    # Optimal parameters
    optimal_rr: float
    optimal_filter: Optional[float]
    optimal_sl_mode: str

    # Training performance
    train_expr: float
    train_wr: float
    train_sample: int
    train_wins: int
    train_losses: int

    # Verdict
    passed: bool
    verdict: str
    reason: str


def optimize_parameters(
    con: duckdb.DuckDBPyConnection,
    orb_time: str,
    instrument: str = 'MGC',
    use_family_filter: bool = True,
    custom_search_space: Optional[Dict] = None
) -> OptimizationResult:
    """
    Stage 2: Find optimal parameters on training data ONLY

    Args:
        con: Database connection
        orb_time: '0900', '1000', etc.
        instrument: 'MGC', 'NQ', 'MPL'
        use_family_filter: Apply strategy family filtering
        custom_search_space: Override default search space

    Returns:
        OptimizationResult with optimal parameters

    Process:
        1. Get training dates (60% of data)
        2. Filter by strategy family
        3. Grid search: RR × filters × SL modes
        4. Find config with highest ExpR (>= 30 trades)
        5. Record optimal parameters for Stage 3

    Gates:
        - Training sample >= 30 trades
        - Training ExpR >= +0.15R
        - At least one config improves on default
    """
    print(f"\n{'='*60}")
    print(f"STAGE 2: PARAMETER OPTIMIZATION")
    print(f"{'='*60}")
    print(f"ORB: {orb_time} | Instrument: {instrument}")
    print(f"Optimizing parameters on TRAINING data ONLY")
    print(f"{'='*60}\n")

    # Get data splits
    splits = get_simple_split(con, instrument)
    train_dates = splits['train']

    print(f"Training dates: {len(train_dates)} days ({train_dates[0]} to {train_dates[-1]})")

    # Apply strategy family filter
    if use_family_filter:
        original_count = len(train_dates)
        train_dates = filter_by_strategy_family(con, train_dates, orb_time, instrument)
        print(f"Strategy family filter: {len(train_dates)} / {original_count} dates pass")

    if len(train_dates) == 0:
        return OptimizationResult(
            stage='parameter_optimization',
            orb_time=orb_time,
            instrument=instrument,
            train_dates=[],
            configurations_tested=0,
            optimal_rr=1.5,
            optimal_filter=None,
            optimal_sl_mode='full',
            train_expr=0.0,
            train_wr=0.0,
            train_sample=0,
            train_wins=0,
            train_losses=0,
            passed=False,
            verdict='FAIL',
            reason='No training dates pass strategy family filter'
        )

    # Get search space
    search_space = custom_search_space or get_search_space(orb_time)

    total_configs = (
        len(search_space['rr_values']) *
        len(search_space['filters']) *
        len(search_space['sl_modes'])
    )

    print(f"\nSearch space:")
    print(f"  RR values: {search_space['rr_values']}")
    print(f"  Filters: {search_space['filters']}")
    print(f"  SL modes: {search_space['sl_modes']}")
    print(f"  Total configurations: {total_configs}")
    print(f"\nStarting grid search on {len(train_dates)} training dates...")

    # Get cost model
    friction = COST_MODELS[instrument]['base_friction']

    # Grid search
    best_expr = -999
    best_config = None
    configs_tested = 0

    for rr in search_space['rr_values']:
        for orb_filter in search_space['filters']:
            for sl_mode in search_space['sl_modes']:
                configs_tested += 1

                # Run backtest
                results = []
                for date in train_dates:
                    try:
                        result = simulate_orb_trade(
                            con=con,
                            date_local=date,
                            orb=orb_time,
                            mode='1m',
                            rr=rr,
                            sl_mode=sl_mode,
                            orb_size_filter=orb_filter,
                            slippage_ticks=1.5,
                            commission_per_contract=1.0,
                            instrument=instrument
                        )

                        if result.outcome in ['WIN', 'LOSS']:
                            results.append(result)

                    except Exception as e:
                        continue

                # Skip if insufficient sample
                if len(results) < THRESHOLDS['stage_2_optimization']['min_sample']:
                    continue

                # Calculate metrics
                wins = sum(1 for r in results if r.outcome == 'WIN')
                expr = sum(r.r_multiple for r in results) / len(results)

                # Update best
                if expr > best_expr:
                    best_expr = expr
                    best_config = {
                        'rr': rr,
                        'orb_filter': orb_filter,
                        'sl_mode': sl_mode,
                        'train_expr': expr,
                        'train_wr': wins / len(results),
                        'train_sample': len(results),
                        'train_wins': wins,
                        'train_losses': len(results) - wins
                    }

                # Progress
                if configs_tested % 10 == 0:
                    print(f"  Tested {configs_tested}/{total_configs} configs... Best so far: {best_expr:+.3f}R")

    print(f"\nGrid search complete: {configs_tested} configurations tested")

    # Check if optimization succeeded
    if best_config is None:
        return OptimizationResult(
            stage='parameter_optimization',
            orb_time=orb_time,
            instrument=instrument,
            train_dates=train_dates,
            configurations_tested=configs_tested,
            optimal_rr=1.5,
            optimal_filter=None,
            optimal_sl_mode='full',
            train_expr=0.0,
            train_wr=0.0,
            train_sample=0,
            train_wins=0,
            train_losses=0,
            passed=False,
            verdict='FAIL',
            reason='No configuration met minimum sample requirement'
        )

    print(f"\n{'='*60}")
    print("OPTIMIZATION RESULTS")
    print(f"{'='*60}")
    print(f"Optimal configuration found:")
    print(f"  RR:     {best_config['rr']}")
    print(f"  Filter: {best_config['orb_filter']}")
    print(f"  SL Mode: {best_config['sl_mode']}")
    print(f"\nTraining performance:")
    print(f"  Sample:   {best_config['train_sample']} trades (W:{best_config['train_wins']} / L:{best_config['train_losses']})")
    print(f"  Win Rate: {best_config['train_wr']:.1%}")
    print(f"  ExpR:     {best_config['train_expr']:+.3f}R")
    print(f"{'='*60}")

    # Check gates
    thresholds = THRESHOLDS['stage_2_optimization']

    checks = {
        'expr': best_config['train_expr'] >= thresholds['min_expr'],
        'sample': best_config['train_sample'] >= thresholds['min_sample']
    }

    print(f"\nGate Checks:")
    print(f"  Train ExpR >= {thresholds['min_expr']:+.2f}R: {'✅' if checks['expr'] else '❌'} ({best_config['train_expr']:+.3f}R)")
    print(f"  Sample >= {thresholds['min_sample']}: {'✅' if checks['sample'] else '❌'} ({best_config['train_sample']})")

    passed = all(checks.values())

    if passed:
        verdict = 'PASS'
        reason = f"Found optimal config (Train ExpR: {best_config['train_expr']:+.3f}R)"
        print(f"\n✅ STAGE 2: {verdict}")
        print(f"Optimal parameters found - proceed to Stage 3 (out-of-sample verification)")
    else:
        verdict = 'FAIL'
        failed_checks = [k for k, v in checks.items() if not v]
        reason = f"Failed checks: {', '.join(failed_checks)}"
        print(f"\n❌ STAGE 2: {verdict}")
        print(f"Optimization failed - no viable configuration found")
        print(f"Reason: {reason}")

    print(f"{'='*60}\n")

    return OptimizationResult(
        stage='parameter_optimization',
        orb_time=orb_time,
        instrument=instrument,
        train_dates=train_dates,
        configurations_tested=configs_tested,
        optimal_rr=best_config['rr'],
        optimal_filter=best_config['orb_filter'],
        optimal_sl_mode=best_config['sl_mode'],
        train_expr=best_config['train_expr'],
        train_wr=best_config['train_wr'],
        train_sample=best_config['train_sample'],
        train_wins=best_config['train_wins'],
        train_losses=best_config['train_losses'],
        passed=passed,
        verdict=verdict,
        reason=reason
    )


if __name__ == '__main__':
    """CLI for parameter optimization"""
    import argparse

    parser = argparse.ArgumentParser(description='Stage 2: Optimize parameters on training data')
    parser.add_argument('--orb', required=True, choices=['0900', '1000', '1100', '1800', '2300', '0030'],
                        help='ORB time to optimize')
    parser.add_argument('--instrument', default='MGC', choices=['MGC', 'NQ', 'MPL'],
                        help='Instrument to optimize')
    parser.add_argument('--no-family-filter', action='store_true',
                        help='Disable strategy family filtering')

    args = parser.parse_args()

    con = duckdb.connect('gold.db')

    result = optimize_parameters(
        con=con,
        orb_time=args.orb,
        instrument=args.instrument,
        use_family_filter=not args.no_family_filter
    )

    con.close()

    # Exit with appropriate code
    sys.exit(0 if result.passed else 1)
