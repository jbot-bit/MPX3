"""
ADVANCED TRADE MANAGEMENT FILTERS

Tests dynamic SL adjustment and early invalidation rules:

1. EARLY INVALIDATION (cut loss before full stop):
   - If price reverses back inside ORB after X bars → Exit
   - If target not hit within Y bars → Exit
   - If opposite ORB boundary touched → Exit (full reversal signal)

2. BREAKEVEN SL (lock in wins):
   - Move SL to entry after price moves +0.5R
   - Move SL to entry after X bars in profit
   - Trailing stop (follow price at -0.5R)

3. ALTERNATIVE STOPS:
   - 1/4 ORB (tighter stop, higher RR)
   - 1/2 ORB (half stop - already tested)
   - ATR-based stop (volatility-adjusted)

4. TIME-BASED EXITS:
   - Exit if still open at end of session
   - Exit if X hours pass with no progress

For each rule, compare:
- Original (full ORB stop, no management)
- With rule applied
- See if improvement > 0.10R (worth the complexity)
"""

import duckdb
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

DB_PATH = 'data/db/gold.db'
SYMBOL = 'MGC'

def simulate_with_early_invalidation(bars_1m, orb_high, orb_low, rr, invalidation_bars=5):
    """
    Early invalidation: Exit if price reverses back inside ORB within N bars.

    This detects failed breakouts early.
    """
    if len(bars_1m) == 0:
        return None

    # Find touch/entry
    for i, row in bars_1m.iterrows():
        close = float(row['close'])

        if close > orb_high or close < orb_low:
            direction = 'UP' if close > orb_high else 'DOWN'
            entry = close
            stop = orb_low if direction == 'UP' else orb_high
            entry_bar = i
            break
    else:
        return None

    risk = abs(entry - stop)
    target = entry + (rr * risk) if direction == 'UP' else entry - (rr * risk)

    # Check for early invalidation or outcome
    for j in range(entry_bar + 1, len(bars_1m)):
        row = bars_1m.iloc[j]
        high = float(row['high'])
        low = float(row['low'])
        close = float(row['close'])

        bars_since_entry = j - entry_bar

        # EARLY INVALIDATION: Reverses back inside ORB within N bars
        if bars_since_entry <= invalidation_bars:
            if direction == 'UP':
                reverses_inside = close < orb_high
            else:
                reverses_inside = close > orb_low

            if reverses_inside:
                # Exit immediately - estimate loss
                if direction == 'UP':
                    loss_r = (close - entry) / risk
                else:
                    loss_r = (entry - close) / risk

                return {
                    'outcome': 'INVALIDATED',
                    'r_multiple': loss_r,
                    'exited_early': True,
                    'bars_held': bars_since_entry
                }

        # Normal stop/target check
        if direction == 'UP':
            if low <= stop:
                return {'outcome': 'LOSS', 'r_multiple': -1.0, 'exited_early': False, 'bars_held': bars_since_entry}
            elif high >= target:
                return {'outcome': 'WIN', 'r_multiple': rr, 'exited_early': False, 'bars_held': bars_since_entry}
        else:
            if high >= stop:
                return {'outcome': 'LOSS', 'r_multiple': -1.0, 'exited_early': False, 'bars_held': bars_since_entry}
            elif low <= target:
                return {'outcome': 'WIN', 'r_multiple': rr, 'exited_early': False, 'bars_held': bars_since_entry}

    return {'outcome': 'NO_EXIT', 'r_multiple': 0.0, 'exited_early': False, 'bars_held': len(bars_1m) - entry_bar}

