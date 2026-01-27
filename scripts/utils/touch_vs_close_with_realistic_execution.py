"""
TOUCH vs CLOSE WITH REALISTIC EXECUTION COSTS

HONEST slippage modeling:

TOUCH ENTRY (market order on touch):
- Entry: ORB boundary + 0.5pts slippage
- Cost: $2.50
- Entry bar: First bar where high/low touches boundary

CLOSE ENTRY (market order after close):
- Entry: Close price (already ~0.5pts beyond boundary) + 0.5pts additional slippage
- Cost: $2.50
- Entry bar: First bar that closes outside ORB

Total entry degradation:
- Touch: +0.5pts from boundary
- Close: +1.0pts from boundary (0.5 to close, +0.5 slippage)

Close should be worse by ~0.5pts on average.

BUT: Close has CONFIRMATION value (filters weak breakouts).

Question: Does confirmation compensate for 0.5pts worse entry?
"""

import duckdb
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

DB_PATH = 'data/db/gold.db'
SYMBOL = 'MGC'

COMMISSION = 1.0
SLIPPAGE_TICKS = 5  # 0.5 points = 5 ticks
TICK_SIZE = 0.1
POINT_VALUE = 10.0

SLIPPAGE_POINTS = SLIPPAGE_TICKS * TICK_SIZE

def simulate_touch_with_costs(bars_1m, orb_high, orb_low, rr):
    """
    Touch entry with realistic execution:
    - Entry at boundary + slippage
    - Costs: $2.50
    """
    if len(bars_1m) == 0:
        return None

    # Find touch
    for i, row in bars_1m.iterrows():
        high = float(row['high'])
        low = float(row['low'])

        if high >= orb_high and low <= orb_low:
            return None

        if high >= orb_high:
            direction = 'UP'
            entry = orb_high + SLIPPAGE_POINTS  # Realistic fill
            stop = orb_low
            break
        elif low <= orb_low:
            direction = 'DOWN'
            entry = orb_low - SLIPPAGE_POINTS  # Realistic fill
            stop = orb_high
            break
    else:
        return None

    risk = abs(entry - stop)
    target = entry + (rr * risk) if direction == 'UP' else entry - (rr * risk)

    # Check outcome
    for j in range(i + 1, len(bars_1m)):
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
    cost_r = (COMMISSION + SLIPPAGE_TICKS * TICK_SIZE * POINT_VALUE) / (risk * POINT_VALUE)

    return outcome_r - cost_r

def simulate_close_with_costs(bars_1m, orb_high, orb_low, rr):
    """
    Close entry with realistic execution:
    - Entry at close price + additional slippage
    - Costs: $2.50
    - Close price already ~0.5pts beyond boundary
    """
    if len(bars_1m) == 0:
        return None

    # Find first close outside
    for i, row in bars_1m.iterrows():
        close = float(row['close'])

        if close > orb_high or close < orb_low:
            direction = 'UP' if close > orb_high else 'DOWN'

            # Entry at close + slippage on next bar
            entry = close + SLIPPAGE_POINTS if direction == 'UP' else close - SLIPPAGE_POINTS

            stop = orb_low if direction == 'UP' else orb_high
            break
    else:
        return None

    risk = abs(entry - stop)
    target = entry + (rr * risk) if direction == 'UP' else entry - (rr * risk)

    # Check outcome
    for j in range(i + 1, len(bars_1m)):
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
    cost_r = (COMMISSION + SLIPPAGE_TICKS * TICK_SIZE * POINT_VALUE) / (risk * POINT_VALUE)

    return outcome_r - cost_r


print("="*80)
print("TOUCH vs CLOSE WITH REALISTIC EXECUTION COSTS")
print("="*80)
print()
print("Both use market orders with $2.50 costs")
print("Touch: Entry at boundary + 0.5pts slippage")
print("Close: Entry at close + 0.5pts slippage (total ~1.0pt from boundary)")
print()

conn = duckdb.connect(DB_PATH, read_only=True)

# Test validated setups
ORB_CONFIGS = {
    '0900': {'hour': 9, 'minute': 0, 'rr': 6.0},
    '1000': {'hour': 10, 'minute': 0, 'rr': 8.0},
    '1100': {'hour': 11, 'minute': 0, 'rr': 3.0},
    '1800': {'hour': 18, 'minute': 0, 'rr': 1.5},
}

for orb_time, config in ORB_CONFIGS.items():
    hour = config['hour']
    minute = config['minute']
    rr = config['rr']

    print(f"\n{'='*80}")
    print(f"{orb_time} ORB - RR={rr:.1f}")
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

    touch_results = []
    close_results = []

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

        touch_r = simulate_touch_with_costs(bars, orb_high, orb_low, rr)
        close_r = simulate_close_with_costs(bars, orb_high, orb_low, rr)

        if touch_r is not None:
            touch_results.append(touch_r)
        if close_r is not None:
            close_results.append(close_r)

    # Stats
    touch_count = len(touch_results)
    touch_total = sum(touch_results)
    touch_avg = touch_total / touch_count if touch_count > 0 else 0

    close_count = len(close_results)
    close_total = sum(close_results)
    close_avg = close_total / close_count if close_count > 0 else 0

    diff = touch_total - close_total

    print(f"Touch: {touch_count} trades, {touch_avg:+.3f} avg R, {touch_total:+.1f}R total")
    print(f"Close: {close_count} trades, {close_avg:+.3f} avg R, {close_total:+.1f}R total")
    print()

    if abs(diff) < 10:
        print(f"NEUTRAL ({diff:+.1f}R difference)")
    elif diff > 0:
        print(f"TOUCH WINS by {diff:+.1f}R")
    else:
        print(f"CLOSE WINS by {abs(diff):+.1f}R")

    print()

conn.close()

print("="*80)
print("HONEST ANSWER")
print("="*80)
print()
print("Both methods cost $2.50 per trade (market orders)")
print("Close entry is ~1.0pt worse price due to:")
print("  - Wait for close (~0.5pts beyond boundary)")
print("  - Plus slippage on next bar (+0.5pts)")
print()
print("If touch and close have similar results after costs:")
print("  Entry method doesn't matter")
print("  Confirmation value ~= Entry price advantage")
print()
print("Focus on what ACTUALLY improves edges:")
print("  - Filters (session type, ORB size)")
print("  - Trade management (SL, early exit)")
print("  - Position sizing")
print()
