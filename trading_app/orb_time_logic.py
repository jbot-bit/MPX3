"""
ORB Time Logic - Determines Current/Upcoming ORB for Trading

Answers: "What should I trade RIGHT NOW?"

Used by Production tab hero display to show time-aware setup recommendations.
"""

from datetime import datetime, time, timedelta
from typing import Dict, Optional, Tuple
from zoneinfo import ZoneInfo

TZ_BRISBANE = ZoneInfo("Australia/Brisbane")

# ORB Schedule with trading windows
ORB_SCHEDULE = {
    '0900': {
        'form_time': time(9, 5),   # ORB forms at 09:05
        'end_time': time(9, 50),   # Stop trading at 09:50 (10 min before next ORB)
        'window_minutes': 45
    },
    '1000': {
        'form_time': time(10, 5),
        'end_time': time(10, 50),
        'window_minutes': 45
    },
    '1100': {
        'form_time': time(11, 5),
        'end_time': time(17, 50),  # Long window until 1800 ORB
        'window_minutes': 405  # 6h 45m
    },
    '1800': {
        'form_time': time(18, 5),
        'end_time': time(22, 50),
        'window_minutes': 285  # 4h 45m
    },
    '2300': {
        'form_time': time(23, 5),
        'end_time': time(0, 20),   # Next day
        'window_minutes': 75  # 1h 15m
    },
    '0030': {
        'form_time': time(0, 35),
        'end_time': time(8, 50),
        'window_minutes': 495  # 8h 15m
    }
}


def get_current_orb_status(now: Optional[datetime] = None) -> Dict:
    """
    Determine current ORB status based on Brisbane time

    Returns:
        Dict with:
        - current_orb: ORB name if within trading window, else None
        - upcoming_orb: Next ORB name in schedule
        - status: 'ACTIVE' | 'UPCOMING' | 'STANDBY'
        - minutes_remaining: Minutes until window expires (if ACTIVE)
        - minutes_until: Minutes until upcoming ORB forms (if UPCOMING)
    """
    if now is None:
        now = datetime.now(TZ_BRISBANE)
    else:
        now = now.astimezone(TZ_BRISBANE)

    current_time = now.time()
    current_date = now.date()

    # Check if we're within a trading window
    for orb_name, schedule in ORB_SCHEDULE.items():
        form_time = schedule['form_time']
        end_time = schedule['end_time']

        # Handle overnight ORBs (2300, 0030)
        if form_time > end_time:
            # ORB spans midnight
            if current_time >= form_time or current_time < end_time:
                # We're in the window
                if current_time >= form_time:
                    # Same day, after form time
                    form_dt = datetime.combine(current_date, form_time, TZ_BRISBANE)
                    end_dt = datetime.combine(current_date + timedelta(days=1), end_time, TZ_BRISBANE)
                else:
                    # Next day, before end time
                    form_dt = datetime.combine(current_date - timedelta(days=1), form_time, TZ_BRISBANE)
                    end_dt = datetime.combine(current_date, end_time, TZ_BRISBANE)

                if now < end_dt:
                    minutes_remaining = int((end_dt - now).total_seconds() / 60)
                    return {
                        'current_orb': orb_name,
                        'upcoming_orb': _get_next_orb(orb_name),
                        'status': 'ACTIVE',
                        'minutes_remaining': minutes_remaining,
                        'minutes_until': None,
                        'form_time': form_dt,
                        'end_time': end_dt
                    }
        else:
            # Normal ORB (same day)
            if form_time <= current_time < end_time:
                form_dt = datetime.combine(current_date, form_time, TZ_BRISBANE)
                end_dt = datetime.combine(current_date, end_time, TZ_BRISBANE)
                minutes_remaining = int((end_dt - now).total_seconds() / 60)

                return {
                    'current_orb': orb_name,
                    'upcoming_orb': _get_next_orb(orb_name),
                    'status': 'ACTIVE',
                    'minutes_remaining': minutes_remaining,
                    'minutes_until': None,
                    'form_time': form_dt,
                    'end_time': end_dt
                }

    # No active window - find next upcoming ORB
    upcoming_orb, minutes_until = _find_next_orb(now)

    return {
        'current_orb': None,
        'upcoming_orb': upcoming_orb,
        'status': 'UPCOMING' if minutes_until < 60 else 'STANDBY',
        'minutes_remaining': None,
        'minutes_until': minutes_until,
        'form_time': None,
        'end_time': None
    }


