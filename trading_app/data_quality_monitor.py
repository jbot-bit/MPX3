"""
DATA QUALITY MONITORING - Critical safety system
Prevents trading on stale, bad, or missing data.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from zoneinfo import ZoneInfo
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class DataStatus:
    """Data feed status constants"""
    LIVE = "LIVE"           # Data fresh (< 10 seconds)
    DELAYED = "DELAYED"     # Data slow (10-60 seconds)
    STALE = "STALE"         # Data old (> 60 seconds)
    DEAD = "DEAD"           # No data (> 5 minutes)
    UNKNOWN = "UNKNOWN"     # Never received data


@dataclass
class DataQualityMetrics:
    """Data quality metrics for an instrument"""
    instrument: str
    last_update: Optional[datetime]
    status: str
    seconds_since_update: Optional[float]
    total_bars_today: int
    gaps_detected: int
    last_gap_time: Optional[datetime]
    avg_update_interval: Optional[float]

    def is_healthy(self) -> bool:
        """Check if data feed is healthy"""
        return self.status in [DataStatus.LIVE, DataStatus.DELAYED]

    def get_color(self) -> str:
        """Get color for status indicator"""
        colors = {
            DataStatus.LIVE: "green",
            DataStatus.DELAYED: "yellow",
            DataStatus.STALE: "orange",
            DataStatus.DEAD: "red",
            DataStatus.UNKNOWN: "gray"
        }
        return colors.get(self.status, "gray")

    def get_emoji(self) -> str:
        """Get emoji for status indicator"""
        emojis = {
            DataStatus.LIVE: "[LIVE]",
            DataStatus.DELAYED: "[DELAYED]",
            DataStatus.STALE: "[STALE]",
            DataStatus.DEAD: "[DEAD]",
            DataStatus.UNKNOWN: "[UNKNOWN]"
        }
        return emojis.get(self.status, "[?]")


class DataQualityMonitor:
    """
    Monitor data quality and detect issues.

    Critical safety system that prevents trading on bad data.
    """

    def __init__(self, timezone: ZoneInfo = ZoneInfo("Australia/Brisbane")):
        self.tz = timezone
        self.last_bars = {}  # Track last bar per instrument
        self.bar_history = {}  # Track recent bars for gap detection
        self.alerts_triggered = []

        # Thresholds (seconds)
        self.LIVE_THRESHOLD = 10
        self.DELAYED_THRESHOLD = 60
        self.STALE_THRESHOLD = 300  # 5 minutes

        # Gap detection
        self.EXPECTED_BAR_INTERVAL = 60  # 1 minute
        self.GAP_TOLERANCE = 120  # 2 minutes = gap

    def update_bar(self, instrument: str, timestamp: datetime, bar_data: dict):
        """
        Record a new bar received.

        Args:
            instrument: Instrument symbol
            timestamp: Bar timestamp
            bar_data: Bar OHLCV data
        """
        now = datetime.now(self.tz)

        # Store last bar
        self.last_bars[instrument] = {
            'timestamp': timestamp,
            'received_at': now,
            'data': bar_data
        }

        # Add to history for gap detection
        if instrument not in self.bar_history:
            self.bar_history[instrument] = []

        self.bar_history[instrument].append({
            'timestamp': timestamp,
            'received_at': now
        })

        # Keep only last 100 bars
        if len(self.bar_history[instrument]) > 100:
            self.bar_history[instrument] = self.bar_history[instrument][-100:]

        logger.debug(f"Data update: {instrument} at {timestamp}")

    def get_status(self, instrument: str) -> DataQualityMetrics:
        """
        Get current data quality status for instrument.

        Args:
            instrument: Instrument symbol

        Returns:
            DataQualityMetrics object
        """
        now = datetime.now(self.tz)

        if instrument not in self.last_bars:
            return DataQualityMetrics(
                instrument=instrument,
                last_update=None,
                status=DataStatus.UNKNOWN,
                seconds_since_update=None,
                total_bars_today=0,
                gaps_detected=0,
                last_gap_time=None,
                avg_update_interval=None
            )

        last_bar = self.last_bars[instrument]
        received_at = last_bar['received_at']
        seconds_since = (now - received_at).total_seconds()

        # Determine status
        if seconds_since < self.LIVE_THRESHOLD:
            status = DataStatus.LIVE
        elif seconds_since < self.DELAYED_THRESHOLD:
            status = DataStatus.DELAYED
        elif seconds_since < self.STALE_THRESHOLD:
            status = DataStatus.STALE
        else:
            status = DataStatus.DEAD

        # Count bars today
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        bars_today = sum(1 for bar in self.bar_history.get(instrument, [])
                        if bar['timestamp'] >= today_start)

        # Detect gaps
        gaps, last_gap = self._detect_gaps(instrument)

        # Calculate average update interval
        avg_interval = self._calculate_avg_interval(instrument)

        return DataQualityMetrics(
            instrument=instrument,
            last_update=received_at,
            status=status,
            seconds_since_update=seconds_since,
            total_bars_today=bars_today,
            gaps_detected=gaps,
            last_gap_time=last_gap,
            avg_update_interval=avg_interval
        )

    def _detect_gaps(self, instrument: str) -> Tuple[int, Optional[datetime]]:
        """
        Detect gaps in data (missing bars).

        Returns:
            Tuple of (gap_count, last_gap_time)
        """
        if instrument not in self.bar_history:
            return 0, None

        history = self.bar_history[instrument]
        if len(history) < 2:
            return 0, None

        gaps = 0
        last_gap = None

        for i in range(1, len(history)):
            prev_bar = history[i-1]
            curr_bar = history[i]

            time_diff = (curr_bar['timestamp'] - prev_bar['timestamp']).total_seconds()

            if time_diff > self.GAP_TOLERANCE:
                gaps += 1
                last_gap = curr_bar['timestamp']

        return gaps, last_gap

    def _calculate_avg_interval(self, instrument: str) -> Optional[float]:
        """Calculate average time between bars"""
        if instrument not in self.bar_history:
            return None

        history = self.bar_history[instrument]
        if len(history) < 2:
            return None

        intervals = []
        for i in range(1, min(len(history), 20)):  # Last 20 bars
            prev_bar = history[-(i+1)]
            curr_bar = history[-i]
            interval = (curr_bar['timestamp'] - prev_bar['timestamp']).total_seconds()
            if interval < self.GAP_TOLERANCE:  # Exclude gaps
                intervals.append(interval)

        if not intervals:
            return None

        return sum(intervals) / len(intervals)

    def check_all_instruments(self, instruments: List[str]) -> Dict[str, DataQualityMetrics]:
        """
        Check data quality for all instruments.

        Args:
            instruments: List of instrument symbols

        Returns:
            Dict of instrument -> metrics
        """
        results = {}
        for instrument in instruments:
            results[instrument] = self.get_status(instrument)
        return results

    def is_safe_to_trade(self, instrument: str) -> Tuple[bool, str]:
        """
        Check if it's safe to trade this instrument.

        Args:
            instrument: Instrument symbol

        Returns:
            Tuple of (is_safe, reason)
        """
        metrics = self.get_status(instrument)

        if metrics.status == DataStatus.UNKNOWN:
            return False, "No data received yet"

        if metrics.status == DataStatus.DEAD:
            return False, f"Data feed dead ({metrics.seconds_since_update:.0f}s since update)"

        if metrics.status == DataStatus.STALE:
            return False, f"Data stale ({metrics.seconds_since_update:.0f}s old)"

        if metrics.gaps_detected > 5:
            return False, f"Too many data gaps ({metrics.gaps_detected} detected)"

        return True, "Data quality OK"

    def get_warning_message(self, instrument: str) -> Optional[str]:
        """
        Get warning message if data quality is poor.

        Returns:
            Warning message or None if OK
        """
        metrics = self.get_status(instrument)

        if metrics.status == DataStatus.DEAD:
            return f"[CRITICAL] {instrument} data feed DEAD - NO TRADING"

        if metrics.status == DataStatus.STALE:
            return f"[WARNING] {instrument} data STALE - Check connection"

        if metrics.status == DataStatus.DELAYED:
            return f"[CAUTION] {instrument} data delayed by {metrics.seconds_since_update:.0f}s"

        if metrics.gaps_detected > 3:
            return f"[WARNING] {instrument} has {metrics.gaps_detected} data gaps"

        return None

    def trigger_alert(self, instrument: str, alert_type: str, message: str):
        """Record an alert"""
        alert = {
            'instrument': instrument,
            'type': alert_type,
            'message': message,
            'timestamp': datetime.now(self.tz)
        }
        self.alerts_triggered.append(alert)
        logger.warning(f"Data quality alert: {message}")

    def get_recent_alerts(self, minutes: int = 15) -> List[dict]:
        """Get alerts from last N minutes"""
        cutoff = datetime.now(self.tz) - timedelta(minutes=minutes)
        return [a for a in self.alerts_triggered if a['timestamp'] > cutoff]


# ============================================================================
# STREAMLIT UI COMPONENTS
# ============================================================================

def render_data_quality_indicator(metrics: DataQualityMetrics) -> str:
    """
    Render data quality indicator HTML.

    Returns:
        HTML string with styled indicator
    """
    color = metrics.get_color()
    status = metrics.get_emoji()

    # Color mapping for background
    bg_colors = {
        "green": "#d1e7dd",
        "yellow": "#fff3cd",
        "orange": "#ffe5d0",
        "red": "#f8d7da",
        "gray": "#e2e3e5"
    }

    bg_color = bg_colors.get(color, "#e2e3e5")

    if metrics.last_update:
        time_str = metrics.last_update.strftime("%H:%M:%S")
        age_str = f"{metrics.seconds_since_update:.0f}s ago"
    else:
        time_str = "Never"
        age_str = ""

    html = f"""
    <div style="
        background: {bg_color};
        border-left: 4px solid {color};
        border-radius: 4px;
        padding: 8px 12px;
        margin: 4px 0;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong>{metrics.instrument}</strong>
                <span style="margin-left: 8px; font-weight: bold; color: {color};">
                    {status}
                </span>
            </div>
            <div style="font-size: 12px; color: #666;">
                {time_str} ({age_str})
            </div>
        </div>
        <div style="font-size: 11px; color: #666; margin-top: 4px;">
            Bars today: {metrics.total_bars_today} | Gaps: {metrics.gaps_detected}
        </div>
    </div>
    """

    return html


def render_data_quality_panel(monitor: DataQualityMonitor, instruments: List[str]) -> str:
    """
    Render complete data quality monitoring panel.

    Args:
        monitor: DataQualityMonitor instance
        instruments: List of instruments to monitor

    Returns:
        HTML string with complete panel
    """
    all_metrics = monitor.check_all_instruments(instruments)

    # Check if any critical issues
    critical_issues = [m for m in all_metrics.values()
                      if m.status in [DataStatus.DEAD, DataStatus.STALE]]

    # Build panel HTML
    if critical_issues:
        panel_color = "#dc3545"
        panel_title = "[CRITICAL] DATA QUALITY ISSUES"
    else:
        panel_color = "#198754"
        panel_title = "[OK] Data Quality"

    html = f"""
    <div style="
        border: 2px solid {panel_color};
        border-radius: 8px;
        padding: 12px;
        margin: 12px 0;
        background: white;
    ">
        <div style="
            font-weight: bold;
            color: {panel_color};
            margin-bottom: 8px;
            font-size: 14px;
        ">
            {panel_title}
        </div>
    """

    # Add each instrument status
    for instrument in instruments:
        metrics = all_metrics[instrument]
        html += render_data_quality_indicator(metrics)

    # Add warnings if any
    warnings = [monitor.get_warning_message(inst) for inst in instruments]
    warnings = [w for w in warnings if w]

    if warnings:
        html += """
        <div style="
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 8px 12px;
            margin-top: 8px;
            border-radius: 4px;
        ">
            <strong>Warnings:</strong><br>
        """
        for warning in warnings:
            html += f"<div style='margin: 4px 0;'>{warning}</div>"
        html += "</div>"

    html += "</div>"

    return html
