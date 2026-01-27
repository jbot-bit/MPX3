"""
5-MINUTE CONFIRMATION FILTER - PHASE 2 WALK-FORWARD VALIDATION
================================================================

Tests if 5min confirmation improvement holds on OUT-OF-SAMPLE data.

PHASE 2 VALIDATION:
- Split data: TRAIN (2020-2024) vs TEST (2025-2026)
- Optimize window parameter on TRAIN set
- Validate on TEST set (unseen data)
- Check if improvement holds out-of-sample

VALIDATION CRITERIA:
- Improvement must hold in test period
- No overfitting (test performance >= 70% of train performance)
- Must pass for L4 and BOTH_LOST contexts

HONESTY OVER OUTCOME - If it doesn't hold, we reject it.
"""

import duckdb
import sys
from datetime import datetime, timedelta
import pytz

sys.path.insert(0, 'C:/Users/sydne/OneDrive/Desktop/MPX2_fresh')
from pipeline.cost_model import COST_MODELS

DB_PATH = 'gold.db'
conn = duckdb.connect(DB_PATH)

# Cost model
MGC_COSTS = COST_MODELS['MGC']
MGC_POINT_VALUE = MGC_COSTS['point_value']
MGC_FRICTION = MGC_COSTS['total_friction']

# Date splits (ACTUAL DATA RANGE: 2024-01-02 to 2026-01-26)
TRAIN_START = '2024-01-01'
TRAIN_END = '2025-06-30'  # 1.5 years train
TEST_START = '2025-07-01'
TEST_END = '2026-01-31'   # ~6 months test

print("=" * 80)
print("PHASE 2 WALK-FORWARD VALIDATION - 5MIN CONFIRMATION FILTER")
print("=" * 80)
print()
print(f"TRAIN period: {TRAIN_START} to {TRAIN_END}")
print(f"TEST period:  {TEST_START} to {TEST_END}")
print()

def calculate_realized_r(entry, stop, target_distance_points, outcome):
    """Calculate realized R using CANONICAL formulas."""
    stop_dist_points = abs(entry - stop)
    realized_risk_dollars = (stop_dist_points * MGC_POINT_VALUE) + MGC_FRICTION
    realized_reward_dollars = (target_distance_points * MGC_POINT_VALUE) - MGC_FRICTION

    if outcome == 'WIN':
        net_pnl = realized_reward_dollars
    else:
        net_pnl = -realized_risk_dollars

    return net_pnl / realized_risk_dollars


def simulate_5min_confirmation(date_local, orb_time, orb_high, orb_low, break_dir, outcome, confirmation_window_minutes):
    """Simulate 5min confirmation filter."""
    tz = pytz.timezone('Australia/Brisbane')

    # Query 5min bars after ORB end
    orb_end_time = datetime.strptime(f"{date_local} {orb_time}", "%Y-%m-%d %H%M")
    orb_end_time = tz.localize(orb_end_time)
    orb_end_time += timedelta(minutes=5)

    window_end_time = orb_end_time + timedelta(minutes=confirmation_window_minutes)

    # Get 5min bars in confirmation window
    bars_5m = conn.execute("""
        SELECT ts_local, high, low, close
        FROM (
            SELECT
                ts_utc AT TIME ZONE 'UTC' AT TIME ZONE 'Australia/Brisbane' as ts_local,
                high, low, close
            FROM bars_5m
            WHERE symbol = 'MGC'
              AND ts_utc AT TIME ZONE 'UTC' AT TIME ZONE 'Australia/Brisbane' >= ?
              AND ts_utc AT TIME ZONE 'UTC' AT TIME ZONE 'Australia/Brisbane' < ?
            ORDER BY ts_utc
        ) subq
    """, [orb_end_time, window_end_time]).fetchall()

    if not bars_5m:
        return {'confirmed': False}

    # Check if any 5min candle closes outside ORB
    for bar in bars_5m:
        ts_local, high, low, close = bar

        if break_dir == 'UP' and close > orb_high:
            return {'confirmed': True}
        elif break_dir == 'DOWN' and close < orb_low:
            return {'confirmed': True}

    return {'confirmed': False}


