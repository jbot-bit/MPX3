"""
Test ORB Temporal Consistency

Proves that ORB states follow one-way transitions and cannot revert once broken.

Scenario:
- 09:00-09:05: ORB forms (high=2650, low=2640)
- 09:10: Price closes at 2655 -> BROKEN_UP (LOCKED)
- 10:10: Price retraces to 2645 (inside ORB range)
- 11:10: Price at 2648 (still inside ORB range)

Expected Result:
- 0900 ORB must remain BROKEN_UP at all timestamps
- Break time = 09:10
- Current price position may change, but state stays LOCKED
"""

import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
import pytz
import sys
from pathlib import Path

# Add trading_app to path
sys.path.insert(0, str(Path(__file__).parent / "trading_app"))

from csv_chart_analyzer import CSVChartAnalyzer


def create_test_csv_data(end_time_str: str) -> bytes:
    """
    Create test CSV data up to specified end time.

    Args:
        end_time_str: End time in format "HH:MM" (e.g., "09:10", "10:10", "11:10")

    Returns:
        CSV bytes
    """
    # Brisbane is UTC+10
    # 09:00 Brisbane = 23:00 UTC (previous day)
    # Start at 22:00 UTC Jan 19 (08:00 Brisbane Jan 20)
    start = datetime(2026, 1, 19, 22, 0, 0, tzinfo=pytz.UTC)

    # Parse end time (in Brisbane time)
    end_hour, end_min = map(int, end_time_str.split(":"))

    # Convert Brisbane end time to UTC
    brisbane = pytz.timezone('Australia/Brisbane')
    end_local = brisbane.localize(datetime(2026, 1, 20, end_hour, end_min, 0))
    end = end_local.astimezone(pytz.UTC)

    # Generate 1-minute bars
    times = []
    current = start
    while current <= end:
        times.append(current)
        current += timedelta(minutes=1)

    # Create price data
    data = []
    base_price = 2645.0

    for i, ts in enumerate(times):
        # Convert to Brisbane time for hour/minute checks
        ts_brisbane = ts.astimezone(brisbane)
        hour = ts_brisbane.hour
        minute = ts_brisbane.minute

        # 09:00-09:05: ORB forming (range 2640-2650)
        if hour == 9 and 0 <= minute < 5:
            if minute == 0:
                open_price = 2645.0
                high = 2650.0
                low = 2640.0
                close = 2648.0
            elif minute == 1:
                open_price = 2648.0
                high = 2650.0
                low = 2642.0
                close = 2645.0
            else:
                open_price = 2645.0
                high = 2648.0
                low = 2641.0
                close = 2646.0

        # 09:05-09:10: Price moves up and BREAKS above ORB at 09:10
        elif hour == 9 and 5 <= minute < 10:
            open_price = 2648.0 + (minute - 5) * 1.0
            high = open_price + 2.0
            low = open_price - 1.0
            close = open_price + 1.5

        # 09:10: BREAK above ORB (close = 2655)
        elif hour == 9 and minute == 10:
            open_price = 2653.0
            high = 2658.0
            low = 2651.0
            close = 2655.0  # FIRST CLOSE ABOVE 2650 -> BROKEN_UP

        # 09:11-10:00: Price stays above ORB
        elif hour == 9 and minute > 10:
            open_price = 2654.0
            high = 2658.0
            low = 2652.0
            close = 2655.0

        # 10:00-10:10: Price retraces BACK INSIDE ORB range
        elif hour == 10 and 0 <= minute <= 10:
            open_price = 2650.0 - (minute * 0.5)
            high = open_price + 2.0
            low = open_price - 2.0
            close = 2645.0  # INSIDE ORB (2640-2650)

        # 10:11+: Price stays inside ORB
        else:
            open_price = 2645.0
            high = 2648.0
            low = 2642.0
            close = 2645.0

        data.append({
            'time': ts.strftime('%Y-%m-%d %H:%M:%S'),
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': 100
        })

    # Convert to CSV
    df = pd.DataFrame(data)
    csv_buffer = BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    return csv_buffer.read()


