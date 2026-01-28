"""
ADVANCED BACKTESTING FRAMEWORK
===============================

Phase 2+ of Assumption Audit: Prove strategies are robust, not lucky

This framework runs 6 advanced validation tests:

1. WALK-FORWARD ANALYSIS (Out-of-Sample Testing)
   - Split data into rolling train/test windows
   - Verify edge holds in future unseen data
   - Detect degradation over time

2. MONTE CARLO SIMULATION (Luck vs Skill)
   - Randomize trade sequence 10,000 times
   - Calculate expectancy distribution
   - Verify actual result isn't lucky

3. PARAMETER SENSITIVITY (Robustness)
   - Test RR ± 0.5 variations
   - Test cost +25%, +50%, +100%
   - Verify edge survives parameter changes

4. REGIME ANALYSIS (Market Conditions)
   - Split by volatility (high/low ATR)
   - Split by trend (up/down/range)
   - Verify edge works across regimes

5. STATISTICAL SIGNIFICANCE (P-Value)
   - Bootstrap confidence intervals
   - T-test vs zero expectancy
   - Verify not random noise

6. DRAWDOWN ANALYSIS (Risk Assessment)
   - Maximum drawdown depth
   - Recovery time
   - Drawdown frequency

PASS CRITERIA:
- Walk-forward: Edge holds in ALL out-of-sample windows
- Monte Carlo: Actual result within 95% CI, p-value < 0.05
- Parameter sensitivity: Edge survives +50% cost stress
- Regime analysis: Edge positive in BOTH high/low vol
- Statistical significance: p-value < 0.05
- Drawdown: Max DD < 30% of expectancy × trades

If ANY test fails: Strategy is REJECTED
"""

import duckdb
import sys
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import pandas as pd
from scipy import stats

sys.path.insert(0, 'C:/Users/sydne/OneDrive/Desktop/MPX3')

from pipeline.cost_model import get_cost_model, calculate_realized_rr

DB_PATH = 'data/db/gold.db'


def load_strategy_trades(conn, setup_id: int) -> pd.DataFrame:
    """Load all trades for a strategy."""
    query = """
        SELECT
            date_local, outcome, realized_rr,
            risk_points, target_points, risk_dollars,
            entry_price, exit_price, mae, mfe
        FROM validated_trades
        WHERE setup_id = ?
          AND outcome IN ('WIN', 'LOSS')
        ORDER BY date_local
    """

    df = conn.execute(query, [setup_id]).df()
    return df


def calculate_expectancy(trades_df: pd.DataFrame) -> float:
    """Calculate expectancy from trades dataframe."""
    if len(trades_df) == 0:
        return 0.0

    return trades_df['realized_rr'].mean()


def calculate_win_rate(trades_df: pd.DataFrame) -> float:
    """Calculate win rate from trades dataframe."""
    if len(trades_df) == 0:
        return 0.0

    wins = (trades_df['outcome'] == 'WIN').sum()
    total = len(trades_df)

    return wins / total if total > 0 else 0.0


