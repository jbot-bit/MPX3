#!/usr/bin/env python3
"""
Theoretical vs Realized RR Analysis - PHASE 1 VALIDATION

Compares current theoretical RR calculations vs canonical logic (costs embedded).

NO CODE CHANGES - Pure analysis to inform decision.

Based on:
- CANONICAL_LOGIC.txt
- COST_MODEL_MGC_TRADOVATE.txt
"""

import duckdb
import sys

DB_PATH = "gold.db"

# MGC Contract Specs
POINT_VALUE = 10.0  # $10 per point
TICK_SIZE = 0.10
TICK_VALUE = 1.00

# Tradovate Real Costs (from COST_MODEL_MGC_TRADOVATE.txt)
COMMISSION_RT = 2.40  # Round-trip commission + exchange + NFA
SLIPPAGE_RT = 4.00    # 4 ticks normal conditions
SPREAD = 1.00         # 1 tick spread
TOTAL_FRICTION = COMMISSION_RT + SLIPPAGE_RT + SPREAD  # $7.40


def calculate_realized_rr(stop_distance_points: float, rr_theoretical: float) -> dict:
    """
    Calculate realized RR using canonical logic.

    Canonical formulas (MANDATORY):
    - Realized_Risk_$ = (stop_distance × PointValue) + TotalFriction
    - Realized_Reward_$ = (target_distance × PointValue) - TotalFriction
    - Realized_RR = Realized_Reward_$ / Realized_Risk_$

    Args:
        stop_distance_points: Stop distance in points (e.g., ORB size)
        rr_theoretical: Target RR ratio (e.g., 1.5 means target = 1.5 × stop)

    Returns:
        dict with realized_rr, risk_$, reward_$, delta_rr, delta_pct
    """
    # Target distance = RR × stop distance
    target_distance_points = rr_theoretical * stop_distance_points

    # Canonical logic: costs embedded
    realized_risk_dollars = (stop_distance_points * POINT_VALUE) + TOTAL_FRICTION
    realized_reward_dollars = (target_distance_points * POINT_VALUE) - TOTAL_FRICTION

    # Realized RR
    realized_rr = realized_reward_dollars / realized_risk_dollars

    # Delta
    delta_rr = realized_rr - rr_theoretical
    delta_pct = (delta_rr / rr_theoretical) * 100

    return {
        'realized_rr': realized_rr,
        'risk_$': realized_risk_dollars,
        'reward_$': realized_reward_dollars,
        'delta_rr': delta_rr,
        'delta_pct': delta_pct,
        'stop_points': stop_distance_points,
        'target_points': target_distance_points
    }


def calculate_new_expectancy(win_rate: float, realized_rr: float) -> float:
    """
    Calculate expectancy with realized RR.

    Expectancy = (WinRate × AvgWin_R) - (LossRate × AvgLoss_R)

    Assumptions:
    - AvgWin = Realized_RR (full target hit)
    - AvgLoss = 1.0R (full stop hit)
    - Costs already embedded in realized_rr
    """
    loss_rate = 1.0 - win_rate
    expectancy_r = (win_rate * realized_rr) - (loss_rate * 1.0)
    return expectancy_r


def determine_status(expectancy_r: float) -> tuple:
    """Determine edge status based on expectancy."""
    if expectancy_r >= 0.15:
        return "SURVIVES", "green"
    elif expectancy_r >= 0.05:
        return "MARGINAL", "yellow"
    else:
        return "FAILS", "red"


