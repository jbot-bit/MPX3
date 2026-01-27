"""
SESSION TIMING HELPER
=====================

Explains session timing and L4_CONSOLIDATION filter logic to users.
Critical for understanding when to trade L4-dependent setups.
"""

import duckdb
from datetime import datetime, timedelta
import pytz
from config import DB_PATH, TZ_LOCAL


def get_l4_status_for_trading(instrument='MGC'):
    """
    Check if L4_CONSOLIDATION filter is met for TODAY'S trading.

    Returns:
        dict with keys:
            - 'l4_met': bool (True if yesterday was L4_CONSOLIDATION)
            - 'check_date': str (which date was checked)
            - 'explanation': str (what this means)
            - 'tradable_setups': list (which setups are tradable today)
    """
    tz = pytz.timezone(TZ_LOCAL)
    now = datetime.now(tz)

    # Current trading day started at 09:00 today
    # We check YESTERDAY'S completed sessions
    yesterday = (now - timedelta(days=1)).date()

    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
        result = conn.execute("""
            SELECT london_type_code,
                   asia_high, asia_low,
                   london_high, london_low
            FROM daily_features
            WHERE instrument = ?
              AND date_local = ?
        """, [instrument, str(yesterday)]).fetchone()
        conn.close()

        if not result:
            return {
                'l4_met': False,
                'check_date': str(yesterday),
                'explanation': f"No data for {yesterday}. Cannot determine L4 status.",
                'tradable_setups': []
            }

        london_type, asia_h, asia_l, london_h, london_l = result
        l4_met = (london_type == 'L4_CONSOLIDATION')

        if l4_met:
            explanation = f"✅ {yesterday} was L4_CONSOLIDATION (London {london_l:.1f}-{london_h:.1f} stayed inside Asia {asia_l:.1f}-{asia_h:.1f})"
            tradable_setups = ['0900 ORB', '1000 ORB'] if instrument == 'MGC' else []
        else:
            explanation = f"❌ {yesterday} was NOT L4_CONSOLIDATION (london_type={london_type})"
            tradable_setups = []

        return {
            'l4_met': l4_met,
            'check_date': str(yesterday),
            'explanation': explanation,
            'tradable_setups': tradable_setups
        }

    except Exception as e:
        return {
            'l4_met': False,
            'check_date': str(yesterday),
            'explanation': f"Error checking L4 status: {e}",
            'tradable_setups': []
        }


def get_session_timing_explanation():
    """
    Return a markdown-formatted explanation of session timing.
    Critical for users to understand L4_CONSOLIDATION filter timing.
    """
    return """
### 🕐 Session Timing Explained

**Trading Day Definition:** 09:00 Brisbane → next day 09:00 Brisbane

**Session Windows (Brisbane time):**
- **Asia**: 09:00-17:00 (daytime)
- **London**: 18:00-23:00 (evening, same calendar day)
- **NY**: 23:00-02:00 (night into next day)

**L4_CONSOLIDATION Filter:**
- Definition: London session stayed INSIDE Asia session range
- Check: `london_high <= asia_high AND london_low >= asia_low`

**CRITICAL: When checking L4 for today's trades:**
- At 10:00am Monday, you check **SUNDAY's** sessions
- At 11:00am Monday, you check **SUNDAY's** sessions
- At 18:00pm Monday, you check **SUNDAY's** sessions

**Why?** Because Monday's trading day (09:00 Mon → 09:00 Tue) is still IN PROGRESS.
Monday's London session won't happen until 18:00-23:00 tonight.

**Example:**
```
SUNDAY:
  09:00-17:00 → Asia session (day)
  18:00-23:00 → London session (evening)
  [Did London stay inside Asia? YES/NO]

MONDAY:
  09:00 → Trading day starts
  10:00 → Check Sunday's L4 status
    If YES → Trade 1000 ORB setups
    If NO → Skip 1000 ORB
  18:00-23:00 → Today's London session happens

TUESDAY:
  09:00 → Check Monday's L4 status
    (using data from Mon 09:00-17:00 Asia, Mon 18:00-23:00 London)
```

**Key Takeaway:** L4 filter checks YESTERDAY's completed sessions, not today's.
"""


def render_session_timing_panel():
    """
    Streamlit component to display session timing explanation.
    Call this in the app sidebar or main tabs.
    """
    import streamlit as st

    st.markdown("---")
    st.markdown("### 📚 Session Timing Guide")

    # Get L4 status
    l4_status = get_l4_status_for_trading()

    if l4_status['l4_met']:
        st.success(l4_status['explanation'])
        if l4_status['tradable_setups']:
            st.info(f"**Tradable today:** {', '.join(l4_status['tradable_setups'])}")
    else:
        st.warning(l4_status['explanation'])
        st.error("**L4-dependent setups NOT tradable today** (skip 0900/1000 ORB)")

    # Expandable explanation
    with st.expander("🕐 How Session Timing Works"):
        st.markdown(get_session_timing_explanation())


def get_filter_status_summary(instrument='MGC'):
    """
    Return a compact summary of filter status for today's trading.

    Returns:
        dict with keys:
            - 'l4': bool
            - 'summary_text': str
    """
    l4_status = get_l4_status_for_trading(instrument)

    if l4_status['l4_met']:
        summary = f"✅ L4 MET ({l4_status['check_date']}) - 0900/1000 ORB tradable"
    else:
        summary = f"❌ L4 NOT MET ({l4_status['check_date']}) - Skip 0900/1000 ORB"

    return {
        'l4': l4_status['l4_met'],
        'summary_text': summary
    }