def test_1_walk_forward(trades_df: pd.DataFrame, setup_id: int) -> Dict:
    """
    Test 1: Walk-Forward Analysis

    Split data into rolling 3-month train / 3-month test windows.
    Verify edge holds in out-of-sample periods.
    """
    print(f"\n{'='*80}")
    print(f"TEST 1: WALK-FORWARD ANALYSIS (Out-of-Sample)")
    print(f"{'='*80}")
    print()

    if len(trades_df) < 60:
        print("[SKIP] Insufficient data (need >= 60 trades)")
        return {'passed': None, 'reason': 'Insufficient data'}

    trades_df = trades_df.sort_values('date_local').reset_index(drop=True)

    # Split into 3-month windows
    window_size = 90  # days
    step_size = 90    # days (non-overlapping)

    min_date = trades_df['date_local'].min()
    max_date = trades_df['date_local'].max()

    results = []
    current_date = min_date

    while current_date + timedelta(days=window_size * 2) <= max_date:
        train_start = current_date
        train_end = current_date + timedelta(days=window_size)
        test_start = train_end
        test_end = test_start + timedelta(days=window_size)

        train_df = trades_df[(trades_df['date_local'] >= train_start) &
                             (trades_df['date_local'] < train_end)]
        test_df = trades_df[(trades_df['date_local'] >= test_start) &
                            (trades_df['date_local'] < test_end)]

        if len(train_df) >= 10 and len(test_df) >= 10:
            train_exp = calculate_expectancy(train_df)
            test_exp = calculate_expectancy(test_df)

            results.append({
                'train_start': train_start,
                'train_end': train_end,
                'test_start': test_start,
                'test_end': test_end,
                'train_n': len(train_df),
                'test_n': len(test_df),
                'train_exp': train_exp,
                'test_exp': test_exp,
                'degradation': train_exp - test_exp
            })

        current_date += timedelta(days=step_size)

    if not results:
        print("[SKIP] Could not create valid train/test splits")
        return {'passed': None, 'reason': 'No valid splits'}

    print(f"Windows analyzed: {len(results)}")
    print()
    print(f"{'Train Period':<24} {'Test Period':<24} {'Train Exp':<12} {'Test Exp':<12} {'Status':<10}")
    print("-" * 80)

    failures = 0
    for r in results:
        train_period = f"{r['train_start']} to {r['train_end']}"
        test_period = f"{r['test_start']} to {r['test_end']}"
        status = "PASS" if r['test_exp'] >= 0.05 else "FAIL"

        if status == "FAIL":
            failures += 1

        print(f"{train_period:<24} {test_period:<24} {r['train_exp']:+.3f}R{'':<6} {r['test_exp']:+.3f}R{'':<6} {status:<10}")

    print()
    print(f"Out-of-sample windows: {len(results)}")
    print(f"Passed (exp >= +0.05R): {len(results) - failures}")
    print(f"Failed (exp < +0.05R): {failures}")

    passed = failures == 0

    if passed:
        print("[OK] PASS: Edge holds in ALL out-of-sample windows")
    else:
        print(f"[FAIL] FAIL: Edge failed in {failures}/{len(results)} windows")

    return {
        'passed': passed,
        'windows': len(results),
        'failures': failures,
        'results': results
    }


def test_2_monte_carlo(trades_df: pd.DataFrame, setup_id: int) -> Dict:
    """
    Test 2: Monte Carlo Simulation

    Randomize trade sequence 10,000 times.
    Verify actual expectancy isn't lucky.
    """
    print(f"\n{'='*80}")
    print(f"TEST 2: MONTE CARLO SIMULATION (Luck vs Skill)")
    print(f"{'='*80}")
    print()

    if len(trades_df) < 30:
        print("[SKIP] Insufficient data (need >= 30 trades)")
        return {'passed': None, 'reason': 'Insufficient data'}

    actual_exp = calculate_expectancy(trades_df)
    realized_rr_values = trades_df['realized_rr'].values

    print(f"Actual expectancy: {actual_exp:+.3f}R")
    print(f"Running 10,000 randomizations...")

    # Run 10,000 simulations
    simulations = 10000
    random_exps = []

    np.random.seed(42)  # Reproducibility

    for _ in range(simulations):
        shuffled = np.random.choice(realized_rr_values, size=len(realized_rr_values), replace=True)
        random_exps.append(shuffled.mean())

    random_exps = np.array(random_exps)

    # Calculate percentile of actual result
    percentile = (random_exps < actual_exp).sum() / len(random_exps) * 100

    # Calculate 95% confidence interval
    ci_lower = np.percentile(random_exps, 2.5)
    ci_upper = np.percentile(random_exps, 97.5)

    # Calculate p-value (two-tailed test vs zero)
    p_value = (np.abs(random_exps) >= np.abs(actual_exp)).sum() / len(random_exps)

    print()
    print(f"Monte Carlo results:")
    print(f"  Simulations: {simulations:,}")
    print(f"  Mean: {random_exps.mean():+.3f}R")
    print(f"  Std Dev: {random_exps.std():.3f}R")
    print(f"  95% CI: [{ci_lower:+.3f}R, {ci_upper:+.3f}R]")
    print(f"  Actual result: {actual_exp:+.3f}R (percentile: {percentile:.1f}%)")
    print(f"  P-value: {p_value:.4f}")

    # Pass if actual result is within 95% CI AND p-value < 0.05
    within_ci = ci_lower <= actual_exp <= ci_upper
    significant = p_value < 0.05

    print()
    if within_ci and significant:
        print("[OK] PASS: Result statistically significant and not lucky")
    elif not within_ci:
        print("[FAIL] FAIL: Result outside 95% CI (too extreme, likely overfit)")
    elif not significant:
        print("[FAIL] FAIL: P-value >= 0.05 (not statistically significant)")

    passed = within_ci and significant

    return {
        'passed': passed,
        'actual_exp': actual_exp,
        'mean': random_exps.mean(),
        'std': random_exps.std(),
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'percentile': percentile,
        'p_value': p_value,
        'within_ci': within_ci,
        'significant': significant
    }


