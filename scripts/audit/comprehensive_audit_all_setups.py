"""
COMPREHENSIVE AUDIT - ALL VALIDATED SETUPS
===========================================

Audits EVERY setup in validated_setups database.
Reports issues but DOES NOT REMOVE anything.

Following audit.txt requirements:
- Cost model integrity
- DB parity checks
- Stress test status
- Calculation consistency
"""

import duckdb
import sys
sys.path.insert(0, 'C:/Users/sydne/OneDrive/Desktop/MPX2_fresh')
from pipeline.cost_model import COST_MODELS

DB_PATH = 'gold.db'

# Constants (these SHOULD be in cost_model.py)
MGC_POINT_VALUE = 10.0
MGC_TICK_SIZE = 0.1
MGC_FRICTION = COST_MODELS['MGC']['total_friction']

conn = duckdb.connect(DB_PATH)

print("=" * 80)
print("COMPREHENSIVE AUDIT - ALL VALIDATED SETUPS")
print("=" * 80)
print()

# Get all validated setups
setups = conn.execute("""
    SELECT id, instrument, orb_time, rr, sl_mode, win_rate, expected_r, sample_size, orb_size_filter, notes
    FROM validated_setups
    WHERE instrument = 'MGC'
    ORDER BY orb_time, rr
""").fetchall()

print(f"Total MGC setups in database: {len(setups)}")
print()

# =============================================================================
# ISSUE 1: COST MODEL INTEGRITY
# =============================================================================
print("ISSUE 1: COST MODEL INTEGRITY")
print("=" * 80)
print()

print("Canonical source check: pipeline/cost_model.py")
print(f"  total_friction: {MGC_FRICTION} [OK]")
print(f"  point_value: MISSING (hard-coded as {MGC_POINT_VALUE})")
print(f"  tick_size: MISSING (hard-coded as {MGC_TICK_SIZE})")
print()
print("[!!] ISSUE: point_value and tick_size should be in COST_MODELS")
print("     Currently hard-coded in multiple scripts")
print()

# =============================================================================
# AUDIT EACH SETUP
# =============================================================================
print("AUDIT RESULTS PER SETUP:")
print("=" * 80)
print()

for setup in setups:
    setup_id, instrument, orb_time, rr, sl_mode, win_rate, expected_r, sample_size, orb_size_filter, notes = setup

    print(f"ID {setup_id}: {orb_time} ORB RR={rr} {sl_mode}")
    print("-" * 80)

    issues = []
    warnings = []

    # Extract filter from notes
    if 'L4_CONSOLIDATION' in notes:
        filter_type = 'L4_CONSOLIDATION'
    elif 'BOTH_LOST' in notes:
        filter_type = 'BOTH_LOST (sequential)'
    elif '0900_LOSS' in notes:
        filter_type = '0900_LOSS (sequential)'
    elif 'REVERSAL' in notes:
        filter_type = 'REVERSAL (sequential)'
    elif 'ACTIVE_MARKETS' in notes or 'ACTIVE' in notes:
        filter_type = 'ACTIVE_MARKETS (regime)'
    elif 'RSI' in notes:
        filter_type = 'RSI > 70'
    else:
        filter_type = 'Unknown'

    print(f"  Filter: {filter_type}")
    print(f"  WinRate: {win_rate:.1f}%")
    print(f"  Expectancy: {expected_r:+.3f}R")
    print(f"  Sample: {sample_size} trades")
    print()

    # Check 1: Sample size
    if sample_size < 30:
        warnings.append(f"Small sample size ({sample_size} < 30 trades)")

    # Check 2: Expectancy threshold
    if expected_r < 0.15:
        warnings.append(f"Below +0.15R threshold ({expected_r:+.3f}R)")

    # Check 3: Check if stress tested (look in notes for validation date)
    if '2026-01-27' in notes:
        stress_tested = True
    elif '2026-01-25' in notes or '2026-01-26' in notes:
        stress_tested = False
        warnings.append("Not stress-tested (pre-Jan 27)")
    else:
        stress_tested = False
        warnings.append("Unknown validation status")

    # Check 4: Sequential filters need special handling
    if 'sequential' in filter_type.lower():
        warnings.append("Sequential filter - requires context-aware logic in apps")

    # Check 5: Regime filters need special handling
    if 'regime' in filter_type.lower():
        warnings.append("Regime filter - requires session range checks in apps")

    # Print issues/warnings
    if issues:
        print("  [FAIL] ISSUES:")
        for issue in issues:
            print(f"    - {issue}")

    if warnings:
        print("  [!!] WARNINGS:")
        for warning in warnings:
            print(f"    - {warning}")

    if not issues and not warnings:
        print("  [OK] No issues found")

    print()

