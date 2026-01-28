"""
NIGHT ORB BASELINE VALIDATION (Discovery AI Framework - Phase 4)
=================================================================

Following discovery_ai.txt framework:
- Phase 1: ML hypothesis generation (DONE - research_night_orb_comprehensive.py)
- Phase 2: Hypothesis distillation (DONE - identified 2300/0030 baselines)
- Phase 3: Baseline family definition (DONE - ORB_NIGHT family)
- Phase 4: Baseline validation (THIS SCRIPT)

Testing two baseline candidates:
1. 2300 ORB RR=3.0 (no filters)
2. 0030 ORB RR=3.0 (no filters)

VALIDATION FRAMEWORK:
1. Temporal splits (2024, 2025, 2026)
2. Walk-forward splits (train/test)
3. Regime splits (volatility)
4. Stress tests (+25%, +50% costs)

HONESTY OVER OUTCOME: These are IN-SAMPLE ML findings. Must prove robustness.
"""

import duckdb
import sys
import numpy as np
from datetime import date

sys.path.insert(0, 'pipeline')
from cost_model import get_cost_model, get_instrument_specs

DB_PATH = 'data/db/gold.db'

# CANONICAL COST MODEL
mgc_specs = get_instrument_specs('MGC')
mgc_costs = get_cost_model('MGC', stress_level='normal')
POINT_VALUE = mgc_specs['point_value']
FRICTION = mgc_costs['total_friction']

print("=" * 80)
print("NIGHT ORB BASELINE VALIDATION (Discovery AI Framework)")
print("=" * 80)
print()
print(f"Cost Model: ${FRICTION:.2f} RT (honest double-spread)")
print(f"Approval Threshold: +0.15R at ${FRICTION:.2f} AND survives +50% stress")
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

        if (orb_high is None or orb_low is None or
            break_dir is None or outcome is None):
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


def validate_baseline(orb_name, orb_data, rr, friction):
    """Run full 7-phase validation on baseline."""
    print(f"\n{'=' * 80}")
    print(f"VALIDATING: {orb_name} ORB RR={rr} (BASELINE - NO FILTERS)")
    print("=" * 80)

    # PHASE 1: Sample Size
    print("\nPHASE 1: Sample Size Check")
    print("-" * 80)
    n = len(orb_data)
    print(f"Sample size: {n}")
    if n < 30:
        print("[REJECT] Sample size < 30")
        return {'classification': 'BASELINE_REJECTED', 'reason': 'N < 30'}
    print("[PASS] Sample size >= 30")

    # PHASE 2: Baseline Expectancy
    print("\nPHASE 2: Baseline Expectancy")
    print("-" * 80)
    exp_baseline, _ = calculate_expectancy(orb_data, rr, POINT_VALUE, friction)
    print(f"Expectancy at ${friction:.2f}: {exp_baseline:+.3f}R")

    if exp_baseline < 0.15:
        print(f"[REJECT] Below +0.15R threshold")
        return {'classification': 'BASELINE_REJECTED', 'reason': f'ExpR {exp_baseline:+.3f}R < +0.15R'}
    print("[PASS] Above +0.15R threshold")

    # PHASE 3: Stress Testing
    print("\nPHASE 3: Stress Testing")
    print("-" * 80)
    friction_25 = friction * 1.25
    friction_50 = friction * 1.50

    exp_25, _ = calculate_expectancy(orb_data, rr, POINT_VALUE, friction_25)
    exp_50, _ = calculate_expectancy(orb_data, rr, POINT_VALUE, friction_50)

    print(f"+25% costs (${friction_25:.2f}): {exp_25:+.3f}R")
    print(f"+50% costs (${friction_50:.2f}): {exp_50:+.3f}R")

    if exp_50 < 0.15:
        print("[REJECT] Fails +50% stress test")
        return {
            'classification': 'BASELINE_REJECTED',
            'reason': f'Passes ${friction:.2f} ({exp_baseline:+.3f}R) but fails +50% stress ({exp_50:+.3f}R)'
        }
    print("[PASS] Survives +50% stress")

    # PHASE 4: Temporal Validation
    print("\nPHASE 4: Temporal Validation")
    print("-" * 80)
    orb_data['year'] = orb_data['date_local'].apply(lambda x: str(x)[:4])
    years = orb_data['year'].unique()

    temporal_fail = False
    for year in sorted(years):
        year_data = orb_data[orb_data['year'] == year]
        if len(year_data) < 10:
            print(f"  {year}: {len(year_data)} trades (skip - too few)")
            continue

        exp_year, n_year = calculate_expectancy(year_data, rr, POINT_VALUE, friction)
        print(f"  {year}: {n_year} trades, {exp_year:+.3f}R")

        if exp_year < 0:
            temporal_fail = True

    if temporal_fail:
        print("[WARN] Negative in some periods (edge may be time-dependent)")
    else:
        print("[PASS] Positive across all time periods")

    # PHASE 5: Walk-Forward Validation
    print("\nPHASE 5: Walk-Forward Validation")
    print("-" * 80)

    # Split: 2024-2025 H1 = train, 2025 H2-2026 = test
    train = orb_data[orb_data['date_local'] < '2025-07-01']
    test = orb_data[orb_data['date_local'] >= '2025-07-01']

    exp_train, n_train = calculate_expectancy(train, rr, POINT_VALUE, friction)
    exp_test, n_test = calculate_expectancy(test, rr, POINT_VALUE, friction)

    print(f"Train (2024-2025 H1): {n_train} trades, {exp_train:+.3f}R")
    print(f"Test (2025 H2-2026): {n_test} trades, {exp_test:+.3f}R")

    if n_test < 20:
        print("[WARN] Small test sample")

    if exp_test < 0:
        print("[REJECT] Negative out-of-sample (overfitting detected)")
        return {
            'classification': 'BASELINE_REJECTED',
            'reason': f'In-sample {exp_train:+.3f}R, but out-of-sample {exp_test:+.3f}R (overfitting)'
        }

    retention = (exp_test / exp_train * 100) if exp_train > 0 else 0
    print(f"Retention: {retention:.0f}% (out-of-sample / in-sample)")

    if retention < 50:
        print("[WARN] Low retention (possible overfitting)")
    else:
        print("[PASS] Good out-of-sample retention")

    # PHASE 6: Regime Validation (Volatility)
    print("\nPHASE 6: Regime Validation (Volatility)")
    print("-" * 80)

    median_ny_range = orb_data['ny_range'].median()
    low_vol = orb_data[orb_data['ny_range'] < median_ny_range]
    high_vol = orb_data[orb_data['ny_range'] >= median_ny_range]

    exp_low, n_low = calculate_expectancy(low_vol, rr, POINT_VALUE, friction)
    exp_high, n_high = calculate_expectancy(high_vol, rr, POINT_VALUE, friction)

    print(f"Low volatility ({n_low} trades): {exp_low:+.3f}R")
    print(f"High volatility ({n_high} trades): {exp_high:+.3f}R")

    if exp_low < 0 or exp_high < 0:
        print("[WARN] Negative in some regimes")
    else:
        print("[PASS] Positive in both regimes")

    # FINAL CLASSIFICATION
    print("\nFINAL CLASSIFICATION")
    print("-" * 80)
    print(f"Classification: BASELINE_APPROVED")
    print(f"Reason: Passes ${friction:.2f} ({exp_baseline:+.3f}R) AND survives +50% stress ({exp_50:+.3f}R)")
    print(f"Out-of-sample: {exp_test:+.3f}R ({retention:.0f}% retention)")

    return {
        'classification': 'BASELINE_APPROVED',
        'expectancy': exp_baseline,
        'exp_stress_50': exp_50,
        'exp_test': exp_test,
        'retention': retention,
        'n': n
    }


