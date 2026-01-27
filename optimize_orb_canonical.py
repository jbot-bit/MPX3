"""
ORB OPTIMIZATION - CANONICAL EXECUTION LOGIC

Matches build_daily_features.py EXACTLY:
- Entry: First CLOSE outside ORB (not ORB edge)
- Risk: ORB EDGE to stop (not entry to stop)
- Target: ORB EDGE +/- RR × risk
- Stop modes:
  * FULL (1.00): opposite ORB boundary → risk = ORB size
  * HALF (0.50): midpoint → risk = ORB size / 2
  * QUARTER (0.25): 1/4 from edge → risk = ORB size / 4
  * Custom fractions: stop_frac × ORB size from edge

Usage: python optimize_orb_canonical.py 1000
"""

import sys
import duckdb
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json

TZ_LOCAL = ZoneInfo("Australia/Brisbane")
TZ_UTC = ZoneInfo("UTC")

DB_PATH = 'gold.db'  # Canonical path (root, not data/db)
SYMBOL = 'MGC'

# LOCKED ASSUMPTIONS (2026-01-25 Audit)
# See AUDIT_LOCKED_ASSUMPTIONS.md for complete definitions
#
# MGC Trading Costs:
# - Tick size: 0.1 points
# - Tick value: $1.00
# - Point value: $10.00 (1 point = 10 ticks)
# - Commission (round turn): $2.40-$3.00
# - Total cost per trade: $3.00 (conservative)
#
# Entry: First 1-min CLOSE outside ORB + slippage
# Fill price: close ± 0.5 points (market order)
# Total one-way cost: $3.00 (commission + slippage)
#
COMMISSION = 1.5  # Round-trip commission
SLIPPAGE_COST = 1.5  # Round-trip slippage
TOTAL_COST_PER_TRADE = 3.0  # Total round-trip cost
TICK_SIZE = 0.1
POINT_VALUE = 10.0

def simulate_canonical(bars_1m, orb_high, orb_low, rr, stop_fraction):
    """
    CANONICAL execution logic matching build_daily_features.py

    LOCKED ASSUMPTIONS (Audit 2026-01-25):
    - Entry trigger: First 1-min CLOSE outside ORB
    - Entry fill: close price + 0.5 points slippage (market order)
    - Risk: ORB EDGE to stop (canonical, NOT entry to stop)
    - Target: ORB EDGE + RR × risk (canonical)
    - Stop modes: 1.0=FULL, 0.5=HALF, 0.25=QUARTER
    - Same-bar hit: Always LOSS (conservative)
    - NO_OUTCOME: Counted as ~LOSS (0.0R - costs)
    - Costs: $3.00 per trade

    Args:
        bars_1m: 1-minute bars AFTER ORB completes
        orb_high, orb_low: ORB boundaries
        rr: Risk/reward ratio
        stop_fraction: Fraction of ORB size for risk (1.0=FULL, 0.5=HALF, 0.25=QUARTER)

    Returns:
        R-multiple after costs, or None if no trade
    """
    if len(bars_1m) == 0:
        return None

    orb_size = orb_high - orb_low

    # Find entry: First CLOSE outside ORB
    entry_idx = None
    for i in range(len(bars_1m)):
        close = float(bars_1m.iloc[i]['close'])

        if close > orb_high:
            break_dir = 'UP'
            entry_price = close
            entry_idx = i
            break
        elif close < orb_low:
            break_dir = 'DOWN'
            entry_price = close
            entry_idx = i
            break

    if entry_idx is None:
        # No breakout = NO_OUTCOME
        # Count as loss after costs (conservative)
        cost_dollars = TOTAL_COST_PER_TRADE
        cost_r = cost_dollars / (orb_size * POINT_VALUE)  # Use full ORB size for cost calc
        return -cost_r

    # CANONICAL: Risk from ORB EDGE to stop (not entry to stop)
    orb_edge = orb_high if break_dir == 'UP' else orb_low

    # Calculate stop position based on fraction
    # stop_fraction = 1.0 (FULL) means stop at opposite edge
    # stop_fraction = 0.5 (HALF) means stop at midpoint
    # stop_fraction = 0.25 (QUARTER) means stop at edge - 0.25×ORB_size
    risk = orb_size * stop_fraction

    if break_dir == 'UP':
        stop = orb_edge - risk  # For FULL: orb_high - orb_size = orb_low
    else:
        stop = orb_edge + risk  # For FULL: orb_low + orb_size = orb_high

    # CANONICAL: Target from ORB EDGE (not entry)
    target = orb_edge + (rr * risk) if break_dir == 'UP' else orb_edge - (rr * risk)

    # Check outcome on subsequent bars
    for j in range(entry_idx + 1, len(bars_1m)):
        high = float(bars_1m.iloc[j]['high'])
        low = float(bars_1m.iloc[j]['low'])

        if break_dir == 'UP':
            hit_stop = low <= stop
            hit_target = high >= target
        else:
            hit_stop = high >= stop
            hit_target = low <= target

        # Conservative: both hit in same bar = LOSS
        if hit_stop and hit_target:
            outcome_r = -1.0
            break
        elif hit_target:
            outcome_r = rr
            break
        elif hit_stop:
            outcome_r = -1.0
            break
    else:
        outcome_r = 0.0  # Neither hit = no outcome

    # Subtract costs (canonical uses ORB-anchored risk)
    cost_dollars = TOTAL_COST_PER_TRADE  # $3.00 total (commission + slippage)
    cost_r = cost_dollars / (risk * POINT_VALUE)

    return outcome_r - cost_r


if len(sys.argv) < 2:
    print("Usage: python optimize_orb_canonical.py <orb_time>")
    print("Example: python optimize_orb_canonical.py 1000")
    sys.exit(1)