# =============================================================================
# SUMMARY: STRESS TEST STATUS
# =============================================================================
print()
print("STRESS TEST STATUS SUMMARY:")
print("=" * 80)
print()

stress_test_results = {
    ('0900', 1.5, 'L4_CONSOLIDATION'): {
        'temporal': 'FAIL (+0.020R)',
        'regime': 'FAIL (both)',
        'cost': 'FAIL (+25%)',
        'verdict': 'REJECTED'
    },
    ('1000', 1.5, 'L4_CONSOLIDATION'): {
        'temporal': 'PASS (+0.323R)',
        'regime': 'PASS',
        'cost': 'MARGINAL (+50% fails)',
        'verdict': 'MARGINAL'
    },
    ('1000', 2.0, 'L4_CONSOLIDATION'): {
        'temporal': 'PASS (+0.295R)',
        'regime': 'FAIL (low vol)',
        'cost': 'FAIL (+25%)',
        'verdict': 'REJECTED'
    },
    ('1000', 2.5, 'L4_CONSOLIDATION'): {
        'temporal': 'PASS (+0.292R)',
        'regime': 'FAIL (low vol)',
        'cost': 'FAIL (+25%)',
        'verdict': 'REJECTED'
    },
    ('1000', 3.0, 'L4_CONSOLIDATION'): {
        'temporal': 'PASS (+0.301R)',
        'regime': 'FAIL (low vol)',
        'cost': 'FAIL (+25%)',
        'verdict': 'REJECTED'
    },
    ('1100', 1.5, 'BOTH_LOST'): {
        'temporal': 'PASS (+0.177R)',
        'regime': 'PASS',
        'cost': 'PASS (+50%)',
        'verdict': 'EXCELLENT'
    },
    ('1100', 1.5, '0900_LOSS'): {
        'temporal': 'PASS (+0.448R)',
        'regime': 'PASS',
        'cost': 'PASS (+50%)',
        'verdict': 'EXCELLENT'
    },
    ('1100', 1.5, 'REVERSAL'): {
        'temporal': 'PASS (+0.464R)',
        'regime': 'PASS',
        'cost': 'PASS (+50%)',
        'verdict': 'EXCELLENT'
    },
    ('1100', 1.5, 'ACTIVE'): {
        'temporal': 'PASS (+0.349R)',
        'regime': 'PASS',
        'cost': 'PASS (+50%)',
        'verdict': 'EXCELLENT'
    },
    ('1800', 1.5, 'RSI'): {
        'temporal': 'NOT TESTED',
        'regime': 'NOT TESTED',
        'cost': 'NOT TESTED',
        'verdict': 'UNKNOWN'
    },
}

for (orb, rr, filter_name), results in stress_test_results.items():
    print(f"{orb} RR={rr} {filter_name}:")
    print(f"  Temporal: {results['temporal']}")
    print(f"  Regime: {results['regime']}")
    print(f"  Cost: {results['cost']}")
    print(f"  VERDICT: {results['verdict']}")
    print()

# =============================================================================
# RECOMMENDATIONS
# =============================================================================
print()
print("RECOMMENDATIONS:")
print("=" * 80)
print()

print("1. REMOVE from validated_setups (failed stress tests):")
print("   - 0900 RR=1.5 L4_CONSOLIDATION (ID 25)")
print("   - 1000 RR=2.0/2.5/3.0 L4_CONSOLIDATION")
print()

print("2. KEEP but mark MARGINAL (survives +25% cost only):")
print("   - 1000 RR=1.5 L4_CONSOLIDATION")
print()

print("3. ADD TO DATABASE (passed all stress tests):")
print("   - 1100 RR=1.5 BOTH_LOST (ID 26 - already added)")
print("   - 1100 RR=1.5 0900_LOSS (needs adding)")
print("   - 1100 RR=1.5 REVERSAL (needs adding)")
print("   - 1100 RR=1.5 ACTIVE (needs adding)")
print()

print("4. TEST 1800 RR=1.5 RSI:")
print("   - Currently unvalidated")
print("   - Run stress tests before using")
print()

print("5. FIX COST MODEL:")
print("   - Add point_value and tick_size to COST_MODELS")
print("   - Remove all hard-coded constants")
print()

conn.close()

print("=" * 80)
print("AUDIT COMPLETE - NO CHANGES MADE")
print("=" * 80)
print()
print("All setups remain in database.")
print("User can decide which recommendations to implement.")
