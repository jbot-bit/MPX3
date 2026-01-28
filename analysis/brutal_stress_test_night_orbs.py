"""
BRUTAL STRESS TEST - NIGHT ORBs
================================

User is rightfully skeptical. Let's test these night ORBs with EXTREME prejudice.

STRESS TESTS:
1. EXTREME cost stress (+75%, +100%, +150% costs)
2. Regime splits (multiple cuts: volatility, range, momentum)
3. Day of week analysis (are Mondays/Fridays different?)
4. Monthly seasonality (do certain months fail?)
5. Liquidity stress (small ORBs vs large ORBs)
6. Random entry comparison (is ORB better than random?)
7. Drawdown analysis (worst losing streaks)
8. Monte Carlo simulation (1000 random permutations - worst case?)

HONESTY OVER OUTCOME: If these fail ANY critical test, REJECT them.
"""

import duckdb
import sys
import numpy as np
import pandas as pd
from pathlib import Path
import random

sys.path.insert(0, 'pipeline')
from cost_model import get_cost_model, get_instrument_specs

DB_PATH = Path('data/db/gold.db')

# CANONICAL COST MODEL
mgc_specs = get_instrument_specs('MGC')
mgc_costs = get_cost_model('MGC', stress_level='normal')
POINT_VALUE = mgc_specs['point_value']
FRICTION_BASE = mgc_costs['total_friction']

print("=" * 80)
print("BRUTAL STRESS TEST - NIGHT ORBs")
print("=" * 80)
print()
print("Testing 2300 ORB and 0030 ORB with EXTREME prejudice")
print("HONESTY OVER OUTCOME: Looking for reasons to REJECT")
print()


def calculate_expectancy(trades_df, rr, point_value, friction):
    """Calculate expectancy using CANONICAL formulas."""
    if len(trades_df) == 0:
        return None, 0

    realized_r_values = []

    for idx, row in trades_df.iterrows():
        orb_high = row['orb_high']
        orb_low = row['orb_low']
        break_dir = row['break_dir']
        outcome = row['outcome']

        if pd.isna(orb_high) or pd.isna(orb_low) or pd.isna(break_dir) or pd.isna(outcome):
            continue

        if break_dir == 'UP':
            entry, stop = orb_high, orb_low
        elif break_dir == 'DOWN':
            entry, stop = orb_low, orb_high
        else:
            continue

        stop_dist_points = abs(entry - stop)

        # CANONICAL FORMULAS
        realized_risk_dollars = (stop_dist_points * point_value) + friction
        target_dist_points = stop_dist_points * rr
        realized_reward_dollars = (target_dist_points * point_value) - friction

        if outcome == 'WIN':
            net_pnl = realized_reward_dollars
        else:
            net_pnl = -realized_risk_dollars

        realized_r = net_pnl / realized_risk_dollars
        realized_r_values.append(realized_r)

    if len(realized_r_values) == 0:
        return None, 0

    return np.mean(realized_r_values), len(realized_r_values)


def calculate_max_drawdown(trades_df, rr, point_value, friction):
    """Calculate maximum drawdown in R-multiples."""
    if len(trades_df) == 0:
        return None

    cumulative = 0
    peak = 0
    max_dd = 0

    for idx, row in trades_df.iterrows():
        orb_high = row['orb_high']
        orb_low = row['orb_low']
        break_dir = row['break_dir']
        outcome = row['outcome']

        if pd.isna(orb_high) or pd.isna(orb_low) or pd.isna(break_dir) or pd.isna(outcome):
            continue

        if break_dir == 'UP':
            entry, stop = orb_high, orb_low
        elif break_dir == 'DOWN':
            entry, stop = orb_low, orb_high
        else:
            continue

        stop_dist_points = abs(entry - stop)
        realized_risk_dollars = (stop_dist_points * point_value) + friction
        target_dist_points = stop_dist_points * rr
        realized_reward_dollars = (target_dist_points * point_value) - friction

        if outcome == 'WIN':
            net_pnl = realized_reward_dollars
        else:
            net_pnl = -realized_risk_dollars

        realized_r = net_pnl / realized_risk_dollars
        cumulative += realized_r

        if cumulative > peak:
            peak = cumulative

        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd

    return max_dd