def simulate_with_breakeven_sl(bars_1m, orb_high, orb_low, rr, be_threshold=0.5):
    """
    Breakeven SL: Move stop to entry after price moves +0.5R in your favor.

    This locks in winners and prevents winning trades from becoming losers.
    """
    if len(bars_1m) == 0:
        return None

    # Find entry
    for i, row in bars_1m.iterrows():
        close = float(row['close'])

        if close > orb_high or close < orb_low:
            direction = 'UP' if close > orb_high else 'DOWN'
            entry = close
            original_stop = orb_low if direction == 'UP' else orb_high
            entry_bar = i
            break
    else:
        return None

    risk = abs(entry - original_stop)
    target = entry + (rr * risk) if direction == 'UP' else entry - (rr * risk)

    # Breakeven trigger level
    be_level = entry + (be_threshold * risk) if direction == 'UP' else entry - (be_threshold * risk)

    current_stop = original_stop
    be_triggered = False

    # Check outcome with dynamic SL
    for j in range(entry_bar + 1, len(bars_1m)):
        row = bars_1m.iloc[j]
        high = float(row['high'])
        low = float(row['low'])

        # Check if BE threshold reached
        if not be_triggered:
            if direction == 'UP':
                if high >= be_level:
                    current_stop = entry  # Move stop to breakeven
                    be_triggered = True
            else:
                if low <= be_level:
                    current_stop = entry
                    be_triggered = True

        # Check if stopped out or hit target
        if direction == 'UP':
            if low <= current_stop:
                # Hit stop - was it original or BE?
                if be_triggered:
                    return {'outcome': 'BE_STOP', 'r_multiple': 0.0, 'be_triggered': True}
                else:
                    return {'outcome': 'LOSS', 'r_multiple': -1.0, 'be_triggered': False}
            elif high >= target:
                return {'outcome': 'WIN', 'r_multiple': rr, 'be_triggered': be_triggered}
        else:
            if high >= current_stop:
                if be_triggered:
                    return {'outcome': 'BE_STOP', 'r_multiple': 0.0, 'be_triggered': True}
                else:
                    return {'outcome': 'LOSS', 'r_multiple': -1.0, 'be_triggered': False}
            elif low <= target:
                return {'outcome': 'WIN', 'r_multiple': rr, 'be_triggered': be_triggered}

    return {'outcome': 'NO_EXIT', 'r_multiple': 0.0, 'be_triggered': be_triggered}

def simulate_with_tight_stop(bars_1m, orb_high, orb_low, rr, stop_fraction=0.25):
    """
    Tight stop: Use fraction of ORB (e.g. 1/4) instead of full ORB.

    Tighter stop = higher effective RR, but more likely to get stopped.
    """
    if len(bars_1m) == 0:
        return None

    orb_size = orb_high - orb_low
    orb_mid = (orb_high + orb_low) / 2

    # Find entry
    for i, row in bars_1m.iterrows():
        close = float(row['close'])

        if close > orb_high or close < orb_low:
            direction = 'UP' if close > orb_high else 'DOWN'
            entry = close
            entry_bar = i
            break
    else:
        return None

    # Tight stop (fraction of ORB from entry)
    tight_risk = orb_size * stop_fraction

    if direction == 'UP':
        stop = entry - tight_risk
    else:
        stop = entry + tight_risk

    target = entry + (rr * tight_risk) if direction == 'UP' else entry - (rr * tight_risk)

    # Check outcome
    for j in range(entry_bar + 1, len(bars_1m)):
        row = bars_1m.iloc[j]
        high = float(row['high'])
        low = float(row['low'])

        if direction == 'UP':
            if low <= stop:
                return {'outcome': 'LOSS', 'r_multiple': -1.0, 'stop_distance': tight_risk}
            elif high >= target:
                return {'outcome': 'WIN', 'r_multiple': rr, 'stop_distance': tight_risk}
        else:
            if high >= stop:
                return {'outcome': 'LOSS', 'r_multiple': -1.0, 'stop_distance': tight_risk}
            elif low <= target:
                return {'outcome': 'WIN', 'r_multiple': rr, 'stop_distance': tight_risk}

    return {'outcome': 'NO_EXIT', 'r_multiple': 0.0, 'stop_distance': tight_risk}


