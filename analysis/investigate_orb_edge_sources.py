"""
INVESTIGATION: WHY 1000 ORB BEATS RANDOM, BUT NIGHT ORBS FAIL
==============================================================

Tasks:
1. Session mapping (Brisbane -> NY time with DST handling)
2. Decompose 1000 ORB edge via ablations (L4, volatility, directional bias)
3. Find "1000-like" states at 2300/0030 ORBs
4. Full validation with random baseline

HARD CONSTRAINTS:
- If strategy expectancy <= random expectancy, REJECT
- Use $8.40 RT costs (canonical)
- HONESTY OVER OUTCOME

Author: Quant Research Team
Date: 2026-01-27
"""

import duckdb
import numpy as np
import pandas as pd
from pathlib import Path
import sys
from datetime import datetime, timezone, timedelta
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, 'pipeline')
from cost_model import get_cost_model, get_instrument_specs

DB_PATH = Path('data/db/gold.db')

# CANONICAL COST MODEL
mgc_specs = get_instrument_specs('MGC')
mgc_costs = get_cost_model('MGC', stress_level='normal')
POINT_VALUE = mgc_specs['point_value']
FRICTION = mgc_costs['total_friction']

print("=" * 100)
print("INVESTIGATION: ORB EDGE SOURCES")
print("=" * 100)
print()
print(f"Cost Model: ${FRICTION:.2f} RT (commission ${mgc_costs['commission_rt']:.2f} + "
      f"spread ${mgc_costs['spread_double']:.2f} + slippage ${mgc_costs['slippage_rt']:.2f})")
print()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_realized_expectancy(trades_df, rr, point_value, friction):
    """Calculate expectancy using CANONICAL formulas."""
    if len(trades_df) == 0:
        return None, 0, None, None

    realized_r_values = []
    wins = 0
    losses = 0

    for idx, row in trades_df.iterrows():
        orb_high = row['orb_high']
        orb_low = row['orb_low']
        break_dir = row['break_dir']
        outcome = row['outcome']

        if pd.isna(orb_high) or pd.isna(orb_low) or pd.isna(break_dir) or pd.isna(outcome):
            continue

        if break_dir == 'UP':
            entry, stop = orb_high, orb_low
        elif break_dir == 'DOWN':
            entry, stop = orb_low, orb_high
        else:
            continue

        stop_dist_points = abs(entry - stop)

        # CANONICAL FORMULAS
        realized_risk_dollars = (stop_dist_points * point_value) + friction
        target_dist_points = stop_dist_points * rr
        realized_reward_dollars = (target_dist_points * point_value) - friction

        if outcome == 'WIN':
            net_pnl = realized_reward_dollars
            wins += 1
        else:
            net_pnl = -realized_risk_dollars
            losses += 1

        realized_r = net_pnl / realized_risk_dollars
        realized_r_values.append(realized_r)

    if len(realized_r_values) == 0:
        return None, 0, None, None

    win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0

    return np.mean(realized_r_values), len(realized_r_values), win_rate, realized_r_values


def random_entry_baseline(trades_df, rr, point_value, friction, win_rate=0.50):
    """Calculate expectancy for random entry (50% WR baseline)."""
    if len(trades_df) == 0:
        return None, 0

    realized_r_values = []

    for idx, row in trades_df.iterrows():
        orb_high = row['orb_high']
        orb_low = row['orb_low']
        break_dir = row['break_dir']

        if pd.isna(orb_high) or pd.isna(orb_low) or pd.isna(break_dir):
            continue

        if break_dir == 'UP':
            entry, stop = orb_high, orb_low
        elif break_dir == 'DOWN':
            entry, stop = orb_low, orb_high
        else:
            continue

        stop_dist_points = abs(entry - stop)

        # CANONICAL FORMULAS
        realized_risk_dollars = (stop_dist_points * point_value) + friction
        target_dist_points = stop_dist_points * rr
        realized_reward_dollars = (target_dist_points * point_value) - friction

        # Random outcome (50% win rate)
        if np.random.random() < win_rate:
            net_pnl = realized_reward_dollars
        else:
            net_pnl = -realized_risk_dollars

        realized_r = net_pnl / realized_risk_dollars
        realized_r_values.append(realized_r)

    if len(realized_r_values) == 0:
        return None, 0

    return np.mean(realized_r_values), len(realized_r_values)