def test_configuration(trades, orb_time, rr, confirmation_window_minutes):
    """Test a specific configuration and return metrics."""
    # Baseline (1min entry)
    baseline_results = []
    for trade in trades:
        date_local, orb_high, orb_low, break_dir, outcome = trade

        if break_dir == 'UP':
            entry, stop = orb_high, orb_low
        else:
            entry, stop = orb_low, orb_high

        stop_dist_points = abs(entry - stop)
        target_dist_points = stop_dist_points * rr

        realized_r = calculate_realized_r(entry, stop, target_dist_points, outcome)
        baseline_results.append({'outcome': outcome, 'realized_r': realized_r})

    baseline_wins = [r for r in baseline_results if r['outcome'] == 'WIN']
    baseline_wr = len(baseline_wins) / len(baseline_results) if baseline_results else 0
    baseline_exp = sum(r['realized_r'] for r in baseline_results) / len(baseline_results) if baseline_results else 0

    # 5min confirmation
    confirmed_results = []
    no_entry_count = 0

    for trade in trades:
        date_local, orb_high, orb_low, break_dir, outcome = trade

        confirmation = simulate_5min_confirmation(
            date_local, orb_time, orb_high, orb_low, break_dir, outcome, confirmation_window_minutes
        )

        if not confirmation['confirmed']:
            no_entry_count += 1
            continue

        if break_dir == 'UP':
            entry, stop = orb_high, orb_low
        else:
            entry, stop = orb_low, orb_high

        stop_dist_points = abs(entry - stop)
        target_dist_points = stop_dist_points * rr

        realized_r = calculate_realized_r(entry, stop, target_dist_points, outcome)
        confirmed_results.append({'outcome': outcome, 'realized_r': realized_r})

    if not confirmed_results:
        return {
            'baseline_trades': len(baseline_results),
            'baseline_wr': baseline_wr,
            'baseline_exp': baseline_exp,
            'confirmed_trades': 0,
            'confirmed_wr': 0,
            'confirmed_exp': 0,
            'exp_change': 0
        }

    conf_wins = [r for r in confirmed_results if r['outcome'] == 'WIN']
    conf_wr = len(conf_wins) / len(confirmed_results)
    conf_exp = sum(r['realized_r'] for r in confirmed_results) / len(confirmed_results)

    return {
        'baseline_trades': len(baseline_results),
        'baseline_wr': baseline_wr,
        'baseline_exp': baseline_exp,
        'confirmed_trades': len(confirmed_results),
        'confirmed_wr': conf_wr,
        'confirmed_exp': conf_exp,
        'exp_change': conf_exp - baseline_exp
    }


# Test contexts (L4 and BOTH_LOST only, skip RSI)
test_contexts = [
    {
        'name': '0900 ORB (L4_CONSOLIDATION)',
        'orb_time': '0900',
        'filter_sql': "london_type_code = 'L4_CONSOLIDATION'",
        'rr_values': [1.5, 2.0, 2.5, 3.0]
    },
    {
        'name': '1000 ORB (L4_CONSOLIDATION)',
        'orb_time': '1000',
        'filter_sql': "london_type_code = 'L4_CONSOLIDATION'",
        'rr_values': [1.5, 2.0, 2.5, 3.0]
    },
    {
        'name': '1100 ORB (BOTH_LOST)',
        'orb_time': '1100',
        'filter_sql': "orb_0900_outcome = 'LOSS' AND orb_1000_outcome = 'LOSS'",
        'rr_values': [1.5]
    }
]

CONFIRMATION_WINDOWS = [5, 10, 15, 20, 25, 30]

results_summary = []

