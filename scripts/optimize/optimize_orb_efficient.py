"""
OPTIMIZED ORB OPTIMIZATION - Efficient Version

Fixes CPU overload by:
1. Pre-loading all 1-minute bars for each day (single query per day)
2. Caching bars in memory
3. Testing all stop/RR combos on cached data (no repeated queries)
4. Processing one ORB at a time
5. Saving intermediate results

Usage: python optimize_orb_efficient.py 1000
"""

import sys
import duckdb
import pandas as pd
from datetime import datetime, timedelta
import json

DB_PATH = 'data/db/gold.db'
SYMBOL = 'MGC'

COMMISSION = 1.0
SLIPPAGE_TICKS = 5
TICK_SIZE = 0.1
POINT_VALUE = 10.0

def simulate_with_stop_and_costs(bars_1m, orb_high, orb_low, rr, stop_fraction):
    """Simulate with fractional stop and realistic costs"""
    if len(bars_1m) == 0:
        return None

    orb_size = orb_high - orb_low

    # Find entry (close outside)
    entry_idx = None
    for i in range(len(bars_1m)):
        close = float(bars_1m.iloc[i]['close'])

        if close > orb_high or close < orb_low:
            direction = 'UP' if close > orb_high else 'DOWN'
            entry = close
            entry_idx = i
            break

    if entry_idx is None:
        return None

    # Stop at fraction of ORB from entry
    risk = orb_size * stop_fraction

    if direction == 'UP':
        stop = entry - risk
    else:
        stop = entry + risk

    target = entry + (rr * risk) if direction == 'UP' else entry - (rr * risk)

    # Check outcome
    for j in range(entry_idx + 1, len(bars_1m)):
        high = float(bars_1m.iloc[j]['high'])
        low = float(bars_1m.iloc[j]['low'])

        if direction == 'UP':
            if low <= stop:
                outcome_r = -1.0
                break
            elif high >= target:
                outcome_r = rr
                break
        else:
            if high >= stop:
                outcome_r = -1.0
                break
            elif low <= target:
                outcome_r = rr
                break
    else:
        outcome_r = 0.0

    # Subtract costs
    cost_dollars = COMMISSION + SLIPPAGE_TICKS * TICK_SIZE * POINT_VALUE
    cost_r = cost_dollars / (risk * POINT_VALUE)

    return outcome_r - cost_r


if len(sys.argv) < 2:
    print("Usage: python optimize_orb_efficient.py <orb_time>")
    print("Example: python optimize_orb_efficient.py 1000")
    sys.exit(1)

orb_time = sys.argv[1]

ORBS = {
    '0900': (9, 0),
    '1000': (10, 0),
    '1100': (11, 0),
    '1800': (18, 0),
}

if orb_time not in ORBS:
    print(f"Invalid ORB time. Must be one of: {', '.join(ORBS.keys())}")
    sys.exit(1)

hour, minute = ORBS[orb_time]

print("="*80)
print(f"OPTIMIZING {orb_time} ORB (Efficient Version)")
print("="*80)
print()

conn = duckdb.connect(DB_PATH, read_only=True)

# Step 1: Get all days with valid ORBs
query = f"""
    SELECT
        date_local,
        orb_{orb_time}_high as orb_high,
        orb_{orb_time}_low as orb_low
    FROM daily_features_v2
    WHERE instrument = 'MGC'
      AND orb_{orb_time}_high IS NOT NULL
      AND orb_{orb_time}_low IS NOT NULL
    ORDER BY date_local
"""

df_days = conn.execute(query).fetchdf()
total_days = len(df_days)
print(f"Found {total_days} valid trading days")
print()

# Step 2: Pre-load 1-minute bars for ALL days (single efficient query)
print("Pre-loading 1-minute bars for all days...")

# Get date range
min_date = df_days['date_local'].min()
max_date = df_days['date_local'].max()

# Query all bars in one go
bars_query = """
    SELECT
        (ts_utc AT TIME ZONE 'Australia/Brisbane') as ts_local,
        open, high, low, close
    FROM bars_1m
    WHERE symbol = ?
      AND DATE((ts_utc AT TIME ZONE 'Australia/Brisbane')) >= ?
      AND DATE((ts_utc AT TIME ZONE 'Australia/Brisbane')) <= ?
    ORDER BY ts_utc
"""

all_bars = conn.execute(bars_query, [SYMBOL, min_date, max_date]).fetchdf()
all_bars['date_local'] = pd.to_datetime(all_bars['ts_local']).dt.date
all_bars['time_local'] = pd.to_datetime(all_bars['ts_local']).dt.time
conn.close()