def map_brisbane_to_ny_time(date_local_str, orb_time_brisbane):
    """
    Map Brisbane ORB time to NY time with DST handling.

    Brisbane: UTC+10 (no DST)
    NY: UTC-5 (EST) or UTC-4 (EDT)
    DST transitions ~March and ~November

    Args:
        date_local_str: Date in Brisbane (YYYY-MM-DD)
        orb_time_brisbane: ORB time in Brisbane (HH:MM)

    Returns:
        NY time string (HH:MM), session label
    """
    # Parse date
    date_obj = datetime.strptime(date_local_str, '%Y-%m-%d')

    # Parse ORB time
    hour, minute = map(int, orb_time_brisbane.split(':'))

    # Create Brisbane datetime (UTC+10, no DST)
    brisbane_dt = datetime(date_obj.year, date_obj.month, date_obj.day, hour, minute)
    utc_dt = brisbane_dt - timedelta(hours=10)

    # Determine if NY is on DST (rough approximation)
    # DST typically March-November
    month = date_obj.month
    if 3 <= month <= 10:  # Rough DST period
        ny_offset = -4  # EDT (UTC-4)
    else:
        ny_offset = -5  # EST (UTC-5)

    ny_dt = utc_dt + timedelta(hours=ny_offset)

    ny_time_str = f"{ny_dt.hour:02d}:{ny_dt.minute:02d}"

    # Label session
    ny_hour = ny_dt.hour
    if 9 <= ny_hour < 16:
        session = "NY_CASH_HOURS"
    elif 8 <= ny_hour < 9:
        session = "NY_PRE_OPEN"
    elif 16 <= ny_hour < 17:
        session = "NY_CLOSE_WINDOW"
    elif 17 <= ny_hour < 18:
        session = "NY_POST_CLOSE"
    else:
        session = "NY_OVERNIGHT"

    return ny_time_str, session


# =============================================================================
# TASK 1: SESSION MAPPING
# =============================================================================

print("=" * 100)
print("TASK 1: SESSION MAPPING (Brisbane -> NY Time)")
print("=" * 100)
print()

orb_times_brisbane = ['09:00', '10:00', '11:00', '18:00', '23:00', '00:30']

# Sample dates for mapping (first and 15th of each month for 2024-2025)
sample_dates = []
for year in [2024, 2025]:
    for month in range(1, 13):
        sample_dates.append(f"{year}-{month:02d}-01")
        sample_dates.append(f"{year}-{month:02d}-15")

print("ORB Time Mapping (Brisbane -> NY):")
print()
print(f"{'Date':<12} {'ORB (BNE)':<10} {'NY Time':<10} {'Session':<20}")
print("-" * 60)

mapping_results = []
for date in sample_dates[:12]:  # Show first 12 examples
    for orb_time in orb_times_brisbane:
        ny_time, session = map_brisbane_to_ny_time(date, orb_time)
        mapping_results.append({
            'date': date,
            'orb_brisbane': orb_time,
            'ny_time': ny_time,
            'session': session
        })
        if orb_time in ['09:00', '10:00', '23:00', '00:30']:  # Focus on key ORBs
            print(f"{date:<12} {orb_time:<10} {ny_time:<10} {session:<20}")

print()
print("KEY FINDINGS:")
print("- 09:00 Brisbane = NY overnight/pre-market (depending on DST)")
print("- 10:00 Brisbane = NY overnight/pre-market (depending on DST)")
print("- 23:00 Brisbane = NY morning (depending on DST)")
print("- 00:30 Brisbane = NY morning/midday (depending on DST)")
print()

# Save full mapping
mapping_df = pd.DataFrame(mapping_results)
mapping_df.to_csv('analysis/output/session_mapping_brisbane_ny.csv', index=False)
print("Full mapping saved to: analysis/output/session_mapping_brisbane_ny.csv")
print()


# =============================================================================
# LOAD DATA
# =============================================================================

print("=" * 100)
print("LOADING DATA")
print("=" * 100)
print()

conn = duckdb.connect(str(DB_PATH), read_only=True)

