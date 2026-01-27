"""
TEST FILTERS ON OPTIMAL SETUPS

After finding optimal stop/RR combinations, test if filters improve them further.

Filters to test:
- Session type: CONSOLIDATION, SWEEP_HIGH, SWEEP_LOW, EXPANSION
- RSI: > 70, < 30
- ORB size: Large (>1.5 ATR), Small (<0.8 ATR)
- Combinations: CONSOLIDATION + Small ORB, etc.

For each filter:
- Compare filtered vs unfiltered performance
- Only implement if improvement > 0.05R per trade (worth complexity)
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

    # Stop at fraction of ORB
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


# OPTIMAL SETUPS (manually input best from optimization)
# Replace these with actual results after optimization completes
OPTIMAL_SETUPS = {
    '0900': {'stop_frac': 0.25, 'rr': 6.0},  # Placeholder
    '1000': {'stop_frac': 0.25, 'rr': 8.0},  # Known from earlier test
    '1100': {'stop_frac': 0.25, 'rr': 3.0},  # Placeholder
    '1800': {'stop_frac': 0.25, 'rr': 1.5},  # Placeholder
}

# Define filters
FILTERS = {
    'NO_FILTER': lambda row: True,
    'CONSOLIDATION': lambda row: row['london_type'] == 'CONSOLIDATION' if pd.notna(row['london_type']) else False,
    'SWEEP_HIGH': lambda row: row['london_type'] == 'SWEEP_HIGH' if pd.notna(row['london_type']) else False,
    'SWEEP_LOW': lambda row: row['london_type'] == 'SWEEP_LOW' if pd.notna(row['london_type']) else False,
    'EXPANSION': lambda row: row['london_type'] == 'EXPANSION' if pd.notna(row['london_type']) else False,
    'RSI_GT_70': lambda row: row['rsi'] > 70 if pd.notna(row['rsi']) else False,
    'RSI_LT_30': lambda row: row['rsi'] < 30 if pd.notna(row['rsi']) else False,
    'LARGE_ORB': lambda row: (row['orb_size'] / row['atr_20']) > 1.5 if pd.notna(row['atr_20']) and row['atr_20'] > 0 else False,
    'SMALL_ORB': lambda row: (row['orb_size'] / row['atr_20']) < 0.8 if pd.notna(row['atr_20']) and row['atr_20'] > 0 else False,
    'CONSOL_SMALL': lambda row: (row['london_type'] == 'CONSOLIDATION' if pd.notna(row['london_type']) else False) and ((row['orb_size'] / row['atr_20']) < 0.8 if pd.notna(row['atr_20']) and row['atr_20'] > 0 else False),
}

print("="*80)
print("FILTER TESTING ON OPTIMAL SETUPS")
print("="*80)
print()
print("Testing if filters improve already-optimal stop/RR combinations")
print()

conn = duckdb.connect(DB_PATH, read_only=True)

ORBS = {
    '0900': (9, 0),
    '1000': (10, 0),
    '1100': (11, 0),
    '1800': (18, 0),
}

all_results = []

for orb_time, (hour, minute) in ORBS.items():
    config = OPTIMAL_SETUPS[orb_time]
    stop_frac = config['stop_frac']
    rr = config['rr']

    print(f"\n{'='*80}")
    print(f"{orb_time} ORB - Optimal: Stop={stop_frac:.2f}, RR={rr:.1f}")
    print(f"{'='*80}\n")

    # Get data with filter columns
    query = f"""
        SELECT
            date_local,
            orb_{orb_time}_high as orb_high,
            orb_{orb_time}_low as orb_low,
            orb_{orb_time}_size as orb_size,
            london_type,
            rsi_at_orb as rsi,
            atr_20
        FROM daily_features
        WHERE instrument = 'MGC'
          AND orb_{orb_time}_high IS NOT NULL
          AND orb_{orb_time}_low IS NOT NULL
        ORDER BY date_local
    """

    df = conn.execute(query).fetchdf()

    for filter_name, filter_func in FILTERS.items():
        # Apply filter
        df_filtered = df[df.apply(filter_func, axis=1)].copy()

        if len(df_filtered) < 30:  # Skip if too few trades
            continue

        # Simulate
        results = []

        for idx, row in df_filtered.iterrows():
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

            all_results.append({
                'orb_time': orb_time,
                'stop_frac': stop_frac,
                'rr': rr,
                'filter': filter_name,
                'trades': count,
                'wr': wr,
                'avg_r': avg_r,
                'total_r': total_r
            })

            # Print if filter improves
            if filter_name != 'NO_FILTER':
                baseline = [r for r in all_results if r['orb_time'] == orb_time and r['filter'] == 'NO_FILTER']
                if baseline:
                    baseline_avg_r = baseline[0]['avg_r']
                    improvement = avg_r - baseline_avg_r

                    if improvement > 0.05:
                        print(f"{filter_name}: {count} trades, {wr:.1f}% WR, {avg_r:+.3f} avg R, {total_r:+.1f}R total")
                        print(f"  Improvement: {improvement:+.3f}R per trade *** SIGNIFICANT ***")

conn.close()

# Summary
print("\n" + "="*80)
print("FILTER RESULTS SUMMARY")
print("="*80)
print()

df_all = pd.DataFrame(all_results)

# For each ORB, compare filters to baseline
for orb_time in ORBS.keys():
    orb_results = df_all[df_all['orb_time'] == orb_time]
    baseline = orb_results[orb_results['filter'] == 'NO_FILTER']

    if len(baseline) == 0:
        continue

    baseline_avg_r = baseline.iloc[0]['avg_r']
    baseline_trades = baseline.iloc[0]['trades']

    print(f"\n{orb_time} ORB (Baseline: {baseline_trades} trades, {baseline_avg_r:+.3f} avg R):")
    print("-" * 60)

    # Find filters that improve significantly
    filtered = orb_results[orb_results['filter'] != 'NO_FILTER'].copy()
    filtered['improvement'] = filtered['avg_r'] - baseline_avg_r

    significant = filtered[filtered['improvement'] > 0.05].sort_values('improvement', ascending=False)

    if len(significant) > 0:
        print("\nFilters that IMPROVE performance (>0.05R per trade):")
        for idx, row in significant.iterrows():
            print(f"  {row['filter']}: {row['trades']} trades, {row['avg_r']:+.3f} avg R (improvement: {row['improvement']:+.3f}R)")
    else:
        print("  No filters significantly improve performance")

print()

# Final recommendations
print("="*80)
print("FINAL RECOMMENDATIONS")
print("="*80)
print()

# Compile best setups
best_setups = []
for orb_time in ORBS.keys():
    orb_results = df_all[df_all['orb_time'] == orb_time]
    best = orb_results.nlargest(1, 'avg_r').iloc[0]

    best_setups.append({
        'orb_time': best['orb_time'],
        'stop_frac': best['stop_frac'],
        'rr': best['rr'],
        'filter': best['filter'],
        'trades': best['trades'],
        'wr': best['wr'],
        'avg_r': best['avg_r'],
        'total_r': best['total_r']
    })

df_best = pd.DataFrame(best_setups)

print("BEST SETUP FOR EACH ORB (with or without filter):")
print()
print(df_best[['orb_time', 'stop_frac', 'rr', 'filter', 'trades', 'wr', 'avg_r', 'total_r']].to_string(index=False))

print()

# Count how many benefit from filters
filtered_count = len(df_best[df_best['filter'] != 'NO_FILTER'])

if filtered_count > 0:
    print(f"{filtered_count} / {len(ORBS)} ORBs benefit from filters")
    print()
    print("IMPLEMENT FILTERS for:")
    for idx, row in df_best[df_best['filter'] != 'NO_FILTER'].iterrows():
        print(f"  {row['orb_time']} ORB: Use {row['filter']} filter")
else:
    print("NO ORBs benefit from filters")
    print("Use optimal stop/RR without additional filtering")

print()