print(f"Loaded {len(all_bars):,} 1-minute bars")
print()

# Step 3: Group bars by trading day
print("Grouping bars by trading day...")
bars_by_day = {}

from datetime import time as dt_time

for date in df_days['date_local']:
    # Get bars after ORB completes (from HH:MM+5 to next day HH:00)
    start_time = dt_time(hour, minute+5, 0)
    end_time = dt_time(hour, 0, 0)

    next_day = date + pd.Timedelta(days=1)

    # Filter bars for this trading day window
    day_bars = all_bars[
        ((all_bars['date_local'] == date) & (all_bars['time_local'] >= start_time)) |
        ((all_bars['date_local'] == next_day) & (all_bars['time_local'] <= end_time))
    ].reset_index(drop=True)

    bars_by_day[str(date)] = day_bars

print(f"Cached bars for {len(bars_by_day)} days")
print()

# Test parameters
STOP_FRACTIONS = [0.20, 0.25, 0.33, 0.50, 0.75, 1.00]
RR_VALUES = [1.5, 2.0, 3.0, 4.0, 6.0, 8.0]

print("Testing all stop/RR combinations...")
print()

all_results = []
completed = 0
total_combos = len(STOP_FRACTIONS) * len(RR_VALUES)

for stop_frac in STOP_FRACTIONS:
    for rr in RR_VALUES:
        completed += 1

        # Test this combination on ALL days using cached bars
        results = []

        for idx, row in df_days.iterrows():
            date_str = str(row['date_local'])
            orb_high = row['orb_high']
            orb_low = row['orb_low']

            # Get cached bars for this day
            bars = bars_by_day.get(date_str)

            if bars is not None and len(bars) > 0:
                r_result = simulate_with_stop_and_costs(bars, orb_high, orb_low, rr, stop_frac)

                if r_result is not None:
                    results.append(r_result)

        if len(results) > 0:
            count = len(results)
            total_r = sum(results)
            avg_r = total_r / count
            wins = len([r for r in results if r > 0])
            wr = wins / count * 100
            be_wr = 100 / (rr + 1)

            all_results.append({
                'stop_frac': stop_frac,
                'rr': rr,
                'trades': count,
                'wr': wr,
                'be_wr': be_wr,
                'avg_r': avg_r,
                'total_r': total_r
            })

            # Progress update
            status = f"[{completed}/{total_combos}] Stop={stop_frac:.2f}, RR={rr:.1f}: {count} trades, {wr:.1f}% WR, {avg_r:+.3f} avg R"
            if avg_r > 0.10:
                print(f"{status} *** PROFITABLE ***")
            elif completed % 6 == 0:  # Print every 6th (each stop fraction)
                print(status)

print()
print("="*80)
print("RESULTS")
print("="*80)
print()

df_all = pd.DataFrame(all_results)

# Save raw results to JSON
results_file = f'optimization_results_{orb_time}.json'
with open(results_file, 'w') as f:
    json.dump(all_results, f, indent=2)
print(f"Saved raw results to {results_file}")
print()

# Profitable setups
profitable = df_all[df_all['avg_r'] > 0.10].sort_values('avg_r', ascending=False)

if len(profitable) > 0:
    print(f"Found {len(profitable)} PROFITABLE combinations:")
    print()
    print(profitable[['stop_frac', 'rr', 'trades', 'wr', 'avg_r', 'total_r']].to_string(index=False))
    print()

    best = profitable.iloc[0]
    print("BEST SETUP:")
    print(f"  Stop: {best['stop_frac']:.2f} x ORB")
    print(f"  RR: {best['rr']:.1f}")
    print(f"  Trades: {best['trades']:.0f}")
    print(f"  Win rate: {best['wr']:.1f}% (need {best['be_wr']:.1f}%)")
    print(f"  Avg R: {best['avg_r']:+.3f}")
    print(f"  Total R: {best['total_r']:+.1f}")
else:
    print("NO PROFITABLE SETUPS FOUND")
    print()

    # Show best (even if unprofitable)
    best = df_all.nlargest(1, 'avg_r').iloc[0]
    print("BEST SETUP (still unprofitable):")
    print(f"  Stop: {best['stop_frac']:.2f} x ORB")
    print(f"  RR: {best['rr']:.1f}")
    print(f"  Avg R: {best['avg_r']:+.3f}")
    print(f"  Total R: {best['total_r']:+.1f}")

print()
