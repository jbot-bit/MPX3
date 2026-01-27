"""
5-MINUTE CONFIRMATION FILTER RESEARCH
======================================

Tests if requiring a 5-minute candle to confirm 1-minute entry improves edge.

HYPOTHESIS:
- Current: Entry on 1min close outside ORB (may catch false breakouts)
- Proposed: Entry on 1min close BUT require 5min candle to ALSO close outside ORB within X minutes
- If no 5min confirmation within X minutes: Cancel trade (no entry)

RESEARCH QUESTIONS:
1. What's the optimal X (wait time for 5min confirmation)?
2. Does this improve win rate?
3. Does this hurt realized R (by missing fast moves)?
4. Net effect on expectancy?
5. Does it work for all ORB times or only some?

METHODOLOGY:
- Test on L4_CONSOLIDATION trades (0900, 1000 ORB)
- Test multiple X values: 5, 10, 15, 20, 25, 30 minutes
- Compare: Current system vs Confirmation system
- Metrics: Win rate, Realized R (WIN), Realized R (LOSS), Expectancy
"""

import duckdb
import sys
from datetime import datetime, timedelta

sys.path.insert(0, 'C:/Users/sydne/OneDrive/Desktop/MPX2_fresh')
from pipeline.cost_model import COST_MODELS

DB_PATH = 'gold.db'
conn = duckdb.connect(DB_PATH)

# Cost model
MGC_COSTS = COST_MODELS['MGC']
MGC_POINT_VALUE = MGC_COSTS['point_value']
MGC_FRICTION = MGC_COSTS['total_friction']

print("=" * 80)
print("5-MINUTE CONFIRMATION FILTER RESEARCH")
print("=" * 80)
print()
print(f"Cost Model: ${MGC_FRICTION:.2f} RT, ${MGC_POINT_VALUE:.2f}/point")
print()

# Test parameters
ORB_TIMES = ['0900', '1000']
RR_VALUES = [1.5, 2.0, 2.5, 3.0]
CONFIRMATION_WINDOWS = [5, 10, 15, 20, 25, 30]  # minutes

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


def simulate_5min_confirmation(date_local, orb_time, orb_high, orb_low, break_dir, outcome, rr, confirmation_window_minutes):
    """
    Simulate 5min confirmation filter.

    Returns:
        dict with:
            - 'confirmed': bool (did 5min candle close outside ORB within window?)
            - 'confirmation_minutes': int (how many minutes until confirmation)
            - 'entry_method': str ('1MIN' or '5MIN_CONFIRMED' or 'NO_ENTRY')
    """
    import pytz
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
        return {
            'confirmed': False,
            'confirmation_minutes': None,
            'entry_method': 'NO_ENTRY',
            'reason': 'No 5min bars in window'
        }

    # Check if any 5min candle closes outside ORB
    for bar in bars_5m:
        ts_local, high, low, close = bar

        # Check if close is outside ORB range
        if break_dir == 'UP' and close > orb_high:
            minutes_elapsed = int((ts_local - orb_end_time).total_seconds() / 60)
            return {
                'confirmed': True,
                'confirmation_minutes': minutes_elapsed,
                'entry_method': '5MIN_CONFIRMED',
                'reason': f'5min close above ORB at +{minutes_elapsed}min'
            }
        elif break_dir == 'DOWN' and close < orb_low:
            minutes_elapsed = int((ts_local - orb_end_time).total_seconds() / 60)
            return {
                'confirmed': True,
                'confirmation_minutes': minutes_elapsed,
                'entry_method': '5MIN_CONFIRMED',
                'reason': f'5min close below ORB at +{minutes_elapsed}min'
            }

    # No 5min confirmation within window
    return {
        'confirmed': False,
        'confirmation_minutes': None,
        'entry_method': 'NO_ENTRY',
        'reason': f'No 5min close outside ORB within {confirmation_window_minutes}min'
    }


# Store results
all_results = []

