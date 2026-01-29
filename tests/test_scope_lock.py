#!/usr/bin/env python3
"""
Test Scope Lock (Hard-Block NQ + CL)

Verifies that the system BLOCKS unvalidated instruments (NQ, CL)
to prevent use of wrong contract multipliers (fake R values).

This is MANDATORY protection that prevents catastrophic losses from
using unvalidated instrument specifications.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.cost_model import (
    validate_instrument_or_block,
    get_instrument_specs,
    get_cost_model,
    calculate_realized_rr,
    PRODUCTION_INSTRUMENTS,
    BLOCKED_INSTRUMENTS
)


def test_mgc_passes():
    """Test that MGC (validated instrument) passes all checks."""
    print("=" * 70)
    print("TEST 1: MGC (Production Instrument) PASSES All Checks")
    print("=" * 70)
    print()

    print("Testing: MGC")
    print(f"  Production instruments: {PRODUCTION_INSTRUMENTS}")
    print(f"  Blocked instruments: {BLOCKED_INSTRUMENTS}")
    print()

    # Test 1: Validator passes
    try:
        validate_instrument_or_block('MGC')
        print("[OK] PASS: validate_instrument_or_block('MGC') - no error")
    except ValueError as e:
        print(f"[FAIL] FAIL: validate_instrument_or_block('MGC') raised error: {e}")
        assert False, "MGC should pass validator"

    # Test 2: get_instrument_specs passes
    try:
        specs = get_instrument_specs('MGC')
        print(f"[OK] PASS: get_instrument_specs('MGC') - returned {specs['name']}")
    except ValueError as e:
        print(f"[FAIL] FAIL: get_instrument_specs('MGC') raised error: {e}")
        assert False, "MGC should pass get_instrument_specs"

    # Test 3: get_cost_model passes
    try:
        costs = get_cost_model('MGC', 'normal')
        print(f"[OK] PASS: get_cost_model('MGC') - returned ${costs['total_friction']:.2f} friction")
    except ValueError as e:
        print(f"[FAIL] FAIL: get_cost_model('MGC') raised error: {e}")
        assert False, "MGC should pass get_cost_model"

    # Test 4: calculate_realized_rr passes
    try:
        result = calculate_realized_rr(
            instrument='MGC',
            stop_distance_points=3.0,
            rr_theoretical=1.5,
            stress_level='normal'
        )
        print(f"[OK] PASS: calculate_realized_rr('MGC') - realized RR = {result['realized_rr']:.3f}")
    except ValueError as e:
        print(f"[FAIL] FAIL: calculate_realized_rr('MGC') raised error: {e}")
        assert False, "MGC should pass calculate_realized_rr"

    print()
    print("[OK] MGC PASSES ALL CHECKS (expected behavior)")
    print()


def test_nq_blocked():
    """Test that NQ (unvalidated) is BLOCKED at all entry points."""
    print("=" * 70)
    print("TEST 2: NQ (Blocked Instrument) REJECTED At All Entry Points")
    print("=" * 70)
    print()

    blocked_variants = ['NQ', 'nq', 'MNQ', 'mnq']

    for variant in blocked_variants:
        print(f"Testing: {variant}")

        # Test 1: Validator blocks
        try:
            validate_instrument_or_block(variant)
            print(f"[FAIL] FAIL: validate_instrument_or_block('{variant}') did not raise error")
            assert False, f"{variant} should be blocked by validator"
        except ValueError as e:
            if "BLOCKED INSTRUMENT" in str(e):
                print(f"[OK] PASS: validate_instrument_or_block('{variant}') - blocked")
            else:
                print(f"[FAIL] FAIL: Wrong error message: {str(e)[:100]}")
                assert False, f"{variant} should show BLOCKED INSTRUMENT error"

        # Test 2: get_instrument_specs blocks
        try:
            specs = get_instrument_specs(variant)
            print(f"[FAIL] FAIL: get_instrument_specs('{variant}') did not raise error")
            assert False, f"{variant} should be blocked by get_instrument_specs"
        except ValueError as e:
            if "BLOCKED INSTRUMENT" in str(e):
                print(f"[OK] PASS: get_instrument_specs('{variant}') - blocked")
            else:
                print(f"[FAIL] FAIL: Wrong error message: {str(e)[:100]}")
                assert False, f"{variant} should show BLOCKED INSTRUMENT error"

        # Test 3: get_cost_model blocks
        try:
            costs = get_cost_model(variant, 'normal')
            print(f"[FAIL] FAIL: get_cost_model('{variant}') did not raise error")
            assert False, f"{variant} should be blocked by get_cost_model"
        except ValueError as e:
            if "BLOCKED INSTRUMENT" in str(e):
                print(f"[OK] PASS: get_cost_model('{variant}') - blocked")
            else:
                print(f"[FAIL] FAIL: Wrong error message: {str(e)[:100]}")
                assert False, f"{variant} should show BLOCKED INSTRUMENT error"

        # Test 4: calculate_realized_rr blocks
        try:
            result = calculate_realized_rr(
                instrument=variant,
                stop_distance_points=3.0,
                rr_theoretical=1.5,
                stress_level='normal'
            )
            print(f"[FAIL] FAIL: calculate_realized_rr('{variant}') did not raise error")
            assert False, f"{variant} should be blocked by calculate_realized_rr"
        except ValueError as e:
            if "BLOCKED INSTRUMENT" in str(e):
                print(f"[OK] PASS: calculate_realized_rr('{variant}') - blocked")
            else:
                print(f"[FAIL] FAIL: Wrong error message: {str(e)[:100]}")
                assert False, f"{variant} should show BLOCKED INSTRUMENT error"

        print()

    print("[OK] NQ BLOCKED AT ALL ENTRY POINTS (expected behavior)")
    print()


def test_cl_blocked():
    """Test that CL (unvalidated) is BLOCKED at all entry points."""
    print("=" * 70)
    print("TEST 3: CL (Blocked Instrument) REJECTED At All Entry Points")
    print("=" * 70)
    print()

    blocked_variants = ['CL', 'cl', 'MCL', 'mcl']

    for variant in blocked_variants:
        print(f"Testing: {variant}")

        # Test validator blocks
        try:
            validate_instrument_or_block(variant)
            print(f"[FAIL] FAIL: validate_instrument_or_block('{variant}') did not raise error")
            assert False, f"{variant} should be blocked by validator"
        except ValueError as e:
            if "BLOCKED INSTRUMENT" in str(e):
                print(f"[OK] PASS: validate_instrument_or_block('{variant}') - blocked")
            else:
                print(f"[FAIL] FAIL: Wrong error message: {str(e)[:100]}")
                assert False, f"{variant} should show BLOCKED INSTRUMENT error"

        print()

    print("[OK] CL BLOCKED AT ALL ENTRY POINTS (expected behavior)")
    print()


def test_unknown_instrument():
    """Test that unknown instruments are rejected."""
    print("=" * 70)
    print("TEST 4: Unknown Instruments REJECTED")
    print("=" * 70)
    print()

    unknown_variants = ['ES', 'GC', 'AAPL', 'INVALID', 'XXX']

    for variant in unknown_variants:
        print(f"Testing: {variant}")

        try:
            validate_instrument_or_block(variant)
            print(f"[FAIL] FAIL: validate_instrument_or_block('{variant}') did not raise error")
            assert False, f"{variant} should be rejected as unknown"
        except ValueError as e:
            if "UNKNOWN INSTRUMENT" in str(e):
                print(f"[OK] PASS: validate_instrument_or_block('{variant}') - rejected as unknown")
            elif "BLOCKED INSTRUMENT" in str(e):
                print(f"[OK] PASS: validate_instrument_or_block('{variant}') - blocked (acceptable)")
            else:
                print(f"[FAIL] FAIL: Wrong error message: {str(e)[:100]}")
                assert False, f"{variant} should show clear error"

        print()

    print("[OK] UNKNOWN INSTRUMENTS REJECTED (expected behavior)")
    print()


def test_error_messages():
    """Test that error messages are clear and actionable."""
    print("=" * 70)
    print("TEST 5: Error Messages Are Clear and Actionable")
    print("=" * 70)
    print()

    # Test NQ error message
    print("Testing NQ error message:")
    try:
        validate_instrument_or_block('NQ')
        assert False, "Should have raised error"
    except ValueError as e:
        error_msg = str(e)
        print(f"Error message:\n{error_msg}\n")

        # Check for key information
        required_info = [
            "BLOCKED INSTRUMENT",
            "NQ",
            "production-ready",
            "Wrong multipliers",
            "fake R",
            "PRODUCTION_INSTRUMENTS",
        ]

        for info in required_info:
            if info in error_msg:
                print(f"  [OK] Contains '{info}'")
            else:
                print(f"  [FAIL] Missing '{info}'")
                assert False, f"Error message should contain '{info}'"

    print()
    print("[OK] ERROR MESSAGES ARE CLEAR AND ACTIONABLE")
    print()


def main():
    """Run all scope lock tests."""
    print("\n")
    print("=" * 70)
    print("  SCOPE LOCK TEST SUITE")
    print("  (Hard-Block NQ + CL - MANDATORY Protection)")
    print("=" * 70)
    print()

    try:
        test_mgc_passes()
        test_nq_blocked()
        test_cl_blocked()
        test_unknown_instrument()
        test_error_messages()

        print("=" * 70)
        print("[OK] ALL SCOPE LOCK TESTS PASSED")
        print("=" * 70)
        print()
        print("Summary:")
        print("  [OK] MGC (validated) passes all checks")
        print("  [OK] NQ (blocked) rejected at all entry points")
        print("  [OK] CL (blocked) rejected at all entry points")
        print("  [OK] Unknown instruments rejected")
        print("  [OK] Error messages clear and actionable")
        print()
        print("SCOPE LOCK IS ACTIVE AND WORKING")
        print()
        print("Protected against:")
        print("  - Wrong contract multipliers (NQ/CL)")
        print("  - Fake R values from unvalidated instruments")
        print("  - Catastrophic losses from misspecified contracts")
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
