"""
Test that SetupDetector properly surfaces multiple setups per ORB time.

Critical for ensuring the architecture fix (multi-setup support) works at runtime.
"""

import pytest
import sys
from pathlib import Path

# Add trading_app to path
sys.path.insert(0, str(Path(__file__).parent.parent / "trading_app"))

from setup_detector import SetupDetector


def test_mgc_1000_has_two_setups():
    """
    Test that MGC 1000 ORB returns BOTH candidates 47 and 48.

    This is the critical test for multi-setup architecture.
    Before the fix, only one setup would be returned (silent overwrite).
    After the fix, both setups must be present.
    """
    detector = SetupDetector(None)  # Cloud-aware connection

    # Get all MGC setups
    all_setups = detector.get_all_validated_setups('MGC')

    assert len(all_setups) > 0, "Should have at least some MGC setups"

    # Filter for MGC 1000 ORB setups
    mgc_1000_setups = [s for s in all_setups if s['orb_time'] == '1000']

    # CRITICAL: Must have exactly 2 setups for MGC 1000
    assert len(mgc_1000_setups) == 2, \
        f"Expected 2 MGC 1000 setups (candidates 47+48), found {len(mgc_1000_setups)}"

    # Extract RR values
    rr_values = sorted([s['rr'] for s in mgc_1000_setups])

    # Should have RR=1.0 and RR=2.0
    assert rr_values == [1.0, 2.0], \
        f"Expected RR values [1.0, 2.0], got {rr_values}"

    # Extract SL modes
    sl_modes = sorted([s['sl_mode'] for s in mgc_1000_setups])

    # Should have FULL and HALF
    assert sl_modes == ['FULL', 'HALF'], \
        f"Expected SL modes ['FULL', 'HALF'], got {sl_modes}"

    # Check setup IDs
    setup_ids = sorted([s['setup_id'] for s in mgc_1000_setups])

    assert 'MGC_1000_047' in setup_ids, "Candidate 47 missing"
    assert 'MGC_1000_048' in setup_ids, "Candidate 48 missing"


def test_all_orb_times_return_lists():
    """
    Test that all ORB times return proper setup lists (not single values).
    """
    detector = SetupDetector(None)

    all_setups = detector.get_all_validated_setups('MGC')

    # Group by orb_time
    by_orb_time = {}
    for setup in all_setups:
        orb_time = setup['orb_time']
        if orb_time not in by_orb_time:
            by_orb_time[orb_time] = []
        by_orb_time[orb_time].append(setup)

    # All ORB times should have list of setups
    for orb_time, setups in by_orb_time.items():
        assert isinstance(setups, list), \
            f"ORB time {orb_time} should return list, got {type(setups)}"

        assert len(setups) >= 1, \
            f"ORB time {orb_time} should have at least 1 setup"

    # Specifically check 1000 has multiple
    assert len(by_orb_time.get('1000', [])) == 2, \
        "MGC 1000 should have 2 setups"


def test_no_silent_overwrites():
    """
    Test that multiple setups with same orb_time are not silently overwritten.

    This would catch regression back to the old broken architecture.
    """
    detector = SetupDetector(None)

    all_setups = detector.get_all_validated_setups('MGC')

    # Count setups by (orb_time, rr, sl_mode) - should be unique
    unique_combos = set()
    for setup in all_setups:
        combo = (setup['orb_time'], setup['rr'], setup['sl_mode'])
        assert combo not in unique_combos, \
            f"Duplicate setup detected: {combo} (silent overwrite?)"
        unique_combos.add(combo)

    # Should have at least 7 unique MGC setups (excluding CASCADE/SINGLE_LIQ)
    time_based_setups = [s for s in all_setups
                         if s['orb_time'] not in ['CASCADE', 'SINGLE_LIQ']]

    assert len(time_based_setups) >= 7, \
        f"Expected at least 7 time-based MGC setups, found {len(time_based_setups)}"


if __name__ == "__main__":
    # Run tests directly
    print("Testing multi-setup ORB detection...")
    print()

    try:
        test_mgc_1000_has_two_setups()
        print("[PASS] test_mgc_1000_has_two_setups")
    except AssertionError as e:
        print(f"[FAIL] test_mgc_1000_has_two_setups: {e}")
        sys.exit(1)

    try:
        test_all_orb_times_return_lists()
        print("[PASS] test_all_orb_times_return_lists")
    except AssertionError as e:
        print(f"[FAIL] test_all_orb_times_return_lists: {e}")
        sys.exit(1)

    try:
        test_no_silent_overwrites()
        print("[PASS] test_no_silent_overwrites")
    except AssertionError as e:
        print(f"[FAIL] test_no_silent_overwrites: {e}")
        sys.exit(1)

    print()
    print("All multi-setup tests PASSED!")