orb_time = sys.argv[1]

ORBS = {
    '0900': (9, 0),
    '1000': (10, 0),
    '1100': (11, 0),
    '1800': (18, 0),
    '2300': (23, 0),
    '0030': (0, 30),
}

if orb_time not in ORBS:
    print(f"Invalid ORB time. Must be one of: {', '.join(ORBS.keys())}")
    sys.exit(1)

hour, minute = ORBS[orb_time]

print("="*80)
print(f"OPTIMIZING {orb_time} ORB - CANONICAL EXECUTION LOGIC")
print("="*80)
print()

conn = duckdb.connect(DB_PATH, read_only=True)

# Get all days with valid ORBs from CANONICAL table
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
print(f"Found {total_days} valid trading days")
print()

# Pre-load bars for each day (cache to avoid repeated queries)
print("Pre-loading 1-minute bars...")

bars_cache = {}

for idx, row in df_days.iterrows():
    trade_date = pd.to_datetime(row['date_local']).date()

    # Scan window: ORB end to next 09:00 local (LOCKED ASSUMPTION)
    # CRITICAL: Only 0030 ORB is on next day, 2300 ORB is on SAME day
    if hour == 0 and minute == 30:
        # 0030 ORB is on (D+1)
        orb_start = datetime(trade_date.year, trade_date.month, trade_date.day, hour, minute, tzinfo=TZ_LOCAL) + timedelta(days=1)
    else:
        # All other ORBs (0900, 1000, 1100, 1800, 2300) are on D
        orb_start = datetime(trade_date.year, trade_date.month, trade_date.day, hour, minute, tzinfo=TZ_LOCAL)

    scan_start = orb_start + timedelta(minutes=5)  # After ORB completes

    # Scan until next 09:00 local (trading day boundary)
    # If ORB is before 09:00, scan to 09:00 same day
    # If ORB is after 09:00, scan to 09:00 next day
    if hour < 9 or (hour == 0 and minute == 30):
        # 0030 ORB -> scan to 09:00 same calendar day
        scan_end = datetime(orb_start.year, orb_start.month, orb_start.day, 9, 0, tzinfo=TZ_LOCAL)
    else:
        # 0900, 1000, 1100, 1800, 2300 -> scan to 09:00 next day
        scan_end = datetime(orb_start.year, orb_start.month, orb_start.day, 9, 0, tzinfo=TZ_LOCAL) + timedelta(days=1)

    # Convert to UTC for query
    start_utc = scan_start.astimezone(TZ_UTC)
    end_utc = scan_end.astimezone(TZ_UTC)

    bars_query = """
        SELECT high, low, close
        FROM bars_1m
        WHERE symbol = ?
          AND ts_utc >= ?
          AND ts_utc < ?
        ORDER BY ts_utc
    """

    bars = conn.execute(bars_query, [SYMBOL, start_utc, end_utc]).fetchdf()
    bars_cache[str(trade_date)] = bars

    if (idx + 1) % 100 == 0:
        print(f"  Loaded {idx + 1}/{total_days} days...")

conn.close()

print(f"  Completed! Cached {len(bars_cache)} days")
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

        # Test this combination on ALL days
        results = []

        for idx, row in df_days.iterrows():
            date_str = str(pd.to_datetime(row['date_local']).date())
            orb_high = row['orb_high']
            orb_low = row['orb_low']

            bars = bars_cache.get(date_str)

            if bars is not None and len(bars) > 0:
                r_result = simulate_canonical(bars, orb_high, orb_low, rr, stop_frac)
                # Always append result (includes NO_OUTCOME as small loss)
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
            if avg_r > 0.10:
                print(f"[{completed}/{total_combos}] Stop={stop_frac:.2f}, RR={rr:.1f}: {count} trades, {wr:.1f}% WR, {avg_r:+.3f} avg R *** PROFITABLE ***")
            elif completed % 6 == 0:  # Print every 6th
                print(f"[{completed}/{total_combos}] Stop={stop_frac:.2f}, RR={rr:.1f}: {count} trades, {wr:.1f}% WR, {avg_r:+.3f} avg R")

print()
print("="*80)
print("RESULTS")
print("="*80)
print()

if len(all_results) == 0:
    print("ERROR: No results generated")
    sys.exit(1)

df_all = pd.DataFrame(all_results)

# Save raw results
results_file = f'optimization_results_{orb_time}_canonical.json'
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
    print("="*80)
    print("BEST SETUP:")
    print("="*80)
    print(f"  Stop: {best['stop_frac']:.2f} x ORB (risk = {best['stop_frac']:.2f} × ORB size)")
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
    print(f"  Trades: {best['trades']:.0f}")
    print(f"  Win rate: {best['wr']:.1f}% (need {best['be_wr']:.1f}%)")
    print(f"  Avg R: {best['avg_r']:+.3f}")
    print(f"  Total R: {best['total_r']:+.1f}")

print()

# Analysis
print("="*80)
print("STOP FRACTION ANALYSIS")
print("="*80)
print()

print("Average R by stop fraction (across all RR values):")
for stop_frac in STOP_FRACTIONS:
    frac_data = df_all[df_all['stop_frac'] == stop_frac]
    avg = frac_data['avg_r'].mean()
    print(f"  {stop_frac:.2f}: {avg:+.3f} avg R")

print()
print("Average R by RR (across all stop fractions):")
for rr_val in RR_VALUES:
    rr_data = df_all[df_all['rr'] == rr_val]
    avg = rr_data['avg_r'].mean()
    print(f"  RR {rr_val:.1f}: {avg:+.3f} avg R")

print()