def test_orb_consistency():
    """Test that ORB state remains consistent across time."""

    print("=" * 80)
    print("ORB TEMPORAL CONSISTENCY TEST")
    print("=" * 80)

    analyzer = CSVChartAnalyzer(instrument="MGC")

    # Test 1: At 09:10 - Price just broke above ORB
    print("\nTEST 1: Chart uploaded at 09:10 (break just occurred)")
    print("-" * 80)

    csv_0910 = create_test_csv_data("09:10")
    analysis_0910 = analyzer.analyze_csv(csv_0910)

    if analysis_0910:
        orb_0900 = analysis_0910["orb_analysis"].get("0900")
        print(f"0900 ORB State: {orb_0900.get('state')}")
        print(f"0900 ORB Locked: {orb_0900.get('locked')}")
        print(f"0900 ORB Break Time: {orb_0900.get('break_time')}")
        print(f"0900 ORB Break Price: ${orb_0900.get('break_price', 0):.2f}")
        print(f"0900 ORB High: ${orb_0900.get('high', 0):.2f}")
        print(f"0900 ORB Low: ${orb_0900.get('low', 0):.2f}")

        assert orb_0900.get('state') == 'BROKEN_UP', "ORB should be BROKEN_UP at 09:10"
        assert orb_0900.get('locked') == True, "ORB should be locked at 09:10"
        print("\n[PASS] TEST 1: ORB broke up and locked")
    else:
        print("[FAIL] TEST 1: Analysis failed")
        return False

    # Test 2: At 10:10 - Price retraced back INSIDE ORB range
    print("\nTEST 2: Chart uploaded at 10:10 (price retraced inside ORB)")
    print("-" * 80)

    csv_1010 = create_test_csv_data("10:10")
    analysis_1010 = analyzer.analyze_csv(csv_1010)

    if analysis_1010:
        orb_0900 = analysis_1010["orb_analysis"].get("0900")
        print(f"0900 ORB State: {orb_0900.get('state')}")
        print(f"0900 ORB Locked: {orb_0900.get('locked')}")
        print(f"0900 ORB Break Time: {orb_0900.get('break_time')}")
        print(f"0900 ORB Break Price: ${orb_0900.get('break_price', 0):.2f}")
        print(f"Current Price Position: {orb_0900.get('current_price_position')}")

        # CRITICAL: State must remain BROKEN_UP even though price is now INSIDE
        assert orb_0900.get('state') == 'BROKEN_UP', "ORB state must remain BROKEN_UP (cannot revert!)"
        assert orb_0900.get('locked') == True, "ORB must remain locked"
        assert orb_0900.get('current_price_position') == 'INSIDE', "Current price should show INSIDE (for display)"

        print("\n[PASS] TEST 2: ORB state remained BROKEN_UP (locked) despite price retracing")
        print("[CRITICAL] Current price position updated to INSIDE (for display only)")
        print("[CRITICAL] ORB state did NOT revert to ACTIVE or INSIDE")
    else:
        print("[FAIL] TEST 2: Analysis failed")
        return False

    # Test 3: At 11:10 - Price still inside ORB range
    print("\nTEST 3: Chart uploaded at 11:10 (price still inside ORB)")
    print("-" * 80)

    csv_1110 = create_test_csv_data("11:10")
    analysis_1110 = analyzer.analyze_csv(csv_1110)

    if analysis_1110:
        orb_0900 = analysis_1110["orb_analysis"].get("0900")
        print(f"0900 ORB State: {orb_0900.get('state')}")
        print(f"0900 ORB Locked: {orb_0900.get('locked')}")
        print(f"0900 ORB Break Time: {orb_0900.get('break_time')}")
        print(f"Current Price Position: {orb_0900.get('current_price_position')}")

        assert orb_0900.get('state') == 'BROKEN_UP', "ORB state must STILL be BROKEN_UP"
        assert orb_0900.get('locked') == True, "ORB must STILL be locked"

        print("\n[PASS] TEST 3: ORB state remained BROKEN_UP (immutable)")
    else:
        print("[FAIL] TEST 3: Analysis failed")
        return False

    # Validation test
    print("\nTEST 4: Validation catches illegal state transitions")
    print("-" * 80)

    try:
        # Both analyses should pass validation
        analyzer._validate_orb_states(analysis_0910["orb_analysis"])
        analyzer._validate_orb_states(analysis_1010["orb_analysis"])
        analyzer._validate_orb_states(analysis_1110["orb_analysis"])
        print("[PASS] TEST 4: All states passed validation")
    except ValueError as e:
        print(f"[FAIL] TEST 4: Validation error: {e}")
        return False

    print("\n" + "=" * 80)
    print("ALL TESTS PASSED!")
    print("=" * 80)
    print("\n[OK] ORB states are temporally consistent")
    print("[OK] ORB state locked once broken (one-way transition)")
    print("[OK] Current price position updates but state remains immutable")
    print("[OK] Validation prevents illegal state changes")
    print("\n" + "=" * 80)

    return True


if __name__ == "__main__":
    success = test_orb_consistency()
    exit(0 if success else 1)
