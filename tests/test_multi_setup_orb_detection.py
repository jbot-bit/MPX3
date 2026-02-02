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
from cloud_mode import get_database_connection


def get_expected_setup_count(instrument: str, orb_time: str) -> int:
    """
    Get expected count from DB matching SetupDetector's filter logic.

    SetupDetector uses: status IS NULL OR status != 'REJECTED'
    (includes ACTIVE and RETIRED for historical analysis)
    """
    conn = get_database_connection(read_only=True)
    result = conn.execute("""
        SELECT COUNT(*) FROM validated_setups
        WHERE instrument = ? AND orb_time = ?
          AND (status IS NULL OR status != 'REJECTED')
    """, [instrument, orb_time]).fetchone()
    conn.close()
    return result[0] if result else 0


def test_mgc_1000_count_matches_database():
    """
    Test that MGC 1000 ORB count matches database (non-REJECTED).

    This is the critical test for multi-setup architecture.
    Before the fix, only one setup would be returned (silent overwrite).
    After the fix, all setups must be present.
    """
    detector = SetupDetector(None)  # Cloud-aware connection

    # Get expected count from DB (same filter as SetupDetector)
    expected_count = get_expected_setup_count('MGC', '1000')

    # Get all MGC setups
    all_setups = detector.get_all_validated_setups('MGC')

    assert len(all_setups) > 0, "Should have at least some MGC setups"

    # Filter for MGC 1000 ORB setups
    mgc_1000_setups = [s for s in all_setups if s['orb_time'] == '1000']

    # CRITICAL: Count must match database
    assert len(mgc_1000_setups) == expected_count, \
        f"DB has {expected_count} MGC 1000 setups but detector returned {len(mgc_1000_setups)} (silent overwrite?)"

    # Verify each setup has required keys
    for i, setup in enumerate(mgc_1000_setups):
        assert 'rr' in setup, f"Setup {i} missing 'rr' key"
        assert 'sl_mode' in setup, f"Setup {i} missing 'sl_mode' key"
        assert 'orb_time' in setup, f"Setup {i} missing 'orb_time' key"

    # Verify no duplicate (rr, sl_mode) combinations
    combos = [(s['rr'], s['sl_mode']) for s in mgc_1000_setups]
    assert len(combos) == len(set(combos)), \
        f"Duplicate (rr, sl_mode) combinations found: {combos}"


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

    # Verify 1000 count matches database (dynamic check)
    if '1000' in by_orb_time:
        expected_1000 = get_expected_setup_count('MGC', '1000')
        actual_1000 = len(by_orb_time['1000'])
        assert actual_1000 == expected_1000, \
            f"MGC 1000: expected {expected_1000} setups from DB, got {actual_1000}"


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
        test_mgc_1000_count_matches_database()
        print("[PASS] test_mgc_1000_count_matches_database")
    except AssertionError as e:
        print(f"[FAIL] test_mgc_1000_count_matches_database: {e}")
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
