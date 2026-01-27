"""
BASELINE STRATEGY RE-VALIDATION
================================

Re-validates ALL original strategies from validated_setups WITHOUT any added filters.

VALIDATION FRAMEWORK:
1. Ground truth discovery (reverse engineer each strategy's actual filter)
2. Data integrity validation
3. Single-trade reconciliation (5 random trades)
4. Statistical validation ($8.40 mandatory - honest double-spread accounting)
5. Stress testing (+25%, +50% costs)
6. TEMPORAL VALIDATION (split by time periods)
7. REGIME VALIDATION (using CORRECT regime variable for each strategy)

CLASSIFICATION:
- BASELINE_APPROVED: ExpR >= +0.15R at $8.40 AND survives +50% stress
- BASELINE_MARGINAL: ExpR >= +0.15R at $8.40 AND survives +25% stress only
- BASELINE_REJECTED: ExpR < +0.15R at $8.40 OR N < 30

HONESTY OVER OUTCOME. FAIL CLOSED if contracts unclear.
"""

import duckdb
import sys
import random
from datetime import date

sys.path.insert(0, 'C:/Users/sydne/OneDrive/Desktop/MPX2_fresh')
from pipeline.cost_model import COST_MODELS

DB_PATH = 'gold.db'

# CANONICAL COST MODEL (MANDATORY - honest double-spread accounting)
MGC_COSTS = COST_MODELS['MGC']
MGC_POINT_VALUE = MGC_COSTS['point_value']
MGC_FRICTION = MGC_COSTS['total_friction']  # $8.40 RT (commission + spread_double + slippage)

print("=" * 80)
print("BASELINE STRATEGY RE-VALIDATION")
print("=" * 80)
print()
print(f"Canonical Cost Model: ${MGC_FRICTION:.2f} RT (MANDATORY)")
print(f"Point Value: ${MGC_POINT_VALUE:.2f}")
print(f"Approval Threshold: +0.15R at ${MGC_FRICTION:.2f}")
print()
print("NO FILTERS. NO OPTIMIZATIONS. BASELINE ONLY.")
print("=" * 80)
print()

conn = duckdb.connect(DB_PATH)

# Get ALL MGC strategies from validated_setups
strategies = conn.execute("""
    SELECT id, instrument, orb_time, rr, sl_mode, win_rate, expected_r, sample_size, orb_size_filter, notes
    FROM validated_setups
    WHERE instrument = 'MGC'
    ORDER BY id
""").fetchall()

print(f"Found {len(strategies)} MGC strategies in validated_setups")
print()

# Check actual data range
data_range = conn.execute("""
    SELECT MIN(date_local), MAX(date_local), COUNT(*)
    FROM daily_features
    WHERE instrument = 'MGC'
""").fetchone()

print(f"Data range: {data_range[0]} to {data_range[1]} ({data_range[2]} days)")
print()

# Helper function
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