def _get_next_orb(current_orb: str) -> str:
    """Get next ORB in sequence"""
    sequence = ['0900', '1000', '1100', '1800', '2300', '0030']
    idx = sequence.index(current_orb)
    return sequence[(idx + 1) % len(sequence)]


def _find_next_orb(now: datetime) -> Tuple[str, int]:
    """
    Find next ORB that will form after current time

    Returns:
        (orb_name, minutes_until_forms)
    """
    current_time = now.time()
    current_date = now.date()

    # Build list of (orb_name, form_datetime)
    candidates = []

    for orb_name, schedule in ORB_SCHEDULE.items():
        form_time = schedule['form_time']

        # Try today
        form_dt_today = datetime.combine(current_date, form_time, TZ_BRISBANE)
        if form_dt_today > now:
            candidates.append((orb_name, form_dt_today))

        # Try tomorrow (for overnight ORBs)
        form_dt_tomorrow = datetime.combine(current_date + timedelta(days=1), form_time, TZ_BRISBANE)
        candidates.append((orb_name, form_dt_tomorrow))

    # Sort by time
    candidates.sort(key=lambda x: x[1])

    # Return first future ORB
    if candidates:
        orb_name, form_dt = candidates[0]
        minutes_until = int((form_dt - now).total_seconds() / 60)
        return orb_name, minutes_until

    # Fallback (shouldn't happen)
    return '0900', 0


def format_time_remaining(minutes: int) -> str:
    """
    Format minutes into human-readable string

    Examples:
    - 15 → "15 min"
    - 90 → "1h 30m"
    - 420 → "7h"
    """
    if minutes < 60:
        return f"{minutes} min"
    else:
        hours = minutes // 60
        mins = minutes % 60
        if mins == 0:
            return f"{hours}h"
        else:
            return f"{hours}h {mins}m"


def get_status_emoji(status: str) -> str:
    """Get emoji for ORB status"""
    return {
        'ACTIVE': '🟢',
        'UPCOMING': '🟡',
        'STANDBY': '⏸️'
    }.get(status, '⏸️')


def get_status_color(status: str) -> str:
    """Get color for ORB status"""
    return {
        'ACTIVE': '#198754',    # Green
        'UPCOMING': '#ffc107',  # Yellow
        'STANDBY': '#6c757d'    # Gray
    }.get(status, '#6c757d')


if __name__ == "__main__":
    # Test at different times
    test_times = [
        time(10, 30),  # 10:30 AM - should be ACTIVE (1000 ORB)
        time(10, 55),  # 10:55 AM - should be UPCOMING (1100 ORB)
        time(11, 10),  # 11:10 AM - should be ACTIVE (1100 ORB)
        time(9, 0),    # 09:00 AM - should be UPCOMING (0900 ORB, forms in 5 min)
        time(23, 10),  # 23:10 PM - should be ACTIVE (2300 ORB)
        time(0, 40),   # 00:40 AM - should be ACTIVE (0030 ORB)
    ]

    for test_time in test_times:
        now = datetime.combine(datetime.now().date(), test_time, TZ_BRISBANE)
        status = get_current_orb_status(now)

        print(f"\n{test_time.strftime('%H:%M')} - {status['status']}")
        if status['current_orb']:
            print(f"  Current: {status['current_orb']} ({format_time_remaining(status['minutes_remaining'])} remaining)")
        if status['upcoming_orb']:
            mins_until = status.get('minutes_until')
            if mins_until is not None:
                print(f"  Next: {status['upcoming_orb']} (in {format_time_remaining(mins_until)})")
            else:
                print(f"  Next: {status['upcoming_orb']}")