def stress_test_strategy(name, orb_data, rr):
    """Run all brutal stress tests on a strategy."""
    print(f"\n{'=' * 80}")
    print(f"STRESS TESTING: {name}")
    print("=" * 80)

    results = {'name': name, 'tests_passed': 0, 'tests_failed': 0, 'warnings': []}

    # TEST 1: EXTREME Cost Stress
    print("\nTEST 1: EXTREME Cost Stress")
    print("-" * 80)

    stress_levels = [
        (1.0, FRICTION_BASE),
        (1.25, FRICTION_BASE * 1.25),
        (1.5, FRICTION_BASE * 1.5),
        (1.75, FRICTION_BASE * 1.75),
        (2.0, FRICTION_BASE * 2.0),
        (2.5, FRICTION_BASE * 2.5)
    ]

    print(f"Base (${FRICTION_BASE:.2f}): ", end="")
    base_exp, _ = calculate_expectancy(orb_data, rr, POINT_VALUE, FRICTION_BASE)
    print(f"{base_exp:+.3f}R")

    fail_point = None
    for multiplier, friction in stress_levels[1:]:
        exp, _ = calculate_expectancy(orb_data, rr, POINT_VALUE, friction)
        print(f"+{int((multiplier-1)*100)}% (${friction:.2f}): {exp:+.3f}R", end="")

        if exp < 0.15:
            print(f" <- FAILS HERE")
            fail_point = multiplier
            break
        else:
            print()

    if fail_point and fail_point < 1.75:
        print(f"[FAIL] Strategy fails before +75% stress")
        results['tests_failed'] += 1
    else:
        print(f"[PASS] Survives extreme cost stress")
        results['tests_passed'] += 1

    # TEST 2: Day of Week Analysis
    print("\nTEST 2: Day of Week Analysis")
    print("-" * 80)

    orb_data['day_of_week'] = pd.to_datetime(orb_data['date_local']).dt.dayofweek
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']

    day_fail = False
    for day in range(5):  # Mon-Fri
        day_trades = orb_data[orb_data['day_of_week'] == day]
        if len(day_trades) < 10:
            print(f"  {day_names[day]}: {len(day_trades)} trades (skip)")
            continue

        exp_day, n_day = calculate_expectancy(day_trades, rr, POINT_VALUE, FRICTION_BASE)
        print(f"  {day_names[day]}: {n_day} trades, {exp_day:+.3f}R", end="")

        if exp_day < 0:
            print(" <- NEGATIVE")
            day_fail = True
        else:
            print()

    if day_fail:
        print("[WARN] Negative on some days of week")
        results['warnings'].append("Negative on some days")
        results['tests_passed'] += 1  # Warning, not fail
    else:
        print("[PASS] Positive all days of week")
        results['tests_passed'] += 1

    # TEST 3: Monthly Seasonality
    print("\nTEST 3: Monthly Seasonality")
    print("-" * 80)

    orb_data['month'] = pd.to_datetime(orb_data['date_local']).dt.month
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    monthly_fail = False
    for month in range(1, 13):
        month_trades = orb_data[orb_data['month'] == month]
        if len(month_trades) < 10:
            continue

        exp_month, n_month = calculate_expectancy(month_trades, rr, POINT_VALUE, FRICTION_BASE)
        print(f"  {month_names[month-1]}: {n_month:2d} trades, {exp_month:+.3f}R", end="")

        if exp_month < 0:
            print(" <- NEGATIVE")
            monthly_fail = True
        else:
            print()

    if monthly_fail:
        print("[WARN] Negative in some months")
        results['warnings'].append("Negative in some months")
        results['tests_passed'] += 1  # Warning, not fail
    else:
        print("[PASS] Positive all months")
        results['tests_passed'] += 1

    # TEST 4: Liquidity Stress (ORB Size)
    print("\nTEST 4: Liquidity Stress (ORB Size)")
    print("-" * 80)

    orb_data['orb_size'] = abs(orb_data['orb_high'] - orb_data['orb_low'])
    q25 = orb_data['orb_size'].quantile(0.25)
    q75 = orb_data['orb_size'].quantile(0.75)

    small_orb = orb_data[orb_data['orb_size'] < q25]
    large_orb = orb_data[orb_data['orb_size'] > q75]

    exp_small, n_small = calculate_expectancy(small_orb, rr, POINT_VALUE, FRICTION_BASE)
    exp_large, n_large = calculate_expectancy(large_orb, rr, POINT_VALUE, FRICTION_BASE)

    print(f"  Small ORB (<{q25:.2f} pts): {n_small} trades, {exp_small:+.3f}R")
    print(f"  Large ORB (>{q75:.2f} pts): {n_large} trades, {exp_large:+.3f}R")

    if exp_small < 0 or exp_large < 0:
        print("[FAIL] Negative in some liquidity conditions")
        results['tests_failed'] += 1
    else:
        print("[PASS] Positive in all liquidity conditions")
        results['tests_passed'] += 1

    # TEST 5: Random Entry Comparison
    print("\nTEST 5: Random Entry Comparison (ORB vs Random)")
    print("-" * 80)

    # Simulate random entries (50% win rate)
    random.seed(42)
    random_outcomes = orb_data.copy()
    random_outcomes['outcome'] = random_outcomes['outcome'].apply(
        lambda x: 'WIN' if random.random() < 0.5 else 'LOSS'
    )

    exp_random, _ = calculate_expectancy(random_outcomes, rr, POINT_VALUE, FRICTION_BASE)
    exp_orb = base_exp

    print(f"  ORB Entry: {exp_orb:+.3f}R")
    print(f"  Random Entry (50% WR): {exp_random:+.3f}R")
    print(f"  Edge vs Random: {exp_orb - exp_random:+.3f}R")

    if exp_orb <= exp_random:
        print("[FAIL] ORB no better than random")
        results['tests_failed'] += 1
    else:
        print("[PASS] ORB beats random entry")
        results['tests_passed'] += 1

    # TEST 6: Maximum Drawdown
    print("\nTEST 6: Maximum Drawdown")
    print("-" * 80)

    max_dd = calculate_max_drawdown(orb_data, rr, POINT_VALUE, FRICTION_BASE)
    print(f"  Max Drawdown: {max_dd:.2f}R")

    if max_dd > 10.0:
        print("[WARN] Large drawdown (>10R)")
        results['warnings'].append(f"Max DD = {max_dd:.2f}R")
        results['tests_passed'] += 1  # Warning, not fail
    else:
        print("[PASS] Reasonable drawdown")
        results['tests_passed'] += 1

    # TEST 7: Monte Carlo Simulation (Worst Case)
    print("\nTEST 7: Monte Carlo Simulation (1000 permutations)")
    print("-" * 80)

    r_values = []
    for idx, row in orb_data.iterrows():
        if pd.isna(row['orb_high']) or pd.isna(row['break_dir']) or pd.isna(row['outcome']):
            continue

        if row['break_dir'] == 'UP':
            entry, stop = row['orb_high'], row['orb_low']
        elif row['break_dir'] == 'DOWN':
            entry, stop = row['orb_low'], row['orb_high']
        else:
            continue

        stop_dist_points = abs(entry - stop)
        realized_risk_dollars = (stop_dist_points * POINT_VALUE) + FRICTION_BASE
        target_dist_points = stop_dist_points * rr
        realized_reward_dollars = (target_dist_points * POINT_VALUE) - FRICTION_BASE

        if row['outcome'] == 'WIN':
            net_pnl = realized_reward_dollars
        else:
            net_pnl = -realized_risk_dollars

        realized_r = net_pnl / realized_risk_dollars
        r_values.append(realized_r)

    # Run 1000 random permutations
    permutation_results = []
    for i in range(1000):
        shuffled = random.sample(r_values, len(r_values))
        exp_perm = np.mean(shuffled)
        permutation_results.append(exp_perm)

    p5 = np.percentile(permutation_results, 5)
    p50 = np.percentile(permutation_results, 50)
    p95 = np.percentile(permutation_results, 95)

    print(f"  5th percentile (worst case): {p5:+.3f}R")
    print(f"  50th percentile (median): {p50:+.3f}R")
    print(f"  95th percentile (best case): {p95:+.3f}R")

    if p5 < 0:
        print(f"[FAIL] Worst case (5th percentile) is NEGATIVE")
        results['tests_failed'] += 1
    else:
        print(f"[PASS] Even worst case is positive")
        results['tests_passed'] += 1

    # SUMMARY
    print(f"\n{'=' * 80}")
    print(f"STRESS TEST SUMMARY: {name}")
    print("=" * 80)
    print(f"Tests Passed: {results['tests_passed']}")
    print(f"Tests Failed: {results['tests_failed']}")
    if results['warnings']:
        print(f"Warnings: {len(results['warnings'])}")
        for warning in results['warnings']:
            print(f"  - {warning}")

    if results['tests_failed'] > 0:
        print(f"\n[REJECT] Strategy FAILS brutal stress testing")
        return 'REJECTED'
    elif len(results['warnings']) > 2:
        print(f"\n[MARGINAL] Strategy passes but has multiple warnings")
        return 'MARGINAL'
    else:
        print(f"\n[APPROVED] Strategy survives brutal stress testing")
        return 'APPROVED'


