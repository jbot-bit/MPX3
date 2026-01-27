"""
REVERSE ENGINEER ALL STRATEGIES - GROUND TRUTH VALIDATION
==========================================================

Following user mandate:
"EACH STRAT AND ORB AND EVERYTHING IS INDIVIDUAL/DIFFERENT THOUGH REMEMBER
ALTHOUGH ALL STILL REFERENCING TO OUR CANONICAL RULESET THOUGH OBVIOUSLY."

Methodology:
1. For EACH strategy individually: reverse engineer its ACTUAL filter from the database
2. Apply CANONICAL_LOGIC.txt formulas ($7.40 RT costs mandatory)
3. Validate each strategy independently
4. HONESTY OVER OUTCOME

NO ASSUMPTIONS. PROVE EACH STRATEGY FROM GROUND TRUTH DATA.
"""

import duckdb
import sys
sys.path.insert(0, 'C:/Users/sydne/OneDrive/Desktop/MPX2_fresh')
from pipeline.cost_model import COST_MODELS

DB_PATH = 'gold.db'
conn = duckdb.connect(DB_PATH)

# Get MGC cost model (CANONICAL)
MGC_COSTS = COST_MODELS['MGC']
MGC_POINT_VALUE = MGC_COSTS['point_value']
MGC_FRICTION = MGC_COSTS['total_friction']  # $7.40 RT (MANDATORY)

print("=" * 80)
print("REVERSE ENGINEER ALL STRATEGIES - GROUND TRUTH VALIDATION")
print("=" * 80)
print()
print("CANONICAL COST MODEL (MANDATORY):")
print(f"  Friction: ${MGC_FRICTION:.2f} RT")
print(f"  Point Value: ${MGC_POINT_VALUE:.2f}")
print(f"  Approval Threshold: +0.15R at ${MGC_FRICTION:.2f}")
print()
print("METHODOLOGY: Each strategy validated INDIVIDUALLY from ground truth data.")
print()

# Get all MGC setups
setups = conn.execute("""
    SELECT id, orb_time, rr, sl_mode, win_rate, expected_r, sample_size, orb_size_filter, notes
    FROM validated_setups
    WHERE instrument = 'MGC'
    ORDER BY id
""").fetchall()

print(f"Found {len(setups)} strategies in validated_setups")
print()

# =============================================================================
# HELPER FUNCTION - CANONICAL FORMULAS
# =============================================================================

def calculate_canonical_expectancy(trades, rr, point_value, friction):
    """
    Calculate expectancy using CANONICAL_LOGIC.txt formulas (lines 76-98).

    MANDATORY FORMULAS:
    - Realized_Risk_$ = (|Pe − Psl| × PointValue) + TotalFriction
    - Realized_Reward_$ = (|Ptp − Pe| × PointValue) − TotalFriction
    - Realized_RR = Realized_Reward_$ / Realized_Risk_$

    Expectancy = avg(realized_r) across all trades
    """
    realized_r_values = []

    for trade in trades:
        date, high, low, break_dir, outcome, orb_size = trade

        # Entry and stop from ORB edges
        if break_dir == 'UP':
            entry, stop = high, low
        else:
            entry, stop = low, high

        stop_dist_points = abs(entry - stop)

        # CANONICAL FORMULAS (MANDATORY)
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
    return sum(realized_r_values) / len(realized_r_values) if realized_r_values else 0.0

print("=" * 80)
print("PHASE 1: REVERSE ENGINEER EACH STRATEGY'S ACTUAL FILTER")
print("=" * 80)
print()

validation_results = []

