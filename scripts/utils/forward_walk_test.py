"""
FORWARD WALK TEST - Detect Overfitting

Splits data into:
- In-sample (train): First 70% of data
- Out-of-sample (test): Last 30% of data

Tests if optimal parameters from in-sample still work out-of-sample.
"""

import duckdb
import pandas as pd
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import sys

TZ_LOCAL = ZoneInfo("Australia/Brisbane")
TZ_UTC = ZoneInfo("UTC")

DB_PATH = 'gold.db'
SYMBOL = 'MGC'

# Import the simulation function
from optimize_orb_canonical import simulate_canonical

def forward_walk_test(orb_time, stop_frac, rr):
    """
    Test setup on in-sample vs out-of-sample data
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

    # Split 70/30
    split_idx = int(total_days * 0.7)
    df_train = df_days.iloc[:split_idx]
    df_test = df_days.iloc[split_idx:]

    print(f"=== FORWARD WALK: {orb_time} ORB ===")
    print(f"Setup: Stop={stop_frac}, RR={rr}")
    print()
    print(f"Total days: {total_days}")
    print(f"In-sample (train): {len(df_train)} days ({df_train.iloc[0]['date_local']} to {df_train.iloc[-1]['date_local']})")
    print(f"Out-of-sample (test): {len(df_test)} days ({df_test.iloc[0]['date_local']} to {df_test.iloc[-1]['date_local']})")
    print()

    # Pre-load bars for all days
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

    # Test on in-sample
    train_results = []
    for idx, row in df_train.iterrows():
        date_str = str(pd.to_datetime(row['date_local']).date())
        orb_high = row['orb_high']
        orb_low = row['orb_low']
        bars = bars_cache.get(date_str)

        if bars is not None and len(bars) > 0:
            r_result = simulate_canonical(bars, orb_high, orb_low, rr, stop_frac)
            train_results.append(r_result)

    # Test on out-of-sample
    test_results = []
    for idx, row in df_test.iterrows():
        date_str = str(pd.to_datetime(row['date_local']).date())
        orb_high = row['orb_high']
        orb_low = row['orb_low']
        bars = bars_cache.get(date_str)

        if bars is not None and len(bars) > 0:
            r_result = simulate_canonical(bars, orb_high, orb_low, rr, stop_frac)
            test_results.append(r_result)

    # Calculate metrics
    def calc_metrics(results, label):
        if len(results) == 0:
            return

        total_r = sum(results)
        avg_r = total_r / len(results)
        wins = len([r for r in results if r > 0])
        wr = wins / len(results) * 100

        print(f"{label}:")
        print(f"  Trades: {len(results)}")
        print(f"  Win rate: {wr:.1f}%")
        print(f"  Avg R: {avg_r:+.3f}")
        print(f"  Total R: {total_r:+.1f}")

        return {'trades': len(results), 'wr': wr, 'avg_r': avg_r, 'total_r': total_r}

    train_metrics = calc_metrics(train_results, "IN-SAMPLE (Train)")
    print()
    test_metrics = calc_metrics(test_results, "OUT-OF-SAMPLE (Test)")
    print()

    # Compare
    if train_metrics and test_metrics:
        wr_diff = test_metrics['wr'] - train_metrics['wr']
        r_diff = test_metrics['avg_r'] - train_metrics['avg_r']

        print("COMPARISON:")
        print(f"  WR difference: {wr_diff:+.1f}% (test vs train)")
        print(f"  Avg R difference: {r_diff:+.3f}R (test vs train)")
        print()

        if abs(wr_diff) < 5.0 and abs(r_diff) < 0.10:
            print("✓ ROBUST: Out-of-sample performance similar to in-sample")
        elif r_diff < -0.15:
            print("⚠ DEGRADATION: Out-of-sample performance significantly worse")
            print("  Possible overfitting or regime change")
        elif r_diff > 0.15:
            print("⚠ IMPROVEMENT: Out-of-sample better than in-sample")
            print("  Unusual - check for bugs or lucky period")
        else:
            print("⚠ MARGINAL: Small difference, acceptable variance")

    return train_metrics, test_metrics


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python forward_walk_test.py <orb_time> <stop_frac> <rr>")
        print("Example: python forward_walk_test.py 1100 0.20 8.0")
        sys.exit(1)

    orb_time = sys.argv[1]
    stop_frac = float(sys.argv[2])
    rr = float(sys.argv[3])

    forward_walk_test(orb_time, stop_frac, rr)
