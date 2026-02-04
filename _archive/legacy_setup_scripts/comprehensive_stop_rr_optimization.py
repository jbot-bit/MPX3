"""
COMPREHENSIVE STOP/RR OPTIMIZATION - ALL ORBs

Tests ALL combinations of:
- Stop fractions: 0.20, 0.25, 0.33, 0.50, 0.75, 1.00
- RR values: 1.5, 2.0, 3.0, 4.0, 6.0, 8.0
- ORBs: 0900, 1000, 1100, 1800

Outputs:
- Best stop/RR combination for each ORB
- Which setups are profitable (avg R > 0.10 after costs)
- Recommended updates to validated_setups
"""

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


print("="*80)
print("COMPREHENSIVE STOP/RR OPTIMIZATION - ALL ORBs")
print("="*80)
print()
print("Testing ALL combinations to find optimal setups")
print()

conn = duckdb.connect(DB_PATH, read_only=True)

# ORB configurations
ORBS = {
    '0900': (9, 0),
    '1000': (10, 0),
    '1100': (11, 0),
    '1800': (18, 0),
}

# Test parameters
STOP_FRACTIONS = [0.20, 0.25, 0.33, 0.50, 0.75, 1.00]
RR_VALUES = [1.5, 2.0, 3.0, 4.0, 6.0, 8.0]

all_results = []

for orb_time, (hour, minute) in ORBS.items():
    print(f"\n{'='*80}")
    print(f"TESTING {orb_time} ORB")
    print(f"{'='*80}\n")

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

    for stop_frac in STOP_FRACTIONS:
        print(f"\n  Testing stop fraction = {stop_frac:.2f}...")

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

                # Calculate breakeven WR
                be_wr = 100 / (rr + 1)

                all_results.append({
                    'orb_time': orb_time,
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
                    print(f"    RR={rr:.1f}: {count} trades, {wr:.1f}% WR (BE={be_wr:.1f}%), {avg_r:+.3f} avg R, {total_r:+.1f}R *** PROFITABLE ***")

conn.close()

# Analysis
df_all = pd.DataFrame(all_results)

print("\n" + "="*80)
print("PROFITABLE SETUPS (avg R > 0.10 post-cost)")
print("="*80)
print()

profitable = df_all[df_all['avg_r'] > 0.10].sort_values('avg_r', ascending=False)

if len(profitable) > 0:
    print(profitable.to_string(index=False))
    print()
    print(f"Found {len(profitable)} profitable combinations")
else:
    print("NO PROFITABLE SETUPS FOUND")
    print()
    print("All combinations are unprofitable after $2.50 costs.")

print()

# Best setup per ORB
print("="*80)
print("BEST SETUP PER ORB")
print("="*80)
print()

for orb_time in ORBS.keys():
    orb_results = df_all[df_all['orb_time'] == orb_time]
    best = orb_results.nlargest(1, 'avg_r').iloc[0]

    print(f"{orb_time} ORB:")
    print(f"  Stop: {best['stop_frac']:.2f} × ORB")
    print(f"  RR: {best['rr']:.1f}")
    print(f"  Trades: {best['trades']:.0f}")
    print(f"  Win rate: {best['wr']:.1f}% (need {best['be_wr']:.1f}%)")
    print(f"  Avg R: {best['avg_r']:+.3f}")
    print(f"  Total R: {best['total_r']:+.1f}")

    if best['avg_r'] > 0.10:
        print(f"  *** PROFITABLE ***")
    else:
        print(f"  (Unprofitable)")

    print()

# Summary statistics
print("="*80)
print("ANALYSIS: What makes setups profitable?")
print("="*80)
print()

if len(profitable) > 0:
    print("Stop fraction distribution:")
    stop_counts = profitable.groupby('stop_frac').size().sort_values(ascending=False)
    for stop, count in stop_counts.items():
        pct = count / len(profitable) * 100
        print(f"  {stop:.2f}: {count} setups ({pct:.1f}%)")

    print()
    print("RR distribution:")
    rr_counts = profitable.groupby('rr').size().sort_values(ascending=False)
    for rr, count in rr_counts.items():
        pct = count / len(profitable) * 100
        print(f"  {rr:.1f}: {count} setups ({pct:.1f}%)")

    print()
    print("ORB distribution:")
    orb_counts = profitable.groupby('orb_time').size().sort_values(ascending=False)
    for orb, count in orb_counts.items():
        pct = count / len(profitable) * 100
        print(f"  {orb}: {count} setups ({pct:.1f}%)")

    print()

    # Optimal ranges
    print("OPTIMAL RANGES:")
    print(f"  Stop fraction: {profitable['stop_frac'].min():.2f} to {profitable['stop_frac'].max():.2f}")
    print(f"  RR: {profitable['rr'].min():.1f} to {profitable['rr'].max():.1f}")
    print(f"  Win rate: {profitable['wr'].min():.1f}% to {profitable['wr'].max():.1f}%")
    print()

# Recommendations for validated_setups
print("="*80)
print("RECOMMENDED UPDATES TO validated_setups")
print("="*80)
print()

if len(profitable) > 0:
    print("Replace current MGC setups with these profitable combinations:")
    print()

    for idx, row in profitable.nlargest(10, 'avg_r').iterrows():
        # Map stop fraction to sl_mode
        if row['stop_frac'] >= 0.9:
            sl_mode = 'FULL'
        elif 0.4 <= row['stop_frac'] < 0.6:
            sl_mode = 'HALF'
        elif row['stop_frac'] <= 0.35:
            sl_mode = 'QUARTER'
        else:
            sl_mode = f"{int(row['stop_frac']*100)}PCT"

        print(f"INSERT INTO validated_setups (instrument, orb_time, rr, sl_mode, win_rate, expected_r, sample_size)")
        print(f"  VALUES ('MGC', '{row['orb_time']}', {row['rr']:.1f}, '{sl_mode}', {row['wr']:.1f}, {row['avg_r']:.3f}, {row['trades']:.0f});")

    print()
else:
    print("No profitable setups found. Need to:")
    print("  1. Add filters (session type, ORB size, RSI)")
    print("  2. Test different instruments (NQ, MPL)")
    print("  3. Consider advanced management (BE SL, partial exits)")

print()
