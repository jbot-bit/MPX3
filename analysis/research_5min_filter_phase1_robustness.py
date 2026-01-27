"""
5-MINUTE CONFIRMATION FILTER - PHASE 1 ROBUSTNESS TESTING
==========================================================

Tests if 5min confirmation improvement is ROBUST across different contexts.

PHASE 1 VALIDATION:
- Test on 1100 ORB (BOTH_LOST filter)
- Test on 1800 ORB (RSI > 70 filter)
- Compare to L4_CONSOLIDATION results (0900, 1000 ORB)

VALIDATION CRITERIA:
- Improvement must be consistent (+0.05R minimum)
- Must work across multiple contexts
- Must not degrade in any context

HONESTY OVER OUTCOME.
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

print("=" * 80)
print("PHASE 1 ROBUSTNESS TESTING - 5MIN CONFIRMATION FILTER")
print("=" * 80)
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
    orb_end_time += timedelta(minutes=5)  # ORB is 5 minutes long

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
        return {'confirmed': False, 'entry_method': 'NO_ENTRY'}

    # Check if any 5min candle closes outside ORB
    for bar in bars_5m:
        ts_local, high, low, close = bar

        if break_dir == 'UP' and close > orb_high:
            return {'confirmed': True, 'entry_method': '5MIN_CONFIRMED'}
        elif break_dir == 'DOWN' and close < orb_low:
            return {'confirmed': True, 'entry_method': '5MIN_CONFIRMED'}

    return {'confirmed': False, 'entry_method': 'NO_ENTRY'}


# Test contexts
test_contexts = [
    {
        'name': '1100 ORB (BOTH_LOST)',
        'orb_time': '1100',
        'filter_sql': "orb_0900_outcome = 'LOSS' AND orb_1000_outcome = 'LOSS'",
        'rr_values': [1.5],  # Only RR=1.5 validated for 1100
        'best_window_expected': 20  # From L4 results
    },
    {
        'name': '1800 ORB (RSI > 70)',
        'orb_time': '1800',
        'filter_sql': "rsi_at_orb > 70",
        'rr_values': [1.5],  # Only RR=1.5 validated for 1800
        'best_window_expected': 15  # Mid-range guess
    }
]

results_summary = []

for context in test_contexts:
    print(f"{'=' * 80}")
    print(f"TESTING: {context['name']}")
    print(f"{'=' * 80}")
    print()

    orb_time = context['orb_time']
    filter_sql = context['filter_sql']
    rr_values = context['rr_values']

    # Get trades
    orb_col = f'orb_{orb_time}'
    trades = conn.execute(f"""
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
        ORDER BY date_local
    """).fetchall()

    print(f"Found {len(trades)} trades with filter: {context['filter_sql']}")
    print()

    if len(trades) < 30:
        print(f"[SKIP] Insufficient sample size: {len(trades)} < 30")
        print()
        continue

    for rr in rr_values:
        print(f"Testing RR={rr}")
        print("-" * 80)

        # Baseline (current system)
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
            baseline_results.append({
                'outcome': outcome,
                'realized_r': realized_r
            })

        # Calculate baseline metrics
        baseline_wins = [r for r in baseline_results if r['outcome'] == 'WIN']
        baseline_win_rate = len(baseline_wins) / len(baseline_results) if baseline_results else 0
        baseline_expectancy = sum(r['realized_r'] for r in baseline_results) / len(baseline_results) if baseline_results else 0

        print(f"BASELINE (1min entry):")
        print(f"  Trades: {len(baseline_results)} | WR: {baseline_win_rate*100:.1f}% | ExpR: {baseline_expectancy:+.3f}R")
        print()

        # Test optimal window from L4 results
        best_window = context['best_window_expected']

        confirmed_results = []
        no_entry_count = 0

        for trade in trades:
            date_local, orb_high, orb_low, break_dir, outcome = trade

            # Simulate 5min confirmation
            confirmation = simulate_5min_confirmation(
                date_local, orb_time, orb_high, orb_low, break_dir, outcome, best_window
            )

            if confirmation['entry_method'] == 'NO_ENTRY':
                no_entry_count += 1
                continue

            # Trade taken
            if break_dir == 'UP':
                entry, stop = orb_high, orb_low
            else:
                entry, stop = orb_low, orb_high

            stop_dist_points = abs(entry - stop)
            target_dist_points = stop_dist_points * rr

            realized_r = calculate_realized_r(entry, stop, target_dist_points, outcome)
            confirmed_results.append({
                'outcome': outcome,
                'realized_r': realized_r
            })

        # Calculate confirmation metrics
        if confirmed_results:
            conf_wins = [r for r in confirmed_results if r['outcome'] == 'WIN']
            conf_win_rate = len(conf_wins) / len(confirmed_results)
            conf_expectancy = sum(r['realized_r'] for r in confirmed_results) / len(confirmed_results)

            wr_change = (conf_win_rate - baseline_win_rate) * 100
            exp_change = conf_expectancy - baseline_expectancy

            verdict = "IMPROVED" if exp_change > 0.05 else "DEGRADED" if exp_change < -0.05 else "NEUTRAL"

            print(f"  {best_window}min window: {len(confirmed_results)} trades ({no_entry_count} skipped)")
            print(f"    WR: {conf_win_rate*100:.1f}% ({wr_change:+.1f}%) | ExpR: {conf_expectancy:+.3f}R ({exp_change:+.3f}R) [{verdict}]")

            results_summary.append({
                'context': context['name'],
                'orb_time': orb_time,
                'rr': rr,
                'baseline_trades': len(baseline_results),
                'baseline_wr': baseline_win_rate,
                'baseline_exp': baseline_expectancy,
                'confirmed_trades': len(confirmed_results),
                'confirmed_wr': conf_win_rate,
                'confirmed_exp': conf_expectancy,
                'exp_change': exp_change,
                'verdict': verdict
            })
        else:
            print(f"  {best_window}min window: 0 trades (all skipped) [NO DATA]")
            results_summary.append({
                'context': context['name'],
                'orb_time': orb_time,
                'rr': rr,
                'baseline_trades': len(baseline_results),
                'baseline_wr': baseline_win_rate,
                'baseline_exp': baseline_expectancy,
                'confirmed_trades': 0,
                'confirmed_wr': 0,
                'confirmed_exp': 0,
                'exp_change': 0,
                'verdict': 'NO_DATA'
            })

        print()

conn.close()

# Phase 1 Verdict
print()
print("=" * 80)
print("PHASE 1 ROBUSTNESS VERDICT")
print("=" * 80)
print()

improved = [r for r in results_summary if r['verdict'] == 'IMPROVED']
degraded = [r for r in results_summary if r['verdict'] == 'DEGRADED']
neutral = [r for r in results_summary if r['verdict'] == 'NEUTRAL']
no_data = [r for r in results_summary if r['verdict'] == 'NO_DATA']

print(f"IMPROVED: {len(improved)} contexts")
for r in improved:
    print(f"  - {r['context']} RR={r['rr']}: {r['exp_change']:+.3f}R improvement")

print()
print(f"DEGRADED: {len(degraded)} contexts")
for r in degraded:
    print(f"  - {r['context']} RR={r['rr']}: {r['exp_change']:+.3f}R degradation")

print()
print(f"NEUTRAL: {len(neutral)} contexts")
print(f"NO_DATA: {len(no_data)} contexts")

print()
print("-" * 80)

if len(degraded) > 0:
    print("[FAIL] PHASE 1 FAILED: Filter degrades in some contexts")
    print("   Do NOT proceed to Phase 2.")
elif len(improved) == len(results_summary):
    print("[PASS] PHASE 1 PASSED: Filter improves in ALL tested contexts")
    print("   Proceed to Phase 2 (Walk-Forward Validation)")
else:
    print("[MIXED] PHASE 1 MIXED: Filter works in some contexts, neutral in others")
    print("   Proceed with caution to Phase 2")

print()
print("=" * 80)
