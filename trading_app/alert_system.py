"""
ALERT SYSTEM - Multi-channel alerts for trading setups
Provides audio alerts, desktop notifications, and price level monitoring.
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)


class AlertType:
    """Alert type constants"""
    ORB_OPENING_SOON = "orb_opening_soon"
    ORB_WINDOW_OPEN = "orb_window_open"
    SETUP_DETECTED = "setup_detected"
    PRICE_LEVEL = "price_level"
    TARGET_HIT = "target_hit"
    STOP_APPROACHING = "stop_approaching"
    SETUP_TRIGGERED = "setup_triggered"


class AlertPriority:
    """Alert priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PriceAlert:
    """Price level alert configuration"""
    def __init__(
        self,
        alert_id: str,
        name: str,
        price: float,
        condition: str,  # "above", "below", "cross_above", "cross_below"
        enabled: bool = True,
        triggered: bool = False,
        instrument: str = "MGC"
    ):
        self.alert_id = alert_id
        self.name = name
        self.price = price
        self.condition = condition
        self.enabled = enabled
        self.triggered = triggered
        self.instrument = instrument
        self.created_at = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            "alert_id": self.alert_id,
            "name": self.name,
            "price": self.price,
            "condition": self.condition,
            "enabled": self.enabled,
            "triggered": self.triggered,
            "instrument": self.instrument,
            "created_at": self.created_at.isoformat()
        }

    @staticmethod
    def from_dict(data: dict) -> 'PriceAlert':
        """Create from dictionary"""
        alert = PriceAlert(
            alert_id=data["alert_id"],
            name=data["name"],
            price=data["price"],
            condition=data["condition"],
            enabled=data["enabled"],
            triggered=data["triggered"],
            instrument=data["instrument"]
        )
        alert.created_at = datetime.fromisoformat(data["created_at"])
        return alert


