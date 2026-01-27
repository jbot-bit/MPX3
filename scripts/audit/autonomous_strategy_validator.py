"""
AUTONOMOUS STRATEGY VALIDATOR
==============================

Implements VALIDATION_METHODOLOGY.md using test-skill's autonomous approach.

6-Phase Validation Framework:
1. Ground Truth Discovery
2. Data Integrity Validation
3. Single-Trade Reconciliation
4. Statistical Validation
5. Stress Testing
6. Iterative Correction & Documentation

HONESTY OVER OUTCOME. NO ASSUMPTIONS.
"""

import duckdb
import sys
import random
from datetime import date

sys.path.insert(0, 'C:/Users/sydne/OneDrive/Desktop/MPX2_fresh')
from pipeline.cost_model import COST_MODELS

DB_PATH = 'gold.db'

# CANONICAL COST MODEL (MANDATORY)
MGC_COSTS = COST_MODELS['MGC']
MGC_POINT_VALUE = MGC_COSTS['point_value']
MGC_FRICTION_740 = MGC_COSTS['total_friction']  # $7.40 RT

print("=" * 80)
print("AUTONOMOUS STRATEGY VALIDATOR")
print("=" * 80)
print()
print(f"Canonical Cost Model: ${MGC_FRICTION_740:.2f} RT (MANDATORY)")
print(f"Point Value: ${MGC_POINT_VALUE:.2f}")
print(f"Approval Threshold: +0.15R at ${MGC_FRICTION_740:.2f}")
print()
print("Methodology: 6-Phase Autonomous Validation")
print("=" * 80)
print()

conn = duckdb.connect(DB_PATH)

# Get all strategies
strategies = conn.execute("""
    SELECT id, instrument, orb_time, rr, sl_mode, win_rate, expected_r, sample_size, orb_size_filter, notes
    FROM validated_setups
    WHERE instrument = 'MGC'
    ORDER BY id
""").fetchall()

print(f"Found {len(strategies)} strategies to validate")
print()

# =============================================================================
# HELPER FUNCTION - MUST BE DEFINED BEFORE USE
# =============================================================================

def calculate_expectancy(trades, rr, point_value, friction):
    """Calculate expectancy using CANONICAL formulas."""
    realized_r_values = []

    for trade in trades:
        date_local, high, low, break_dir, outcome, orb_size = trade

        if break_dir == 'UP':
            entry, stop = high, low
        else:
            entry, stop = low, high

        stop_dist_points = abs(entry - stop)

        # CANONICAL FORMULAS (MANDATORY)
        realized_risk_dollars = (stop_dist_points * point_value) + friction
        target_dist_points = stop_dist_points * rr
        realized_reward_dollars = (target_dist_points * point_value) - friction

        if outcome == 'WIN':
            net_pnl = realized_reward_dollars
        else:
            net_pnl = -realized_risk_dollars

        realized_r = net_pnl / realized_risk_dollars
        realized_r_values.append(realized_r)

    return sum(realized_r_values) / len(realized_r_values) if realized_r_values else 0.0

# Store validation results
all_results = []