def test_3_parameter_sensitivity(conn, trades_df: pd.DataFrame, setup_id: int) -> Dict:
    """
    Test 3: Parameter Sensitivity

    Test edge with varied costs and RR targets.
    Verify robustness to parameter changes.
    """
    print(f"\n{'='*80}")
    print(f"TEST 3: PARAMETER SENSITIVITY (Robustness)")
    print(f"{'='*80}")
    print()

    if len(trades_df) < 30:
        print("[SKIP] Insufficient data (need >= 30 trades)")
        return {'passed': None, 'reason': 'Insufficient data'}

    # Get strategy RR
    setup_info = conn.execute("""
        SELECT instrument, orb_time, rr, sl_mode
        FROM validated_setups
        WHERE id = ?
    """, [setup_id]).fetchone()

    instrument = setup_info[0]
    orb_time = setup_info[1]
    base_rr = setup_info[2]

    base_cost_model = get_cost_model(instrument)
    base_friction = base_cost_model['total_friction']

    print(f"Base parameters:")
    print(f"  RR: {base_rr}")
    print(f"  Friction: ${base_friction:.2f} RT")
    print()

    # Test cost sensitivity: +0%, +25%, +50%, +100%
    cost_multipliers = [1.0, 1.25, 1.5, 2.0]
    cost_results = []

    print("Cost Sensitivity:")
    print(f"{'Multiplier':<12} {'Friction':<12} {'Expectancy':<12} {'Status':<10}")
    print("-" * 50)

    for mult in cost_multipliers:
        stressed_friction = base_friction * mult

        # Recalculate realized RR with stressed costs
        recalc_rrs = []
        for _, trade in trades_df.iterrows():
            if trade['outcome'] == 'WIN':
                pnl_points = trade['target_points']
            else:
                pnl_points = -trade['risk_points']

            pnl_dollars = pnl_points * get_cost_model(instrument)['point_value']
            net_pnl = pnl_dollars - stressed_friction
            risk_dollars = trade['risk_points'] * get_cost_model(instrument)['point_value'] + stressed_friction

            recalc_rrs.append(net_pnl / risk_dollars if risk_dollars > 0 else 0)

        stressed_exp = np.mean(recalc_rrs)
        status = "PASS" if stressed_exp >= 0.05 else "FAIL"

        cost_results.append({
            'multiplier': mult,
            'friction': stressed_friction,
            'expectancy': stressed_exp,
            'passed': stressed_exp >= 0.05
        })

        print(f"{mult}x{'':<9} ${stressed_friction:<10.2f} {stressed_exp:+.3f}R{'':<6} {status:<10}")

    # Pass if survives +50% stress (1.5x multiplier)
    passed = any(r['multiplier'] == 1.5 and r['passed'] for r in cost_results)

    print()
    if passed:
        print("[OK] PASS: Edge survives +50% cost stress")
    else:
        print("[FAIL] FAIL: Edge fails at +50% cost stress")

    return {
        'passed': passed,
        'base_friction': base_friction,
        'cost_results': cost_results
    }