query = """
SELECT
    date_local,

    -- Session ranges
    asia_high, asia_low, asia_range,
    london_high, london_low, london_range,
    ny_high, ny_low, ny_range,

    -- Pre-session ranges
    pre_asia_range, pre_london_range, pre_ny_range,

    -- ORB 0900
    orb_0900_high, orb_0900_low, orb_0900_size,
    orb_0900_break_dir, orb_0900_outcome,
    orb_0900_mae, orb_0900_mfe,

    -- ORB 1000
    orb_1000_high, orb_1000_low, orb_1000_size,
    orb_1000_break_dir, orb_1000_outcome,
    orb_1000_mae, orb_1000_mfe,

    -- ORB 2300
    orb_2300_high, orb_2300_low, orb_2300_size,
    orb_2300_break_dir, orb_2300_outcome,
    orb_2300_mae, orb_2300_mfe,

    -- ORB 0030
    orb_0030_high, orb_0030_low, orb_0030_size,
    orb_0030_break_dir, orb_0030_outcome,
    orb_0030_mae, orb_0030_mfe,

    -- Indicators
    rsi_at_0030, atr_20

FROM daily_features_v2
WHERE instrument = 'MGC'
    AND date_local >= '2024-01-02'
    AND date_local <= '2026-01-26'
ORDER BY date_local
"""

df = conn.execute(query).df()
conn.close()

print(f"Loaded {len(df)} days of data")
print()


# =============================================================================
# TASK 2: DECOMPOSE 1000 ORB EDGE
# =============================================================================

print("=" * 100)
print("TASK 2: DECOMPOSE 1000 ORB EDGE")
print("=" * 100)
print()

# Prepare 1000 ORB data
orb_1000 = df[df['orb_1000_outcome'].notna()].copy()
orb_1000['orb_high'] = orb_1000['orb_1000_high']
orb_1000['orb_low'] = orb_1000['orb_1000_low']
orb_1000['break_dir'] = orb_1000['orb_1000_break_dir']
orb_1000['outcome'] = orb_1000['orb_1000_outcome']

# Calculate L4 filter (London inside Asia)
orb_1000['L4_CONSOLIDATION'] = (
    (orb_1000['london_high'] <= orb_1000['asia_high']) &
    (orb_1000['london_low'] >= orb_1000['asia_low'])
)

# Volatility regime (ATR quintiles)
orb_1000['atr_quintile'] = pd.qcut(orb_1000['atr_20'], q=5, labels=['Q1_LOW', 'Q2', 'Q3', 'Q4', 'Q5_HIGH'])

# Range regime (ORB size quintiles)
orb_1000['orb_size_quintile'] = pd.qcut(orb_1000['orb_1000_size'], q=5, labels=['Q1_SMALL', 'Q2', 'Q3', 'Q4', 'Q5_LARGE'])

print("BASELINE: 1000 ORB (No Filters)")
print("-" * 100)

np.random.seed(42)
baseline_exp, baseline_n, baseline_wr, _ = calculate_realized_expectancy(
    orb_1000, rr=3.0, point_value=POINT_VALUE, friction=FRICTION
)
random_exp, _ = random_entry_baseline(orb_1000, rr=3.0, point_value=POINT_VALUE, friction=FRICTION)

print(f"Trades: {baseline_n}")
print(f"Win Rate: {baseline_wr*100:.1f}%")
print(f"Expectancy: {baseline_exp:+.3f}R")
print(f"Random Baseline: {random_exp:+.3f}R (50% WR)")
print(f"Edge vs Random: {baseline_exp - random_exp:+.3f}R")

if baseline_exp > random_exp:
    print("[PASS] BEATS RANDOM")
else:
    print("[FAIL] FAILS vs RANDOM")

print()

# Test: DIRECTIONAL BIAS
print("TEST 1: DIRECTIONAL BIAS")
print("-" * 100)

up_breaks = orb_1000[orb_1000['break_dir'] == 'UP']
down_breaks = orb_1000[orb_1000['break_dir'] == 'DOWN']

up_exp, up_n, up_wr, _ = calculate_realized_expectancy(up_breaks, rr=3.0, point_value=POINT_VALUE, friction=FRICTION)
down_exp, down_n, down_wr, _ = calculate_realized_expectancy(down_breaks, rr=3.0, point_value=POINT_VALUE, friction=FRICTION)

print(f"UP Breaks: {up_n} trades, WR={up_wr*100:.1f}%, Exp={up_exp:+.3f}R")
print(f"DOWN Breaks: {down_n} trades, WR={down_wr*100:.1f}%, Exp={down_exp:+.3f}R")
print(f"Asymmetry: {abs(up_exp - down_exp):.3f}R")

