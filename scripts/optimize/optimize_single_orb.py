"""
OPTIMIZE SINGLE ORB - Efficient version

Test one ORB at a time to avoid threading issues.
Usage: python optimize_single_orb.py 1000
"""

import sys
import duckdb
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

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
    for i, row in bars_1m.iterrows():
        close = float(row['close'])

        if close > orb_high or close < orb_low:
            direction = 'UP' if close > orb_high else 'DOWN'
            entry = close
            entry_bar = i
            break
    else:
        return None

    # Stop at fraction of ORB from entry
    risk = orb_size * stop_fraction

    if direction == 'UP':
        stop = entry - risk
    else:
        stop = entry + risk

    target = entry + (rr * risk) if direction == 'UP' else entry - (rr * risk)

    # Check outcome
    for j in range(entry_bar + 1, len(bars_1m)):
        row = bars_1m.iloc[j]
        high = float(row['high'])
        low = float(row['low'])

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
    print("Usage: python optimize_single_orb.py <orb_time>")
    print("Example: python optimize_single_orb.py 1000")
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
print(f"OPTIMIZING {orb_time} ORB")
print("="*80)
print()

conn = duckdb.connect(DB_PATH, read_only=True)

query = f"""
    SELECT
        date_local,
        orb_{orb_time}_high as orb_high,
        orb_{orb_time}_low as orb_low
    FROM daily_features
    WHERE instrument = 'MGC'
      AND orb_{orb_time}_high IS NOT NULL
      AND orb_{orb_time}_low IS NOT NULL
    ORDER BY date_local
"""

df = conn.execute(query).fetchdf()
print(f"Loaded {len(df)} days")
print()

# Test parameters
STOP_FRACTIONS = [0.20, 0.25, 0.33, 0.50, 0.75, 1.00]
RR_VALUES = [1.5, 2.0, 3.0, 4.0, 6.0, 8.0]

all_results = []

for stop_frac in STOP_FRACTIONS:
    print(f"Testing stop fraction = {stop_frac:.2f}...")

    for rr in RR_VALUES:
        results = []

        for idx, row in df.iterrows():
            date_local = pd.to_datetime(row['date_local']).date()
            orb_high = row['orb_high']
            orb_low = row['orb_low']

            start_dt = datetime.combine(date_local, datetime.min.time()).replace(hour=hour, minute=minute+5)
            start_time = start_dt.strftime("%Y-%m-%d %H:%M:%S")
            end_dt = datetime.combine(date_local + timedelta(days=1), datetime.min.time()).replace(hour=hour)
            end_time = end_dt.strftime("%Y-%m-%d %H:%M:%S")

            bars_query = """
                SELECT
                    (ts_utc AT TIME ZONE 'Australia/Brisbane') as ts_local,
                    open, high, low, close
                FROM bars_1m
                WHERE symbol = ?
                  AND (ts_utc AT TIME ZONE 'Australia/Brisbane') > CAST(? AS TIMESTAMP)
                  AND (ts_utc AT TIME ZONE 'Australia/Brisbane') <= CAST(? AS TIMESTAMP)
                ORDER BY ts_local
            """

            bars = conn.execute(bars_query, [SYMBOL, start_time, end_time]).fetchdf()

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

            # Print if profitable
            if avg_r > 0.10:
                print(f"  RR={rr:.1f}: {count} trades, {wr:.1f}% WR (BE={be_wr:.1f}%), {avg_r:+.3f} avg R, {total_r:+.1f}R *** PROFITABLE ***")

conn.close()

print()
print("="*80)
print("RESULTS")
print("="*80)
print()

df_all = pd.DataFrame(all_results)

# Profitable setups
profitable = df_all[df_all['avg_r'] > 0.10].sort_values('avg_r', ascending=False)

if len(profitable) > 0:
    print(f"Found {len(profitable)} profitable combinations:")
    print()
    print(profitable[['stop_frac', 'rr', 'trades', 'wr', 'avg_r', 'total_r']].to_string(index=False))
    print()

    best = profitable.iloc[0]
    print("BEST SETUP:")
    print(f"  Stop: {best['stop_frac']:.2f} × ORB")
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
    print(f"  Stop: {best['stop_frac']:.2f} × ORB")
    print(f"  RR: {best['rr']:.1f}")
    print(f"  Avg R: {best['avg_r']:+.3f}")
    print(f"  Total R: {best['total_r']:+.1f}")

print()