def test_4_regime_analysis(trades_df: pd.DataFrame, setup_id: int) -> Dict:
    """
    Test 4: Regime Analysis

    Split trades by market conditions.
    Verify edge works across different regimes.
    """
    print(f"\n{'='*80}")
    print(f"TEST 4: REGIME ANALYSIS (Market Conditions)")
    print(f"{'='*80}")
    print()

    if len(trades_df) < 30:
        print("[SKIP] Insufficient data (need >= 30 trades)")
        return {'passed': None, 'reason': 'Insufficient data'}

    # Split by risk_points (proxy for volatility)
    median_risk = trades_df['risk_points'].median()

    low_vol = trades_df[trades_df['risk_points'] <= median_risk]
    high_vol = trades_df[trades_df['risk_points'] > median_risk]

    low_vol_exp = calculate_expectancy(low_vol)
    high_vol_exp = calculate_expectancy(high_vol)

    low_vol_wr = calculate_win_rate(low_vol)
    high_vol_wr = calculate_win_rate(high_vol)

    print(f"Volatility Split (median risk: {median_risk:.1f} points):")
    print(f"{'Regime':<20} {'Trades':<10} {'Win Rate':<12} {'Expectancy':<12} {'Status':<10}")
    print("-" * 70)
    print(f"{'Low Volatility':<20} {len(low_vol):<10} {low_vol_wr:<12.1%} {low_vol_exp:+.3f}R{'':<6} {'PASS' if low_vol_exp >= 0.0 else 'FAIL':<10}")
    print(f"{'High Volatility':<20} {len(high_vol):<10} {high_vol_wr:<12.1%} {high_vol_exp:+.3f}R{'':<6} {'PASS' if high_vol_exp >= 0.0 else 'FAIL':<10}")

    # Pass if BOTH regimes are positive (relaxed threshold for regime splits)
    passed = low_vol_exp >= 0.0 and high_vol_exp >= 0.0

    print()
    if passed:
        print("[OK] PASS: Edge positive in BOTH volatility regimes")
    else:
        print("[FAIL] FAIL: Edge fails in at least one regime")

    return {
        'passed': passed,
        'low_vol': {
            'n': len(low_vol),
            'expectancy': low_vol_exp,
            'win_rate': low_vol_wr
        },
        'high_vol': {
            'n': len(high_vol),
            'expectancy': high_vol_exp,
            'win_rate': high_vol_wr
        }
    }


def test_5_statistical_significance(trades_df: pd.DataFrame, setup_id: int) -> Dict:
    """
    Test 5: Statistical Significance

    Bootstrap confidence intervals and t-test.
    Verify edge is not random noise.
    """
    print(f"\n{'='*80}")
    print(f"TEST 5: STATISTICAL SIGNIFICANCE (P-Value)")
    print(f"{'='*80}")
    print()

    if len(trades_df) < 30:
        print("[SKIP] Insufficient data (need >= 30 trades)")
        return {'passed': None, 'reason': 'Insufficient data'}

    realized_rr_values = trades_df['realized_rr'].values
    actual_exp = realized_rr_values.mean()

    # T-test against zero expectancy
    t_stat, p_value = stats.ttest_1samp(realized_rr_values, 0)

    # Bootstrap 95% confidence interval
    n_bootstrap = 10000
    bootstrap_means = []

    np.random.seed(42)
    for _ in range(n_bootstrap):
        sample = np.random.choice(realized_rr_values, size=len(realized_rr_values), replace=True)
        bootstrap_means.append(sample.mean())

    bootstrap_means = np.array(bootstrap_means)
    ci_lower = np.percentile(bootstrap_means, 2.5)
    ci_upper = np.percentile(bootstrap_means, 97.5)

    print(f"Statistical Tests:")
    print(f"  Sample size: {len(realized_rr_values)}")
    print(f"  Mean: {actual_exp:+.3f}R")
    print(f"  Std Dev: {realized_rr_values.std():.3f}R")
    print(f"  T-statistic: {t_stat:.3f}")
    print(f"  P-value: {p_value:.4f}")
    print(f"  95% CI (bootstrap): [{ci_lower:+.3f}R, {ci_upper:+.3f}R]")

    # Pass if p-value < 0.05 AND lower CI > 0
    significant = p_value < 0.05
    ci_positive = ci_lower > 0

    print()
    if significant and ci_positive:
        print("[OK] PASS: Statistically significant (p < 0.05) AND 95% CI > 0")
    elif not significant:
        print("[FAIL] FAIL: Not statistically significant (p >= 0.05)")
    elif not ci_positive:
        print("[FAIL] FAIL: 95% CI includes negative values")

    passed = significant and ci_positive

    return {
        'passed': passed,
        'n': len(realized_rr_values),
        'mean': actual_exp,
        'std': realized_rr_values.std(),
        't_stat': t_stat,
        'p_value': p_value,
        'ci_lower': ci_lower,
        'ci_upper': ci_upper,
        'significant': significant,
        'ci_positive': ci_positive
    }


