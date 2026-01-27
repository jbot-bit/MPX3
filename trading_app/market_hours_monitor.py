"""
MARKET HOURS & LIQUIDITY MONITORING
Prevents trading during thin liquidity periods.
"""

from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class LiquidityLevel:
    """Liquidity level constants"""
    EXCELLENT = "EXCELLENT"  # Major session, high volume
    GOOD = "GOOD"           # Active session, normal volume
    THIN = "THIN"           # Transition period, low volume
    VERY_THIN = "VERY_THIN" # Outside hours, very low volume
    CLOSED = "CLOSED"       # Weekend or holiday


class SessionType:
    """Trading session types"""
    ASIA = "ASIA"
    LONDON = "LONDON"
    NY = "NY"
    TRANSITION = "TRANSITION"
    CLOSED = "CLOSED"


@dataclass
class MarketConditions:
    """Current market conditions"""
    instrument: str
    current_session: str
    liquidity_level: str
    is_holiday: bool
    is_weekend: bool
    next_session: str
    time_to_next_session: Optional[timedelta]
    spread_warning: bool
    volume_vs_average: Optional[float]  # 1.0 = average, 0.5 = half average

    def is_safe_to_trade(self) -> bool:
        """Check if conditions are safe for trading"""
        if self.is_holiday or self.is_weekend:
            return False
        if self.liquidity_level in [LiquidityLevel.VERY_THIN, LiquidityLevel.CLOSED]:
            return False
        if self.spread_warning:
            return False
        return True

    def get_color(self) -> str:
        """Get color for liquidity indicator"""
        colors = {
            LiquidityLevel.EXCELLENT: "green",
            LiquidityLevel.GOOD: "lightgreen",
            LiquidityLevel.THIN: "yellow",
            LiquidityLevel.VERY_THIN: "orange",
            LiquidityLevel.CLOSED: "red"
        }
        return colors.get(self.liquidity_level, "gray")

    def get_status_text(self) -> str:
        """Get status text"""
        if self.is_weekend:
            return "[CLOSED] Weekend"
        if self.is_holiday:
            return "[CLOSED] Holiday"
        if self.liquidity_level == LiquidityLevel.EXCELLENT:
            return f"[LIQUID] {self.current_session}"
        if self.liquidity_level == LiquidityLevel.GOOD:
            return f"[ACTIVE] {self.current_session}"
        if self.liquidity_level == LiquidityLevel.THIN:
            return f"[THIN] {self.current_session}"
        if self.liquidity_level == LiquidityLevel.VERY_THIN:
            return "[VERY THIN] Off Hours"
        return "[CLOSED]"


