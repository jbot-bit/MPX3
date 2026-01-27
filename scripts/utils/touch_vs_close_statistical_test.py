"""
STATISTICAL SIGNIFICANCE TEST: Touch vs Close

Are the differences REAL or just NOISE?

Uses proper statistical tests to determine if touch vs close matters.
"""

import duckdb
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy import stats

DB_PATH = 'data/db/gold.db'
SYMBOL = 'MGC'

def simulate_close_entry(bars_1m, orb_high, orb_low, rr):
    """Simulate CLOSE entry"""
    if len(bars_1m) == 0:
        return None

    for i, row in bars_1m.iterrows():
        close = float(row['close'])

        if close > orb_high or close < orb_low:
            direction = 'UP' if close > orb_high else 'DOWN'
            entry = close
            stop = orb_low if direction == 'UP' else orb_high
            risk = abs(entry - stop)
            target = entry + (rr * risk) if direction == 'UP' else entry - (rr * risk)

            for j in range(i + 1, len(bars_1m)):
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

    return None

def simulate_touch_entry(bars_1m, orb_high, orb_low, rr):
    """Simulate TOUCH entry"""
    if len(bars_1m) == 0:
        return None

    for i, row in bars_1m.iterrows():
        high = float(row['high'])
        low = float(row['low'])

        if high >= orb_high and low <= orb_low:
            return None

        if high >= orb_high or low <= orb_low:
            direction = 'UP' if high >= orb_high else 'DOWN'
            entry = orb_high if direction == 'UP' else orb_low
            stop = orb_low if direction == 'UP' else orb_high
            risk = abs(entry - stop)
            target = entry + (rr * risk) if direction == 'UP' else entry - (rr * risk)

            for j in range(i + 1, len(bars_1m)):
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

    return None


print("="*80)
print("STATISTICAL SIGNIFICANCE: Touch vs Close")
print("="*80)
print()

conn = duckdb.connect(DB_PATH, read_only=True)

# Test on validated setup: 1000 ORB at RR=8.0
orb_time = '1000'
hour, minute = 10, 0
rr = 8.0

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

print(f"Testing {orb_time} ORB at RR={rr:.1f} on {len(df)} days")
print()

# Simulate both methods
touch_results = []
close_results = []
paired_results = []  # For paired t-test

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

    touch_r = simulate_touch_entry(bars, orb_high, orb_low, rr)
    close_r = simulate_close_entry(bars, orb_high, orb_low, rr)

    if touch_r is not None:
        touch_results.append(touch_r)

    if close_r is not None:
        close_results.append(close_r)

    # For days where BOTH methods traded
    if touch_r is not None and close_r is not None:
        paired_results.append({
            'date': date_local,
            'touch': touch_r,
            'close': close_r,
            'diff': touch_r - close_r
        })

conn.close()

# Calculate statistics
touch_arr = np.array(touch_results)
close_arr = np.array(close_results)

touch_mean = np.mean(touch_arr)
touch_std = np.std(touch_arr, ddof=1)
touch_se = touch_std / np.sqrt(len(touch_arr))

close_mean = np.mean(close_arr)
close_std = np.std(close_arr, ddof=1)
close_se = close_std / np.sqrt(len(close_arr))

print("="*80)
print("DESCRIPTIVE STATISTICS")
print("="*80)
print()

print(f"TOUCH ENTRY:")
print(f"  N: {len(touch_arr)}")
print(f"  Mean: {touch_mean:+.3f}R")
print(f"  Std Dev: {touch_std:.3f}R")
print(f"  Std Error: {touch_se:.3f}R")
print(f"  95% CI: [{touch_mean - 1.96*touch_se:+.3f}, {touch_mean + 1.96*touch_se:+.3f}]")
print()

print(f"CLOSE ENTRY:")
print(f"  N: {len(close_arr)}")
print(f"  Mean: {close_mean:+.3f}R")
print(f"  Std Dev: {close_std:.3f}R")
print(f"  Std Error: {close_se:.3f}R")
print(f"  95% CI: [{close_mean - 1.96*close_se:+.3f}, {close_mean + 1.96*close_se:+.3f}]")
print()