print("="*80)
print("ADVANCED TRADE MANAGEMENT FILTERS TEST")
print("="*80)
print()
print("Testing dynamic SL and early invalidation rules")
print()

conn = duckdb.connect(DB_PATH, read_only=True)

# Test on best validated setup: 1000 ORB, RR=8.0
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

# BASELINE: Original (full stop, no management)
baseline_results = []

# RULE 1: Early invalidation (exit if reverses inside ORB within 5 bars)
invalidation_results = []

# RULE 2: Breakeven SL (move to entry after +0.5R)
breakeven_results = []

# RULE 3: Tight stop (1/4 ORB)
tight_stop_results = []

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

    # Test each rule
    result_baseline = simulate_with_early_invalidation(bars, orb_high, orb_low, rr, invalidation_bars=999)  # No invalidation
    result_invalidation = simulate_with_early_invalidation(bars, orb_high, orb_low, rr, invalidation_bars=5)
    result_breakeven = simulate_with_breakeven_sl(bars, orb_high, orb_low, rr, be_threshold=0.5)
    result_tight = simulate_with_tight_stop(bars, orb_high, orb_low, rr, stop_fraction=0.25)

    if result_baseline is not None:
        baseline_results.append(result_baseline['r_multiple'])
    if result_invalidation is not None:
        invalidation_results.append(result_invalidation)
    if result_breakeven is not None:
        breakeven_results.append(result_breakeven)
    if result_tight is not None:
        tight_stop_results.append(result_tight)

conn.close()

# Analyze results
print("="*80)
print("BASELINE: Full ORB stop, no management")
print("="*80)
print()

baseline_arr = np.array(baseline_results)
baseline_mean = np.mean(baseline_arr)
baseline_total = np.sum(baseline_arr)
baseline_count = len(baseline_arr)
baseline_wins = len([r for r in baseline_arr if r > 0])
baseline_wr = baseline_wins / baseline_count * 100

print(f"Trades: {baseline_count}")
print(f"Win rate: {baseline_wr:.1f}%")
print(f"Avg R: {baseline_mean:+.3f}")
print(f"Total R: {baseline_total:+.1f}")
print()

# RULE 1: Early invalidation
print("="*80)
print("RULE 1: Early Invalidation (exit if reverses inside within 5 bars)")
print("="*80)
print()

df_inv = pd.DataFrame(invalidation_results)
inv_count = len(df_inv)
inv_total = df_inv['r_multiple'].sum()
inv_avg = df_inv['r_multiple'].mean()
inv_wins = len(df_inv[df_inv['outcome'] == 'WIN'])
inv_wr = inv_wins / inv_count * 100
inv_early_exits = len(df_inv[df_inv['exited_early'] == True])

print(f"Trades: {inv_count}")
print(f"Early exits: {inv_early_exits} ({inv_early_exits/inv_count*100:.1f}%)")
print(f"Win rate: {inv_wr:.1f}%")
print(f"Avg R: {inv_avg:+.3f}")
print(f"Total R: {inv_total:+.1f}")
print()

inv_improvement = inv_total - baseline_total

print(f"vs BASELINE: {inv_improvement:+.1f}R ({inv_avg - baseline_mean:+.3f}R per trade)")

if inv_improvement > baseline_count * 0.10:
    print("SIGNIFICANT IMPROVEMENT (+0.10R/trade threshold)")
    print("RECOMMENDATION: Implement early invalidation")
else:
    print("Minimal/negative improvement")
    print("RECOMMENDATION: Skip this rule")

print()

# Analyze what early exits looked like
early_exit_trades = df_inv[df_inv['exited_early'] == True]
if len(early_exit_trades) > 0:
    avg_exit_r = early_exit_trades['r_multiple'].mean()
    avg_bars = early_exit_trades['bars_held'].mean()

    print(f"Early exit trades:")
    print(f"  Count: {len(early_exit_trades)}")
    print(f"  Avg R: {avg_exit_r:+.3f}")
    print(f"  Avg bars held: {avg_bars:.1f}")
    print()