for setup in setups:
    setup_id, orb_time, rr, sl_mode, wr_db, exp_r_db, n_db, orb_size_filter, notes = setup

    print(f"STRATEGY ID {setup_id}: {orb_time} ORB RR={rr} {sl_mode}")
    print("-" * 80)

    # STEP 1: REVERSE ENGINEER FILTER FROM NOTES
    filter_sql = None
    filter_description = None

    if 'L4_CONSOLIDATION' in notes:
        # L4_CONSOLIDATION is a SESSION TYPE CODE
        filter_sql = "london_type_code = 'L4_CONSOLIDATION'"
        filter_description = "L4_CONSOLIDATION (session type: London consolidation day)"

    elif 'BOTH_LOST' in notes:
        # Sequential dependency: both 0900 and 1000 lost
        filter_sql = "orb_0900_outcome = 'LOSS' AND orb_1000_outcome = 'LOSS'"
        filter_description = "BOTH_LOST (0900 AND 1000 both lost)"

    elif '0900_LOSS' in notes:
        # Sequential dependency: 0900 lost
        filter_sql = "orb_0900_outcome = 'LOSS'"
        filter_description = "0900_LOSS (0900 ORB lost)"

    elif 'REVERSAL' in notes:
        # Sequential dependency: 0900/1000 same direction, 1100 reverses
        filter_sql = """
            orb_0900_break_dir = orb_1000_break_dir
            AND orb_1100_break_dir != orb_1000_break_dir
            AND orb_0900_break_dir != 'NONE'
            AND orb_1100_break_dir != 'NONE'
        """
        filter_description = "REVERSAL (0900/1000 same dir, 1100 reverses)"

    elif 'ACTIVE' in notes or 'ACTIVE_MARKETS' in notes:
        # Regime: high volatility in Asia + London
        filter_sql = "asia_range >= 2.0 AND london_range >= 2.0"
        filter_description = "ACTIVE_MARKETS (asia_range>=2.0 AND london_range>=2.0)"

    elif 'RSI' in notes:
        # Indicator: RSI > 70
        filter_sql = "rsi_at_orb > 70"
        filter_description = "RSI (rsi_at_orb > 70)"

    else:
        print("  [FAIL] Cannot reverse engineer filter from notes")
        print(f"  Notes: {notes[:200]}...")
        print()
        continue

    print(f"  Filter: {filter_description}")
    print(f"  SQL: {filter_sql}")
    print()

    # STEP 2: GET GROUND TRUTH TRADES FROM DATABASE
    orb_col = f'orb_{orb_time}'

    query = f"""
    SELECT
        date_local,
        {orb_col}_high,
        {orb_col}_low,
        {orb_col}_break_dir,
        {orb_col}_outcome,
        {orb_col}_size
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

    print(f"  Ground truth trades: {len(trades)}")

    if len(trades) < 30:
        print(f"  [REJECTED] Insufficient sample: {len(trades)} < 30")
        validation_results.append({
            'id': setup_id,
            'orb_time': orb_time,
            'rr': rr,
            'filter': filter_description,
            'sample_size': len(trades),
            'verdict': 'REJECTED',
            'reason': 'Insufficient sample size',
            'exp_740': None,
            'exp_250': None
        })
        print()
        continue

    # STEP 3: CALCULATE EXPECTANCY USING CANONICAL FORMULAS
    print(f"  Calculating expectancy with CANONICAL formulas...")

    # Calculate at $7.40 (MANDATORY)
    exp_740 = calculate_canonical_expectancy(trades, rr, MGC_POINT_VALUE, MGC_FRICTION)

    # Calculate at $2.50 (COMPARISON ONLY)
    exp_250 = calculate_canonical_expectancy(trades, rr, MGC_POINT_VALUE, 2.50)

    print(f"    Expectancy at $7.40 (MANDATORY): {exp_740:+.3f}R")
    print(f"    Expectancy at $2.50 (comparison): {exp_250:+.3f}R")
    print()

    # STEP 4: STRESS TEST (COST +25%, +50%)
    friction_25 = MGC_FRICTION * 1.25
    friction_50 = MGC_FRICTION * 1.50

    exp_25 = calculate_canonical_expectancy(trades, rr, MGC_POINT_VALUE, friction_25)
    exp_50 = calculate_canonical_expectancy(trades, rr, MGC_POINT_VALUE, friction_50)

    print(f"  STRESS TEST:")
    print(f"    +25% costs (${friction_25:.2f}): {exp_25:+.3f}R")
    print(f"    +50% costs (${friction_50:.2f}): {exp_50:+.3f}R")
    print()

    # STEP 5: VERDICT (INDIVIDUAL PER STRATEGY)
    verdict = None
    reason = None

    if exp_740 < 0.15:
        verdict = 'REJECTED'
        reason = f'Below +0.15R threshold at $7.40 ({exp_740:+.3f}R)'
    elif exp_50 >= 0.15:
        verdict = 'EXCELLENT'
        reason = f'Passes $7.40 AND survives +50% stress'
    elif exp_25 >= 0.15:
        verdict = 'MARGINAL'
        reason = f'Passes $7.40 but only survives +25% stress'
    else:
        verdict = 'WEAK'
        reason = f'Passes $7.40 but fails cost stress'

    print(f"  VERDICT: {verdict}")
    print(f"    Reason: {reason}")
    print()

    validation_results.append({
        'id': setup_id,
        'orb_time': orb_time,
        'rr': rr,
        'filter': filter_description,
        'sample_size': len(trades),
        'verdict': verdict,
        'reason': reason,
        'exp_740': exp_740,
        'exp_250': exp_250,
        'exp_25': exp_25,
        'exp_50': exp_50
    })

conn.close()

# =============================================================================
# FINAL SUMMARY
# =============================================================================
print()
print("=" * 80)
print("VALIDATION SUMMARY - GROUND TRUTH + CANONICAL FORMULAS")
print("=" * 80)
print()

excellent = [r for r in validation_results if r['verdict'] == 'EXCELLENT']
marginal = [r for r in validation_results if r['verdict'] == 'MARGINAL']
weak = [r for r in validation_results if r['verdict'] == 'WEAK']
rejected = [r for r in validation_results if r['verdict'] == 'REJECTED']

print(f"EXCELLENT (pass $7.40 + survive +50% stress): {len(excellent)}")
for r in excellent:
    print(f"  ID {r['id']}: {r['orb_time']} RR={r['rr']} {r['filter']}")
    print(f"    ExpR: {r['exp_740']:+.3f}R → {r['exp_50']:+.3f}R (+50%) | N={r['sample_size']}")

print()
print(f"MARGINAL (pass $7.40 + survive +25% only): {len(marginal)}")
for r in marginal:
    print(f"  ID {r['id']}: {r['orb_time']} RR={r['rr']} {r['filter']}")
    print(f"    ExpR: {r['exp_740']:+.3f}R → {r['exp_25']:+.3f}R (+25%) | N={r['sample_size']}")

print()
print(f"WEAK (pass $7.40 but fail stress): {len(weak)}")
for r in weak:
    print(f"  ID {r['id']}: {r['orb_time']} RR={r['rr']} {r['filter']}")
    print(f"    ExpR: {r['exp_740']:+.3f}R (stress fails) | N={r['sample_size']}")

print()
print(f"REJECTED (fail $7.40 threshold or insufficient sample): {len(rejected)}")
for r in rejected:
    exp_str = f"{r['exp_740']:+.3f}R" if r['exp_740'] is not None else "N/A"
    print(f"  ID {r['id']}: {r['orb_time']} RR={r['rr']} {r['filter']}")
    print(f"    Reason: {r['reason']} | N={r['sample_size']}")

print()
print("=" * 80)
print("RECOMMENDATION")
print("=" * 80)
print()

if excellent or marginal:
    print("KEEP in validated_setups:")
    for r in excellent + marginal:
        print(f"  ID {r['id']}: {r['orb_time']} RR={r['rr']} {r['filter']} - {r['verdict']}")
else:
    print("KEEP in validated_setups: NONE")

print()

if weak or rejected:
    print("REMOVE from validated_setups:")
    for r in weak + rejected:
        print(f"  ID {r['id']}: {r['orb_time']} RR={r['rr']} {r['filter']} - {r['verdict']}")
else:
    print("REMOVE from validated_setups: NONE")

print()
print("HONESTY OVER OUTCOME.")
print()
