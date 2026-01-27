"""
CORRECT VALIDATION - $7.40 RT COSTS (Mandatory)
================================================

Following user mandate:
"All strategies must pass validation at $7.40 RT to be tradable.
Lower costs may be reported for comparison only, never for approval."

Following audit.txt + CANONICAL_LOGIC.txt + COST_MODEL_MGC_TRADOVATE.txt:
- Use CORRECT regime variables (london_range for L4_CONSOLIDATION)
- Skip temporal tests (irrelevant for regime strategies)
- Use $7.40 friction (Tradovate production)
- Costs INCREASE risk, REDUCE reward (canonical formulas)

Test Framework:
1. Regime split (CORRECT variable)
2. Cost stress (+25%, +50% friction)
3. Sample size validation (min 30 trades)

Approval Threshold: +0.15R at $7.40 costs
"""

import duckdb
import sys
sys.path.insert(0, 'C:/Users/sydne/OneDrive/Desktop/MPX2_fresh')
from pipeline.cost_model import COST_MODELS

DB_PATH = 'gold.db'
conn = duckdb.connect(DB_PATH)

# Get MGC cost model
MGC_COSTS = COST_MODELS['MGC']
MGC_POINT_VALUE = MGC_COSTS['point_value']
MGC_FRICTION = MGC_COSTS['total_friction']  # $7.40

print("=" * 80)
print("CORRECT VALIDATION - $7.40 RT COSTS (Mandatory)")
print("=" * 80)
print()
print(f"Cost Model: ${MGC_FRICTION:.2f} RT (Tradovate production)")
print(f"Point Value: ${MGC_POINT_VALUE:.2f}")
print(f"Approval Threshold: +0.15R at ${MGC_FRICTION:.2f} costs")
print()

# Get all MGC setups
setups = conn.execute("""
    SELECT id, orb_time, rr, sl_mode, win_rate, expected_r, sample_size, notes
    FROM validated_setups
    WHERE instrument = 'MGC'
    ORDER BY id
""").fetchall()

print(f"Testing {len(setups)} MGC strategies...")
print()

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_expectancy_740(trades, rr, point_value, friction):
    """
    Calculate expectancy using CANONICAL_LOGIC.txt formulas.

    Realized Risk = (stop_distance × point_value) + friction
    Realized Reward = (target_distance × point_value) - friction

    For wins: net_pnl = realized_reward
    For losses: net_pnl = -realized_risk

    Expectancy = avg(net_pnl / realized_risk)
    """
    realized_r_values = []

    for trade in trades:
        date, high, low, break_dir, outcome, orb_size, london_range, asia_range = trade

        # Calculate stop distance
        if break_dir == 'UP':
            entry, stop = high, low
        else:
            entry, stop = low, high

        stop_dist_points = abs(entry - stop)

        # Canonical formulas
        realized_risk_dollars = (stop_dist_points * point_value) + friction
        target_dist_points = stop_dist_points * rr
        realized_reward_dollars = (target_dist_points * point_value) - friction

        # Net P&L
        if outcome == 'WIN':
            net_pnl = realized_reward_dollars
        else:
            net_pnl = -realized_risk_dollars

        # Realized R
        realized_r = net_pnl / realized_risk_dollars
        realized_r_values.append(realized_r)

    # Expectancy = average realized R
    if not realized_r_values:
        return 0.0

    return sum(realized_r_values) / len(realized_r_values)

# =============================================================================
# VALIDATE EACH STRATEGY WITH CORRECT TESTS
# =============================================================================

validation_results = {}