class AlertSystem:
    """
    Comprehensive alert system for trading application.
    Handles audio alerts, desktop notifications, and price level monitoring.
    """

    def __init__(self):
        self.alerts_triggered = []  # Recently triggered alerts
        self.price_alerts: List[PriceAlert] = []
        self.last_price = {}  # Track last price per instrument for crossing detection

        # Alert cooldowns (prevent spam)
        self.cooldowns = {
            AlertType.ORB_OPENING_SOON: 300,  # 5 minutes
            AlertType.ORB_WINDOW_OPEN: 300,    # 5 minutes
            AlertType.SETUP_DETECTED: 60,      # 1 minute
            AlertType.PRICE_LEVEL: 30,         # 30 seconds
            AlertType.TARGET_HIT: 60,          # 1 minute
            AlertType.STOP_APPROACHING: 30,    # 30 seconds
            AlertType.SETUP_TRIGGERED: 60,     # 1 minute
        }

        self.last_alert_time = {}  # Track last alert time by type+key

    def should_trigger_alert(self, alert_type: str, alert_key: str = "") -> bool:
        """
        Check if enough time has passed since last alert of this type.

        Args:
            alert_type: Type of alert
            alert_key: Optional key to differentiate same type alerts (e.g., "MGC_1000")

        Returns:
            True if alert should trigger, False if in cooldown period
        """
        key = f"{alert_type}_{alert_key}"

        if key not in self.last_alert_time:
            self.last_alert_time[key] = datetime.now()
            return True

        cooldown = self.cooldowns.get(alert_type, 60)
        elapsed = (datetime.now() - self.last_alert_time[key]).total_seconds()

        if elapsed >= cooldown:
            self.last_alert_time[key] = datetime.now()
            return True

        return False

    def trigger_orb_opening_soon(self, orb_name: str, minutes_until: int, instrument: str = "MGC"):
        """Alert that ORB window is opening soon"""
        alert_key = f"{instrument}_{orb_name}"

        if not self.should_trigger_alert(AlertType.ORB_OPENING_SOON, alert_key):
            return None

        alert = {
            "type": AlertType.ORB_OPENING_SOON,
            "priority": AlertPriority.MEDIUM,
            "title": f"{instrument} {orb_name} ORB Opening Soon",
            "message": f"ORB window opens in {minutes_until} minutes",
            "sound": "chime",
            "timestamp": datetime.now().isoformat(),
            "instrument": instrument,
            "orb": orb_name
        }

        self.alerts_triggered.append(alert)
        logger.info(f"Alert triggered: {alert['title']}")
        return alert

    def trigger_orb_window_open(self, orb_name: str, orb_high: float, orb_low: float,
                                 filter_passed: bool, instrument: str = "MGC"):
        """Alert that ORB window is now open"""
        alert_key = f"{instrument}_{orb_name}"

        if not self.should_trigger_alert(AlertType.ORB_WINDOW_OPEN, alert_key):
            return None

        alert = {
            "type": AlertType.ORB_WINDOW_OPEN,
            "priority": AlertPriority.HIGH,
            "title": f"[ACTIVE] {instrument} {orb_name} ORB ACTIVE",
            "message": f"Window open! High: {orb_high:.1f}, Low: {orb_low:.1f}",
            "sound": "bell",
            "timestamp": datetime.now().isoformat(),
            "instrument": instrument,
            "orb": orb_name,
            "filter_passed": filter_passed
        }

        self.alerts_triggered.append(alert)
        logger.info(f"Alert triggered: {alert['title']}")
        return alert

    def trigger_setup_detected(self, orb_name: str, tier: str, win_rate: float,
                               expectancy: float, instrument: str = "MGC"):
        """Alert that a valid setup has been detected"""
        alert_key = f"{instrument}_{orb_name}"

        if not self.should_trigger_alert(AlertType.SETUP_DETECTED, alert_key):
            return None

        alert = {
            "type": AlertType.SETUP_DETECTED,
            "priority": AlertPriority.HIGH if tier in ["S+", "S"] else AlertPriority.MEDIUM,
            "title": f"[SETUP] {instrument} {orb_name} Setup Detected ({tier} Tier)",
            "message": f"Win Rate: {win_rate:.1f}%, Expectancy: +{expectancy:.2f}R",
            "sound": "success",
            "timestamp": datetime.now().isoformat(),
            "instrument": instrument,
            "orb": orb_name,
            "tier": tier
        }

        self.alerts_triggered.append(alert)
        logger.info(f"Alert triggered: {alert['title']}")
        return alert

    def trigger_setup_triggered(self, orb_name: str, direction: str, entry: float,
                                stop: float, target: float, instrument: str = "MGC"):
        """Alert that setup has been triggered (price broke ORB)"""
        alert_key = f"{instrument}_{orb_name}_{direction}"

        if not self.should_trigger_alert(AlertType.SETUP_TRIGGERED, alert_key):
            return None

        alert = {
            "type": AlertType.SETUP_TRIGGERED,
            "priority": AlertPriority.CRITICAL,
            "title": f"[TRIGGERED] {instrument} {orb_name} {direction} TRIGGERED",
            "message": f"Entry: {entry:.1f}, Stop: {stop:.1f}, Target: {target:.1f}",
            "sound": "alert",
            "timestamp": datetime.now().isoformat(),
            "instrument": instrument,
            "orb": orb_name,
            "direction": direction
        }

        self.alerts_triggered.append(alert)
        logger.info(f"Alert triggered: {alert['title']}")
        return alert

    def trigger_target_hit(self, instrument: str, target_price: float, pnl: float):
        """Alert that target has been hit"""
        alert_key = f"{instrument}_target"

        if not self.should_trigger_alert(AlertType.TARGET_HIT, alert_key):
            return None

        alert = {
            "type": AlertType.TARGET_HIT,
            "priority": AlertPriority.HIGH,
            "title": f"[TARGET] {instrument} Target Hit!",
            "message": f"Target {target_price:.1f} reached. P&L: ${pnl:.0f}",
            "sound": "celebration",
            "timestamp": datetime.now().isoformat(),
            "instrument": instrument
        }

        self.alerts_triggered.append(alert)
        logger.info(f"Alert triggered: {alert['title']}")
        return alert

    def trigger_stop_approaching(self, instrument: str, current_price: float,
                                stop_price: float, distance: float):
        """Alert that price is approaching stop loss"""
        alert_key = f"{instrument}_stop"

        if not self.should_trigger_alert(AlertType.STOP_APPROACHING, alert_key):
            return None

        alert = {
            "type": AlertType.STOP_APPROACHING,
            "priority": AlertPriority.HIGH,
            "title": f"[STOP] {instrument} Approaching Stop",
            "message": f"Price {current_price:.1f}, Stop {stop_price:.1f} ({distance:.1f}pts away)",
            "sound": "warning",
            "timestamp": datetime.now().isoformat(),
            "instrument": instrument
        }

        self.alerts_triggered.append(alert)
        logger.info(f"Alert triggered: {alert['title']}")
        return alert

    # ========================================================================
    # PRICE LEVEL ALERTS
    # ========================================================================

    def add_price_alert(self, name: str, price: float, condition: str, instrument: str = "MGC") -> PriceAlert:
        """Add a new price level alert"""
        import uuid
        alert_id = str(uuid.uuid4())
        alert = PriceAlert(alert_id, name, price, condition, enabled=True, instrument=instrument)
        self.price_alerts.append(alert)
        logger.info(f"Price alert added: {name} @ {price} ({condition})")
        return alert

    def remove_price_alert(self, alert_id: str):
        """Remove a price alert"""
        self.price_alerts = [a for a in self.price_alerts if a.alert_id != alert_id]
        logger.info(f"Price alert removed: {alert_id}")

    def check_price_alerts(self, instrument: str, current_price: float) -> List[dict]:
        """
        Check if any price alerts should trigger.

        Args:
            instrument: Instrument symbol
            current_price: Current price

        Returns:
            List of triggered alerts
        """
        triggered = []
        last_price = self.last_price.get(instrument)

        for alert in self.price_alerts:
            if not alert.enabled or alert.triggered or alert.instrument != instrument:
                continue

            should_trigger = False

            if alert.condition == "above" and current_price > alert.price:
                should_trigger = True
            elif alert.condition == "below" and current_price < alert.price:
                should_trigger = True
            elif alert.condition == "cross_above" and last_price is not None:
                if last_price <= alert.price < current_price:
                    should_trigger = True
            elif alert.condition == "cross_below" and last_price is not None:
                if last_price >= alert.price > current_price:
                    should_trigger = True

            if should_trigger:
                alert.triggered = True
                notification = {
                    "type": AlertType.PRICE_LEVEL,
                    "priority": AlertPriority.HIGH,
                    "title": f"Price Alert: {alert.name}",
                    "message": f"{instrument} {current_price:.1f} {alert.condition} {alert.price:.1f}",
                    "sound": "notification",
                    "timestamp": datetime.now().isoformat(),
                    "instrument": instrument,
                    "alert_id": alert.alert_id
                }
                triggered.append(notification)
                self.alerts_triggered.append(notification)
                logger.info(f"Price alert triggered: {alert.name}")

        # Update last price
        self.last_price[instrument] = current_price

        return triggered

    def reset_price_alert(self, alert_id: str):
        """Reset a triggered price alert so it can trigger again"""
        for alert in self.price_alerts:
            if alert.alert_id == alert_id:
                alert.triggered = False
                logger.info(f"Price alert reset: {alert.name}")
                break

    def get_active_price_alerts(self, instrument: Optional[str] = None) -> List[PriceAlert]:
        """Get all active price alerts, optionally filtered by instrument"""
        if instrument:
            return [a for a in self.price_alerts if a.enabled and a.instrument == instrument]
        return [a for a in self.price_alerts if a.enabled]

    def get_recent_alerts(self, limit: int = 10) -> List[dict]:
        """Get recent triggered alerts"""
        return self.alerts_triggered[-limit:]

    def clear_recent_alerts(self):
        """Clear recent alerts history"""
        self.alerts_triggered = []