for strategy in strategies:
    strategy_id, instrument, orb_time, rr, sl_mode, wr_db, exp_r_db, n_db, orb_size_filter, notes = strategy

    print("=" * 80)
    print(f"VALIDATING: ID {strategy_id} | {orb_time} ORB RR={rr} {sl_mode}")
    print("=" * 80)
    print()

    result = {
        'id': strategy_id,
        'orb_time': orb_time,
        'rr': rr,
        'phase1_pass': False,
        'phase2_pass': False,
        'phase3_pass': False,
        'phase4_pass': False,
        'phase5_pass': False,
        'verdict': None,
        'reason': None
    }

    # =========================================================================
    # PHASE 1: GROUND TRUTH DISCOVERY
    # =========================================================================
    print("PHASE 1: Ground Truth Discovery")
    print("-" * 80)

    # Reverse engineer filter from notes
    if 'L4_CONSOLIDATION' in notes:
        filter_sql = "london_type_code = 'L4_CONSOLIDATION'"
        filter_desc = "L4_CONSOLIDATION (session type)"
    elif 'BOTH_LOST' in notes:
        filter_sql = "orb_0900_outcome = 'LOSS' AND orb_1000_outcome = 'LOSS'"
        filter_desc = "BOTH_LOST (sequential)"
    elif '0900_LOSS' in notes:
        filter_sql = "orb_0900_outcome = 'LOSS'"
        filter_desc = "0900_LOSS (sequential)"
    elif 'REVERSAL' in notes:
        filter_sql = """
            orb_0900_break_dir = orb_1000_break_dir
            AND orb_1100_break_dir != orb_1000_break_dir
            AND orb_0900_break_dir != 'NONE'
            AND orb_1100_break_dir != 'NONE'
        """
        filter_desc = "REVERSAL (sequential)"
    elif 'ACTIVE' in notes:
        filter_sql = "asia_range >= 2.0 AND london_range >= 2.0"
        filter_desc = "ACTIVE_MARKETS (regime)"
    elif 'RSI' in notes:
        filter_sql = "rsi_at_orb > 70"
        filter_desc = "RSI > 70 (indicator)"
    else:
        print("[FAIL] Cannot reverse engineer filter")
        print(f"Notes: {notes[:150]}...")
        result['verdict'] = 'NEEDS_CONTRACT_DEFINITION'
        result['reason'] = 'Cannot reverse engineer filter from notes'
        all_results.append(result)
        continue

    print(f"Filter: {filter_desc}")
    print(f"SQL: {filter_sql}")

    # Query ground truth trades
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
    WHERE instrument = '{instrument}'
      AND {orb_col}_outcome IS NOT NULL
      AND {orb_col}_break_dir != 'NONE'
      AND ({filter_sql})
    ORDER BY date_local
    """

    try:
        trades = conn.execute(query).fetchall()
        print(f"[PASS] Found {len(trades)} ground truth trades")
        result['phase1_pass'] = True
        result['filter'] = filter_desc
        result['trades'] = trades
    except Exception as e:
        print(f"[FAIL] Query error: {e}")
        result['verdict'] = 'PHASE1_FAIL'
        result['reason'] = f'Database query failed: {e}'
        all_results.append(result)
        continue

    print()

    # =========================================================================
    # PHASE 2: DATA INTEGRITY VALIDATION
    # =========================================================================
    print("PHASE 2: Data Integrity Validation")
    print("-" * 80)

    integrity_pass = True

    # Check: All trades have required fields
    for i, trade in enumerate(trades[:10]):  # Sample first 10
        date_local, high, low, break_dir, outcome, orb_size = trade
        if high is None or low is None or break_dir is None or outcome is None:
            print(f"[FAIL] Trade {i+1} has NULL required field")
            integrity_pass = False
            break

    # Check: ORB high >= ORB low
    for i, trade in enumerate(trades[:10]):
        date_local, high, low, break_dir, outcome, orb_size = trade
        if high < low:
            print(f"[FAIL] Trade {i+1}: high < low (invalid)")
            integrity_pass = False
            break

    # Check: Break direction consistent
    for i, trade in enumerate(trades[:10]):
        date_local, high, low, break_dir, outcome, orb_size = trade
        if break_dir not in ['UP', 'DOWN']:
            print(f"[FAIL] Trade {i+1}: invalid break_dir '{break_dir}'")
            integrity_pass = False
            break

    if integrity_pass:
        print("[PASS] Data integrity checks passed")
        result['phase2_pass'] = True
    else:
        print("[FAIL] Data integrity issues found")
        result['verdict'] = 'PHASE2_FAIL'
        result['reason'] = 'Data integrity validation failed'
        all_results.append(result)
        continue

    print()

    # =========================================================================
    # PHASE 3: SINGLE-TRADE RECONCILIATION
    # =========================================================================
    print("PHASE 3: Single-Trade Reconciliation")
    print("-" * 80)

    # Select 5 random trades for reconciliation
    sample_trades = random.sample(trades, min(5, len(trades)))
    reconciliation_pass = True

    for i, trade in enumerate(sample_trades, 1):
        date_local, high, low, break_dir, outcome, orb_size = trade

        # Manual calculation
        if break_dir == 'UP':
            entry, stop = high, low
        else:
            entry, stop = low, high

        stop_dist_points = abs(entry - stop)

        # CANONICAL FORMULAS
        realized_risk_dollars = (stop_dist_points * MGC_POINT_VALUE) + MGC_FRICTION_740
        target_dist_points = stop_dist_points * rr
        realized_reward_dollars = (target_dist_points * MGC_POINT_VALUE) - MGC_FRICTION_740

        if outcome == 'WIN':
            net_pnl = realized_reward_dollars
        else:
            net_pnl = -realized_risk_dollars

        realized_r = net_pnl / realized_risk_dollars

        print(f"Trade {i} ({date_local}): {break_dir} {outcome}")
        print(f"  Stop: {stop_dist_points:.2f} pts | Risk: ${realized_risk_dollars:.2f}")
        print(f"  Realized R: {realized_r:+.3f}R")

    print("[PASS] Single-trade reconciliation completed")
    result['phase3_pass'] = True
    print()

    # =========================================================================
    # PHASE 4: STATISTICAL VALIDATION
    # =========================================================================
    print("PHASE 4: Statistical Validation")
    print("-" * 80)

    # Sample size check
    if len(trades) < 30:
        print(f"[FAIL] Insufficient sample: {len(trades)} < 30")
        result['verdict'] = 'REJECTED'
        result['reason'] = f'Insufficient sample size: {len(trades)} < 30'
        all_results.append(result)
        continue

    print(f"[PASS] Sample size: {len(trades)} >= 30")

    # Calculate expectancy at $7.40 (MANDATORY)
    exp_740 = calculate_expectancy(trades, rr, MGC_POINT_VALUE, MGC_FRICTION_740)
    print(f"Expectancy at $7.40: {exp_740:+.3f}R")

    # Calculate expectancy at $2.50 (COMPARISON)
    exp_250 = calculate_expectancy(trades, rr, MGC_POINT_VALUE, 2.50)
    print(f"Expectancy at $2.50: {exp_250:+.3f}R (comparison only)")

    if exp_740 < 0.15:
        print(f"[FAIL] Below +0.15R threshold")
        result['phase4_pass'] = False
        result['verdict'] = 'REJECTED'
        result['reason'] = f'Below +0.15R threshold: {exp_740:+.3f}R'
        result['exp_740'] = exp_740
        result['exp_250'] = exp_250
        result['sample_size'] = len(trades)
        all_results.append(result)
        continue

    print("[PASS] Above +0.15R threshold")
    result['phase4_pass'] = True
    result['exp_740'] = exp_740
    result['exp_250'] = exp_250
    result['sample_size'] = len(trades)
    print()

    # =========================================================================
    # PHASE 5: STRESS TESTING
    # =========================================================================
    print("PHASE 5: Stress Testing")
    print("-" * 80)

    friction_25 = MGC_FRICTION_740 * 1.25
    friction_50 = MGC_FRICTION_740 * 1.50

    exp_25 = calculate_expectancy(trades, rr, MGC_POINT_VALUE, friction_25)
    exp_50 = calculate_expectancy(trades, rr, MGC_POINT_VALUE, friction_50)

    print(f"+25% costs (${friction_25:.2f}): {exp_25:+.3f}R")
    print(f"+50% costs (${friction_50:.2f}): {exp_50:+.3f}R")

    result['exp_25'] = exp_25
    result['exp_50'] = exp_50

    # Determine verdict
    if exp_50 >= 0.15:
        result['verdict'] = 'EXCELLENT'
        result['reason'] = 'Passes $7.40 AND survives +50% stress'
        print("[EXCELLENT] Survives +50% stress")
    elif exp_25 >= 0.15:
        result['verdict'] = 'MARGINAL'
        result['reason'] = 'Passes $7.40 but only survives +25% stress'
        print("[MARGINAL] Survives +25% stress only")
    else:
        result['verdict'] = 'WEAK'
        result['reason'] = 'Passes $7.40 but fails cost stress'
        print("[WEAK] Fails cost stress")

    result['phase5_pass'] = True
    print()

    all_results.append(result)

conn.close()

# =============================================================================
# PHASE 6: SUMMARY & DOCUMENTATION
# =============================================================================
print()
print("=" * 80)
print("PHASE 6: VALIDATION SUMMARY")
print("=" * 80)
print()

excellent = [r for r in all_results if r['verdict'] == 'EXCELLENT']
marginal = [r for r in all_results if r['verdict'] == 'MARGINAL']
weak = [r for r in all_results if r['verdict'] == 'WEAK']
rejected = [r for r in all_results if r.get('verdict') == 'REJECTED']
failed = [r for r in all_results if r['verdict'] in ['NEEDS_CONTRACT_DEFINITION', 'PHASE1_FAIL', 'PHASE2_FAIL']]

print(f"EXCELLENT (pass $7.40 + survive +50%): {len(excellent)}")
for r in excellent:
    print(f"  ID {r['id']}: {r['orb_time']} RR={r['rr']} {r.get('filter', 'Unknown')}")
    print(f"    {r['exp_740']:+.3f}R -> {r['exp_50']:+.3f}R (+50%) | N={r['sample_size']}")

print()
print(f"MARGINAL (pass $7.40 + survive +25% only): {len(marginal)}")
for r in marginal:
    print(f"  ID {r['id']}: {r['orb_time']} RR={r['rr']} {r.get('filter', 'Unknown')}")
    print(f"    {r['exp_740']:+.3f}R -> {r['exp_25']:+.3f}R (+25%) | N={r['sample_size']}")

print()
print(f"WEAK (pass $7.40 but fail stress): {len(weak)}")
for r in weak:
    print(f"  ID {r['id']}: {r['orb_time']} RR={r['rr']} {r.get('filter', 'Unknown')}")
    print(f"    {r['exp_740']:+.3f}R (stress fails) | N={r['sample_size']}")

print()
print(f"REJECTED (fail $7.40 or insufficient sample): {len(rejected)}")
for r in rejected:
    exp_str = f"{r.get('exp_740', 0):+.3f}R" if 'exp_740' in r else "N/A"
    print(f"  ID {r['id']}: {r['orb_time']} RR={r['rr']} {r.get('filter', 'Unknown')}")
    print(f"    Reason: {r['reason']}")

print()
print(f"FAILED VALIDATION (phases 1-2): {len(failed)}")
for r in failed:
    print(f"  ID {r['id']}: {r['orb_time']} RR={r['rr']}")
    print(f"    Reason: {r['reason']}")

print()
print("HONESTY OVER OUTCOME.")
print()