for setup in setups:
    setup_id, orb_time, rr, sl_mode, wr_db, exp_r_db, n_db, notes = setup

    # Extract filter type
    if 'L4_CONSOLIDATION' in notes:
        filter_type = 'L4_CONSOLIDATION'
        regime_var = 'london_range'
        regime_threshold = 2.0
    elif 'BOTH_LOST' in notes:
        filter_type = 'BOTH_LOST'
        regime_var = None  # Sequential dependency, no regime split
        regime_threshold = None
    elif '0900_LOSS' in notes:
        filter_type = '0900_LOSS'
        regime_var = None
        regime_threshold = None
    elif 'REVERSAL' in notes:
        filter_type = 'REVERSAL'
        regime_var = None
        regime_threshold = None
    elif 'ACTIVE' in notes:
        filter_type = 'ACTIVE_MARKETS'
        regime_var = None
        regime_threshold = None
    elif 'RSI' in notes:
        filter_type = 'RSI'
        regime_var = None
        regime_threshold = None
    else:
        filter_type = 'UNKNOWN'
        regime_var = None
        regime_threshold = None

    print(f"ID {setup_id}: {orb_time} RR={rr} {filter_type}")
    print("-" * 80)

    result = {
        'id': setup_id,
        'orb_time': orb_time,
        'rr': rr,
        'filter_type': filter_type,
        'regime_var': regime_var,
        'tests_passed': [],
        'tests_failed': [],
        'expectancy_740': None,
        'expectancy_250': None,
        'sample_size': None,
        'verdict': None
    }

    # Build query for this strategy
    if filter_type == 'L4_CONSOLIDATION':
        filter_sql = "london_range < 2.0"
    elif filter_type == 'BOTH_LOST':
        filter_sql = "orb_0900_outcome = 'LOSS' AND orb_1000_outcome = 'LOSS'"
    elif filter_type == '0900_LOSS':
        filter_sql = "orb_0900_outcome = 'LOSS'"
    elif filter_type == 'REVERSAL':
        filter_sql = """
            orb_0900_break_dir = orb_1000_break_dir
            AND orb_1100_break_dir != orb_1000_break_dir
            AND orb_0900_break_dir != 'NONE'
            AND orb_1100_break_dir != 'NONE'
        """
    elif filter_type == 'ACTIVE_MARKETS':
        filter_sql = "asia_range >= 2.0 AND london_range >= 2.0"
    elif filter_type == 'RSI':
        filter_sql = "rsi_at_orb > 70"
    else:
        print("  [SKIP] Unknown filter type")
        print()
        continue

    # Get trades for this strategy
    orb_col = f'orb_{orb_time}'
    query = f"""
    SELECT
        date_local,
        {orb_col}_high,
        {orb_col}_low,
        {orb_col}_break_dir,
        {orb_col}_outcome,
        {orb_col}_size,
        london_range,
        asia_range
    FROM daily_features
    WHERE instrument = 'MGC'
      AND {orb_col}_outcome IS NOT NULL
      AND {orb_col}_break_dir != 'NONE'
      AND ({filter_sql})
    ORDER BY date_local
    """

    try:
        trades = conn.execute(query).fetchall()
    except Exception as e:
        print(f"  [FAIL] Query error: {e}")
        print()
        continue

    if len(trades) < 30:
        print(f"  [FAIL] Insufficient trades: {len(trades)} < 30")
        result['tests_failed'].append(f"Sample size: {len(trades)} < 30")
        result['verdict'] = 'REJECTED'
        validation_results[setup_id] = result
        print()
        continue

    result['sample_size'] = len(trades)
    result['tests_passed'].append(f"Sample size: {len(trades)} >= 30")

    # =========================================================================
    # TEST 1: REGIME SPLIT (CORRECT VARIABLE)
    # =========================================================================
    if regime_var and filter_type == 'L4_CONSOLIDATION':
        print(f"  TEST 1: Regime split (CORRECT variable: {regime_var})")

        # Split by london_range (CORRECT for L4_CONSOLIDATION)
        # Strategy already filters london_range < 2.0, so check subsets
        low_london = [t for t in trades if t[6] < 1.0]  # Very low london volatility
        high_london = [t for t in trades if t[6] >= 1.0 and t[6] < 2.0]  # Moderate (still < 2.0)

        print(f"    Low london (<1.0): {len(low_london)} trades")
        print(f"    Moderate london (1.0-2.0): {len(high_london)} trades")

        # Calculate expectancy for each regime at $7.40 costs
        for regime_name, regime_trades in [('low_london', low_london), ('high_london', high_london)]:
            if len(regime_trades) < 10:
                print(f"      {regime_name}: SKIP (N={len(regime_trades)} < 10)")
                continue

            regime_exp = calculate_expectancy_740(regime_trades, rr, MGC_POINT_VALUE, MGC_FRICTION)
            print(f"      {regime_name}: {regime_exp:+.3f}R (N={len(regime_trades)})")

            if regime_exp < 0.15:
                result['tests_failed'].append(f"Regime {regime_name}: {regime_exp:+.3f}R < 0.15R")
            else:
                result['tests_passed'].append(f"Regime {regime_name}: {regime_exp:+.3f}R >= 0.15R")

    elif regime_var:
        print(f"  TEST 1: Regime split (SKIPPED - {filter_type} has no regime dependency)")
        result['tests_passed'].append("Regime split: N/A (no regime dependency)")
    else:
        print(f"  TEST 1: Regime split (SKIPPED - sequential/indicator strategy)")
        result['tests_passed'].append("Regime split: N/A (sequential/indicator strategy)")

    # =========================================================================
    # TEST 2: CALCULATE EXPECTANCY AT $7.40 (MANDATORY)
    # =========================================================================
    print(f"  TEST 2: Expectancy at $7.40 costs (MANDATORY)")

    expectancy_740 = calculate_expectancy_740(trades, rr, MGC_POINT_VALUE, MGC_FRICTION)
    result['expectancy_740'] = expectancy_740

    print(f"    Expectancy at $7.40: {expectancy_740:+.3f}R (N={len(trades)})")

    if expectancy_740 >= 0.15:
        result['tests_passed'].append(f"Expectancy $7.40: {expectancy_740:+.3f}R >= 0.15R")
    else:
        result['tests_failed'].append(f"Expectancy $7.40: {expectancy_740:+.3f}R < 0.15R")

    # =========================================================================
    # TEST 3: COST STRESS (+25%, +50%)
    # =========================================================================
    print(f"  TEST 3: Cost stress (+25%, +50%)")

    # +25% costs
    friction_25 = MGC_FRICTION * 1.25
    expectancy_25 = calculate_expectancy_740(trades, rr, MGC_POINT_VALUE, friction_25)
    print(f"    +25% costs (${friction_25:.2f}): {expectancy_25:+.3f}R")

    if expectancy_25 >= 0.15:
        result['tests_passed'].append(f"Cost +25%: {expectancy_25:+.3f}R >= 0.15R")
    else:
        result['tests_failed'].append(f"Cost +25%: {expectancy_25:+.3f}R < 0.15R")

    # +50% costs
    friction_50 = MGC_FRICTION * 1.50
    expectancy_50 = calculate_expectancy_740(trades, rr, MGC_POINT_VALUE, friction_50)
    print(f"    +50% costs (${friction_50:.2f}): {expectancy_50:+.3f}R")

    if expectancy_50 >= 0.15:
        result['tests_passed'].append(f"Cost +50%: {expectancy_50:+.3f}R >= 0.15R")
    else:
        result['tests_failed'].append(f"Cost +50%: {expectancy_50:+.3f}R < 0.15R")

    # =========================================================================
    # COMPARISON: $2.50 costs (COMPARISON ONLY)
    # =========================================================================
    print(f"  COMPARISON: $2.50 costs (comparison only, NOT for approval)")

    expectancy_250 = calculate_expectancy_740(trades, rr, MGC_POINT_VALUE, 2.50)
    result['expectancy_250'] = expectancy_250
    print(f"    Expectancy at $2.50: {expectancy_250:+.3f}R (comparison only)")

    # =========================================================================
    # VERDICT
    # =========================================================================
    print()
    print("  VERDICT:")

    # Must pass ALL tests at $7.40 costs
    critical_failures = [f for f in result['tests_failed'] if '$7.40' in f or 'Cost +' in f or 'Regime' in f]

    if critical_failures:
        result['verdict'] = 'REJECTED'
        print(f"    [REJECTED] Failed critical tests at $7.40 costs")
        for failure in critical_failures:
            print(f"      - {failure}")
    elif result['expectancy_740'] >= 0.15:
        if expectancy_50 >= 0.15:
            result['verdict'] = 'EXCELLENT'
            print(f"    [EXCELLENT] Passes $7.40 + survives +50% cost stress")
        elif expectancy_25 >= 0.15:
            result['verdict'] = 'MARGINAL'
            print(f"    [MARGINAL] Passes $7.40 + survives +25% cost stress only")
        else:
            result['verdict'] = 'WEAK'
            print(f"    [WEAK] Passes $7.40 but fails cost stress")
    else:
        result['verdict'] = 'REJECTED'
        print(f"    [REJECTED] Below +0.15R threshold at $7.40")

    print()
    validation_results[setup_id] = result

