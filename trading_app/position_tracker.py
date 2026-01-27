"""
POSITION TRACKING PANEL
Live monitoring of active positions with P&L, timers, and quick actions.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class PositionAlert:
    """Position-related alert"""
    position_id: str
    alert_type: str  # "BE_REMINDER", "TIME_LIMIT", "STOP_APPROACHING", "TARGET_NEAR"
    message: str
    triggered_at: datetime
    acknowledged: bool = False


class PositionTracker:
    """
    Track and monitor active trading positions.

    Provides live P&L, timers, distance to stop/target, and alerts.
    """

    def __init__(self, timezone: ZoneInfo = ZoneInfo("Australia/Brisbane")):
        self.tz = timezone
        self.position_alerts: List[PositionAlert] = []

        # Alert thresholds
        self.BE_REMINDER_R = 1.0  # Remind to move stop at +1R
        self.STOP_WARNING_POINTS = 2.0  # Alert when within 2 points of stop
        self.TARGET_WARNING_POINTS = 5.0  # Alert when within 5 points of target
        self.MAX_TIME_MINUTES = 90  # Max time for CASCADE/NIGHT_ORB strategies

    def check_position_alerts(self, position: dict, current_price: float,
                              strategy: str = "UNKNOWN") -> List[PositionAlert]:
        """
        Check for position alerts.

        Args:
            position: Position dict with entry, stop, target, entry_time
            current_price: Current market price
            strategy: Strategy name

        Returns:
            List of alerts
        """
        alerts = []
        pos_id = position.get('id', 'unknown')

        # Calculate current P&L in R
        entry = position['entry_price']
        stop = position['stop_price']
        direction = position['direction']

        risk_points = abs(entry - stop)
        if risk_points == 0:
            return alerts

        if direction == "LONG":
            pnl_points = current_price - entry
        else:
            pnl_points = entry - current_price

        pnl_r = pnl_points / risk_points

        # 1. Breakeven reminder at +1R
        if pnl_r >= self.BE_REMINDER_R:
            # Check if we already alerted for BE
            existing = [a for a in self.position_alerts
                       if a.position_id == pos_id and a.alert_type == "BE_REMINDER"]
            if not existing:
                alert = PositionAlert(
                    position_id=pos_id,
                    alert_type="BE_REMINDER",
                    message=f"[ACTION REQUIRED] Position at +{pnl_r:.1f}R - MOVE STOP TO BREAKEVEN",
                    triggered_at=datetime.now(self.tz)
                )
                alerts.append(alert)
                self.position_alerts.append(alert)

        # 2. Stop approaching warning
        if direction == "LONG":
            distance_to_stop = current_price - stop
        else:
            distance_to_stop = stop - current_price

        if 0 < distance_to_stop < self.STOP_WARNING_POINTS:
            # Check if recent alert
            recent = [a for a in self.position_alerts
                     if a.position_id == pos_id
                     and a.alert_type == "STOP_APPROACHING"
                     and (datetime.now(self.tz) - a.triggered_at).total_seconds() < 30]
            if not recent:
                alert = PositionAlert(
                    position_id=pos_id,
                    alert_type="STOP_APPROACHING",
                    message=f"[WARNING] Stop approaching ({distance_to_stop:.1f}pts away)",
                    triggered_at=datetime.now(self.tz)
                )
                alerts.append(alert)
                self.position_alerts.append(alert)

        # 3. Target approaching
        if 'target_price' in position and position['target_price']:
            target = position['target_price']

            if direction == "LONG":
                distance_to_target = target - current_price
            else:
                distance_to_target = current_price - target

            if 0 < distance_to_target < self.TARGET_WARNING_POINTS:
                # Check if recent alert
                recent = [a for a in self.position_alerts
                         if a.position_id == pos_id
                         and a.alert_type == "TARGET_NEAR"
                         and (datetime.now(self.tz) - a.triggered_at).total_seconds() < 30]
                if not recent:
                    alert = PositionAlert(
                        position_id=pos_id,
                        alert_type="TARGET_NEAR",
                        message=f"[INFO] Target approaching ({distance_to_target:.1f}pts away)",
                        triggered_at=datetime.now(self.tz)
                    )
                    alerts.append(alert)
                    self.position_alerts.append(alert)

        # 4. Time limit warning (for strategies with time limits)
        if strategy in ["CASCADE", "NIGHT_ORB"]:
            entry_time = position.get('entry_time')
            if entry_time:
                time_in_trade = (datetime.now(self.tz) - entry_time).total_seconds() / 60

                if time_in_trade >= self.MAX_TIME_MINUTES * 0.9:  # 90% of max time
                    # Check if recent alert
                    recent = [a for a in self.position_alerts
                             if a.position_id == pos_id
                             and a.alert_type == "TIME_LIMIT"
                             and (datetime.now(self.tz) - a.triggered_at).total_seconds() < 60]
                    if not recent:
                        alert = PositionAlert(
                            position_id=pos_id,
                            alert_type="TIME_LIMIT",
                            message=f"[WARNING] {strategy} time limit approaching ({time_in_trade:.0f}/{self.MAX_TIME_MINUTES}min)",
                            triggered_at=datetime.now(self.tz)
                        )
                        alerts.append(alert)
                        self.position_alerts.append(alert)

        return alerts

    def get_unacknowledged_alerts(self, position_id: Optional[str] = None) -> List[PositionAlert]:
        """Get unacknowledged alerts"""
        alerts = [a for a in self.position_alerts if not a.acknowledged]
        if position_id:
            alerts = [a for a in alerts if a.position_id == position_id]
        return alerts

    def acknowledge_alert(self, position_id: str, alert_type: str):
        """Acknowledge an alert"""
        for alert in self.position_alerts:
            if alert.position_id == position_id and alert.alert_type == alert_type:
                alert.acknowledged = True

    def clear_old_alerts(self, hours: int = 24):
        """Clear alerts older than N hours"""
        cutoff = datetime.now(self.tz) - timedelta(hours=hours)
        self.position_alerts = [a for a in self.position_alerts if a.triggered_at > cutoff]


# ============================================================================
# STREAMLIT UI COMPONENTS
# ============================================================================

def render_position_panel(position: dict, current_price: float,
                         tracker: PositionTracker,
                         strategy: str = "UNKNOWN") -> str:
    """
    Render active position tracking panel.

    Args:
        position: Position dict
        current_price: Current market price
        tracker: PositionTracker instance
        strategy: Strategy name

    Returns:
        HTML string with styled panel
    """
    entry = position['entry_price']
    stop = position['stop_price']
    target = position.get('target_price')
    direction = position['direction']
    entry_time = position.get('entry_time', datetime.now())

    # Calculate metrics
    risk_points = abs(entry - stop)
    if direction == "LONG":
        pnl_points = current_price - entry
        distance_to_stop = current_price - stop
        distance_to_target = target - current_price if target else None
    else:
        pnl_points = entry - current_price
        distance_to_stop = stop - current_price
        distance_to_target = current_price - target if target else None

    pnl_r = pnl_points / risk_points if risk_points > 0 else 0.0

    # Time in trade
    time_in_trade = (datetime.now() - entry_time).total_seconds() / 60
    minutes = int(time_in_trade)
    seconds = int((time_in_trade - minutes) * 60)

    # Color based on P&L
    pnl_color = "green" if pnl_points >= 0 else "red"

    # Check for alerts
    alerts = tracker.check_position_alerts(position, current_price, strategy)

    html = f"""
    <div style="
        border: 3px solid {pnl_color};
        border-radius: 12px;
        padding: 20px;
        margin: 16px 0;
        background: linear-gradient(135deg, {'#d1e7dd' if pnl_points >= 0 else '#f8d7da'} 0%, white 50%);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <div>
                <span style="font-size: 24px; font-weight: bold;">
                    {position['instrument']} {direction}
                </span>
                <span style="margin-left: 12px; padding: 4px 8px; background: {'#198754' if direction == 'LONG' else '#dc3545'}; color: white; border-radius: 4px; font-size: 14px;">
                    {strategy}
                </span>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 32px; font-weight: bold; color: {pnl_color};">
                    {pnl_points:+.1f}pts
                </div>
                <div style="font-size: 20px; color: {pnl_color};">
                    {pnl_r:+.2f}R
                </div>
            </div>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 12px; margin-bottom: 16px;">
            <div style="text-align: center; padding: 12px; background: white; border-radius: 8px; border: 1px solid #dee2e6;">
                <div style="font-size: 11px; color: #666; text-transform: uppercase;">Entry</div>
                <div style="font-size: 20px; font-weight: bold;">{entry:.1f}</div>
            </div>
            <div style="text-align: center; padding: 12px; background: white; border-radius: 8px; border: 1px solid #dee2e6;">
                <div style="font-size: 11px; color: #666; text-transform: uppercase;">Current</div>
                <div style="font-size: 20px; font-weight: bold;">{current_price:.1f}</div>
            </div>
            <div style="text-align: center; padding: 12px; background: white; border-radius: 8px; border: 1px solid #dee2e6;">
                <div style="font-size: 11px; color: #666; text-transform: uppercase;">Stop</div>
                <div style="font-size: 20px; font-weight: bold; color: #dc3545;">{stop:.1f}</div>
                <div style="font-size: 11px; color: #666;">{distance_to_stop:.1f}pts</div>
            </div>
            <div style="text-align: center; padding: 12px; background: white; border-radius: 8px; border: 1px solid #dee2e6;">
                <div style="font-size: 11px; color: #666; text-transform: uppercase;">Target</div>
                <div style="font-size: 20px; font-weight: bold; color: #198754;">{target:.1f if target else '—'}</div>
                <div style="font-size: 11px; color: #666;">{distance_to_target:.1f if distance_to_target else '—'}pts</div>
            </div>
            <div style="text-align: center; padding: 12px; background: white; border-radius: 8px; border: 1px solid #dee2e6;">
                <div style="font-size: 11px; color: #666; text-transform: uppercase;">Time</div>
                <div style="font-size: 20px; font-weight: bold;">{minutes}:{seconds:02d}</div>
                <div style="font-size: 11px; color: #666;">minutes</div>
            </div>
        </div>
    """

    # Add alerts if any
    if alerts:
        html += """
        <div style="margin-top: 16px;">
        """
        for alert in alerts:
            alert_colors = {
                "BE_REMINDER": ("#0d6efd", "#cfe2ff"),
                "STOP_APPROACHING": ("#dc3545", "#f8d7da"),
                "TARGET_NEAR": ("#198754", "#d1e7dd"),
                "TIME_LIMIT": ("#ffc107", "#fff3cd")
            }
            border_color, bg_color = alert_colors.get(alert.alert_type, ("#6c757d", "#e2e3e5"))

            html += f"""
            <div style="
                background: {bg_color};
                border-left: 4px solid {border_color};
                padding: 12px;
                margin: 8px 0;
                border-radius: 4px;
                font-weight: bold;
            ">
                {alert.message}
            </div>
            """
        html += "</div>"

    # Quick action buttons (placeholder - would need actual button handlers)
    html += """
    <div style="display: flex; gap: 8px; margin-top: 16px;">
        <div style="flex: 1; text-align: center; padding: 10px; background: #198754; color: white; border-radius: 4px; cursor: pointer; font-weight: bold;">
            MOVE STOP TO BE
        </div>
        <div style="flex: 1; text-align: center; padding: 10px; background: #0d6efd; color: white; border-radius: 4px; cursor: pointer; font-weight: bold;">
            CLOSE 50%
        </div>
        <div style="flex: 1; text-align: center; padding: 10px; background: #dc3545; color: white; border-radius: 4px; cursor: pointer; font-weight: bold;">
            EXIT ALL
        </div>
    </div>
    """

    html += "</div>"

    return html


def render_empty_position_panel() -> str:
    """Render panel when no positions active"""
    html = """
    <div style="
        border: 2px dashed #dee2e6;
        border-radius: 12px;
        padding: 40px;
        text-align: center;
        color: #6c757d;
        margin: 16px 0;
    ">
        <div style="font-size: 48px; margin-bottom: 16px;">📊</div>
        <div style="font-size: 20px; font-weight: bold; margin-bottom: 8px;">
            No Active Positions
        </div>
        <div style="font-size: 14px;">
            Position tracking will appear here when you enter a trade
        </div>
    </div>
    """
    return html