# RULE 2: Breakeven SL
print("="*80)
print("RULE 2: Breakeven SL (move to entry after +0.5R)")
print("="*80)
print()

df_be = pd.DataFrame(breakeven_results)
be_count = len(df_be)
be_total = df_be['r_multiple'].sum()
be_avg = df_be['r_multiple'].mean()
be_wins = len(df_be[df_be['outcome'] == 'WIN'])
be_stops = len(df_be[df_be['outcome'] == 'BE_STOP'])
be_losses = len(df_be[df_be['outcome'] == 'LOSS'])
be_wr = be_wins / be_count * 100

print(f"Trades: {be_count}")
print(f"Wins: {be_wins} ({be_wr:.1f}%)")
print(f"BE stops: {be_stops} (stopped at breakeven)")
print(f"Losses: {be_losses} (stopped before BE trigger)")
print(f"Avg R: {be_avg:+.3f}")
print(f"Total R: {be_total:+.1f}")
print()

be_improvement = be_total - baseline_total

print(f"vs BASELINE: {be_improvement:+.1f}R ({be_avg - baseline_mean:+.3f}R per trade)")

if be_improvement > baseline_count * 0.10:
    print("SIGNIFICANT IMPROVEMENT")
    print("RECOMMENDATION: Implement breakeven SL")
else:
    print("Minimal/negative improvement")
    print("RECOMMENDATION: Skip this rule")

print()

# How many winners became BE stops?
be_triggered = len(df_be[df_be['be_triggered'] == True])
print(f"BE triggered: {be_triggered} trades ({be_triggered/be_count*100:.1f}%)")

if be_stops > 0:
    print(f"  {be_stops} of these became BE stops (would have been losses: saved {be_stops * 1.0:.1f}R)")

print()

# RULE 3: Tight stop (1/4 ORB)
print("="*80)
print("RULE 3: Tight Stop (1/4 ORB instead of full ORB)")
print("="*80)
print()

df_tight = pd.DataFrame(tight_stop_results)
tight_count = len(df_tight)
tight_total = df_tight['r_multiple'].sum()
tight_avg = df_tight['r_multiple'].mean()
tight_wins = len(df_tight[df_tight['outcome'] == 'WIN'])
tight_wr = tight_wins / tight_count * 100

print(f"Trades: {tight_count}")
print(f"Win rate: {tight_wr:.1f}%")
print(f"Avg R: {tight_avg:+.3f}")
print(f"Total R: {tight_total:+.1f}")
print()

tight_improvement = tight_total - baseline_total

print(f"vs BASELINE: {tight_improvement:+.1f}R ({tight_avg - baseline_mean:+.3f}R per trade)")

if tight_improvement > baseline_count * 0.10:
    print("SIGNIFICANT IMPROVEMENT")
    print("RECOMMENDATION: Use 1/4 ORB stops")
else:
    print("Minimal/negative improvement")
    print("RECOMMENDATION: Stick with full ORB stops")

print()

# SUMMARY
print("="*80)
print("SUMMARY: Which management rules add value?")
print("="*80)
print()

rules = [
    ('Baseline', baseline_mean, baseline_total, baseline_count),
    ('Early Invalidation', inv_avg, inv_total, inv_count),
    ('Breakeven SL', be_avg, be_total, be_count),
    ('Tight Stop (1/4)', tight_avg, tight_total, tight_count)
]

summary_df = pd.DataFrame(rules, columns=['Rule', 'Avg R', 'Total R', 'Trades'])
print(summary_df.to_string(index=False))

print()

# Best rule
best_total = max([r[2] for r in rules])
best_rule = [r for r in rules if r[2] == best_total][0]

print(f"BEST RULE: {best_rule[0]}")
print(f"  Total R: {best_rule[2]:+.1f}")
print(f"  Improvement over baseline: {best_rule[2] - baseline_total:+.1f}R")

print()
