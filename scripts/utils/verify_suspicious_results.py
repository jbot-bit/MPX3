"""
VERIFY SUSPICIOUS RESULTS - Red Flag Check

The 2300/0030 ORBs showing 84% WR at RR=8.0 is statistically impossible.

This script audits:
1. Are targets really being hit?
2. Is the scan window correct?
3. Are there data quality issues?
4. Sample individual trades to verify logic
"""

import duckdb
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json

TZ_LOCAL = ZoneInfo("Australia/Brisbane")
TZ_UTC = ZoneInfo("UTC")

DB_PATH = 'gold.db'
SYMBOL = 'MGC'

print("="*80)
print("AUDITING SUSPICIOUS 0030 ORB RESULTS")
print("="*80)
print()

# Load optimization results
with open('optimization_results_0030_canonical.json', 'r') as f:
    results = json.load(f)

# Find the suspicious setup
suspicious = None
for r in results:
    if abs(r['rr'] - 8.0) < 0.01 and abs(r['stop_frac'] - 0.25) < 0.01:
        suspicious = r
        break

if not suspicious:
    print("Could not find suspicious setup in results")
    exit(1)

print("SUSPICIOUS SETUP:")
print(f"  Stop: {suspicious['stop_frac']:.2f} x ORB")
print(f"  RR: {suspicious['rr']:.1f}")
print(f"  Trades: {suspicious['trades']}")
print(f"  Win rate: {suspicious['wr']:.1f}%")
print(f"  Avg R: {suspicious['avg_r']:+.3f}")
print()

# Connect to database
conn = duckdb.connect(DB_PATH, read_only=True)

# Get 0030 ORB data
query = """
    SELECT
        date_local,
        orb_0030_high as orb_high,
        orb_0030_low as orb_low,
        orb_0030_size as orb_size,
        orb_0030_break_dir as break_dir,
        orb_0030_outcome as outcome,
        orb_0030_r_multiple as r_multiple
    FROM daily_features
    WHERE instrument = 'MGC'
      AND orb_0030_high IS NOT NULL
      AND orb_0030_low IS NOT NULL
    ORDER BY date_local
    LIMIT 10
"""

df_db = conn.execute(query).fetchdf()

print("SAMPLE FROM DATABASE (0030 ORB, RR=1.0, FULL mode):")
print(df_db[['date_local', 'orb_size', 'break_dir', 'outcome', 'r_multiple']])
print()

# Check if database has realistic results
db_wins = len(df_db[df_db['r_multiple'] == 1.0])
db_total = len(df_db[df_db['break_dir'] != 'NONE'])
db_wr = db_wins / db_total * 100 if db_total > 0 else 0

print(f"Database 0030 ORB (RR=1.0): {db_wr:.1f}% WR ({db_wins}/{db_total})")
print()

# Now manually verify ONE trade from optimization
print("="*80)
print("MANUAL VERIFICATION - Sample Trade")
print("="*80)
print()

# Get first valid ORB
query2 = """
    SELECT
        date_local,
        orb_0030_high,
        orb_0030_low
    FROM daily_features
    WHERE instrument = 'MGC'
      AND orb_0030_high IS NOT NULL
      AND orb_0030_low IS NOT NULL
      AND orb_0030_break_dir != 'NONE'
    LIMIT 1
"""

row = conn.execute(query2).fetchone()
trade_date = pd.to_datetime(row[0]).date()
orb_high, orb_low = row[1], row[2]
orb_size = orb_high - orb_low

print(f"Trade Date: {trade_date}")
print(f"ORB high: {orb_high:.1f}, low: {orb_low:.1f}, size: {orb_size:.2f}")
print()

# Get bars for 0030 ORB (next day 00:30 + 5 mins to 02:00)
orb_start = datetime(trade_date.year, trade_date.month, trade_date.day, 0, 30, tzinfo=TZ_LOCAL) + timedelta(days=1)
scan_start = orb_start + timedelta(minutes=5)
scan_end = datetime(trade_date.year, trade_date.month, trade_date.day, 2, 0, tzinfo=TZ_LOCAL) + timedelta(days=1)

start_utc = scan_start.astimezone(TZ_UTC)
end_utc = scan_end.astimezone(TZ_UTC)

