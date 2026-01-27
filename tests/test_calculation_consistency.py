#!/usr/bin/env python3
"""
TEST: Calculation Consistency

Verifies deterministic calculations (same input → same output).

CRITICAL: cost_model must produce identical results for identical inputs.
No randomness, no time-based variations, pure deterministic functions.
"""

import sys
from pathlib import Path

# Add project root to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from pipeline.cost_model import calculate_realized_rr


def test_deterministic_calculations():
    """Verify cost_model produces identical results for same inputs."""
    print("=" * 70)
    print("TEST: Deterministic Calculations")
    print("=" * 70)
    print()

    # Test inputs
    test_cases = [
        {'instrument': 'MGC', 'stop_points': 5.0, 'rr': 1.5, 'stress': 'normal'},
        {'instrument': 'MGC', 'stop_points': 10.0, 'rr': 2.0, 'stress': 'normal'},
        {'instrument': 'MGC', 'stop_points': 3.5, 'rr': 3.0, 'stress': 'normal'},
        {'instrument': 'MGC', 'stop_points': 7.5, 'rr': 1.0, 'stress': 'normal'},
    ]

    print(f"Running {len(test_cases)} test cases 3 times each...")
    print()

    inconsistencies = []
    for i, test_case in enumerate(test_cases, 1):
        results = []

        # Run same calculation 3 times
        for run in range(3):
            result = calculate_realized_rr(
                instrument=test_case['instrument'],
                stop_distance_points=test_case['stop_points'],
                rr_theoretical=test_case['rr'],
                stress_level=test_case['stress']
            )
            results.append(result)

        # Verify all 3 runs produced identical results
        first_rr = results[0]['realized_rr']
        first_risk = results[0]['realized_risk_dollars']
        first_reward = results[0]['realized_reward_dollars']

        all_match = all(
            abs(r['realized_rr'] - first_rr) < 0.0001 and
            abs(r['realized_risk_dollars'] - first_risk) < 0.01 and
            abs(r['realized_reward_dollars'] - first_reward) < 0.01
            for r in results
        )

        if not all_match:
            inconsistencies.append({
                'case': i,
                'input': test_case,
                'results': results
            })
        else:
            print(f"[OK] Case {i}: {test_case['rr']}R @ {test_case['stop_points']}pts")
            print(f"     Realized RR: {first_rr:.3f} (consistent across 3 runs)")

    print()

    if inconsistencies:
        print(f"[FAIL] {len(inconsistencies)} inconsistent cases:")
        for inc in inconsistencies:
            print(f"\n  Case {inc['case']}: {inc['input']}")
            print(f"  Run 1: RR={inc['results'][0]['realized_rr']:.5f}")
            print(f"  Run 2: RR={inc['results'][1]['realized_rr']:.5f}")
            print(f"  Run 3: RR={inc['results'][2]['realized_rr']:.5f}")
        print()
        print("REQUIRED FIX: Ensure cost_model is purely deterministic")
        return False
    else:
        print(f"[OK] All {len(test_cases)} cases are deterministic")
        return True


def test_no_time_dependency():
    """Verify cost_model doesn't depend on current time."""
    print()
    print("=" * 70)
    print("TEST: No Time Dependency")
    print("=" * 70)
    print()

    import time

    # Calculate now
    result1 = calculate_realized_rr(
        instrument='MGC',
        stop_distance_points=5.0,
        rr_theoretical=1.5,
        stress_level='normal'
    )

    # Wait 1 second
    time.sleep(1)

    # Calculate again
    result2 = calculate_realized_rr(
        instrument='MGC',
        stop_distance_points=5.0,
        rr_theoretical=1.5,
        stress_level='normal'
    )

    rr_match = abs(result1['realized_rr'] - result2['realized_rr']) < 0.0001
    risk_match = abs(result1['realized_risk_dollars'] - result2['realized_risk_dollars']) < 0.01
    reward_match = abs(result1['realized_reward_dollars'] - result2['realized_reward_dollars']) < 0.01

    if rr_match and risk_match and reward_match:
        print("[OK] Results identical despite 1 second delay")
        print(f"     Realized RR: {result1['realized_rr']:.3f} (both runs)")
        print()
        return True
    else:
        print("[FAIL] Results differ after 1 second delay")
        print(f"  Run 1: RR={result1['realized_rr']:.5f}")
        print(f"  Run 2: RR={result2['realized_rr']:.5f}")
        print()
        print("REQUIRED FIX: Remove time-based logic from cost_model")
        return False


def test_no_randomness():
    """Verify cost_model has no randomness."""
    print("=" * 70)
    print("TEST: No Randomness")
    print("=" * 70)
    print()

    # Run 100 times - should get identical results every time
    results = []
    for _ in range(100):
        result = calculate_realized_rr(
            instrument='MGC',
            stop_distance_points=5.0,
            rr_theoretical=1.5,
            stress_level='normal'
        )
        results.append(result['realized_rr'])

    # All should be identical
    first = results[0]
    all_identical = all(abs(r - first) < 0.0001 for r in results)

    if all_identical:
        print(f"[OK] 100 runs produced identical results")
        print(f"     Realized RR: {first:.3f} (all 100 runs)")
        print()
        return True
    else:
        unique_values = set(round(r, 4) for r in results)
        print(f"[FAIL] 100 runs produced {len(unique_values)} different values:")
        for val in sorted(unique_values):
            print(f"  {val:.4f}")
        print()
        print("REQUIRED FIX: Remove random.*, uuid.*, or time.time() from cost_model")
        return False


def test_input_validation():
    """Verify cost_model validates inputs."""
    print("=" * 70)
    print("TEST: Input Validation")
    print("=" * 70)
    print()

    # Test invalid instrument
    try:
        calculate_realized_rr(
            instrument='INVALID',
            stop_distance_points=5.0,
            rr_theoretical=1.5,
            stress_level='normal'
        )
        print("[FAIL] Accepted invalid instrument")
        return False
    except Exception:
        print("[OK] Rejected invalid instrument")

    # Test negative stop
    try:
        calculate_realized_rr(
            instrument='MGC',
            stop_distance_points=-5.0,
            rr_theoretical=1.5,
            stress_level='normal'
        )
        print("[FAIL] Accepted negative stop distance")
        return False
    except Exception:
        print("[OK] Rejected negative stop distance")

    # Test zero RR
    try:
        calculate_realized_rr(
            instrument='MGC',
            stop_distance_points=5.0,
            rr_theoretical=0.0,
            stress_level='normal'
        )
        print("[FAIL] Accepted zero RR")
        return False
    except Exception:
        print("[OK] Rejected zero RR")

    print()
    return True


def run_all_tests():
    """Run all calculation consistency tests."""
    print()
    print("=" * 70)
    print("CALCULATION CONSISTENCY TESTS")
    print("=" * 70)
    print()

    tests = [
        test_deterministic_calculations,
        test_no_time_dependency,
        test_no_randomness,
        test_input_validation,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"[ERROR] Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")
    print()

    if passed == total:
        print("[OK] ALL TESTS PASSED")
        print()
        print("cost_model calculations are deterministic and consistent.")
        return True
    else:
        print("[FAIL] SOME TESTS FAILED")
        print()
        print("CRITICAL: cost_model must be purely deterministic (same input → same output).")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