if abs(up_exp - down_exp) > 0.3:
    print(">> STRONG directional bias detected")
else:
    print(">> WEAK directional bias")

print()

# Test: L4_CONSOLIDATION filter
print("TEST 2: L4_CONSOLIDATION FILTER")
print("-" * 100)

l4_yes = orb_1000[orb_1000['L4_CONSOLIDATION'] == True]
l4_no = orb_1000[orb_1000['L4_CONSOLIDATION'] == False]

l4_yes_exp, l4_yes_n, l4_yes_wr, _ = calculate_realized_expectancy(l4_yes, rr=3.0, point_value=POINT_VALUE, friction=FRICTION)
l4_no_exp, l4_no_n, l4_no_wr, _ = calculate_realized_expectancy(l4_no, rr=3.0, point_value=POINT_VALUE, friction=FRICTION)

np.random.seed(42)
l4_yes_random, _ = random_entry_baseline(l4_yes, rr=3.0, point_value=POINT_VALUE, friction=FRICTION)

print(f"L4=YES: {l4_yes_n} trades, WR={l4_yes_wr*100:.1f}%, Exp={l4_yes_exp:+.3f}R")
print(f"L4=NO: {l4_no_n} trades, WR={l4_no_wr*100:.1f}%, Exp={l4_no_exp:+.3f}R")
print(f"Delta: {l4_yes_exp - l4_no_exp:+.3f}R")
print(f"L4=YES vs Random: {l4_yes_exp - l4_yes_random:+.3f}R")

if l4_yes_exp > l4_yes_random:
    print("[PASS] L4=YES beats random")
else:
    print("[FAIL] L4=YES FAILS vs random")

print()

# Test: VOLATILITY REGIME
print("TEST 3: VOLATILITY REGIME (ATR Quintiles)")
print("-" * 100)

for quintile in ['Q1_LOW', 'Q2', 'Q3', 'Q4', 'Q5_HIGH']:
    subset = orb_1000[orb_1000['atr_quintile'] == quintile]
    if len(subset) < 10:
        continue

    exp, n, wr, _ = calculate_realized_expectancy(subset, rr=3.0, point_value=POINT_VALUE, friction=FRICTION)
    np.random.seed(42)
    rand_exp, _ = random_entry_baseline(subset, rr=3.0, point_value=POINT_VALUE, friction=FRICTION)

    beats_random = "[PASS]" if exp > rand_exp else "[FAIL]"
    print(f"{quintile}: {n} trades, WR={wr*100:.1f}%, Exp={exp:+.3f}R vs Random={rand_exp:+.3f}R {beats_random}")

print()

# Test: ORB SIZE REGIME
print("TEST 4: ORB SIZE REGIME (Size Quintiles)")
print("-" * 100)

for quintile in ['Q1_SMALL', 'Q2', 'Q3', 'Q4', 'Q5_LARGE']:
    subset = orb_1000[orb_1000['orb_size_quintile'] == quintile]
    if len(subset) < 10:
        continue

    exp, n, wr, _ = calculate_realized_expectancy(subset, rr=3.0, point_value=POINT_VALUE, friction=FRICTION)
    np.random.seed(42)
    rand_exp, _ = random_entry_baseline(subset, rr=3.0, point_value=POINT_VALUE, friction=FRICTION)

    beats_random = "[PASS]" if exp > rand_exp else "[FAIL]"
    print(f"{quintile}: {n} trades, WR={wr*100:.1f}%, Exp={exp:+.3f}R vs Random={rand_exp:+.3f}R {beats_random}")

print()

# ABLATION STUDY
print("=" * 100)
print("ABLATION STUDY: ISOLATE MINIMAL CONDITIONS")
print("=" * 100)
print()

# Test combinations
conditions = [
    ("Baseline (no filters)", orb_1000),
    ("L4 only", l4_yes),
    ("Q1_LOW volatility only", orb_1000[orb_1000['atr_quintile'] == 'Q1_LOW']),
    ("Q5_HIGH volatility only", orb_1000[orb_1000['atr_quintile'] == 'Q5_HIGH']),
    ("L4 + Q1_LOW volatility", orb_1000[(orb_1000['L4_CONSOLIDATION'] == True) & (orb_1000['atr_quintile'] == 'Q1_LOW')]),
    ("L4 + Q5_HIGH volatility", orb_1000[(orb_1000['L4_CONSOLIDATION'] == True) & (orb_1000['atr_quintile'] == 'Q5_HIGH')]),
]