for orb_time in ORB_TIMES:
    print(f"{'=' * 80}")
    print(f"TESTING {orb_time} ORB")
    print(f"{'=' * 80}")
    print()

    # Get L4_CONSOLIDATION trades
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
          AND london_type_code = 'L4_CONSOLIDATION'
        ORDER BY date_local
    """).fetchall()

    print(f"Found {len(trades)} L4_CONSOLIDATION trades")
    print()

    for rr in RR_VALUES:
        print(f"Testing RR={rr}")
        print("-" * 80)

        # Baseline (current system - 1min entry)
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
        baseline_losses = [r for r in baseline_results if r['outcome'] == 'LOSS']
        baseline_win_rate = len(baseline_wins) / len(baseline_results) if baseline_results else 0
        baseline_avg_win = sum(r['realized_r'] for r in baseline_wins) / len(baseline_wins) if baseline_wins else 0
        baseline_avg_loss = sum(r['realized_r'] for r in baseline_losses) / len(baseline_losses) if baseline_losses else 0
        baseline_expectancy = sum(r['realized_r'] for r in baseline_results) / len(baseline_results) if baseline_results else 0

        print(f"BASELINE (1min entry):")
        print(f"  Trades: {len(baseline_results)} | WR: {baseline_win_rate*100:.1f}% | ExpR: {baseline_expectancy:+.3f}R")
        print(f"  Avg WIN: {baseline_avg_win:+.3f}R | Avg LOSS: {baseline_avg_loss:+.3f}R")
        print()

        # Test each confirmation window
        for window_minutes in CONFIRMATION_WINDOWS:
            confirmed_results = []
            no_entry_count = 0

            for trade in trades:
                date_local, orb_high, orb_low, break_dir, outcome = trade

                # Simulate 5min confirmation
                confirmation = simulate_5min_confirmation(
                    date_local, orb_time, orb_high, orb_low, break_dir, outcome, rr, window_minutes
                )

                if confirmation['entry_method'] == 'NO_ENTRY':
                    no_entry_count += 1
                    continue  # Trade not taken

                # Trade taken (5min confirmed)
                if break_dir == 'UP':
                    entry, stop = orb_high, orb_low
                else:
                    entry, stop = orb_low, orb_high

                stop_dist_points = abs(entry - stop)
                target_dist_points = stop_dist_points * rr

                realized_r = calculate_realized_r(entry, stop, target_dist_points, outcome)
                confirmed_results.append({
                    'outcome': outcome,
                    'realized_r': realized_r,
                    'confirmation_minutes': confirmation['confirmation_minutes']
                })

            # Calculate confirmation metrics
            if confirmed_results:
                conf_wins = [r for r in confirmed_results if r['outcome'] == 'WIN']
                conf_losses = [r for r in confirmed_results if r['outcome'] == 'LOSS']
                conf_win_rate = len(conf_wins) / len(confirmed_results)
                conf_avg_win = sum(r['realized_r'] for r in conf_wins) / len(conf_wins) if conf_wins else 0
                conf_avg_loss = sum(r['realized_r'] for r in conf_losses) / len(conf_losses) if conf_losses else 0
                conf_expectancy = sum(r['realized_r'] for r in confirmed_results) / len(confirmed_results)

                # Compare to baseline
                wr_change = (conf_win_rate - baseline_win_rate) * 100
                exp_change = conf_expectancy - baseline_expectancy

                verdict = "BETTER" if conf_expectancy > baseline_expectancy else "WORSE"

                print(f"  {window_minutes}min window: {len(confirmed_results)} trades ({no_entry_count} skipped)")
                print(f"    WR: {conf_win_rate*100:.1f}% ({wr_change:+.1f}%) | ExpR: {conf_expectancy:+.3f}R ({exp_change:+.3f}R) [{verdict}]")
            else:
                print(f"  {window_minutes}min window: 0 trades (all skipped) [NO DATA]")

            # Store result
            all_results.append({
                'orb_time': orb_time,
                'rr': rr,
                'window_minutes': window_minutes,
                'baseline_trades': len(baseline_results),
                'baseline_wr': baseline_win_rate,
                'baseline_exp': baseline_expectancy,
                'confirmed_trades': len(confirmed_results) if confirmed_results else 0,
                'confirmed_wr': conf_win_rate if confirmed_results else 0,
                'confirmed_exp': conf_expectancy if confirmed_results else 0,
                'skipped_trades': no_entry_count,
                'wr_change': wr_change if confirmed_results else 0,
                'exp_change': exp_change if confirmed_results else 0
            })

        print()

conn.close()

# Summary
print()
print("=" * 80)
print("SUMMARY - BEST CONFIGURATIONS")
print("=" * 80)
print()

# Find best configurations for each ORB/RR combo
for orb_time in ORB_TIMES:
    for rr in RR_VALUES:
        orb_rr_results = [r for r in all_results if r['orb_time'] == orb_time and r['rr'] == rr]

        if not orb_rr_results:
            continue

        # Sort by expectancy improvement
        orb_rr_results.sort(key=lambda x: x['exp_change'], reverse=True)
        best = orb_rr_results[0]

        if best['exp_change'] > 0:
            print(f"{orb_time} RR={rr}:")
            print(f"  BEST: {best['window_minutes']}min window")
            print(f"  Baseline: {best['baseline_trades']} trades, {best['baseline_wr']*100:.1f}% WR, {best['baseline_exp']:+.3f}R")
            print(f"  Confirmed: {best['confirmed_trades']} trades, {best['confirmed_wr']*100:.1f}% WR, {best['confirmed_exp']:+.3f}R")
            print(f"  Improvement: {best['wr_change']:+.1f}% WR, {best['exp_change']:+.3f}R ExpR")
            print()

print()
print("=" * 80)
print("RECOMMENDATION")
print("=" * 80)
print()

# Overall recommendation
improvements = [r for r in all_results if r['exp_change'] > 0.05]  # Meaningful improvement threshold

if improvements:
    print(f"POSITIVE RESULT: {len(improvements)} configurations show >+0.05R improvement")
    print()
    print("Consider implementing 5min confirmation filter with these parameters:")
    for imp in improvements[:5]:  # Top 5
        print(f"  - {imp['orb_time']} RR={imp['rr']} with {imp['window_minutes']}min window: {imp['exp_change']:+.3f}R improvement")
else:
    print("NEGATIVE RESULT: No configurations show meaningful improvement (>+0.05R)")
    print()
    print("Recommendation: KEEP current 1min entry system (no 5min confirmation needed)")

print()
print("=" * 80)