def analyze_all_setups():
    """Run analysis on all 19 validated setups."""
    conn = duckdb.connect(DB_PATH)

    print("=" * 80)
    print("THEORETICAL vs REALIZED RR ANALYSIS - PHASE 1 VALIDATION")
    print("=" * 80)
    print()
    print("Cost Model: Tradovate Real Data")
    print(f"  Commission (RT): ${COMMISSION_RT:.2f}")
    print(f"  Slippage (RT):   ${SLIPPAGE_RT:.2f}")
    print(f"  Spread:          ${SPREAD:.2f}")
    print(f"  TOTAL FRICTION:  ${TOTAL_FRICTION:.2f} per trade")
    print()

    # Get all validated setups
    query = """
    SELECT
        id,
        instrument,
        orb_time,
        rr,
        sl_mode,
        orb_size_filter,
        win_rate,
        expected_r,
        sample_size,
        notes
    FROM validated_setups
    ORDER BY instrument, orb_time, rr
    """

    setups = conn.execute(query).fetchall()
    print(f"Total Setups: {len(setups)}")
    print()

    # Get average ORB sizes for each time (for MGC instrument)
    orb_sizes = {}
    for orb_time in ['0900', '1000', '1100', '1800', '2300', '0030']:
        orb_col = f"orb_{orb_time}_size"
        size_query = f"""
        SELECT AVG({orb_col}) as avg_size
        FROM daily_features
        WHERE {orb_col} IS NOT NULL
        AND instrument = 'MGC'
        AND date_local >= '2020-01-01'
        """
        result = conn.execute(size_query).fetchone()
        orb_sizes[orb_time] = result[0] if result[0] else 1.0

    print("Average ORB Sizes (Historical):")
    for time, size in sorted(orb_sizes.items()):
        print(f"  {time}: {size:.3f} points")
    print()
    print("=" * 80)
    print()

    # Analyze each setup
    results = []

    for setup in setups:
        setup_id, instrument, orb_time, rr_theoretical, sl_mode, orb_filter, \
        win_rate, expected_r_old, sample_size, notes = setup

        # Get average ORB size for this time
        avg_orb_size = orb_sizes.get(orb_time, 1.0)

        # Calculate stop distance based on sl_mode
        if sl_mode == 'FULL':
            stop_distance = avg_orb_size
        elif sl_mode == 'HALF':
            stop_distance = avg_orb_size / 2.0
        else:
            stop_distance = avg_orb_size  # Default to full

        # Calculate realized RR
        realized = calculate_realized_rr(stop_distance, rr_theoretical)

        # Calculate new expectancy
        win_rate_decimal = win_rate / 100.0
        new_expectancy = calculate_new_expectancy(win_rate_decimal, realized['realized_rr'])

        # Determine status
        status, color = determine_status(new_expectancy)

        results.append({
            'id': setup_id,
            'instrument': instrument,
            'orb_time': orb_time,
            'rr_theoretical': rr_theoretical,
            'rr_realized': realized['realized_rr'],
            'delta_rr': realized['delta_rr'],
            'delta_pct': realized['delta_pct'],
            'win_rate': win_rate,
            'expectancy_old': expected_r_old,
            'expectancy_new': new_expectancy,
            'expectancy_delta': new_expectancy - expected_r_old,
            'status': status,
            'sample_size': sample_size,
            'stop_points': realized['stop_points'],
            'target_points': realized['target_points'],
            'risk_$': realized['risk_$'],
            'reward_$': realized['reward_$']
        })

    # Output results
    print("SETUP-BY-SETUP ANALYSIS")
    print("=" * 80)
    print()

    for r in results:
        print(f"Setup #{r['id']}: {r['instrument']} {r['orb_time']} ORB (RR={r['rr_theoretical']:.1f})")
        print(f"  Sample: {r['sample_size']} trades, Win Rate: {r['win_rate']:.1f}%")
        print(f"  Stop: {r['stop_points']:.3f} pts (${r['risk_$']:.2f}), Target: {r['target_points']:.3f} pts (${r['reward_$']:.2f})")
        print()
        print(f"  Theoretical RR: {r['rr_theoretical']:.3f}")
        print(f"  Realized RR:    {r['rr_realized']:.3f}  (delta: {r['delta_rr']:+.3f}, {r['delta_pct']:+.1f}%)")
        print()
        print(f"  Old Expectancy: {r['expectancy_old']:+.3f}R")
        print(f"  New Expectancy: {r['expectancy_new']:+.3f}R  (delta: {r['expectancy_delta']:+.3f}R)")
        print()
        print(f"  STATUS: [{r['status']}]")
        print()
        print("-" * 80)
        print()

    # Summary statistics
    print("=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print()

    survives = [r for r in results if r['status'] == 'SURVIVES']
    marginal = [r for r in results if r['status'] == 'MARGINAL']
    fails = [r for r in results if r['status'] == 'FAILS']

    print(f"Total Setups: {len(results)}")
    print(f"  SURVIVES (E >= 0.15R): {len(survives)} ({len(survives)/len(results)*100:.1f}%)")
    print(f"  MARGINAL (0.05R <= E < 0.15R): {len(marginal)} ({len(marginal)/len(results)*100:.1f}%)")
    print(f"  FAILS (E < 0.05R): {len(fails)} ({len(fails)/len(results)*100:.1f}%)")
    print()

    avg_delta_rr = sum(r['delta_rr'] for r in results) / len(results)
    avg_delta_pct = sum(r['delta_pct'] for r in results) / len(results)
    avg_expectancy_delta = sum(r['expectancy_delta'] for r in results) / len(results)

    print(f"Average RR Delta: {avg_delta_rr:+.3f} ({avg_delta_pct:+.1f}%)")
    print(f"Average Expectancy Delta: {avg_expectancy_delta:+.3f}R")
    print()

    # By instrument
    for inst in ['MGC', 'NQ', 'MPL']:
        inst_results = [r for r in results if r['instrument'] == inst]
        if not inst_results:
            continue

        inst_survives = len([r for r in inst_results if r['status'] == 'SURVIVES'])
        inst_marginal = len([r for r in inst_results if r['status'] == 'MARGINAL'])
        inst_fails = len([r for r in inst_results if r['status'] == 'FAILS'])

        print(f"{inst}:")
        print(f"  Total: {len(inst_results)}")
        print(f"  Survives: {inst_survives}, Marginal: {inst_marginal}, Fails: {inst_fails}")
        print()

    # Key findings
    print("=" * 80)
    print("KEY FINDINGS")
    print("=" * 80)
    print()

    if len(survives) == len(results):
        print("[OK] ALL edges survive canonical logic")
    elif len(survives) > len(results) / 2:
        print(f"[!] MAJORITY survive ({len(survives)}/{len(results)}), but {len(marginal)+len(fails)} need review")
    else:
        print(f"[X] CRITICAL: Only {len(survives)}/{len(results)} edges survive")
    print()

    if avg_delta_pct < -20:
        print(f"[!] RR reduction is SIGNIFICANT: {avg_delta_pct:.1f}% average")
    elif avg_delta_pct < -10:
        print(f"[!] RR reduction is MODERATE: {avg_delta_pct:.1f}% average")
    else:
        print(f"[OK] RR reduction is MINOR: {avg_delta_pct:.1f}% average")
    print()

    if avg_expectancy_delta < -0.10:
        print(f"[!] Expectancy impact is SIGNIFICANT: {avg_expectancy_delta:+.3f}R average")
    elif avg_expectancy_delta < -0.05:
        print(f"[!] Expectancy impact is MODERATE: {avg_expectancy_delta:+.3f}R average")
    else:
        print(f"[OK] Expectancy impact is MINOR: {avg_expectancy_delta:+.3f}R average")
    print()

    # Worst affected
    worst = sorted(results, key=lambda r: r['expectancy_delta'])[0]
    print(f"Worst affected: Setup #{worst['id']} ({worst['instrument']} {worst['orb_time']} RR={worst['rr_theoretical']:.1f})")
    print(f"  Expectancy: {worst['expectancy_old']:+.3f}R -> {worst['expectancy_new']:+.3f}R (delta: {worst['expectancy_delta']:+.3f}R)")
    print()

    # Best performing
    best = sorted(results, key=lambda r: r['expectancy_new'], reverse=True)[0]
    print(f"Best performing: Setup #{best['id']} ({best['instrument']} {best['orb_time']} RR={best['rr_theoretical']:.1f})")
    print(f"  Expectancy: {best['expectancy_new']:+.3f}R, Status: {best['status']}")
    print()

    # Recommendations
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()

    if len(fails) > 0:
        print(f"1. REMOVE {len(fails)} failing edge(s) from validated_setups:")
        for r in fails:
            print(f"   - Setup #{r['id']}: {r['instrument']} {r['orb_time']} RR={r['rr_theoretical']:.1f} (E={r['expectancy_new']:+.3f}R)")
        print()

    if len(marginal) > 0:
        print(f"2. REVIEW {len(marginal)} marginal edge(s):")
        for r in marginal:
            print(f"   - Setup #{r['id']}: {r['instrument']} {r['orb_time']} RR={r['rr_theoretical']:.1f} (E={r['expectancy_new']:+.3f}R)")
        print("   Decision: Keep with caution or increase sample size")
        print()

    if len(survives) > 0:
        print(f"3. KEEP {len(survives)} surviving edge(s):")
        print("   These edges remain profitable with canonical logic")
        print()

    print("4. PROCEED WITH PHASE 2 (Implementation):")
    print("   - Update execution_engine.py with canonical logic")
    print("   - Rebuild daily_features_v2 with realized RR")
    print("   - Update cost_model.py")
    print("   - Modify schema to store both theoretical + realized RR")
    print()

    print("5. DO NOT PROCEED if:")
    print("   - More than 50% of edges fail")
    print("   - Critical production edges (0900/1000 MGC) fail")
    print("   - Average expectancy drops below 0.10R")
    print()

    # Decision gate
    print("=" * 80)
    print("DECISION GATE")
    print("=" * 80)
    print()

    if len(fails) == 0 and avg_expectancy_delta > -0.15:
        print("[GO] Safe to proceed with canonical logic migration")
        print("     - No edges fail")
        print(f"     - Average expectancy impact: {avg_expectancy_delta:+.3f}R (acceptable)")
    elif len(fails) < len(results) * 0.2 and avg_expectancy_delta > -0.20:
        print("[CAUTION] Proceed with adjustments")
        print(f"     - {len(fails)} edges fail (remove these)")
        print(f"     - Average expectancy impact: {avg_expectancy_delta:+.3f}R (moderate)")
    else:
        print("[STOP] DO NOT proceed with canonical logic migration")
        print(f"     - Too many edges fail ({len(fails)}/{len(results)})")
        print(f"     - Expectancy impact too severe ({avg_expectancy_delta:+.3f}R)")
        print("     - Investigate cost assumptions or strategy validity")
    print()

    conn.close()


if __name__ == "__main__":
    analyze_all_setups()
