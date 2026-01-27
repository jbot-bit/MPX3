"""
STOP FRACTION SWEEP

Test different stop distances to find optimal:
- 1.00 (full ORB) - baseline
- 0.75 (3/4 ORB)
- 0.50 (half ORB) - already in validated_setups
- 0.33 (1/3 ORB)
- 0.25 (1/4 ORB) - showed +93.5R improvement!
- 0.20 (1/5 ORB)

For each, calculate:
- Win rate needed for profitability
- Actual win rate achieved
- Total R
- Optimal RR for that stop distance
"""

import duckdb
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

DB_PATH = 'data/db/gold.db'
SYMBOL = 'MGC'

def simulate_with_stop_fraction(bars_1m, orb_high, orb_low, rr, stop_fraction):
    """Simulate with fractional stop"""
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
                return -1.0
            elif high >= target:
                return rr
        else:
            if high >= stop:
                return -1.0
            elif low <= target:
                return rr

    return 0.0


print("="*80)
print("STOP FRACTION SWEEP")
print("="*80)
print()
print("Testing different stop distances from 1.00 (full ORB) down to 0.20 (1/5 ORB)")
print()

conn = duckdb.connect(DB_PATH, read_only=True)

# Test on 1000 ORB
orb_time = '1000'
hour, minute = 10, 0

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

print(f"Testing {orb_time} ORB on {len(df)} days")
print()

# Test multiple stop fractions and RR values
stop_fractions = [1.00, 0.75, 0.50, 0.33, 0.25, 0.20]
rr_values = [1.5, 2.0, 3.0, 4.0, 6.0, 8.0]

all_results = []

for stop_frac in stop_fractions:
    print(f"Testing stop fraction = {stop_frac:.2f} ({stop_frac*100:.0f}% of ORB)")
    print("-" * 60)

    for rr in rr_values:
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

            r_result = simulate_with_stop_fraction(bars, orb_high, orb_low, rr, stop_frac)

            if r_result is not None:
                results.append(r_result)

        if len(results) > 0:
            count = len(results)
            total_r = sum(results)
            avg_r = total_r / count
            wins = len([r for r in results if r > 0])
            wr = wins / count * 100

            # Calculate breakeven WR for this RR
            # WR × RR + (1-WR) × (-1) = 0
            # WR × RR - 1 + WR = 0
            # WR × (RR + 1) = 1
            # WR = 1 / (RR + 1)
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

            # Print if profitable (avg R > 0.05)
            if avg_r > 0.05:
                print(f"  RR={rr:.1f}: {count} trades, {wr:.1f}% WR (BE={be_wr:.1f}%), {avg_r:+.3f} avg R, {total_r:+.1f}R total *** PROFITABLE ***")

    print()

conn.close()

# Summary table
print("="*80)
print("SUMMARY: Best combinations")
print("="*80)
print()

df_all = pd.DataFrame(all_results)

# Filter for profitable setups (avg R > 0.10)
profitable = df_all[df_all['avg_r'] > 0.10].sort_values('total_r', ascending=False)

if len(profitable) > 0:
    print("PROFITABLE SETUPS (avg R > 0.10):")
    print()
    print(profitable[['stop_frac', 'rr', 'trades', 'wr', 'be_wr', 'avg_r', 'total_r']].to_string(index=False))
    print()

    # Best setup
    best = profitable.iloc[0]
    print(f"BEST SETUP:")
    print(f"  Stop: {best['stop_frac']:.2f} × ORB")
    print(f"  RR: {best['rr']:.1f}")
    print(f"  Win rate: {best['wr']:.1f}% (need {best['be_wr']:.1f}% to break even)")
    print(f"  Avg R: {best['avg_r']:+.3f}")
    print(f"  Total R: {best['total_r']:+.1f} over {best['trades']:.0f} trades")
else:
    print("NO PROFITABLE SETUPS FOUND")
    print()
    print("All combinations are unprofitable.")
    print("Need to:")
    print("  1. Add filters (session type, ORB size, RSI)")
    print("  2. Reduce costs (better broker, limit orders)")
    print("  3. Test different instruments (NQ, MPL)")

print()