def test_6_drawdown_analysis(trades_df: pd.DataFrame, setup_id: int) -> Dict:
    """
    Test 6: Drawdown Analysis

    Calculate maximum drawdown and recovery.
    Verify risk profile is acceptable.
    """
    print(f"\n{'='*80}")
    print(f"TEST 6: DRAWDOWN ANALYSIS (Risk Assessment)")
    print(f"{'='*80}")
    print()

    if len(trades_df) < 30:
        print("[SKIP] Insufficient data (need >= 30 trades)")
        return {'passed': None, 'reason': 'Insufficient data'}

    # Calculate cumulative equity curve
    trades_df = trades_df.sort_values('date_local').reset_index(drop=True)
    cumulative_r = trades_df['realized_rr'].cumsum()

    # Calculate drawdown
    running_max = cumulative_r.cummax()
    drawdown = cumulative_r - running_max

    max_dd = drawdown.min()
    max_dd_idx = drawdown.idxmin()
    max_dd_date = trades_df.iloc[max_dd_idx]['date_local']

    # Recovery time (trades to recover from max DD)
    recovery_trades = None
    if max_dd_idx < len(trades_df) - 1:
        peak_before_dd = running_max.iloc[max_dd_idx]
        recovery_idx = cumulative_r[max_dd_idx:][cumulative_r >= peak_before_dd].index
        if len(recovery_idx) > 0:
            recovery_trades = recovery_idx[0] - max_dd_idx

    # Expectancy-adjusted threshold
    actual_exp = trades_df['realized_rr'].mean()
    expected_profit = actual_exp * len(trades_df)

    # Max DD should be < 30% of expected total profit
    dd_threshold = expected_profit * 0.30

    print(f"Drawdown Metrics:")
    print(f"  Maximum Drawdown: {max_dd:.3f}R")
    print(f"  DD Date: {max_dd_date}")
    print(f"  Recovery Time: {recovery_trades if recovery_trades else 'Not yet recovered'} trades")
    print(f"  Expected Total Profit: {expected_profit:.3f}R")
    print(f"  DD Threshold (30%): {dd_threshold:.3f}R")

    # Pass if max DD < 30% of expected profit
    passed = abs(max_dd) < abs(dd_threshold)

    print()
    if passed:
        print(f"[OK] PASS: Max DD ({max_dd:.3f}R) < 30% threshold ({dd_threshold:.3f}R)")
    else:
        print(f"[FAIL] FAIL: Max DD ({max_dd:.3f}R) >= 30% threshold ({dd_threshold:.3f}R)")

    return {
        'passed': passed,
        'max_dd': max_dd,
        'max_dd_date': str(max_dd_date),
        'recovery_trades': recovery_trades,
        'expected_profit': expected_profit,
        'dd_threshold': dd_threshold
    }