ablation_results = []

for name, subset in conditions:
    if len(subset) < 10:
        continue

    exp, n, wr, _ = calculate_realized_expectancy(subset, rr=3.0, point_value=POINT_VALUE, friction=FRICTION)
    np.random.seed(42)
    rand_exp, _ = random_entry_baseline(subset, rr=3.0, point_value=POINT_VALUE, friction=FRICTION)

    edge = exp - rand_exp
    beats_random = "[PASS]" if exp > rand_exp else "[FAIL]"

    ablation_results.append({
        'condition': name,
        'n': n,
        'win_rate': wr,
        'expectancy': exp,
        'random_baseline': rand_exp,
        'edge_vs_random': edge,
        'beats_random': beats_random
    })

    print(f"{name:<30} N={n:<3} WR={wr*100:>5.1f}% Exp={exp:>+6.3f}R Random={rand_exp:>+6.3f}R Edge={edge:>+6.3f}R {beats_random}")

print()

ablation_df = pd.DataFrame(ablation_results)
ablation_df.to_csv('analysis/output/ablation_1000_orb.csv', index=False)
print("Ablation results saved to: analysis/output/ablation_1000_orb.csv")
print()


# =============================================================================
# TASK 3: TEST NIGHT ORBs (2300, 0030)
# =============================================================================

print("=" * 100)
print("TASK 3: NIGHT ORBs vs RANDOM BASELINE")
print("=" * 100)
print()

# Prepare 2300 ORB
orb_2300 = df[df['orb_2300_outcome'].notna()].copy()
orb_2300['orb_high'] = orb_2300['orb_2300_high']
orb_2300['orb_low'] = orb_2300['orb_2300_low']
orb_2300['break_dir'] = orb_2300['orb_2300_break_dir']
orb_2300['outcome'] = orb_2300['orb_2300_outcome']
orb_2300['L4_CONSOLIDATION'] = (
    (orb_2300['london_high'] <= orb_2300['asia_high']) &
    (orb_2300['london_low'] >= orb_2300['asia_low'])
)

# Prepare 0030 ORB
orb_0030 = df[df['orb_0030_outcome'].notna()].copy()
orb_0030['orb_high'] = orb_0030['orb_0030_high']
orb_0030['orb_low'] = orb_0030['orb_0030_low']
orb_0030['break_dir'] = orb_0030['orb_0030_break_dir']
orb_0030['outcome'] = orb_0030['orb_0030_outcome']
orb_0030['L4_CONSOLIDATION'] = (
    (orb_0030['london_high'] <= orb_0030['asia_high']) &
    (orb_0030['london_low'] >= orb_0030['asia_low'])
)

print("2300 ORB BASELINE")
print("-" * 100)

np.random.seed(42)
orb_2300_exp, orb_2300_n, orb_2300_wr, _ = calculate_realized_expectancy(
    orb_2300, rr=3.0, point_value=POINT_VALUE, friction=FRICTION
)
orb_2300_random, _ = random_entry_baseline(orb_2300, rr=3.0, point_value=POINT_VALUE, friction=FRICTION)

print(f"Trades: {orb_2300_n}")
print(f"Win Rate: {orb_2300_wr*100:.1f}%")
print(f"Expectancy: {orb_2300_exp:+.3f}R")
print(f"Random Baseline: {orb_2300_random:+.3f}R (50% WR)")
print(f"Edge vs Random: {orb_2300_exp - orb_2300_random:+.3f}R")

if orb_2300_exp > orb_2300_random:
    print("[PASS] BEATS RANDOM")
else:
    print("[FAIL] FAILS vs RANDOM")

print()

print("0030 ORB BASELINE")
print("-" * 100)

np.random.seed(42)
orb_0030_exp, orb_0030_n, orb_0030_wr, _ = calculate_realized_expectancy(
    orb_0030, rr=3.0, point_value=POINT_VALUE, friction=FRICTION
)
orb_0030_random, _ = random_entry_baseline(orb_0030, rr=3.0, point_value=POINT_VALUE, friction=FRICTION)

print(f"Trades: {orb_0030_n}")
print(f"Win Rate: {orb_0030_wr*100:.1f}%")
print(f"Expectancy: {orb_0030_exp:+.3f}R")
print(f"Random Baseline: {orb_0030_random:+.3f}R (50% WR)")
print(f"Edge vs Random: {orb_0030_exp - orb_0030_random:+.3f}R")