# ============================================================================
# STREAMLIT UI COMPONENTS
# ============================================================================

def render_audio_player(alert_type: str) -> str:
    """
    Generate HTML/JavaScript for audio alert.

    Args:
        alert_type: Type of alert (determines sound)

    Returns:
        HTML string with audio player
    """
    # Map alert types to sound files or base64 encoded sounds
    # For now, use browser beep API
    sound_map = {
        "chime": "beep",
        "bell": "beep",
        "success": "beep",
        "alert": "beep",
        "celebration": "beep",
        "warning": "beep",
        "notification": "beep"
    }

    # Simple browser beep using AudioContext
    # In production, use actual sound files
    html = """
    <script>
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);

    oscillator.frequency.value = 800;  // Frequency in Hz
    oscillator.type = 'sine';

    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);

    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.5);
    </script>
    """

    return html


def render_desktop_notification(title: str, message: str, priority: str = "medium") -> str:
    """
    Generate HTML/JavaScript for desktop notification.

    Args:
        title: Notification title
        message: Notification message
        priority: Priority level

    Returns:
        HTML string with notification script
    """
    html = f"""
    <script>
    if ("Notification" in window) {{
        if (Notification.permission === "granted") {{
            new Notification("{title}", {{
                body: "{message}",
                icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📈</text></svg>",
                requireInteraction: {'true' if priority == 'critical' else 'false'}
            }});
        }} else if (Notification.permission !== "denied") {{
            Notification.requestPermission().then(function(permission) {{
                if (permission === "granted") {{
                    new Notification("{title}", {{
                        body: "{message}",
                        icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📈</text></svg>"
                    }});
                }}
            }});
        }}
    }}
    </script>
    """

    return html


def render_alert_settings():
    """Render alert settings UI in sidebar"""
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔔 Alert Settings")

    # Initialize alert system in session state if not exists
    if 'alert_system' not in st.session_state:
        st.session_state.alert_system = AlertSystem()

    alert_system = st.session_state.alert_system

    # Audio alerts toggle
    audio_enabled = st.sidebar.checkbox("🔊 Audio Alerts", value=True, key="audio_alerts_enabled")

    # Desktop notifications toggle
    desktop_enabled = st.sidebar.checkbox("🔔 Desktop Notifications", value=True, key="desktop_alerts_enabled")

    # Request notification permission button
    if desktop_enabled:
        if st.sidebar.button("Enable Notifications", key="request_notification_permission"):
            html = """
            <script>
            if ("Notification" in window && Notification.permission !== "granted") {
                Notification.requestPermission();
            }
            </script>
            """
            st.components.v1.html(html, height=0)

    # Alert types to enable
    with st.sidebar.expander("Alert Types", expanded=False):
        st.checkbox("ORB Opening Soon (5 min warning)", value=True, key="alert_orb_opening")
        st.checkbox("ORB Window Open", value=True, key="alert_orb_open")
        st.checkbox("Setup Detected (filter passed)", value=True, key="alert_setup_detected")
        st.checkbox("Setup Triggered (price broke ORB)", value=True, key="alert_setup_triggered")
        st.checkbox("Price Level Alerts", value=True, key="alert_price_levels")

    return alert_system
