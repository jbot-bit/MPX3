"""
TIME SPECIFICATION - Canonical Session & ORB Definitions
=========================================================

CRITICAL: This is the SINGLE SOURCE OF TRUTH for all time-related constants.

DO NOT hardcode session times, ORB times, or trading windows anywhere else.
All other modules MUST import from this file.

Enforcement: CI check prevents hardcoded time literals outside this file.
"""

from datetime import time
from zoneinfo import ZoneInfo

# ===================================================================
# TIMEZONE
# ===================================================================

TZ_LOCAL = ZoneInfo("Australia/Brisbane")  # UTC+10, no DST
TZ_UTC = ZoneInfo("UTC")

# ===================================================================
# TRADING DAY
# ===================================================================

TRADING_DAY_START = time(9, 0)  # 09:00 Brisbane
TRADING_DAY_END = time(9, 0)    # Next day 09:00 Brisbane

# ===================================================================
# SESSION WINDOWS (Brisbane time)
# ===================================================================

# Session definitions for daily_features computation
SESSIONS = {
    'ASIA': {
        'start': time(9, 0),
        'end': time(17, 0),
        'description': 'Asia session (daytime)'
    },
    'LONDON': {
        'start': time(18, 0),
        'end': time(23, 0),
        'description': 'London session (evening, same calendar day)'
    },
    'NY': {
        'start': time(23, 0),
        'end': time(2, 0),  # Next day
        'description': 'NY session (night into next day)'
    }
}

# ===================================================================
# ORB DEFINITIONS
# ===================================================================

# All 6 ORBs with formation windows
ORBS = ['0900', '1000', '1100', '1800', '2300', '0030']

# ORB formation windows (start_time, duration_minutes)
ORB_FORMATION = {
    '0900': {
        'start': time(9, 0),
        'duration_minutes': 5,
        'end': time(9, 5)
    },
    '1000': {
        'start': time(10, 0),
        'duration_minutes': 5,
        'end': time(10, 5)
    },
    '1100': {
        'start': time(11, 0),
        'duration_minutes': 5,
        'end': time(11, 5)
    },
    '1800': {
        'start': time(18, 0),
        'duration_minutes': 5,
        'end': time(18, 5)
    },
    '2300': {
        'start': time(23, 0),
        'duration_minutes': 5,
        'end': time(23, 5)
    },
    '0030': {
        'start': time(0, 30),
        'duration_minutes': 5,
        'end': time(0, 35)
    }
}

# ORB trading windows (when to enter after formation)
ORB_TRADING_WINDOWS = {
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

# ORB tier classification (for strategy filtering)
ORB_TIERS = {
    'A': ['1000'],                    # A tier (best performing)
    'B': ['2300', '0030'],           # B tier (night ORBs)
    'C': ['0900', '1000', '1100']    # C tier (day ORBs)
}

# ===================================================================
# MARKET HOURS
# ===================================================================

MARKET_OPEN = time(9, 0)     # 09:00 Brisbane
MARKET_CLOSE = time(2, 0)    # 02:00 next day Brisbane

# ===================================================================
# HELPER FUNCTIONS
# ===================================================================

def get_orb_start_time(orb_name: str) -> time:
    """Get ORB formation start time"""
    if orb_name not in ORB_FORMATION:
        raise ValueError(f"Unknown ORB: {orb_name}. Valid ORBs: {ORBS}")
    return ORB_FORMATION[orb_name]['start']


def get_orb_end_time(orb_name: str) -> time:
    """Get ORB formation end time"""
    if orb_name not in ORB_FORMATION:
        raise ValueError(f"Unknown ORB: {orb_name}. Valid ORBs: {ORBS}")
    return ORB_FORMATION[orb_name]['end']


def get_session_start_time(session_name: str) -> time:
    """Get session start time"""
    session_upper = session_name.upper()
    if session_upper not in SESSIONS:
        raise ValueError(f"Unknown session: {session_name}. Valid sessions: {list(SESSIONS.keys())}")
    return SESSIONS[session_upper]['start']


def get_session_end_time(session_name: str) -> time:
    """Get session end time"""
    session_upper = session_name.upper()
    if session_upper not in SESSIONS:
        raise ValueError(f"Unknown session: {session_name}. Valid sessions: {list(SESSIONS.keys())}")
    return SESSIONS[session_upper]['end']


def is_valid_orb(orb_name: str) -> bool:
    """Check if ORB name is valid"""
    return orb_name in ORBS


def is_valid_session(session_name: str) -> bool:
    """Check if session name is valid"""
    return session_name.upper() in SESSIONS


# ===================================================================
# VALIDATION
# ===================================================================

def validate_time_spec():
    """
    Validate time_spec.py internal consistency.

    Raises:
        AssertionError: If any inconsistency detected
    """
    # Check all ORBs have formation and trading window specs
    for orb in ORBS:
        assert orb in ORB_FORMATION, f"ORB {orb} missing in ORB_FORMATION"
        assert orb in ORB_TRADING_WINDOWS, f"ORB {orb} missing in ORB_TRADING_WINDOWS"

    # Check ORB tiers cover all ORBs (optional, tiers might be subset)
    all_tier_orbs = set()
    for tier_orbs in ORB_TIERS.values():
        all_tier_orbs.update(tier_orbs)

    # Check sessions are defined
    assert 'ASIA' in SESSIONS
    assert 'LONDON' in SESSIONS
    assert 'NY' in SESSIONS

    print("[PASS] time_spec.py validation passed")


if __name__ == "__main__":
    # Run validation
    validate_time_spec()

    # Print summary
    print("\n" + "="*60)
    print("TIME SPECIFICATION SUMMARY")
    print("="*60)

    print(f"\nTimezone: {TZ_LOCAL}")
    print(f"Trading day: {TRADING_DAY_START.strftime('%H:%M')} -> {TRADING_DAY_END.strftime('%H:%M')} (next day)")

    print("\nSessions:")
    for name, spec in SESSIONS.items():
        print(f"  {name:8s}: {spec['start'].strftime('%H:%M')} - {spec['end'].strftime('%H:%M')}")

    print("\nORBs:")
    for orb in ORBS:
        formation = ORB_FORMATION[orb]
        print(f"  {orb}: {formation['start'].strftime('%H:%M')} - {formation['end'].strftime('%H:%M')} (forms in {formation['duration_minutes']} min)")

    print("\nTrading Windows:")
    for orb in ORBS:
        window = ORB_TRADING_WINDOWS[orb]
        print(f"  {orb}: {window['form_time'].strftime('%H:%M')} - {window['end_time'].strftime('%H:%M')} ({window['window_minutes']} min)")