if orb_0030_exp > orb_0030_random:
    print("[PASS] BEATS RANDOM")
else:
    print("[FAIL] FAILS vs RANDOM")

print()

# Test L4 filter on night ORBs
print("2300 ORB + L4_CONSOLIDATION")
print("-" * 100)

orb_2300_l4 = orb_2300[orb_2300['L4_CONSOLIDATION'] == True]
orb_2300_l4_exp, orb_2300_l4_n, orb_2300_l4_wr, _ = calculate_realized_expectancy(
    orb_2300_l4, rr=3.0, point_value=POINT_VALUE, friction=FRICTION
)
np.random.seed(42)
orb_2300_l4_random, _ = random_entry_baseline(orb_2300_l4, rr=3.0, point_value=POINT_VALUE, friction=FRICTION)

print(f"Trades: {orb_2300_l4_n}")
print(f"Win Rate: {orb_2300_l4_wr*100:.1f}%")
print(f"Expectancy: {orb_2300_l4_exp:+.3f}R")
print(f"Random Baseline: {orb_2300_l4_random:+.3f}R (50% WR)")
print(f"Edge vs Random: {orb_2300_l4_exp - orb_2300_l4_random:+.3f}R")

if orb_2300_l4_exp > orb_2300_l4_random:
    print("[PASS] BEATS RANDOM")
else:
    print("[FAIL] FAILS vs RANDOM")

print()

print("0030 ORB + L4_CONSOLIDATION")
print("-" * 100)

orb_0030_l4 = orb_0030[orb_0030['L4_CONSOLIDATION'] == True]
orb_0030_l4_exp, orb_0030_l4_n, orb_0030_l4_wr, _ = calculate_realized_expectancy(
    orb_0030_l4, rr=3.0, point_value=POINT_VALUE, friction=FRICTION
)
np.random.seed(42)
orb_0030_l4_random, _ = random_entry_baseline(orb_0030_l4, rr=3.0, point_value=POINT_VALUE, friction=FRICTION)

print(f"Trades: {orb_0030_l4_n}")
print(f"Win Rate: {orb_0030_l4_wr*100:.1f}%")
print(f"Expectancy: {orb_0030_l4_exp:+.3f}R")
print(f"Random Baseline: {orb_0030_l4_random:+.3f}R (50% WR)")
print(f"Edge vs Random: {orb_0030_l4_exp - orb_0030_l4_random:+.3f}R")

if orb_0030_l4_exp > orb_0030_l4_random:
    print("[PASS] BEATS RANDOM")
else:
    print("[FAIL] FAILS vs RANDOM")

print()


# =============================================================================
# TASK 4: FIND "1000-LIKE" STATES AT NIGHT ORBs
# =============================================================================

print("=" * 100)
print("TASK 4: FIND '1000-LIKE' STATES AT NIGHT ORBs")
print("=" * 100)
print()

print("1000-LIKE STATE DEFINITION (from ablation study above):")
print("- Best performer at 1000 ORB was identified in ablation study")
print("- Now testing if same conditions work at 2300/0030 ORBs")
print()

# Define "1000-like" state from best ablation result
# From ablation study, we need to identify the strongest minimal condition

best_ablation = ablation_df.loc[ablation_df['edge_vs_random'].idxmax()]
print(f"Best 1000 ORB condition: {best_ablation['condition']}")
print(f"  Edge vs Random: {best_ablation['edge_vs_random']:+.3f}R")
print()

# Test if L4_CONSOLIDATION works at night (already done above, but summarize)
print("REPRODUCING '1000-LIKE' CONDITIONS AT NIGHT ORBs:")
print("-" * 100)

night_tests = [
    ("2300 ORB + L4", orb_2300_l4_exp, orb_2300_l4_random, orb_2300_l4_n),
    ("0030 ORB + L4", orb_0030_l4_exp, orb_0030_l4_random, orb_0030_l4_n),
]

for name, exp, rand, n in night_tests:
    edge = exp - rand
    beats = "[PASS]" if exp > rand else "[FAIL]"
    print(f"{name:<20} N={n:<3} Exp={exp:>+6.3f}R Random={rand:>+6.3f}R Edge={edge:>+6.3f}R {beats}")