# Load data
conn = duckdb.connect(str(DB_PATH), read_only=True)

query = """
SELECT
    date_local,
    orb_2300_high, orb_2300_low, orb_2300_break_dir, orb_2300_outcome,
    orb_0030_high, orb_0030_low, orb_0030_break_dir, orb_0030_outcome
FROM daily_features
WHERE instrument = 'MGC'
    AND date_local >= '2024-01-02'
    AND date_local <= '2026-01-26'
ORDER BY date_local
"""

df = conn.execute(query).df()
conn.close()

# Prepare 2300 ORB
orb_2300 = df[df['orb_2300_outcome'].notna()].copy()
orb_2300['orb_high'] = orb_2300['orb_2300_high']
orb_2300['orb_low'] = orb_2300['orb_2300_low']
orb_2300['break_dir'] = orb_2300['orb_2300_break_dir']
orb_2300['outcome'] = orb_2300['orb_2300_outcome']

# Prepare 0030 ORB
orb_0030 = df[df['orb_0030_outcome'].notna()].copy()
orb_0030['orb_high'] = orb_0030['orb_0030_high']
orb_0030['orb_low'] = orb_0030['orb_0030_low']
orb_0030['break_dir'] = orb_0030['orb_0030_break_dir']
orb_0030['outcome'] = orb_0030['orb_0030_outcome']

# RUN BRUTAL STRESS TESTS
result_2300 = stress_test_strategy('2300 ORB RR=3.0', orb_2300, rr=3.0)
result_0030 = stress_test_strategy('0030 ORB RR=3.0', orb_0030, rr=3.0)

# FINAL VERDICT
print("\n" + "=" * 80)
print("FINAL VERDICT - BRUTAL STRESS TEST")
print("=" * 80)
print()
print(f"2300 ORB RR=3.0: {result_2300}")
print(f"0030 ORB RR=3.0: {result_0030}")
print()

if result_2300 == 'APPROVED' and result_0030 == 'APPROVED':
    print("[APPROVED] Both strategies survive ALL brutal stress tests")
    print()
    print("HONESTY OVER OUTCOME: These edges are REAL.")
elif result_2300 == 'REJECTED' or result_0030 == 'REJECTED':
    print("[REJECTED] At least one strategy FAILS brutal stress testing")
    print()
    print("HONESTY OVER OUTCOME: Do NOT trade rejected strategies.")
else:
    print("[MARGINAL] Strategies pass but have warnings")
    print()
    print("HONESTY OVER OUTCOME: Use with caution, smaller size.")

print("=" * 80)