class MarketHoursMonitor:
    """
    Monitor market hours and liquidity conditions.

    Critical safety system that prevents trading during thin liquidity.
    """

    def __init__(self, timezone: ZoneInfo = ZoneInfo("Australia/Brisbane")):
        self.tz = timezone

        # Session definitions (Brisbane time, UTC+10)
        self.sessions = {
            SessionType.ASIA: {
                'start': time(9, 0),
                'end': time(17, 0),
                'liquidity': LiquidityLevel.GOOD,
                'instruments': ['MGC', 'NQ', 'MPL']
            },
            SessionType.LONDON: {
                'start': time(18, 0),
                'end': time(23, 0),
                'liquidity': LiquidityLevel.EXCELLENT,
                'instruments': ['MGC', 'NQ', 'MPL']
            },
            SessionType.NY: {
                'start': time(23, 0),
                'end': time(2, 0),  # Next day
                'liquidity': LiquidityLevel.EXCELLENT,
                'instruments': ['MGC', 'NQ', 'MPL']
            }
        }

        # Holidays (simplified - expand as needed)
        self.holidays_2026 = [
            datetime(2026, 1, 1),   # New Year
            datetime(2026, 1, 19),  # MLK Day
            datetime(2026, 2, 16),  # Presidents Day
            datetime(2026, 4, 10),  # Good Friday
            datetime(2026, 5, 25),  # Memorial Day
            datetime(2026, 7, 3),   # Independence Day (observed)
            datetime(2026, 9, 7),   # Labor Day
            datetime(2026, 11, 26), # Thanksgiving
            datetime(2026, 12, 25), # Christmas
        ]

        # Volume tracking for comparison
        self.recent_volume = {}

    def get_current_session(self, now: Optional[datetime] = None) -> str:
        """
        Get current trading session.

        Args:
            now: Current time (defaults to now)

        Returns:
            Session name
        """
        if now is None:
            now = datetime.now(self.tz)

        current_time = now.time()

        # Check each session
        for session_name, session_info in self.sessions.items():
            start = session_info['start']
            end = session_info['end']

            # Handle NY session crossing midnight
            if session_name == SessionType.NY:
                if current_time >= start or current_time <= end:
                    return session_name
            else:
                if start <= current_time < end:
                    return session_name

        # Outside all sessions
        return SessionType.TRANSITION

    def get_liquidity_level(self, instrument: str, now: Optional[datetime] = None) -> str:
        """
        Get current liquidity level.

        Args:
            instrument: Instrument symbol
            now: Current time

        Returns:
            Liquidity level
        """
        if now is None:
            now = datetime.now(self.tz)

        # Check if weekend
        if now.weekday() >= 5:  # Saturday=5, Sunday=6
            return LiquidityLevel.CLOSED

        # Check if holiday
        if self.is_holiday(now):
            return LiquidityLevel.CLOSED

        session = self.get_current_session(now)

        if session == SessionType.TRANSITION:
            # Transition periods are thin
            return LiquidityLevel.THIN

        # Get session liquidity
        session_info = self.sessions.get(session, {})
        return session_info.get('liquidity', LiquidityLevel.THIN)

    def is_holiday(self, date: datetime) -> bool:
        """Check if date is a holiday"""
        date_only = date.date()
        return any(h.date() == date_only for h in self.holidays_2026)

    def is_weekend(self, date: datetime) -> bool:
        """Check if date is weekend"""
        return date.weekday() >= 5

    def get_next_session(self, now: Optional[datetime] = None) -> Tuple[str, timedelta]:
        """
        Get next major session and time until it starts.

        Returns:
            Tuple of (session_name, time_delta)
        """
        if now is None:
            now = datetime.now(self.tz)

        current_session = self.get_current_session(now)
        current_time = now.time()

        # Find next session
        next_sessions = []

        for session_name, session_info in self.sessions.items():
            if session_name == SessionType.TRANSITION:
                continue

            start_time = session_info['start']

            # Calculate time to this session
            if session_name == SessionType.NY:
                # NY crosses midnight
                if current_time < start_time:
                    # Today
                    session_dt = now.replace(hour=start_time.hour, minute=start_time.minute,
                                            second=0, microsecond=0)
                else:
                    # Tomorrow
                    session_dt = now.replace(hour=start_time.hour, minute=start_time.minute,
                                            second=0, microsecond=0) + timedelta(days=1)
            else:
                if current_time < start_time:
                    # Today
                    session_dt = now.replace(hour=start_time.hour, minute=start_time.minute,
                                            second=0, microsecond=0)
                else:
                    # Tomorrow
                    session_dt = now.replace(hour=start_time.hour, minute=start_time.minute,
                                            second=0, microsecond=0) + timedelta(days=1)

            time_delta = session_dt - now
            next_sessions.append((session_name, time_delta))

        # Sort by time
        next_sessions.sort(key=lambda x: x[1])

        if next_sessions:
            return next_sessions[0]

        return SessionType.ASIA, timedelta(hours=24)

    def get_market_conditions(self, instrument: str,
                             current_volume: Optional[float] = None) -> MarketConditions:
        """
        Get complete market conditions assessment.

        Args:
            instrument: Instrument symbol
            current_volume: Current bar volume (optional)

        Returns:
            MarketConditions object
        """
        now = datetime.now(self.tz)

        current_session = self.get_current_session(now)
        liquidity = self.get_liquidity_level(instrument, now)
        is_holiday = self.is_holiday(now)
        is_weekend = self.is_weekend(now)
        next_session, time_to_next = self.get_next_session(now)

        # Check spread warning (placeholder - would need real spread data)
        spread_warning = False

        # Calculate volume vs average
        volume_ratio = None
        if current_volume is not None and instrument in self.recent_volume:
            avg_volume = sum(self.recent_volume[instrument]) / len(self.recent_volume[instrument])
            if avg_volume > 0:
                volume_ratio = current_volume / avg_volume

        return MarketConditions(
            instrument=instrument,
            current_session=current_session,
            liquidity_level=liquidity,
            is_holiday=is_holiday,
            is_weekend=is_weekend,
            next_session=next_session,
            time_to_next_session=time_to_next,
            spread_warning=spread_warning,
            volume_vs_average=volume_ratio
        )

    def update_volume(self, instrument: str, volume: float):
        """Update volume tracking"""
        if instrument not in self.recent_volume:
            self.recent_volume[instrument] = []

        self.recent_volume[instrument].append(volume)

        # Keep only last 100 bars
        if len(self.recent_volume[instrument]) > 100:
            self.recent_volume[instrument] = self.recent_volume[instrument][-100:]

    def get_warning_message(self, instrument: str) -> Optional[str]:
        """
        Get warning message if conditions are poor.

        Returns:
            Warning message or None if OK
        """
        conditions = self.get_market_conditions(instrument)

        if conditions.is_weekend:
            return "[CLOSED] Weekend - Markets Closed"

        if conditions.is_holiday:
            return "[CLOSED] Holiday - Markets Closed"

        if conditions.liquidity_level == LiquidityLevel.VERY_THIN:
            hours = conditions.time_to_next_session.total_seconds() / 3600
            return f"[WARNING] Very thin liquidity - {conditions.next_session} opens in {hours:.1f}h"

        if conditions.liquidity_level == LiquidityLevel.THIN:
            return f"[CAUTION] Thin liquidity - Transition period"

        if conditions.spread_warning:
            return "[WARNING] Unusually wide spread detected"

        if conditions.volume_vs_average and conditions.volume_vs_average < 0.5:
            return f"[CAUTION] Low volume ({conditions.volume_vs_average*100:.0f}% of average)"

        return None


