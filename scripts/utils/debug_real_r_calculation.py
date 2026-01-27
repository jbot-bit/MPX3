"""
DEBUG REAL R CALCULATION

Test one setup in detail to understand why real R is negative.
"""

import duckdb
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from execution_metrics import ExecutionMetricsCalculator

TZ_LOCAL = ZoneInfo("Australia/Brisbane")
TZ_UTC = ZoneInfo("UTC")

DB_PATH = 'gold.db'
SYMBOL = 'MGC'

# Test 1100 ORB with stop_frac=1.00 (widest stop)
ORB_TIME = '1100'
STOP_FRAC = 1.00
RR = 1.5

conn = duckdb.connect(DB_PATH, read_only=True)

query = f"""
    SELECT
        date_local,
        orb_{ORB_TIME}_high as orb_high,
        orb_{ORB_TIME}_low as orb_low,
        orb_{ORB_TIME}_break_dir as break_dir
    FROM daily_features
    WHERE instrument = 'MGC'
      AND orb_{ORB_TIME}_high IS NOT NULL
      AND orb_{ORB_TIME}_low IS NOT NULL
      AND orb_{ORB_TIME}_break_dir IS NOT NULL
      AND orb_{ORB_TIME}_break_dir != 'NONE'
    ORDER BY date_local
    LIMIT 5
"""

df_days = conn.execute(query).fetchdf()

calc = ExecutionMetricsCalculator(commission=1.5, slippage_ticks=1.5)

for idx, row in df_days.iterrows():
    trade_date = pd.to_datetime(row['date_local']).date()
    orb_high = row['orb_high']
    orb_low = row['orb_low']
    break_dir = row['break_dir']

    print(f"\n{'='*80}")
    print(f"Date: {trade_date}, Break: {break_dir}")
    print(f"ORB: {orb_low:.1f} - {orb_high:.1f} (size: {orb_high - orb_low:.2f})")

    # Get bars
    orb_start = datetime(trade_date.year, trade_date.month, trade_date.day, 11, 0, tzinfo=TZ_LOCAL)
    scan_start = orb_start + timedelta(minutes=5)
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

    # Find entry
    entry_close = None
    for i, bar in enumerate(bars.itertuples()):
        if break_dir == 'UP' and bar.close > orb_high:
            entry_close = bar.close
            entry_bar_idx = i
            print(f"Entry bar {i}: close={bar.close:.1f} (above ORB high {orb_high:.1f})")
            break
        elif break_dir == 'DOWN' and bar.close < orb_low:
            entry_close = bar.close
            entry_bar_idx = i
            print(f"Entry bar {i}: close={bar.close:.1f} (below ORB low {orb_low:.1f})")
            break

    if entry_close:
        metrics = calc.calculate_trade_metrics(
            orb_high=orb_high,
            orb_low=orb_low,
            entry_close=entry_close,
            break_dir=break_dir,
            bars_1m=bars,
            rr=RR,
            stop_mode=STOP_FRAC,
            entry_bar_idx=entry_bar_idx
        )

        if metrics:
            print(f"\nEntry close: {metrics.entry_close:.1f}")
            print(f"Entry fill (with slippage): {metrics.entry_fill:.1f}")
            print(f"ORB edge: {metrics.orb_edge:.1f}")
            print(f"Entry distance from edge: {metrics.entry_distance_from_edge:.2f} points")
            print(f"\nCanonical stop: {metrics.canonical_stop:.1f}")
            print(f"Canonical risk: {metrics.canonical_risk:.2f} points")
            print(f"Canonical target: {metrics.canonical_target:.1f}")
            print(f"\nReal risk: {metrics.real_risk:.2f} points")
            print(f"Real target: {metrics.real_target:.1f}")
            print(f"\nOutcome: {metrics.outcome}")
            if metrics.outcome != 'NO_OUTCOME':
                print(f"Bars to outcome: {metrics.bars_to_outcome}")
                print(f"\nCanonical R: {metrics.canonical_r:+.3f}")
                print(f"Real R: {metrics.real_r:+.3f}")
                print(f"Degradation: {metrics.real_r - metrics.canonical_r:+.3f}R")

conn.close()