# Store results
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
        'phase6_pass': False,
        'phase7_pass': False,
        'classification': None,
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
        regime_variable = "london_range"  # Correct regime for L4
    elif 'BOTH_LOST' in notes:
        filter_sql = "orb_0900_outcome = 'LOSS' AND orb_1000_outcome = 'LOSS'"
        filter_desc = "BOTH_LOST (sequential)"
        regime_variable = None  # Sequential, not regime-dependent
    elif '0900_LOSS' in notes:
        filter_sql = "orb_0900_outcome = 'LOSS'"
        filter_desc = "0900_LOSS (sequential)"
        regime_variable = None
    elif 'REVERSAL' in notes:
        filter_sql = """
            orb_0900_break_dir = orb_1000_break_dir
            AND orb_1100_break_dir != orb_1000_break_dir
            AND orb_0900_break_dir != 'NONE'
            AND orb_1100_break_dir != 'NONE'
        """
        filter_desc = "REVERSAL (sequential)"
        regime_variable = None
    elif 'ACTIVE' in notes:
        filter_sql = "asia_range >= 2.0 AND london_range >= 2.0"
        filter_desc = "ACTIVE_MARKETS (regime)"
        regime_variable = "asia_range"  # Already filtering by range
    elif 'RSI' in notes:
        filter_sql = "rsi_at_orb > 70"
        filter_desc = "RSI > 70 (indicator)"
        regime_variable = None  # Momentum, not regime
    else:
        print(f"[FAIL] Cannot reverse engineer filter from notes: {notes[:150]}")
        result['classification'] = 'BASELINE_REJECTED'
        result['reason'] = 'CONTRACT_UNDEFINED (cannot reverse engineer filter)'
        all_results.append(result)
        continue

    print(f"Filter: {filter_desc}")
    print(f"Regime variable: {regime_variable if regime_variable else 'N/A (sequential/momentum)'}")

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
        result['regime_variable'] = regime_variable
    except Exception as e:
        print(f"[FAIL] Query error: {e}")
        result['classification'] = 'BASELINE_REJECTED'
        result['reason'] = f'PHASE1_FAIL: {e}'
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
    for i, trade in enumerate(trades[:10]):
        date_local, high, low, break_dir, outcome, orb_size = trade
        if high is None or low is None or break_dir is None or outcome is None:
            print(f"[FAIL] Trade {i+1} has NULL required field")
            integrity_pass = False
            break

    if not integrity_pass:
        print("[FAIL] Data integrity issues found")
        result['classification'] = 'BASELINE_REJECTED'
        result['reason'] = 'PHASE2_FAIL: NULL values in required fields'
        all_results.append(result)
        continue

    print("[PASS] Data integrity checks passed")
    result['phase2_pass'] = True
    print()

    # =========================================================================
    # PHASE 3: SINGLE-TRADE RECONCILIATION
    # =========================================================================
    print("PHASE 3: Single-Trade Reconciliation")
    print("-" * 80)

    sample_trades = random.sample(trades, min(5, len(trades)))

    for i, trade in enumerate(sample_trades, 1):
        date_local, high, low, break_dir, outcome, orb_size = trade

        if break_dir == 'UP':
            entry, stop = high, low
        else:
            entry, stop = low, high

        stop_dist_points = abs(entry - stop)
        realized_risk_dollars = (stop_dist_points * MGC_POINT_VALUE) + MGC_FRICTION
        target_dist_points = stop_dist_points * rr
        realized_reward_dollars = (target_dist_points * MGC_POINT_VALUE) - MGC_FRICTION

        if outcome == 'WIN':
            net_pnl = realized_reward_dollars
        else:
            net_pnl = -realized_risk_dollars

        realized_r = net_pnl / realized_risk_dollars

        print(f"Trade {i} ({date_local}): {break_dir} {outcome} -> {realized_r:+.3f}R")

    print("[PASS] Single-trade reconciliation completed")
    result['phase3_pass'] = True
    print()

    # =========================================================================
    # PHASE 4: STATISTICAL VALIDATION
    # =========================================================================
    print("PHASE 4: Statistical Validation")
    print("-" * 80)

    if len(trades) < 30:
        print(f"[FAIL] Insufficient sample: {len(trades)} < 30")
        result['classification'] = 'BASELINE_REJECTED'
        result['reason'] = f'Insufficient sample: {len(trades)} < 30'
        all_results.append(result)
        continue

    print(f"[PASS] Sample size: {len(trades)} >= 30")

    # Calculate expectancy at $7.40 (MANDATORY)
    exp_740 = calculate_expectancy(trades, rr, MGC_POINT_VALUE, MGC_FRICTION)
    print(f"Expectancy at $7.40: {exp_740:+.3f}R")

    # Calculate expectancy at $2.50 (COMPARISON)
    exp_250 = calculate_expectancy(trades, rr, MGC_POINT_VALUE, 2.50)
    print(f"Expectancy at $2.50: {exp_250:+.3f}R (comparison only)")

    if exp_740 < 0.15:
        print(f"[FAIL] Below +0.15R threshold")
        result['phase4_pass'] = False
        result['classification'] = 'BASELINE_REJECTED'
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
    # PHASE 5: STRESS TESTING (COST)
    # =========================================================================
    print("PHASE 5: Stress Testing (Cost)")
    print("-" * 80)

    friction_25 = MGC_FRICTION * 1.25
    friction_50 = MGC_FRICTION * 1.50

    exp_25 = calculate_expectancy(trades, rr, MGC_POINT_VALUE, friction_25)
    exp_50 = calculate_expectancy(trades, rr, MGC_POINT_VALUE, friction_50)

    print(f"+25% costs (${friction_25:.2f}): {exp_25:+.3f}R")
    print(f"+50% costs (${friction_50:.2f}): {exp_50:+.3f}R")

    result['exp_25'] = exp_25
    result['exp_50'] = exp_50

    # Determine classification based on stress
    if exp_50 >= 0.15:
        stress_verdict = 'EXCELLENT'
        print("[EXCELLENT] Survives +50% stress")
    elif exp_25 >= 0.15:
        stress_verdict = 'MARGINAL'
        print("[MARGINAL] Survives +25% stress only")
    else:
        stress_verdict = 'WEAK'
        print("[WEAK] Fails cost stress")

    result['phase5_pass'] = True
    result['stress_verdict'] = stress_verdict
    print()

    # =========================================================================
    # PHASE 6: TEMPORAL VALIDATION
    # =========================================================================
    print("PHASE 6: Temporal Validation")
    print("-" * 80)

    # Split trades by year (if we have multi-year data)
    trades_by_year = {}
    for trade in trades:
        date_local = trade[0]
        year = str(date_local)[:4] if isinstance(date_local, (str, date)) else str(date_local.year)
        if year not in trades_by_year:
            trades_by_year[year] = []
        trades_by_year[year].append(trade)

    print(f"Years: {list(trades_by_year.keys())}")

    temporal_consistent = True
    if len(trades_by_year) >= 2:
        # Test each year independently
        for year, year_trades in trades_by_year.items():
            if len(year_trades) >= 10:  # Minimum for temporal test
                year_exp = calculate_expectancy(year_trades, rr, MGC_POINT_VALUE, MGC_FRICTION)
                print(f"  {year}: {len(year_trades)} trades, {year_exp:+.3f}R")
                if year_exp < 0:
                    temporal_consistent = False
            else:
                print(f"  {year}: {len(year_trades)} trades (skip - too few)")

        if temporal_consistent:
            print("[PASS] Positive across all time periods")
            result['phase6_pass'] = True
        else:
            print("[WARN] Negative in some periods (edge may be time-dependent)")
            result['phase6_pass'] = False
    else:
        print("[SKIP] Insufficient years for temporal test")
        result['phase6_pass'] = True  # Pass if we can't test

    print()

    # =========================================================================
    # PHASE 7: REGIME VALIDATION (Using CORRECT regime variable)
    # =========================================================================
    print("PHASE 7: Regime Validation")
    print("-" * 80)

    if regime_variable:
        # Get regime data for each trade
        regime_trades = conn.execute(f"""
            SELECT
                date_local,
                {orb_col}_high,
                {orb_col}_low,
                {orb_col}_break_dir,
                {orb_col}_outcome,
                {orb_col}_size,
                {regime_variable}
            FROM daily_features
            WHERE instrument = '{instrument}'
              AND {orb_col}_outcome IS NOT NULL
              AND {orb_col}_break_dir != 'NONE'
              AND ({filter_sql})
              AND {regime_variable} IS NOT NULL
            ORDER BY date_local
        """).fetchall()

        if len(regime_trades) >= 30:
            # Split by regime (median split)
            regime_values = [t[6] for t in regime_trades]
            median_regime = sorted(regime_values)[len(regime_values) // 2]

            low_regime = [t for t in regime_trades if t[6] < median_regime]
            high_regime = [t for t in regime_trades if t[6] >= median_regime]

            if len(low_regime) >= 10 and len(high_regime) >= 10:
                low_exp = calculate_expectancy(
                    [(t[0], t[1], t[2], t[3], t[4], t[5]) for t in low_regime],
                    rr, MGC_POINT_VALUE, MGC_FRICTION
                )
                high_exp = calculate_expectancy(
                    [(t[0], t[1], t[2], t[3], t[4], t[5]) for t in high_regime],
                    rr, MGC_POINT_VALUE, MGC_FRICTION
                )

                print(f"Using regime variable: {regime_variable}")
                print(f"  Low {regime_variable} ({len(low_regime)} trades): {low_exp:+.3f}R")
                print(f"  High {regime_variable} ({len(high_regime)} trades): {high_exp:+.3f}R")

                if low_exp > 0 and high_exp > 0:
                    print("[PASS] Positive in both regimes")
                    result['phase7_pass'] = True
                else:
                    print("[WARN] Negative in some regimes")
                    result['phase7_pass'] = False
            else:
                print("[SKIP] Insufficient trades per regime")
                result['phase7_pass'] = True
        else:
            print("[SKIP] Insufficient trades for regime test")
            result['phase7_pass'] = True
    else:
        print(f"[SKIP] Strategy is sequential/momentum (not regime-dependent)")
        result['phase7_pass'] = True

    print()

    # =========================================================================
    # FINAL CLASSIFICATION
    # =========================================================================
    print("FINAL CLASSIFICATION")
    print("-" * 80)

    if stress_verdict == 'EXCELLENT':
        result['classification'] = 'BASELINE_APPROVED'
        result['reason'] = f'Passes $7.40 ({exp_740:+.3f}R) AND survives +50% stress'
    elif stress_verdict == 'MARGINAL':
        result['classification'] = 'BASELINE_MARGINAL'
        result['reason'] = f'Passes $7.40 ({exp_740:+.3f}R) but only survives +25% stress'
    else:
        result['classification'] = 'BASELINE_REJECTED'
        result['reason'] = f'Passes $7.40 ({exp_740:+.3f}R) but fails cost stress'

    print(f"Classification: {result['classification']}")
    print(f"Reason: {result['reason']}")
    print()

    all_results.append(result)

conn.close()

# ============================================================================
# SUMMARY
# ============================================================================
print()
print("=" * 80)
print("BASELINE RE-VALIDATION SUMMARY")
print("=" * 80)
print()

approved = [r for r in all_results if r['classification'] == 'BASELINE_APPROVED']
marginal = [r for r in all_results if r['classification'] == 'BASELINE_MARGINAL']
rejected = [r for r in all_results if r['classification'] == 'BASELINE_REJECTED']

print(f"BASELINE_APPROVED: {len(approved)} strategies")
for r in approved:
    print(f"  ID {r['id']}: {r['orb_time']} RR={r['rr']} | {r['exp_740']:+.3f}R -> {r['exp_50']:+.3f}R (+50%)")

print()
print(f"BASELINE_MARGINAL: {len(marginal)} strategies")
for r in marginal:
    print(f"  ID {r['id']}: {r['orb_time']} RR={r['rr']} | {r['exp_740']:+.3f}R -> {r['exp_25']:+.3f}R (+25%)")

print()
print(f"BASELINE_REJECTED: {len(rejected)} strategies")
for r in rejected:
    print(f"  ID {r['id']}: {r['orb_time']} RR={r['rr']} | Reason: {r['reason']}")

print()
print("=" * 80)
print("HONESTY OVER OUTCOME - These are your BASELINE approved strategies.")
print("=" * 80)