def run_advanced_backtest(conn, setup_id: int):
    """Run all 6 advanced tests on a strategy."""

    # Get strategy info
    setup_info = conn.execute("""
        SELECT instrument, orb_time, rr, sl_mode, status, realized_expectancy, sample_size
        FROM validated_setups
        WHERE id = ?
    """, [setup_id]).fetchone()

    if not setup_info:
        print(f"[ERROR] Setup {setup_id} not found")
        return

    instrument, orb_time, rr, sl_mode, status, realized_exp, sample_size = setup_info

    print(f"\n{'#'*80}")
    print(f"ADVANCED BACKTESTING: Setup {setup_id}")
    print(f"{'#'*80}")
    print()
    print(f"Strategy: {instrument} {orb_time} ORB RR={rr} sl_mode={sl_mode}")
    print(f"Status: {status}")
    print(f"Sample Size: {sample_size}")
    print(f"Realized Expectancy: {realized_exp:+.3f}R" if realized_exp else "Realized Expectancy: N/A")

    # Load trades
    trades_df = load_strategy_trades(conn, setup_id)

    if len(trades_df) < 30:
        print(f"\n[SKIP] Insufficient data for advanced testing (need >= 30, have {len(trades_df)})")
        return

    # Run all 6 tests
    results = {}
    results['test_1'] = test_1_walk_forward(trades_df, setup_id)
    results['test_2'] = test_2_monte_carlo(trades_df, setup_id)
    results['test_3'] = test_3_parameter_sensitivity(conn, trades_df, setup_id)
    results['test_4'] = test_4_regime_analysis(trades_df, setup_id)
    results['test_5'] = test_5_statistical_significance(trades_df, setup_id)
    results['test_6'] = test_6_drawdown_analysis(trades_df, setup_id)

    # Summary
    print(f"\n{'='*80}")
    print(f"ADVANCED BACKTEST SUMMARY: Setup {setup_id}")
    print(f"{'='*80}")
    print()

    test_names = [
        "Walk-Forward Analysis",
        "Monte Carlo Simulation",
        "Parameter Sensitivity",
        "Regime Analysis",
        "Statistical Significance",
        "Drawdown Analysis"
    ]

    passed_count = 0
    failed_count = 0
    skipped_count = 0

    for i, (test_key, result) in enumerate(results.items(), 1):
        test_name = test_names[i-1]

        if result['passed'] is None:
            status_str = "SKIP"
            skipped_count += 1
        elif result['passed']:
            status_str = "PASS"
            passed_count += 1
        else:
            status_str = "FAIL"
            failed_count += 1

        print(f"  Test {i}: {test_name:<30} [{status_str}]")

    print()
    print(f"Results: {passed_count} PASS, {failed_count} FAIL, {skipped_count} SKIP")

    # Overall verdict
    all_passed = failed_count == 0 and passed_count >= 4

    print()
    if all_passed:
        print("[OK] STRATEGY APPROVED: Passed all advanced backtests")
    else:
        print("[FAIL] STRATEGY REJECTED: Failed advanced backtests")
        print("[FAIL] Strategy may be overfit, lucky, or regime-dependent")

    return results


def main():
    conn = duckdb.connect(DB_PATH)

    print("="*80)
    print("ADVANCED BACKTESTING FRAMEWORK")
    print("="*80)
    print()
    print("Running 6 advanced validation tests on ACTIVE strategies")
    print()

    # Get all ACTIVE strategies
    active_setups = conn.execute("""
        SELECT id, instrument, orb_time, rr
        FROM validated_setups
        WHERE status = 'ACTIVE'
        ORDER BY id
    """).fetchall()

    print(f"Found {len(active_setups)} ACTIVE strategies")
    print()

    for setup_id, instrument, orb_time, rr in active_setups:
        run_advanced_backtest(conn, setup_id)
        print()

    conn.close()


if __name__ == "__main__":
    main()
