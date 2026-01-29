#!/usr/bin/env python3
"""
Test Integrity Gate (30% Cost Threshold)

Verifies that the system REJECTS trades where transaction costs
exceed 30% of stop distance (mathematically unviable trades).

This is MANDATORY protection that applies to ALL instruments, ALL modes.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.cost_model import (
    check_minimum_viable_risk,
    calculate_realized_rr,
    MINIMUM_VIABLE_RISK_THRESHOLD
)

def test_integrity_gate_pass():
    """Test trades that SHOULD PASS the integrity gate."""
    print("=" * 70)
    print("TEST 1: Trades that PASS integrity gate (costs < 30% of stop)")
    print("=" * 70)
    print()

    test_cases = [
        # (stop_points, point_value, total_friction, description)
        (3.0, 10.0, 8.40, "Normal MGC trade (3pt stop)"),
        (2.824, 10.0, 8.40, "Avg 1000 ORB (2.824pt stop)"),
        (5.0, 10.0, 8.40, "Large ORB (5pt stop)"),
        (1.0, 10.0, 2.00, "Small costs (1pt stop, $2 friction)"),
    ]

    for stop_pts, pv, friction, desc in test_cases:
        is_viable, cost_ratio, message = check_minimum_viable_risk(
            stop_distance_points=stop_pts,
            point_value=pv,
            total_friction=friction
        )

        chart_risk = stop_pts * pv
        status = "[OK] PASS" if is_viable else "[FAIL] FAIL"
        print(f"{status} {desc}")
        print(f"  Stop: {stop_pts:.3f} pts (${chart_risk:.2f})")
        print(f"  Costs: ${friction:.2f}")
        print(f"  Ratio: {cost_ratio:.1%} (limit: {MINIMUM_VIABLE_RISK_THRESHOLD:.0%})")
        print(f"  Result: {message}")
        print()

        # Verify PASS
        assert is_viable, f"Expected PASS but got REJECT: {desc}"

    print(f"[OK] ALL {len(test_cases)} PASSING TESTS VERIFIED")
    print()


def test_integrity_gate_reject():
    """Test trades that SHOULD REJECT at the integrity gate."""
    print("=" * 70)
    print("TEST 2: Trades that REJECT at integrity gate (costs > 30% of stop)")
    print("=" * 70)
    print()

    test_cases = [
        # (stop_points, point_value, total_friction, description)
        (0.5, 10.0, 8.40, "Tiny ORB (0.5pt stop, 168% costs)"),
        (0.8, 10.0, 8.40, "Small ORB (0.8pt stop, 105% costs)"),
        (1.0, 10.0, 8.40, "Marginal ORB (1.0pt stop, 84% costs)"),
        (2.0, 10.0, 8.40, "Borderline ORB (2.0pt stop, 42% costs)"),
        (2.5, 10.0, 8.40, "Edge case (2.5pt stop, 33.6% costs)"),
    ]

    for stop_pts, pv, friction, desc in test_cases:
        is_viable, cost_ratio, message = check_minimum_viable_risk(
            stop_distance_points=stop_pts,
            point_value=pv,
            total_friction=friction
        )

        chart_risk = stop_pts * pv
        status = "[OK] REJECT" if not is_viable else "[FAIL] PASS (WRONG!)"
        print(f"{status} {desc}")
        print(f"  Stop: {stop_pts:.3f} pts (${chart_risk:.2f})")
        print(f"  Costs: ${friction:.2f}")
        print(f"  Ratio: {cost_ratio:.1%} (limit: {MINIMUM_VIABLE_RISK_THRESHOLD:.0%})")
        print(f"  Result: {message}")
        print()

        # Verify REJECT
        assert not is_viable, f"Expected REJECT but got PASS: {desc}"

    print(f"[OK] ALL {len(test_cases)} REJECTION TESTS VERIFIED")
    print()


def test_calculate_realized_rr_rejection():
    """Test that calculate_realized_rr() raises ValueError for unviable trades."""
    print("=" * 70)
    print("TEST 3: calculate_realized_rr() REJECTS unviable trades")
    print("=" * 70)
    print()

    # Test case from AUDIT1: 0.5pt stop with $8.40 costs (168% ratio)
    print("Attempting: 0.5pt stop with $8.40 MGC costs (168% cost ratio)")
    print()

    try:
        result = calculate_realized_rr(
            instrument='MGC',
            stop_distance_points=0.5,
            rr_theoretical=1.5,
            stress_level='normal'
        )
        print(f"[FAIL] FAIL: Trade was ACCEPTED (should have been REJECTED)")
        print(f"  Realized RR: {result['realized_rr']:.3f}")
        assert False, "Expected ValueError but got result"

    except ValueError as e:
        print(f"[OK] PASS: Trade was REJECTED by integrity gate")
        print(f"  Error: {str(e)[:200]}...")
        assert "INTEGRITY GATE REJECTION" in str(e), "Wrong error message"

    print()


def test_boundary_case():
    """Test the exact 30% boundary."""
    print("=" * 70)
    print("TEST 4: Boundary case (exactly 30% costs)")
    print("=" * 70)
    print()

    # Calculate stop that gives exactly 30% cost ratio
    # cost_ratio = friction / (stop_pts * pv)
    # 0.30 = 8.40 / (stop_pts * 10.0)
    # stop_pts = 8.40 / (0.30 * 10.0) = 2.8 points

    stop_pts = 8.40 / (0.30 * 10.0)
    print(f"Boundary stop: {stop_pts:.3f} points (should give exactly 30% cost ratio)")
    print()

    is_viable, cost_ratio, message = check_minimum_viable_risk(
        stop_distance_points=stop_pts,
        point_value=10.0,
        total_friction=8.40
    )

    print(f"  Result: {'PASS' if is_viable else 'REJECT'}")
    print(f"  Cost Ratio: {cost_ratio:.6f} (exactly {MINIMUM_VIABLE_RISK_THRESHOLD:.0%})")
    print(f"  Message: {message}")
    print()

    # At exactly 30%, should REJECT (> threshold)
    # But due to floating point, let's check both cases
    if cost_ratio > MINIMUM_VIABLE_RISK_THRESHOLD:
        assert not is_viable, "Should REJECT when > 30%"
        print("[OK] PASS: Correctly REJECTS at/above 30% boundary")
    else:
        assert is_viable, "Should PASS when <= 30%"
        print("[OK] PASS: Correctly PASSES at/below 30% boundary")

    print()


def test_audit1_example():
    """Test the exact example from AUDIT1_RESULTS.md."""
    print("=" * 70)
    print("TEST 5: AUDIT1 Example (0.5pt stop, 168% costs)")
    print("=" * 70)
    print()

    print("From AUDIT1_RESULTS.md:")
    print("  ORB size = 0.5 points ($5.00 risk)")
    print("  Costs = $8.40")
    print("  Cost ratio = 168% of stop")
    print("  Expected: REJECT")
    print()

    is_viable, cost_ratio, message = check_minimum_viable_risk(
        stop_distance_points=0.5,
        point_value=10.0,
        total_friction=8.40
    )

    print(f"Result: {'[OK] REJECT' if not is_viable else '[FAIL] PASS (WRONG!)'}")
    print(f"  Cost Ratio: {cost_ratio:.1%}")
    print(f"  Message: {message}")
    print()

    assert not is_viable, "AUDIT1 example should be REJECTED"
    assert abs(cost_ratio - 1.68) < 0.01, f"Expected 168% cost ratio, got {cost_ratio:.1%}"

    print("[OK] AUDIT1 example correctly REJECTED by integrity gate")
    print()


def main():
    """Run all integrity gate tests."""
    print("\n")
    print("=" * 70)
    print("  INTEGRITY GATE TEST SUITE")
    print("  (30% Cost Threshold - MANDATORY Protection)")
    print("=" * 70)
    print()

    try:
        test_integrity_gate_pass()
        test_integrity_gate_reject()
        test_calculate_realized_rr_rejection()
        test_boundary_case()
        test_audit1_example()

        print("=" * 70)
        print("[OK] ALL INTEGRITY GATE TESTS PASSED")
        print("=" * 70)
        print()
        print("Summary:")
        print("  [OK] Passing trades correctly accepted (costs < 30%)")
        print("  [OK] Unviable trades correctly rejected (costs > 30%)")
        print("  [OK] calculate_realized_rr() enforces gate")
        print("  [OK] Boundary case handled correctly")
        print("  [OK] AUDIT1 example verified")
        print()
        print("INTEGRITY GATE IS ACTIVE AND WORKING")
        print()

        return 0

    except AssertionError as e:
        print()
        print("=" * 70)
        print("[FAIL] TEST FAILED")
        print("=" * 70)
        print(f"Error: {e}")
        print()
        return 1

    except Exception as e:
        print()
        print("=" * 70)
        print("[FAIL] UNEXPECTED ERROR")
        print("=" * 70)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print()
        return 1


if __name__ == '__main__':
    sys.exit(main())