for context in test_contexts:
    print(f"{'=' * 80}")
    print(f"TESTING: {context['name']}")
    print(f"{'=' * 80}")
    print()

    orb_time = context['orb_time']
    filter_sql = context['filter_sql']

    # Get TRAIN trades
    orb_col = f'orb_{orb_time}'
    train_trades = conn.execute(f"""
        SELECT
            date_local,
            {orb_col}_high,
            {orb_col}_low,
            {orb_col}_break_dir,
            {orb_col}_outcome
        FROM daily_features
        WHERE instrument = 'MGC'
          AND {orb_col}_outcome IS NOT NULL
          AND {orb_col}_break_dir != 'NONE'
          AND ({filter_sql})
          AND date_local >= ?
          AND date_local <= ?
        ORDER BY date_local
    """, [TRAIN_START, TRAIN_END]).fetchall()

    # Get TEST trades
    test_trades = conn.execute(f"""
        SELECT
            date_local,
            {orb_col}_high,
            {orb_col}_low,
            {orb_col}_break_dir,
            {orb_col}_outcome
        FROM daily_features
        WHERE instrument = 'MGC'
          AND {orb_col}_outcome IS NOT NULL
          AND {orb_col}_break_dir != 'NONE'
          AND ({filter_sql})
          AND date_local >= ?
          AND date_local <= ?
        ORDER BY date_local
    """, [TEST_START, TEST_END]).fetchall()

    print(f"TRAIN: {len(train_trades)} trades ({TRAIN_START} to {TRAIN_END})")
    print(f"TEST:  {len(test_trades)} trades ({TEST_START} to {TEST_END})")
    print()

    if len(train_trades) < 20 or len(test_trades) < 10:
        print("[SKIP] Insufficient sample size")
        print()
        continue

    for rr in context['rr_values']:
        print(f"RR={rr}")
        print("-" * 80)

        # TRAIN: Find best window
        train_results = []
        for window in CONFIRMATION_WINDOWS:
            metrics = test_configuration(train_trades, orb_time, rr, window)
            train_results.append({
                'window': window,
                'exp_change': metrics['exp_change'],
                'confirmed_exp': metrics['confirmed_exp'],
                'confirmed_trades': metrics['confirmed_trades']
            })

        # Sort by expectancy improvement
        train_results.sort(key=lambda x: x['exp_change'], reverse=True)
        best_window = train_results[0]['window']
        best_train_improvement = train_results[0]['exp_change']

        print(f"TRAIN: Best window = {best_window}min (+{best_train_improvement:.3f}R)")

        # TEST: Validate best window on unseen data
        test_metrics = test_configuration(test_trades, orb_time, rr, best_window)

        test_improvement = test_metrics['exp_change']
        retention = (test_improvement / best_train_improvement * 100) if best_train_improvement > 0 else 0

        print(f"TEST:  {best_window}min window = {test_metrics['confirmed_exp']:+.3f}R ({test_improvement:+.3f}R improvement)")
        print(f"       Baseline: {test_metrics['baseline_exp']:+.3f}R ({test_metrics['baseline_trades']} trades)")
        print(f"       Confirmed: {test_metrics['confirmed_exp']:+.3f}R ({test_metrics['confirmed_trades']} trades)")
        print(f"       Retention: {retention:.1f}% of train improvement")

        # Verdict
        if test_improvement > 0.05 and retention >= 70:
            verdict = "PASS"
        elif test_improvement > 0:
            verdict = "WEAK"
        else:
            verdict = "FAIL"

        print(f"       Verdict: [{verdict}]")
        print()

        results_summary.append({
            'context': context['name'],
            'orb_time': orb_time,
            'rr': rr,
            'best_window': best_window,
            'train_improvement': best_train_improvement,
            'test_improvement': test_improvement,
            'retention': retention,
            'verdict': verdict,
            'test_trades': test_metrics['confirmed_trades']
        })

conn.close()

# Phase 2 Verdict
print()
print("=" * 80)
print("PHASE 2 WALK-FORWARD VERDICT")
print("=" * 80)
print()

passed = [r for r in results_summary if r['verdict'] == 'PASS']
weak = [r for r in results_summary if r['verdict'] == 'WEAK']
failed = [r for r in results_summary if r['verdict'] == 'FAIL']

print(f"PASSED: {len(passed)} configurations")
for r in passed:
    print(f"  - {r['context']} RR={r['rr']}: {r['best_window']}min window")
    print(f"    Train: +{r['train_improvement']:.3f}R | Test: +{r['test_improvement']:.3f}R ({r['retention']:.0f}% retention)")

print()
print(f"WEAK: {len(weak)} configurations (improvement < 0.05R or retention < 70%)")
for r in weak:
    print(f"  - {r['context']} RR={r['rr']}: +{r['test_improvement']:.3f}R ({r['retention']:.0f}% retention)")

print()
print(f"FAILED: {len(failed)} configurations (no improvement in test)")
for r in failed:
    print(f"  - {r['context']} RR={r['rr']}: {r['test_improvement']:.3f}R")

print()
print("-" * 80)

if len(failed) > 0:
    print("[FAIL] PHASE 2 FAILED: Filter does not hold out-of-sample in some contexts")
    print("   OVERFITTING detected. Do NOT proceed to production.")
elif len(passed) == len(results_summary):
    print("[PASS] PHASE 2 PASSED: Filter holds out-of-sample in ALL contexts")
    print("   Proceed to Phase 3 (Regime Analysis)")
else:
    print("[MIXED] PHASE 2 MIXED: Filter holds in some contexts, weak in others")
    print("   Proceed with caution to Phase 3")

print()
print("=" * 80)