# Connect to database
conn = duckdb.connect(str(DB_PATH), read_only=True)

# Load night ORB data
query = """
SELECT
    date_local,
    orb_2300_high, orb_2300_low, orb_2300_break_dir, orb_2300_outcome,
    orb_0030_high, orb_0030_low, orb_0030_break_dir, orb_0030_outcome,
    ny_range
FROM daily_features
WHERE instrument = 'MGC'
    AND date_local >= '2024-01-02'
    AND date_local <= '2026-01-26'
ORDER BY date_local
"""

df = conn.execute(query).df()
conn.close()

# TEST 2300 ORB BASELINE
print("\n\n")
orb_2300 = df[df['orb_2300_outcome'].notna()].copy()
orb_2300['orb_high'] = orb_2300['orb_2300_high']
orb_2300['orb_low'] = orb_2300['orb_2300_low']
orb_2300['break_dir'] = orb_2300['orb_2300_break_dir']
orb_2300['outcome'] = orb_2300['orb_2300_outcome']

result_2300 = validate_baseline('2300', orb_2300, rr=3.0, friction=FRICTION)

# TEST 0030 ORB BASELINE
print("\n\n")
orb_0030 = df[df['orb_0030_outcome'].notna()].copy()
orb_0030['orb_high'] = orb_0030['orb_0030_high']
orb_0030['orb_low'] = orb_0030['orb_0030_low']
orb_0030['break_dir'] = orb_0030['orb_0030_break_dir']
orb_0030['outcome'] = orb_0030['orb_0030_outcome']

result_0030 = validate_baseline('0030', orb_0030, rr=3.0, friction=FRICTION)

# SUMMARY
print("\n" + "=" * 80)
print("NIGHT ORB BASELINE VALIDATION SUMMARY")
print("=" * 80)
print()
print(f"2300 ORB RR=3.0: {result_2300['classification']}")
if result_2300['classification'] == 'BASELINE_APPROVED':
    print(f"  Expectancy: {result_2300['expectancy']:+.3f}R")
    print(f"  Stress +50%: {result_2300['exp_stress_50']:+.3f}R")
    print(f"  Out-of-sample: {result_2300['exp_test']:+.3f}R ({result_2300['retention']:.0f}% retention)")
else:
    print(f"  Reason: {result_2300['reason']}")

print()
print(f"0030 ORB RR=3.0: {result_0030['classification']}")
if result_0030['classification'] == 'BASELINE_APPROVED':
    print(f"  Expectancy: {result_0030['expectancy']:+.3f}R")
    print(f"  Stress +50%: {result_0030['exp_stress_50']:+.3f}R")
    print(f"  Out-of-sample: {result_0030['exp_test']:+.3f}R ({result_0030['retention']:.0f}% retention)")
else:
    print(f"  Reason: {result_0030['reason']}")

print()
print("=" * 80)
print("HONESTY OVER OUTCOME: Validation complete.")
print("=" * 80)
