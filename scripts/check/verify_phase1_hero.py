"""
Phase 1 Verification: Time-Aware Production Hero Display
Tests that the hero display correctly identifies current/upcoming ORB based on time.
"""

import sys
from pathlib import Path
from datetime import datetime, time
from zoneinfo import ZoneInfo

# Add paths
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root / "trading_app"))

from orb_time_logic import get_current_orb_status, format_time_remaining

TZ_BRISBANE = ZoneInfo("Australia/Brisbane")

def test_hero_logic():
    """Test hero display logic at different times"""

    print("="*60)
    print("PHASE 1 VERIFICATION: Time-Aware Hero Display")
    print("="*60)

    test_cases = [
        (time(10, 30), "ACTIVE", "1000"),  # 10:30 AM - should show 1000 ORB as ACTIVE
        (time(10, 55), "UPCOMING", "1100"),  # 10:55 AM - should show 1100 ORB as UPCOMING
        (time(11, 10), "ACTIVE", "1100"),  # 11:10 AM - should show 1100 ORB as ACTIVE
        (time(9, 0), "UPCOMING", "0900"),  # 09:00 AM - should show 0900 ORB as UPCOMING
        (time(23, 10), "ACTIVE", "2300"),  # 23:10 PM - should show 2300 ORB as ACTIVE
        (time(0, 40), "ACTIVE", "0030"),  # 00:40 AM - should show 0030 ORB as ACTIVE
    ]

    all_passed = True

    for test_time, expected_status, expected_orb in test_cases:
        now = datetime.combine(datetime.now().date(), test_time, TZ_BRISBANE)
        status = get_current_orb_status(now)

        # Determine which ORB should be shown (hero logic)
        hero_orb = status['current_orb'] or status['upcoming_orb']

        # Check if matches expected
        status_match = status['status'] == expected_status
        orb_match = hero_orb == expected_orb

        if status_match and orb_match:
            result = "[PASS]"
        else:
            result = "[FAIL]"
            all_passed = False

        print(f"\n{result} Test at {test_time.strftime('%H:%M')}:")
        print(f"  Expected: {expected_status} - {expected_orb} ORB")
        print(f"  Got:      {status['status']} - {hero_orb} ORB")

        if status['status'] == 'ACTIVE':
            print(f"  Time remaining: {format_time_remaining(status['minutes_remaining'])}")
        elif status['status'] in ('UPCOMING', 'STANDBY'):
            print(f"  Time until forms: {format_time_remaining(status['minutes_until'])}")

    print("\n" + "="*60)
    if all_passed:
        print("ALL TESTS PASSED!")
        print("\nPhase 1 time logic is working correctly.")
        print("Hero display will show the right ORB based on current time.")
    else:
        print("SOME TESTS FAILED!")
        print("\nCheck orb_time_logic.py for issues.")
    print("="*60)

    return all_passed


if __name__ == "__main__":
    success = test_hero_logic()
    sys.exit(0 if success else 1)
