"""
RISK MANAGEMENT SAFEGUARDS
Prevents account blowup from overtrading, revenge trading, or excessive losses.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RiskStatus:
    """Risk status constants"""
    SAFE = "SAFE"               # Within all limits
    APPROACHING_LIMIT = "WARN"  # Close to limit
    LIMIT_REACHED = "STOP"      # Limit reached, no more trading
    EMERGENCY = "EMERGENCY"     # Emergency stop all


class LimitType(Enum):
    """Types of risk limits"""
    DAILY_LOSS_DOLLARS = "daily_loss_dollars"
    DAILY_LOSS_R = "daily_loss_r"
    WEEKLY_LOSS_DOLLARS = "weekly_loss_dollars"
    WEEKLY_LOSS_R = "weekly_loss_r"
    MAX_POSITIONS = "max_positions"
    MAX_POSITION_SIZE = "max_position_size"
    CORRELATION = "correlation"


@dataclass
class Position:
    """Active position"""
    position_id: str
    instrument: str
    direction: str  # LONG or SHORT
    entry_price: float
    stop_price: float
    target_price: float
    size: int  # Number of contracts
    entry_time: datetime
    risk_dollars: float
    risk_r: float
    current_pnl_dollars: float = 0.0
    current_pnl_r: float = 0.0

    def update_pnl(self, current_price: float, tick_value: float):
        """Update P&L based on current price"""
        points_move = current_price - self.entry_price
        if self.direction == "SHORT":
            points_move = -points_move

        self.current_pnl_dollars = points_move * self.size * tick_value
        self.current_pnl_r = self.current_pnl_dollars / self.risk_dollars if self.risk_dollars > 0 else 0.0


@dataclass
class RiskLimits:
    """Risk limit configuration"""
    daily_loss_dollars: Optional[float] = None
    daily_loss_r: Optional[float] = None
    weekly_loss_dollars: Optional[float] = None
    weekly_loss_r: Optional[float] = None
    max_concurrent_positions: int = 3
    max_position_size_pct: float = 2.0  # % of account
    max_correlated_positions: int = 1  # Max positions in correlated instruments


@dataclass
class RiskMetrics:
    """Current risk metrics"""
    status: str
    total_positions: int
    total_risk_dollars: float
    total_risk_r: float
    daily_pnl_dollars: float
    daily_pnl_r: float
    weekly_pnl_dollars: float
    weekly_pnl_r: float
    limits_breached: List[str]
    warnings: List[str]

    def is_safe_to_trade(self) -> bool:
        """Check if safe to enter new trades"""
        return self.status == RiskStatus.SAFE


class RiskManager:
    """
    Comprehensive risk management system.

    Critical safety system that prevents account blowup.
    """

    def __init__(self, account_size: float,
                 limits: RiskLimits,
                 timezone: ZoneInfo = ZoneInfo("Australia/Brisbane")):
        self.account_size = account_size
        self.limits = limits
        self.tz = timezone

        # Track positions
        self.active_positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []

        # Track P&L
        self.daily_pnl = {}  # date -> pnl
        self.weekly_pnl = {}  # week_start -> pnl

        # Emergency stop flag
        self.emergency_stop = False

    def add_position(self, position: Position) -> Tuple[bool, str]:
        """
        Add new position (enter trade).

        Args:
            position: Position object

        Returns:
            Tuple of (allowed, reason)
        """
        # Check if trading is allowed
        is_allowed, reason = self.is_trading_allowed()
        if not is_allowed:
            return False, reason

        # Check position limits
        if len(self.active_positions) >= self.limits.max_concurrent_positions:
            return False, f"Max positions reached ({self.limits.max_concurrent_positions})"

        # Check position size
        position_pct = (position.risk_dollars / self.account_size) * 100
        if position_pct > self.limits.max_position_size_pct:
            return False, f"Position too large ({position_pct:.1f}% > {self.limits.max_position_size_pct}%)"

        # Check correlation (simplified - same instrument = correlated)
        correlated_count = sum(1 for p in self.active_positions.values()
                              if p.instrument == position.instrument)
        if correlated_count >= self.limits.max_correlated_positions:
            return False, f"Max correlated positions reached for {position.instrument}"

        # Add position
        self.active_positions[position.position_id] = position
        logger.info(f"Position added: {position.instrument} {position.direction} @ {position.entry_price}")

        return True, "Position added"

    def remove_position(self, position_id: str, exit_price: float,
                       exit_time: datetime) -> Tuple[bool, str]:
        """
        Remove position (exit trade).

        Args:
            position_id: Position ID
            exit_price: Exit price
            exit_time: Exit timestamp

        Returns:
            Tuple of (success, message)
        """
        if position_id not in self.active_positions:
            return False, "Position not found"

        position = self.active_positions[position_id]

        # Calculate final P&L
        if position.instrument == "MGC":
            tick_value = 10.0
        elif position.instrument == "NQ":
            tick_value = 2.0
        elif position.instrument == "MPL":
            tick_value = 50.0
        else:
            tick_value = 1.0

        position.update_pnl(exit_price, tick_value)

        # Update daily/weekly P&L
        self._update_pnl_tracking(position, exit_time)

        # Move to closed positions
        self.closed_positions.append(position)
        del self.active_positions[position_id]

        logger.info(f"Position closed: {position.instrument} P&L=${position.current_pnl_dollars:.2f} ({position.current_pnl_r:.2f}R)")

        return True, f"Position closed: ${position.current_pnl_dollars:.2f}"

    def update_position_pnl(self, position_id: str, current_price: float):
        """Update position P&L with current price"""
        if position_id not in self.active_positions:
            return

        position = self.active_positions[position_id]

        # Determine tick value
        if position.instrument == "MGC":
            tick_value = 10.0
        elif position.instrument == "NQ":
            tick_value = 2.0
        elif position.instrument == "MPL":
            tick_value = 50.0
        else:
            tick_value = 1.0

        position.update_pnl(current_price, tick_value)

    def _update_pnl_tracking(self, position: Position, exit_time: datetime):
        """Update daily and weekly P&L tracking"""
        # Daily P&L
        date_key = exit_time.date()
        if date_key not in self.daily_pnl:
            self.daily_pnl[date_key] = 0.0
        self.daily_pnl[date_key] += position.current_pnl_dollars

        # Weekly P&L (week starts Monday)
        week_start = exit_time - timedelta(days=exit_time.weekday())
        week_key = week_start.date()
        if week_key not in self.weekly_pnl:
            self.weekly_pnl[week_key] = 0.0
        self.weekly_pnl[week_key] += position.current_pnl_dollars

    def get_daily_pnl(self, date: Optional[datetime] = None) -> Tuple[float, float]:
        """
        Get daily P&L (dollars and R).

        Returns:
            Tuple of (pnl_dollars, pnl_r)
        """
        if date is None:
            date = datetime.now(self.tz)

        date_key = date.date()

        # Closed positions P&L
        closed_pnl = self.daily_pnl.get(date_key, 0.0)

        # Open positions P&L
        open_pnl = sum(p.current_pnl_dollars for p in self.active_positions.values())

        total_pnl = closed_pnl + open_pnl

        # Calculate R (assuming $50 = 1R, adjust as needed)
        r_size = 50.0  # Standard 1R size
        pnl_r = total_pnl / r_size

        return total_pnl, pnl_r

    def get_weekly_pnl(self, date: Optional[datetime] = None) -> Tuple[float, float]:
        """
        Get weekly P&L (dollars and R).

        Returns:
            Tuple of (pnl_dollars, pnl_r)
        """
        if date is None:
            date = datetime.now(self.tz)

        week_start = date - timedelta(days=date.weekday())
        week_key = week_start.date()

        # Sum all days in this week
        total_pnl = 0.0
        for i in range(7):
            day = week_start + timedelta(days=i)
            day_key = day.date()
            total_pnl += self.daily_pnl.get(day_key, 0.0)

        # Add open positions
        open_pnl = sum(p.current_pnl_dollars for p in self.active_positions.values())
        total_pnl += open_pnl

        # Calculate R
        r_size = 50.0
        pnl_r = total_pnl / r_size

        return total_pnl, pnl_r

    def is_trading_allowed(self) -> Tuple[bool, str]:
        """
        Check if trading is allowed.

        Returns:
            Tuple of (allowed, reason)
        """
        # Emergency stop
        if self.emergency_stop:
            return False, "EMERGENCY STOP ACTIVATED"

        # Check daily loss limit
        daily_pnl, daily_pnl_r = self.get_daily_pnl()

        if self.limits.daily_loss_dollars and daily_pnl < -abs(self.limits.daily_loss_dollars):
            return False, f"Daily loss limit reached (${daily_pnl:.2f})"

        if self.limits.daily_loss_r and daily_pnl_r < -abs(self.limits.daily_loss_r):
            return False, f"Daily loss limit reached ({daily_pnl_r:.2f}R)"

        # Check weekly loss limit
        weekly_pnl, weekly_pnl_r = self.get_weekly_pnl()

        if self.limits.weekly_loss_dollars and weekly_pnl < -abs(self.limits.weekly_loss_dollars):
            return False, f"Weekly loss limit reached (${weekly_pnl:.2f})"

        if self.limits.weekly_loss_r and weekly_pnl_r < -abs(self.limits.weekly_loss_r):
            return False, f"Weekly loss limit reached ({weekly_pnl_r:.2f}R)"

        return True, "Trading allowed"

    def get_risk_metrics(self) -> RiskMetrics:
        """
        Get current risk metrics.

        Returns:
            RiskMetrics object
        """
        daily_pnl, daily_pnl_r = self.get_daily_pnl()
        weekly_pnl, weekly_pnl_r = self.get_weekly_pnl()

        total_risk_dollars = sum(p.risk_dollars for p in self.active_positions.values())
        total_risk_r = sum(p.risk_r for p in self.active_positions.values())

        # Check for breaches and warnings
        limits_breached = []
        warnings = []

        # Check if allowed to trade
        is_allowed, reason = self.is_trading_allowed()
        if not is_allowed:
            limits_breached.append(reason)

        # Check warnings (80% of limit)
        if self.limits.daily_loss_dollars:
            threshold = -abs(self.limits.daily_loss_dollars) * 0.8
            if daily_pnl < threshold:
                warnings.append(f"Approaching daily loss limit ({daily_pnl:.0f} / {-abs(self.limits.daily_loss_dollars):.0f})")

        if self.limits.daily_loss_r:
            threshold = -abs(self.limits.daily_loss_r) * 0.8
            if daily_pnl_r < threshold:
                warnings.append(f"Approaching daily R limit ({daily_pnl_r:.1f}R / {-abs(self.limits.daily_loss_r):.1f}R)")

        # Position count warning
        if len(self.active_positions) >= self.limits.max_concurrent_positions * 0.8:
            warnings.append(f"Close to max positions ({len(self.active_positions)} / {self.limits.max_concurrent_positions})")

        # Determine status
        if limits_breached:
            status = RiskStatus.LIMIT_REACHED
        elif warnings:
            status = RiskStatus.APPROACHING_LIMIT
        else:
            status = RiskStatus.SAFE

        return RiskMetrics(
            status=status,
            total_positions=len(self.active_positions),
            total_risk_dollars=total_risk_dollars,
            total_risk_r=total_risk_r,
            daily_pnl_dollars=daily_pnl,
            daily_pnl_r=daily_pnl_r,
            weekly_pnl_dollars=weekly_pnl,
            weekly_pnl_r=weekly_pnl_r,
            limits_breached=limits_breached,
            warnings=warnings
        )

    def emergency_stop_all(self):
        """Activate emergency stop - no more trading"""
        self.emergency_stop = True
        logger.critical("EMERGENCY STOP ACTIVATED")

    def reset_emergency_stop(self):
        """Reset emergency stop"""
        self.emergency_stop = False
        logger.info("Emergency stop reset")

    def get_active_positions(self) -> List[Dict]:
        """
        Get list of active positions as dictionaries suitable for UI display.

        Returns:
            List of position dictionaries with all required fields
        """
        positions = []
        for pos_id, pos in self.active_positions.items():
            positions.append({
                'id': pos_id,
                'instrument': pos.instrument,
                'direction': pos.direction,
                'entry_price': pos.entry_price,
                'stop_price': pos.stop_price,
                'target_price': pos.target_price,
                'entry_time': pos.entry_time,
                'strategy': pos.instrument,  # Placeholder - you may want to add strategy field to Position
                'current_pnl_dollars': pos.current_pnl_dollars,
                'current_pnl_r': pos.current_pnl_r
            })
        return positions

    def get_active_positions_summary(self) -> List[Dict]:
        """Get summary of active positions"""
        summary = []
        for pos_id, pos in self.active_positions.items():
            summary.append({
                'id': pos_id,
                'instrument': pos.instrument,
                'direction': pos.direction,
                'entry': pos.entry_price,
                'current_pnl': pos.current_pnl_dollars,
                'current_r': pos.current_pnl_r,
                'time_in_trade': (datetime.now(self.tz) - pos.entry_time).total_seconds() / 60
            })
        return summary


# ============================================================================
# STREAMLIT UI COMPONENTS
# ============================================================================

def render_risk_dashboard(metrics: RiskMetrics) -> str:
    """
    Render risk management dashboard.

    Returns:
        HTML string with styled dashboard
    """
    # Status color
    status_colors = {
        RiskStatus.SAFE: "green",
        RiskStatus.APPROACHING_LIMIT: "yellow",
        RiskStatus.LIMIT_REACHED: "red",
        RiskStatus.EMERGENCY: "darkred"
    }

    color = status_colors.get(metrics.status, "gray")

    html = f"""
    <div style="
        border: 3px solid {color};
        border-radius: 8px;
        padding: 16px;
        margin: 16px 0;
        background: white;
    ">
        <div style="font-weight: bold; font-size: 18px; color: {color}; margin-bottom: 12px;">
            Risk Status: {metrics.status}
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 16px;">
            <div style="text-align: center; padding: 12px; background: #f8f9fa; border-radius: 4px;">
                <div style="font-size: 12px; color: #666;">Active Positions</div>
                <div style="font-size: 24px; font-weight: bold;">{metrics.total_positions}</div>
            </div>
            <div style="text-align: center; padding: 12px; background: #f8f9fa; border-radius: 4px;">
                <div style="font-size: 12px; color: #666;">Daily P&L</div>
                <div style="font-size: 24px; font-weight: bold; color: {'green' if metrics.daily_pnl_dollars >= 0 else 'red'};">
                    ${metrics.daily_pnl_dollars:.0f}
                </div>
                <div style="font-size: 14px; color: #666;">({metrics.daily_pnl_r:.2f}R)</div>
            </div>
            <div style="text-align: center; padding: 12px; background: #f8f9fa; border-radius: 4px;">
                <div style="font-size: 12px; color: #666;">Total Risk</div>
                <div style="font-size: 24px; font-weight: bold;">${metrics.total_risk_dollars:.0f}</div>
                <div style="font-size: 14px; color: #666;">({metrics.total_risk_r:.1f}R)</div>
            </div>
        </div>
    """

    # Limits breached
    if metrics.limits_breached:
        html += """
        <div style="background: #f8d7da; border-left: 4px solid #dc3545; padding: 12px; margin: 8px 0; border-radius: 4px;">
            <strong style="color: #dc3545;">LIMITS BREACHED:</strong><br>
        """
        for breach in metrics.limits_breached:
            html += f"<div style='margin: 4px 0;'>- {breach}</div>"
        html += "</div>"

    # Warnings
    if metrics.warnings:
        html += """
        <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; margin: 8px 0; border-radius: 4px;">
            <strong style="color: #856404;">WARNINGS:</strong><br>
        """
        for warning in metrics.warnings:
            html += f"<div style='margin: 4px 0;'>- {warning}</div>"
        html += "</div>"

    html += "</div>"

    return html