# Independent t-test
t_stat, p_value = stats.ttest_ind(touch_arr, close_arr)

print("="*80)
print("STATISTICAL TEST: Independent t-test")
print("="*80)
print()

print(f"Null hypothesis: Touch and Close have same mean")
print(f"Alternative: Means are different")
print()
print(f"t-statistic: {t_stat:.3f}")
print(f"p-value: {p_value:.4f}")
print()

if p_value < 0.05:
    print(f"SIGNIFICANT (p < 0.05)")
    if touch_mean > close_mean:
        print(f"Touch is STATISTICALLY BETTER by {touch_mean - close_mean:+.3f}R")
    else:
        print(f"Close is STATISTICALLY BETTER by {close_mean - touch_mean:+.3f}R")
else:
    print(f"NOT SIGNIFICANT (p >= 0.05)")
    print(f"Difference of {abs(touch_mean - close_mean):.3f}R could be random")
    print(f"VERDICT: Entry method doesn't matter - use whichever is easier")

print()

# Paired analysis (same days)
if len(paired_results) > 50:
    print("="*80)
    print("PAIRED ANALYSIS (Same Days)")
    print("="*80)
    print()

    df_paired = pd.DataFrame(paired_results)

    print(f"Days where BOTH methods traded: {len(df_paired)}")
    print()

    # Paired t-test
    paired_t, paired_p = stats.ttest_rel(df_paired['touch'], df_paired['close'])

    print(f"Paired t-test:")
    print(f"  t-statistic: {paired_t:.3f}")
    print(f"  p-value: {paired_p:.4f}")
    print()

    if paired_p < 0.05:
        print("SIGNIFICANT difference on same days")
    else:
        print("NO significant difference on same days")

    print()

    # Days where methods disagreed (one won, one lost)
    disagreements = df_paired[
        ((df_paired['touch'] > 0) & (df_paired['close'] < 0)) |
        ((df_paired['touch'] < 0) & (df_paired['close'] > 0))
    ]

    print(f"Days where methods disagreed: {len(disagreements)} / {len(df_paired)} ({len(disagreements)/len(df_paired)*100:.1f}%)")

    if len(disagreements) > 0:
        touch_right = len(disagreements[(disagreements['touch'] > 0) & (disagreements['close'] < 0)])
        close_right = len(disagreements[(disagreements['touch'] < 0) & (disagreements['close'] > 0)])

        print(f"  Touch right, Close wrong: {touch_right}")
        print(f"  Close right, Touch wrong: {close_right}")
        print()

        if touch_right > close_right:
            print(f"Touch is better at avoiding losers")
        elif close_right > touch_right:
            print(f"Close is better at avoiding losers")
        else:
            print(f"Both make similar mistakes")

print()

print("="*80)
print("HONEST ANSWER")
print("="*80)
print()

print("The differences are SMALL and INCONSISTENT across RR values.")
print()
print("At RR=8.0 (best validated setup):")
print(f"  Touch: {touch_mean:+.3f}R avg, {len(touch_arr)} trades")
print(f"  Close: {close_mean:+.3f}R avg, {len(close_arr)} trades")
print(f"  Difference: {abs(touch_mean - close_mean):.3f}R")
print()

if p_value >= 0.05:
    print("This difference is NOT statistically significant.")
    print()
    print("RECOMMENDATION:")
    print("  Entry method doesn't materially affect results")
    print("  Stick with CLOSE entry (current system)")
    print("  Focus on:")
    print("    - Filters (session type, ORB size, RSI)")
    print("    - Trade management (SL adjustment, early exit)")
    print("    - Position sizing")
else:
    winner = "Touch" if touch_mean > close_mean else "Close"
    print(f"This difference IS statistically significant (p={p_value:.4f})")
    print()
    print(f"RECOMMENDATION: Use {winner} entry for {orb_time} ORB at RR={rr:.1f}")

print()
