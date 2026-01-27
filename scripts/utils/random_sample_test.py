"""
RANDOM SAMPLE TEST - Monte Carlo Stability Check

Runs multiple iterations with random 70% subsets of data.
Tests if results are consistent across different samples.
"""

import duckdb
import pandas as pd
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import sys

TZ_LOCAL = ZoneInfo("Australia/Brisbane")
TZ_UTC = ZoneInfo("UTC")

DB_PATH = 'gold.db'
SYMBOL = 'MGC'

from optimize_orb_canonical import simulate_canonical

def random_sample_test(orb_time, stop_frac, rr, n_iterations=10):
    """
    Test setup on random 70% samples (Monte Carlo)
    """
    conn = duckdb.connect(DB_PATH, read_only=True)

    # Get all days with this ORB
    query = f"""
        SELECT
            date_local,
            orb_{orb_time}_high as orb_high,
            orb_{orb_time}_low as orb_low,
            orb_{orb_time}_size as orb_size
        FROM daily_features
        WHERE instrument = 'MGC'
          AND orb_{orb_time}_high IS NOT NULL
          AND orb_{orb_time}_low IS NOT NULL
        ORDER BY date_local
    """

    df_days = conn.execute(query).fetchdf()
    total_days = len(df_days)

    print(f"=== RANDOM SAMPLE TEST: {orb_time} ORB ===")
    print(f"Setup: Stop={stop_frac}, RR={rr}")
    print(f"Total days: {total_days}")
    print(f"Iterations: {n_iterations} random 70% samples")
    print()

    # Pre-load bars
    ORBS = {
        '0900': (9, 0),
        '1000': (10, 0),
        '1100': (11, 0),
        '1800': (18, 0),
        '2300': (23, 0),
        '0030': (0, 30),
    }

    hour, minute = ORBS[orb_time]

    bars_cache = {}
    for idx, row in df_days.iterrows():
        trade_date = pd.to_datetime(row['date_local']).date()

        if hour == 0 and minute == 30:
            orb_start = datetime(trade_date.year, trade_date.month, trade_date.day, hour, minute, tzinfo=TZ_LOCAL) + timedelta(days=1)
        else:
            orb_start = datetime(trade_date.year, trade_date.month, trade_date.day, hour, minute, tzinfo=TZ_LOCAL)

        scan_start = orb_start + timedelta(minutes=5)

        if hour < 9 or (hour == 0 and minute == 30):
            scan_end = datetime(orb_start.year, orb_start.month, orb_start.day, 9, 0, tzinfo=TZ_LOCAL)
        else:
            scan_end = datetime(orb_start.year, orb_start.month, orb_start.day, 9, 0, tzinfo=TZ_LOCAL) + timedelta(days=1)

        start_utc = scan_start.astimezone(TZ_UTC)
        end_utc = scan_end.astimezone(TZ_UTC)

        bars = conn.execute("""
            SELECT high, low, close
            FROM bars_1m
            WHERE symbol = ?
              AND ts_utc >= ?
              AND ts_utc < ?
            ORDER BY ts_utc
        """, [SYMBOL, start_utc, end_utc]).fetchdf()

        bars_cache[str(trade_date)] = bars

    conn.close()

    # Run iterations
    all_wrs = []
    all_avg_rs = []

    sample_size = int(total_days * 0.7)

    for iteration in range(n_iterations):
        # Random 70% sample
        sample_indices = random.sample(range(total_days), sample_size)
        df_sample = df_days.iloc[sample_indices]

        # Test on sample
        results = []
        for idx, row in df_sample.iterrows():
            date_str = str(pd.to_datetime(row['date_local']).date())
            orb_high = row['orb_high']
            orb_low = row['orb_low']
            bars = bars_cache.get(date_str)

            if bars is not None and len(bars) > 0:
                r_result = simulate_canonical(bars, orb_high, orb_low, rr, stop_frac)
                results.append(r_result)

        if len(results) > 0:
            wins = len([r for r in results if r > 0])
            wr = wins / len(results) * 100
            avg_r = sum(results) / len(results)

            all_wrs.append(wr)
            all_avg_rs.append(avg_r)

            print(f"Iteration {iteration+1:2d}: WR={wr:5.1f}%, Avg R={avg_r:+.3f} ({len(results)} trades)")

    # Calculate statistics
    print()
    print("STATISTICS:")
    print(f"  Win Rate:")
    print(f"    Mean: {sum(all_wrs)/len(all_wrs):.1f}%")
    print(f"    Min:  {min(all_wrs):.1f}%")
    print(f"    Max:  {max(all_wrs):.1f}%")
    print(f"    Std:  {pd.Series(all_wrs).std():.1f}%")
    print()
    print(f"  Avg R:")
    print(f"    Mean: {sum(all_avg_rs)/len(all_avg_rs):+.3f}")
    print(f"    Min:  {min(all_avg_rs):+.3f}")
    print(f"    Max:  {max(all_avg_rs):+.3f}")
    print(f"    Std:  {pd.Series(all_avg_rs).std():.3f}")
    print()

    # Assess stability
    wr_std = pd.Series(all_wrs).std()
    r_std = pd.Series(all_avg_rs).std()

    print("STABILITY ASSESSMENT:")
    if r_std < 0.05:
        print("  EXCELLENT: Very stable across samples")
    elif r_std < 0.10:
        print("  GOOD: Stable results")
    elif r_std < 0.15:
        print("  ACCEPTABLE: Some variance but generally stable")
    else:
        print("  WARNING: High variance - results unstable")
        print("  May be overfitting or sample-dependent")

    return all_wrs, all_avg_rs


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python random_sample_test.py <orb_time> <stop_frac> <rr> [iterations]")
        print("Example: python random_sample_test.py 1100 0.20 8.0 20")
        sys.exit(1)

    orb_time = sys.argv[1]
    stop_frac = float(sys.argv[2])
    rr = float(sys.argv[3])
    iterations = int(sys.argv[4]) if len(sys.argv) > 4 else 10

    random_sample_test(orb_time, stop_frac, rr, iterations)