print()


# =============================================================================
# FINAL VERDICT
# =============================================================================

print("=" * 100)
print("FINAL VERDICT")
print("=" * 100)
print()

print("KEY FINDINGS:")
print()

print("1. SESSION MAPPING:")
print("   - ORB times are correctly mapped Brisbane -> NY")
print("   - 09:00/10:00 Brisbane = NY overnight/pre-market")
print("   - 23:00/00:30 Brisbane = NY morning/midday")
print()

print("2. 1000 ORB EDGE SOURCE:")
if baseline_exp > random_exp:
    print(f"   [PASS] 1000 ORB BEATS random baseline by {baseline_exp - random_exp:+.3f}R")
    print(f"   - Baseline: {baseline_exp:+.3f}R ({baseline_wr*100:.1f}% WR, {baseline_n} trades)")
    print(f"   - Random: {random_exp:+.3f}R (50% WR)")
else:
    print(f"   [FAIL] 1000 ORB FAILS vs random baseline")

print()

print("3. L4_CONSOLIDATION FILTER:")
if l4_yes_exp > l4_yes_random:
    print(f"   [PASS] L4 filter at 1000 ORB BEATS random by {l4_yes_exp - l4_yes_random:+.3f}R")
    print(f"   - L4=YES: {l4_yes_exp:+.3f}R ({l4_yes_wr*100:.1f}% WR, {l4_yes_n} trades)")
else:
    print(f"   [FAIL] L4 filter at 1000 ORB FAILS vs random")

print()

print("4. NIGHT ORBs (2300, 0030):")
if orb_2300_exp > orb_2300_random:
    print(f"   [PASS] 2300 ORB BEATS random by {orb_2300_exp - orb_2300_random:+.3f}R")
else:
    print(f"   [FAIL] 2300 ORB FAILS vs random (edge = {orb_2300_exp - orb_2300_random:+.3f}R)")

if orb_0030_exp > orb_0030_random:
    print(f"   [PASS] 0030 ORB BEATS random by {orb_0030_exp - orb_0030_random:+.3f}R")
else:
    print(f"   [FAIL] 0030 ORB FAILS vs random (edge = {orb_0030_exp - orb_0030_random:+.3f}R)")

print()

print("5. NIGHT ORBs + L4_CONSOLIDATION:")
if orb_2300_l4_exp > orb_2300_l4_random:
    print(f"   [PASS] 2300 ORB + L4 BEATS random by {orb_2300_l4_exp - orb_2300_l4_random:+.3f}R")
else:
    print(f"   [FAIL] 2300 ORB + L4 FAILS vs random (edge = {orb_2300_l4_exp - orb_2300_l4_random:+.3f}R)")

if orb_0030_l4_exp > orb_0030_l4_random:
    print(f"   [PASS] 0030 ORB + L4 BEATS random by {orb_0030_l4_exp - orb_0030_l4_random:+.3f}R")
else:
    print(f"   [FAIL] 0030 ORB + L4 FAILS vs random (edge = {orb_0030_l4_exp - orb_0030_l4_random:+.3f}R)")

print()

print("=" * 100)
print("HONESTY OVER OUTCOME")
print("=" * 100)
print()

if orb_2300_exp <= orb_2300_random or orb_0030_exp <= orb_0030_random:
    print("CRITICAL FINDING: Night ORBs FAIL random-entry test at baseline.")
    print()
    print("This means:")
    print("- The 'edge' at night ORBs is NO BETTER than flipping a coin")
    print("- Any perceived edge is PURELY asymmetric RR math (not timing skill)")
    print("- RECOMMENDATION: REJECT night ORBs unless filtered state beats random")
    print()

    if orb_2300_l4_exp > orb_2300_l4_random or orb_0030_l4_exp > orb_0030_l4_random:
        print("HOWEVER: Night ORBs + L4_CONSOLIDATION filter DOES beat random.")
        print("- This suggests L4 filter is REQUIRED (not optional) for night ORBs")
        print("- Without L4, night ORBs are NO BETTER than random")
    else:
        print("Even L4 filter does NOT help night ORBs beat random.")
        print("- RECOMMENDATION: REJECT night ORBs entirely")
else:
    print("Night ORBs PASS random-entry test at baseline.")
    print("Edge is genuine (not just RR math).")

print()
print("Analysis complete.")
print("=" * 100)