bars = conn.execute("""
    SELECT ts_utc, high, low, close
    FROM bars_1m
    WHERE symbol = ?
      AND ts_utc >= ?
      AND ts_utc < ?
    ORDER BY ts_utc
""", [SYMBOL, start_utc, end_utc]).fetchdf()

print(f"Bars available: {len(bars)} (from {scan_start.strftime('%H:%M')} to {scan_end.strftime('%H:%M')} local)")
print()

if len(bars) > 0:
    print("First 5 bars:")
    for i in range(min(5, len(bars))):
        print(f"  {i+1}: close={bars.iloc[i]['close']:.1f}, high={bars.iloc[i]['high']:.1f}, low={bars.iloc[i]['low']:.1f}")
    print()

    # Check for entry
    entry_found = False
    for i in range(len(bars)):
        close = bars.iloc[i]['close']
        if close > orb_high:
            print(f"✅ UP break found at bar {i+1}: close={close:.1f} > orb_high {orb_high:.1f}")
            entry_found = True
            break_dir = 'UP'
            entry_idx = i
            break
        elif close < orb_low:
            print(f"✅ DOWN break found at bar {i+1}: close={close:.1f} < orb_low {orb_low:.1f}")
            entry_found = True
            break_dir = 'DOWN'
            entry_idx = i
            break

    if entry_found:
        # Calculate Stop=0.25, RR=8.0 levels
        orb_edge = orb_high if break_dir == 'UP' else orb_low
        risk = orb_size * 0.25  # Quarter stop

        if break_dir == 'UP':
            stop = orb_edge - risk
            target = orb_edge + (8.0 * risk)
        else:
            stop = orb_edge + risk
            target = orb_edge - (8.0 * risk)

        print()
        print(f"Break direction: {break_dir}")
        print(f"ORB edge: {orb_edge:.1f}")
        print(f"Risk (0.25 × ORB size): {risk:.2f}")
        print(f"Stop: {stop:.1f}")
        print(f"Target (8.0R): {target:.1f}")
        print()

        # Check if target is RIDICULOUSLY far
        target_distance = abs(target - orb_edge)
        print(f"Target distance from ORB edge: {target_distance:.1f} points")
        print()

        # Scan for outcome
        outcome = None
        for j in range(entry_idx + 1, len(bars)):
            high = bars.iloc[j]['high']
            low = bars.iloc[j]['low']

            if break_dir == 'UP':
                if low <= stop:
                    outcome = f"LOSS (stopped at bar {j+1})"
                    break
                elif high >= target:
                    outcome = f"WIN (target hit at bar {j+1})"
                    break
            else:
                if high >= stop:
                    outcome = f"LOSS (stopped at bar {j+1})"
                    break
                elif low <= target:
                    outcome = f"WIN (target hit at bar {j+1})"
                    break

        if outcome:
            print(f"Outcome: {outcome}")
        else:
            print(f"Outcome: NO OUTCOME (neither TP nor SL hit in {len(bars) - entry_idx - 1} bars)")
            print()
            print("⚠️  THIS IS THE PROBLEM!")
            print("Scan window is TOO SHORT for RR=8.0!")
            print(f"Target distance: {target_distance:.1f} points")
            print(f"Bars available: {len(bars) - entry_idx - 1}")
            print()
            print("With no outcome, the script likely returns 0.0 (neutral)")
            print("But it should return None (no trade)")

    else:
        print("❌ No break found in this sample")

else:
    print("❌ NO BARS FOUND - Scan window is WRONG!")
    print()
    print("0030 ORB is on NEXT DAY:")
    print(f"  Trade date: {trade_date}")
    print(f"  ORB starts: {trade_date + timedelta(days=1)} 00:30")
    print(f"  Scan window: {scan_start} to {scan_end}")

conn.close()

print()
print("="*80)
print("DIAGNOSIS")
print("="*80)
print()
print("The high WR is likely due to:")
print("1. Scan window TOO SHORT for high RR (8.0)")
print("2. Trades ending with NO OUTCOME counted as wins (0.0 instead of None)")
print("3. Need longer scan window OR exclude NO_OUTCOME trades")
print()
print("FIX: Extend scan window from 2 hours to 24 hours for 0030/2300 ORBs")
print()