# ============================================================================
# STREAMLIT UI COMPONENTS
# ============================================================================

def render_market_hours_indicator(conditions: MarketConditions) -> str:
    """
    Render market hours indicator HTML.

    Returns:
        HTML string with styled indicator
    """
    color = conditions.get_color()
    status = conditions.get_status_text()

    # Color mapping
    bg_colors = {
        "green": "#d1e7dd",
        "lightgreen": "#d1f2eb",
        "yellow": "#fff3cd",
        "orange": "#ffe5d0",
        "red": "#f8d7da"
    }

    bg_color = bg_colors.get(color, "#e2e3e5")

    html = f"""
    <div style="
        background: {bg_color};
        border-left: 4px solid {color};
        border-radius: 4px;
        padding: 12px;
        margin: 8px 0;
    ">
        <div style="font-weight: bold; font-size: 16px; margin-bottom: 8px;">
            {status}
        </div>
        <div style="font-size: 13px; color: #666;">
            Next: {conditions.next_session} in {format_timedelta(conditions.time_to_next_session)}
        </div>
    """

    # Add volume info if available
    if conditions.volume_vs_average is not None:
        volume_pct = conditions.volume_vs_average * 100
        html += f"""
        <div style="font-size: 12px; color: #666; margin-top: 4px;">
            Volume: {volume_pct:.0f}% of average
        </div>
        """

    html += "</div>"

    return html


def format_timedelta(td: Optional[timedelta]) -> str:
    """Format timedelta as human-readable string"""
    if td is None:
        return "Unknown"

    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