conn.close()

# =============================================================================
# SUMMARY
# =============================================================================
print()
print("=" * 80)
print("VALIDATION SUMMARY - $7.40 RT COSTS (Mandatory)")
print("=" * 80)
print()

excellent = [r for r in validation_results.values() if r['verdict'] == 'EXCELLENT']
marginal = [r for r in validation_results.values() if r['verdict'] == 'MARGINAL']
weak = [r for r in validation_results.values() if r['verdict'] == 'WEAK']
rejected = [r for r in validation_results.values() if r['verdict'] == 'REJECTED']

print(f"EXCELLENT (pass $7.40 + survive +50% stress): {len(excellent)}")
for r in excellent:
    print(f"  ID {r['id']}: {r['orb_time']} RR={r['rr']} {r['filter_type']} - {r['expectancy_740']:+.3f}R (N={r['sample_size']})")

print()
print(f"MARGINAL (pass $7.40 + survive +25% stress only): {len(marginal)}")
for r in marginal:
    print(f"  ID {r['id']}: {r['orb_time']} RR={r['rr']} {r['filter_type']} - {r['expectancy_740']:+.3f}R (N={r['sample_size']})")

print()
print(f"WEAK (pass $7.40 but fail cost stress): {len(weak)}")
for r in weak:
    print(f"  ID {r['id']}: {r['orb_time']} RR={r['rr']} {r['filter_type']} - {r['expectancy_740']:+.3f}R (N={r['sample_size']})")

print()
print(f"REJECTED (fail $7.40 threshold): {len(rejected)}")
for r in rejected:
    exp = r['expectancy_740'] if r['expectancy_740'] is not None else 'N/A'
    n = r['sample_size'] if r['sample_size'] is not None else 'N/A'
    print(f"  ID {r['id']}: {r['orb_time']} RR={r['rr']} {r['filter_type']} - {exp}R (N={n})")

print()
print("=" * 80)
print("RECOMMENDATION")
print("=" * 80)
print()
print("KEEP in validated_setups:")
for r in excellent + marginal:
    print(f"  ID {r['id']}: {r['orb_time']} RR={r['rr']} {r['filter_type']} - {r['verdict']}")

print()
print("REMOVE from validated_setups:")
for r in weak + rejected:
    print(f"  ID {r['id']}: {r['orb_time']} RR={r['rr']} {r['filter_type']} - {r['verdict']}")

print()
print("NEXT STEP: Update database and config.py, then run test_app_sync.py")
