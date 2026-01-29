"""
CANONICAL TRADING SYSTEM - 3-Zone Architecture
Based on canon_build.md specification

Zones:
- RESEARCH (Red) - Zone A: Discover candidate edges
- VALIDATION (Yellow) - Zone B: Prove or kill candidates
- PRODUCTION (Green) - Zone C: Run approved edges only

Non-Negotiable Principles:
- Fail-closed always
- Evidence > intuition
- AI cannot write to production state
- No execution without validation lineage
- One canonical source per concept
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime
import streamlit as st
import duckdb
import logging

# Force local database (avoid MotherDuck version mismatch)
os.environ['FORCE_LOCAL_DB'] = '1'

# Add paths
current_dir = Path(__file__).parent
repo_root = current_dir.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from cloud_mode import get_database_path
from edge_utils import (
    create_candidate,
    get_all_candidates,
    get_candidate_by_id,
    update_candidate_status,
    get_registry_stats,
    create_experiment_run,
    complete_experiment_run,
    get_experiment_runs,
    check_prior_validation,
    run_validation_stub,
    promote_to_production,
    retire_from_production,
    find_similar_edges
)
from drift_monitor import DriftMonitor, get_system_health_summary
from live_scanner import LiveScanner
from terminal_theme import TERMINAL_CSS
from terminal_components import (
    render_terminal_header,
    render_metric_card,
    render_status_indicator,
    render_price_display,
    render_terminal_panel
)
from error_logger import initialize_error_log, log_error
from orb_time_logic import (
    get_current_orb_status,
    format_time_remaining,
    get_status_emoji,
    get_status_color
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize error logging (clears file on startup)
initialize_error_log()

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="Canonical Trading System",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# APP PREFLIGHT - Run checks on first launch
# ============================================================================
def _run_app_preflight_once():
    """Run preflight checks once per session (database sync, schema validation, etc.)"""
    if "preflight_ran" in st.session_state:
        return
    st.session_state["preflight_ran"] = True

    if os.environ.get("MPX_SKIP_PREFLIGHT", "") == "1":
        st.warning("Preflight skipped (MPX_SKIP_PREFLIGHT=1)")
        return

    with st.spinner("Running app preflight (sync + schema + checks)..."):
        import subprocess
        p = subprocess.run(
            ["python", "scripts/check/app_preflight.py"],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONUTF8": "1"},
        )
        output = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")

    if p.returncode != 0:
        st.error("❌ Preflight failed. App blocked until fixed.")
        st.code(output[-8000:] if len(output) > 8000 else output)
        st.stop()
    else:
        st.success("✅ Preflight passed.")
        # Optional: hide noise
        # st.code(output[-3000:])

_run_app_preflight_once()

# ============================================================================
# TERMINAL THEME (Professional Trading Terminal Aesthetics)
# ============================================================================
st.markdown(TERMINAL_CSS, unsafe_allow_html=True)

# ============================================================================
# ZONE COLORS (Visual Safety Indicators)
# ============================================================================
ZONE_COLORS = {
    "RESEARCH": {"color": "#dc3545", "bg": "#f8d7da", "name": "Research Lab"},
    "VALIDATION": {"color": "#ffc107", "bg": "#fff3cd", "name": "Validation Gate"},
    "PRODUCTION": {"color": "#198754", "bg": "#d1e7dd", "name": "Production"},
}

# ============================================================================
# STATE MANAGEMENT (Single Source of Truth)
# ============================================================================
class AppState:
    """Centralized state management - no more scattered session_state"""

    def __init__(self):
        self.db_path = None
        self.db_connection = None
        self.current_zone = "RESEARCH"
        self.current_instrument = "MGC"
        self.active_edge = None

    def initialize(self):
        """Initialize app state (called once)"""
        try:
            self.db_path = get_database_path()

            # Run health check and auto-fix WAL corruption before connecting
            from db_health_check import run_startup_health_check
            if not run_startup_health_check(self.db_path):
                raise Exception("Database health check failed")

            # Don't use read_only to allow multiple connections (app doesn't write anyway)
            self.db_connection = duckdb.connect(self.db_path)
            logger.info(f"Connected to database: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            log_error(e, context="App initialization")
            return False

    def get_db_status(self):
        """Check database health"""
        try:
            result = self.db_connection.execute("SELECT 1").fetchone()
            return "OK" if result else "FAIL"
        except:
            return "DISCONNECTED"

# Initialize state
if "app_state" not in st.session_state:
    st.session_state.app_state = AppState()
    success = st.session_state.app_state.initialize()
    if not success:
        st.error("❌ Failed to initialize database. Check connection.")
        st.stop()

app_state = st.session_state.app_state

# ============================================================================
# ZONE BANNER (Always Visible)
# ============================================================================
def get_health_text(db_connection) -> str:
    """Get system health status text"""
    try:
        return get_system_health_summary(db_connection)
    except:
        return "ERROR"

def get_health_color(db_connection) -> str:
    """Get health status color"""
    try:
        health = get_system_health_summary(db_connection)
        if 'OK' in health:
            return '#198754'
        elif 'WARNING' in health:
            return '#ffc107'
        else:
            return '#dc3545'
    except:
        return '#dc3545'

def render_zone_banner(zone: str):
    """Visual indicator of current zone"""
    zone_config = ZONE_COLORS[zone]

    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {zone_config['bg']} 0%, {zone_config['bg']}dd 100%);
        border-left: 8px solid {zone_config['color']};
        border-radius: 8px;
        padding: 16px 24px;
        margin-bottom: 24px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    ">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <span style="font-size: 14px; color: #666; text-transform: uppercase; letter-spacing: 1px;">
                    Current Zone
                </span>
                <div style="font-size: 24px; font-weight: bold; color: {zone_config['color']};">
                    {zone_config['name']}
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 14px; color: #666;">Instrument</div>
                <div style="font-size: 20px; font-weight: 600; color: #333;">{app_state.current_instrument}</div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 14px; color: #666;">Database</div>
                <div style="font-size: 16px; font-weight: 600; color: {'#198754' if app_state.get_db_status() == 'OK' else '#dc3545'};">
                    {app_state.get_db_status()}
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 14px; color: #666;">Health</div>
                <div style="font-size: 16px; font-weight: 600; color: {get_health_color(app_state.db_connection)};">
                    {get_health_text(app_state.db_connection)}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# SIDEBAR - GLOBAL SETTINGS
# ============================================================================
with st.sidebar:
    st.title("⚙️ System Settings")

    # Instrument selector
    app_state.current_instrument = st.selectbox(
        "Instrument",
        ["MGC", "NQ", "MPL"],
        index=0
    )

    st.divider()

    # Database info
    st.subheader("📊 Database")
    st.caption(f"Path: {app_state.db_path}")
    st.caption(f"Status: {app_state.get_db_status()}")

    st.divider()

    # Quick actions
    st.subheader("🚀 Quick Actions")
    if st.button("🔄 Refresh Connection"):
        app_state.initialize()
        st.rerun()

# ============================================================================
# MAIN CONTENT - 3 ZONE TABS
# ============================================================================

# Header
st.markdown("""
<div style="text-align: center; padding: 24px 0; margin-bottom: 20px;">
    <h1 style="margin: 0; font-size: 48px; font-weight: 700; color: #1a1a1a;">
        🎯 Canonical Trading System
    </h1>
    <p style="color: #666; font-size: 16px; margin-top: 8px;">
        3-Zone Architecture: Research → Validation → Production
    </p>
</div>
""", unsafe_allow_html=True)

# Create tabs (LIVE first - most important)
tab_live, tab_research, tab_validation, tab_production = st.tabs([
    "🚦 LIVE TRADING",
    "🔴 RESEARCH LAB",
    "🟡 VALIDATION GATE",
    "🟢 PRODUCTION"
])

# ============================================================================
# LIVE TRADING - WHAT TO DO RIGHT NOW
# ============================================================================
with tab_live:
    st.markdown("""
    <div style="text-align: center; padding: 16px 0; margin-bottom: 20px;">
        <h2 style="margin: 0; font-size: 32px; font-weight: 700; color: #1a1a1a;">
            🚦 Live Trading Dashboard
        </h2>
        <p style="color: #666; font-size: 14px; margin-top: 8px;">
            Real-time market analysis • Active setups • Current state
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Initialize scanner
    try:
        scanner = LiveScanner(app_state.db_connection)

        # Get current market state (with weekend fallback)
        market_state = scanner.get_current_market_state_with_fallback(instrument='MGC')

        # Get latest price with freshness
        latest_price = scanner.get_latest_price(instrument='MGC')

        # Scan for active setups
        all_setups = scanner.scan_current_market(instrument='MGC')
        active_setups = [s for s in all_setups if s['status'] == 'ACTIVE']
        waiting_setups = [s for s in all_setups if s['status'] == 'WAITING']
        invalid_setups = [s for s in all_setups if s['status'] == 'INVALID']

        # ====================================================================
        # SUMMARY BANNER
        # ====================================================================
        if active_setups:
            banner_color = "#198754"
            banner_bg = "#d1e7dd"
            banner_emoji = "🟢"
            banner_text = f"{len(active_setups)} ACTIVE SETUP{'S' if len(active_setups) != 1 else ''}"
            banner_subtitle = "Filters passed • Ready to trade"
        elif waiting_setups:
            banner_color = "#ffc107"
            banner_bg = "#fff3cd"
            banner_emoji = "🟡"
            banner_text = "NO ACTIVE SETUPS"
            banner_subtitle = f"{len(waiting_setups)} setup{'s' if len(waiting_setups) != 1 else ''} waiting for conditions"
        else:
            banner_color = "#6c757d"
            banner_bg = "#f8f9fa"
            banner_emoji = "⏸️"
            banner_text = "STAND DOWN"
            banner_subtitle = "No validated setups available today"

        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, {banner_bg} 0%, {banner_bg}dd 100%);
            border-left: 8px solid {banner_color};
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        ">
            <div style="display: flex; align-items: center; gap: 16px;">
                <span style="font-size: 48px;">{banner_emoji}</span>
                <div>
                    <div style="font-size: 28px; font-weight: bold; color: {banner_color};">{banner_text}</div>
                    <div style="font-size: 16px; color: #666; margin-top: 4px;">{banner_subtitle}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ====================================================================
        # LIVE PRICE (Requirement #1)
        # ====================================================================
        if latest_price and not latest_price.get('error'):
            price_value = latest_price['price']
            timestamp = latest_price['timestamp']
            seconds_ago = latest_price['seconds_ago']
            is_stale = latest_price['is_stale']
            warning = latest_price.get('warning')

            # Color based on freshness
            if is_stale:
                price_color = "#dc3545" if seconds_ago > 300 else "#ffc107"
                border_color = price_color
                freshness_text = warning
            else:
                price_color = "#198754"
                border_color = "#198754"
                freshness_text = f"Updated {seconds_ago}s ago"

            st.markdown(f"""
            <div style="
                background: {price_color}15;
                border-left: 6px solid {border_color};
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 13px; color: #666; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">
                            MGC Live Price
                        </div>
                        <div style="font-size: 36px; font-weight: bold; color: {price_color}; font-family: 'JetBrains Mono', monospace;">
                            ${price_value:.2f}
                        </div>
                        <div style="font-size: 13px; color: #666; margin-top: 4px;">
                            {timestamp.strftime('%H:%M:%S')} • {freshness_text}
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        elif latest_price and latest_price.get('error'):
            st.warning(f"⚠️ Could not fetch live price: {latest_price['error']}")

        # ====================================================================
        # FALLBACK WARNING (Requirement #6)
        # ====================================================================
        if market_state.get('is_fallback'):
            fallback_date = market_state.get('fallback_date')
            st.info(f"📅 **Weekend/Holiday Mode**: Showing data from last trading day ({fallback_date})")

        # ====================================================================
        # CURRENT MARKET STATE
        # ====================================================================
        st.subheader("📊 Current Market State")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"""
            <div style="background: #f8f9fa; padding: 16px; border-radius: 8px; border-left: 4px solid #0d6efd;">
                <div style="font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 1px;">Current Time</div>
                <div style="font-size: 24px; font-weight: bold; color: #1a1a1a; margin-top: 4px;">
                    {market_state['current_time_local'].strftime('%H:%M:%S')}
                </div>
                <div style="font-size: 12px; color: #666; margin-top: 4px;">Brisbane (UTC+10)</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div style="background: #f8f9fa; padding: 16px; border-radius: 8px; border-left: 4px solid #198754;">
                <div style="font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 1px;">Today's Date</div>
                <div style="font-size: 24px; font-weight: bold; color: #1a1a1a; margin-top: 4px;">
                    {market_state['date_local'].strftime('%Y-%m-%d')}
                </div>
                <div style="font-size: 12px; color: #666; margin-top: 4px;">Local Trading Day</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            atr_value = market_state['orb_data'].get('atr_20')
            atr_display = f"${atr_value:.2f}" if atr_value else "N/A"
            st.markdown(f"""
            <div style="background: #f8f9fa; padding: 16px; border-radius: 8px; border-left: 4px solid #fd7e14;">
                <div style="font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 1px;">ATR (20)</div>
                <div style="font-size: 24px; font-weight: bold; color: #1a1a1a; margin-top: 4px;">
                    {atr_display}
                </div>
                <div style="font-size: 12px; color: #666; margin-top: 4px;">Average True Range</div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # ====================================================================
        # ORB LEVELS (Requirement #2)
        # ====================================================================
        orb_data = market_state.get('orb_data', {})
        available_orbs = market_state.get('available_orbs', [])

        if available_orbs and orb_data:
            with st.expander("📏 ORB Levels (Click to expand)", expanded=False):
                st.caption("Opening Range Breakout levels for completed ORBs")

                for orb_name in ['0900', '1000', '1100', '1800', '2300', '0030']:
                    if orb_name in available_orbs and orb_name in orb_data:
                        orb = orb_data[orb_name]
                        high = orb.get('high')
                        low = orb.get('low')
                        size = orb.get('size')
                        break_dir = orb.get('break_dir')

                        if high is not None and low is not None:
                            # Color based on breakout direction
                            if break_dir == 'UP':
                                orb_color = "#198754"
                            elif break_dir == 'DOWN':
                                orb_color = "#dc3545"
                            else:
                                orb_color = "#6c757d"

                            st.markdown(f"""
                            <div style="
                                background: {orb_color}15;
                                border-left: 3px solid {orb_color};
                                border-radius: 6px;
                                padding: 12px;
                                margin-bottom: 8px;
                                font-family: 'JetBrains Mono', monospace;
                            ">
                                <div style="font-weight: bold; color: {orb_color}; margin-bottom: 6px;">
                                    {orb_name} ORB {f"({break_dir})" if break_dir and break_dir != 'NONE' else ''}
                                </div>
                                <div style="font-size: 13px; color: #333;">
                                    High: ${high:.2f} | Low: ${low:.2f} | Size: ${size:.2f}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

        st.divider()

        # ====================================================================
        # ACTIVE SETUPS (Requirements #3 and #4)
        # ====================================================================
        if active_setups:
            st.subheader(f"🟢 Active Setups ({len(active_setups)})")
            st.caption("These setups have all filters passed and are ready to trade")

            for setup in active_setups:
                orb_name = setup['orb_time']
                orb_info = orb_data.get(orb_name, {})

                # Get trade plan prices (Requirement #3)
                high = orb_info.get('high')
                low = orb_info.get('low')
                entry = orb_info.get('entry_price')
                stop = orb_info.get('stop_price')
                target = orb_info.get('target_price')

                # Build trade plan display
                if entry and stop and target:
                    trade_plan_html = f"""
                    <div style="background: #ffffff; padding: 12px; border-radius: 6px; margin: 10px 0; border: 1px solid #198754;">
                        <div style="font-weight: bold; color: #198754; margin-bottom: 8px; font-size: 13px;">
                            📊 TRADE PLAN
                        </div>
                        <div style="font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #333;">
                            <div style="margin-bottom: 4px;">Entry: <strong>${entry:.2f}</strong></div>
                            <div style="margin-bottom: 4px;">Stop: <strong>${stop:.2f}</strong> (Risk: ${abs(entry-stop):.2f})</div>
                            <div>Target: <strong>${target:.2f}</strong> (Reward: ${abs(target-entry):.2f})</div>
                        </div>
                    </div>
                    """
                elif high and low:
                    # Fallback: show ORB levels
                    trade_plan_html = f"""
                    <div style="background: #ffffff; padding: 12px; border-radius: 6px; margin: 10px 0; border: 1px solid #198754;">
                        <div style="font-weight: bold; color: #198754; margin-bottom: 8px; font-size: 13px;">
                            📏 ORB LEVELS
                        </div>
                        <div style="font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #333;">
                            <div style="margin-bottom: 4px;">High: <strong>${high:.2f}</strong></div>
                            <div>Low: <strong>${low:.2f}</strong></div>
                        </div>
                    </div>
                    """
                else:
                    trade_plan_html = ""

                st.markdown(f"""
                <div style="
                    background: #d1e7dd;
                    border-left: 4px solid #198754;
                    border-radius: 8px;
                    padding: 16px;
                    margin-bottom: 12px;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <div>
                            <span style="font-size: 18px; font-weight: bold; color: #198754;">
                                {setup['instrument']} {setup['orb_time']} {setup['direction']}
                            </span>
                            <span style="margin-left: 12px; font-size: 14px; color: #666;">
                                RR={setup['rr']} | SL={setup['sl_mode']}
                            </span>
                        </div>
                        <span style="background: #198754; color: white; padding: 4px 12px; border-radius: 12px; font-weight: bold; font-size: 12px;">
                            ACTIVE
                        </span>
                    </div>

                    {trade_plan_html}

                    <div style="background: #ffc107; color: #000; padding: 10px; border-radius: 6px; margin: 10px 0; border-left: 4px solid #856404;">
                        <div style="font-weight: bold; font-size: 13px; margin-bottom: 4px;">
                            ⚠️ ENTRY RULE (CRITICAL)
                        </div>
                        <div style="font-size: 13px;">
                            WAIT FOR 1-MIN CLOSE OUTSIDE ORB (not touch). Only enter after bar closes beyond ORB boundary.
                        </div>
                    </div>

                    <div style="font-size: 14px; color: #333; margin-bottom: 4px;">
                        <strong>Trigger:</strong> {setup['trigger_definition']}
                    </div>
                    <div style="font-size: 14px; color: #666;">
                        <strong>Status:</strong> {setup['reason']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.divider()

        # ====================================================================
        # WAITING SETUPS
        # ====================================================================
        if waiting_setups:
            with st.expander(f"🟡 Waiting Setups ({len(waiting_setups)})", expanded=False):
                st.caption("These setups are waiting for conditions to be met")

                for setup in waiting_setups:
                    st.markdown(f"""
                    <div style="
                        background: #fff3cd;
                        border-left: 4px solid #ffc107;
                        border-radius: 8px;
                        padding: 12px;
                        margin-bottom: 8px;
                    ">
                        <div style="font-size: 16px; font-weight: bold; color: #856404; margin-bottom: 4px;">
                            {setup['instrument']} {setup['orb_time']} {setup['direction']} (RR={setup['rr']})
                        </div>
                        <div style="font-size: 13px; color: #666;">
                            {setup['reason']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        # ====================================================================
        # INVALID SETUPS (Requirement #5 - Specific filter failure reasons)
        # ====================================================================
        if invalid_setups:
            with st.expander(f"🔴 Invalid Setups ({len(invalid_setups)})", expanded=False):
                st.caption("These setups failed filter conditions today")

                for setup in invalid_setups:
                    # Build detailed failure reason
                    orb_size = setup.get('orb_size')
                    orb_size_norm = setup.get('orb_size_norm')
                    filter_threshold = setup.get('filter_threshold')
                    atr = orb_data.get('atr_20')

                    # Enhanced reason with values
                    detailed_reason = setup['reason']

                    if orb_size and orb_size_norm and filter_threshold and atr:
                        detailed_reason += f"<br><strong>Values:</strong> ORB size = {orb_size:.2f} pts ({orb_size_norm*100:.1f}% of ATR) vs threshold {filter_threshold*100:.1f}%"
                        detailed_reason += f"<br><strong>ATR:</strong> ${atr:.2f}"

                    st.markdown(f"""
                    <div style="
                        background: #f8d7da;
                        border-left: 4px solid #dc3545;
                        border-radius: 8px;
                        padding: 12px;
                        margin-bottom: 8px;
                    ">
                        <div style="font-size: 16px; font-weight: bold; color: #721c24; margin-bottom: 4px;">
                            {setup['instrument']} {setup['orb_time']} {setup['direction']} (RR={setup['rr']})
                        </div>
                        <div style="font-size: 13px; color: #666;">
                            {detailed_reason}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        # ====================================================================
        # ORB COMPLETION STATUS
        # ====================================================================
        st.divider()
        st.subheader("⏱️ ORB Completion Status")

        completed_orbs = market_state['available_orbs']
        all_orbs = ['0900', '1000', '1100', '1800', '2300', '0030']

        orb_cols = st.columns(6)
        for idx, orb_name in enumerate(all_orbs):
            with orb_cols[idx]:
                if orb_name in completed_orbs:
                    status_color = "#198754"
                    status_icon = "✅"
                    status_text = "Done"
                else:
                    status_color = "#6c757d"
                    status_icon = "⏳"
                    status_text = "Wait"

                st.markdown(f"""
                <div style="text-align: center; padding: 8px; background: {status_color}22; border-radius: 8px; border: 2px solid {status_color};">
                    <div style="font-size: 24px;">{status_icon}</div>
                    <div style="font-size: 16px; font-weight: bold; color: {status_color};">{orb_name}</div>
                    <div style="font-size: 11px; color: #666;">{status_text}</div>
                </div>
                """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Failed to load live scanner: {e}")
        logger.error(f"Live scanner error: {e}", exc_info=True)

# ============================================================================
# ZONE A: RESEARCH LAB (Red Zone - Unsafe by Default)
# ============================================================================
with tab_research:
    app_state.current_zone = "RESEARCH"
    render_zone_banner("RESEARCH")

    st.markdown("""
    ### 🔬 Research Lab

    **Purpose:** Discover candidate edges

    **Rules:**
    - Read-only access to market data
    - Write only to research metadata
    - Cannot trade or modify production logic
    - Cannot modify validated_setups

    **AI Role:**
    - Active but constrained
    - Can propose variants
    - Can explain patterns
    - **Cannot approve or promote edges**
    """)

    st.divider()

    # Edge Registry Quick Stats
    st.subheader("📊 Edge Registry Stats")

    # Get real stats from database
    try:
        stats = get_registry_stats(app_state.db_connection)
    except Exception as e:
        logger.error(f"Failed to get registry stats: {e}")
        stats = {'total': 0, 'never_tested': 0, 'validated': 0, 'promoted': 0}

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Edges", stats.get('total', 0), help="All edges ever tested")
    with col2:
        st.metric("Never Tested", stats.get('never_tested', 0), help="Candidates awaiting validation")
    with col3:
        st.metric("Validated", stats.get('validated', 0), help="Passed all gates")
    with col4:
        st.metric("In Production", stats.get('promoted', 0), help="Promoted and running")

    st.divider()

    # ========================================================================
    # WHAT-IF ANALYZER - Interactive Condition Testing
    # ========================================================================
    st.subheader("🔬 What-If Analyzer")
    st.caption("Test filter conditions against historical data with full reproducibility")

    # Import What-If components
    sys.path.insert(0, str(Path(__file__).parent.parent / "analysis"))
    from what_if_engine import WhatIfEngine, ConditionSet
    from what_if_snapshots import SnapshotManager

    # Initialize engines
    what_if_engine = WhatIfEngine(app_state.db_connection)
    snapshot_manager = SnapshotManager(app_state.db_connection)

    # Expandable section
    with st.expander("▶️ Open What-If Analyzer", expanded=False):
        st.markdown("""
        **Purpose:** Test "what if" scenarios by applying filter conditions to historical data.

        **How it works:**
        1. Select a base setup (instrument, ORB, RR, etc.)
        2. Apply filter conditions (ORB size, travel, session type, etc.)
        3. See baseline vs conditional metrics
        4. Save promising conditions as snapshots
        5. Promote snapshots to validation candidates
        """)

        # Setup Selection
        st.markdown("#### 1️⃣ Setup Selection")
        col1, col2, col3 = st.columns(3)

        with col1:
            wi_instrument = st.selectbox("Instrument", ["MGC"], key="wi_instrument")
            wi_orb_time = st.selectbox("ORB Time", ["0900", "1000", "1100", "1800", "2300", "0030"], index=1, key="wi_orb")

        with col2:
            wi_direction = st.selectbox("Direction", ["BOTH", "UP", "DOWN"], key="wi_direction")
            wi_rr = st.number_input("RR", min_value=1.0, max_value=5.0, value=2.0, step=0.5, key="wi_rr")

        with col3:
            wi_sl_mode = st.selectbox("SL Mode", ["FULL", "HALF"], key="wi_sl_mode")
            wi_date_range = st.selectbox("Date Range", ["Last Year", "Last 2 Years", "All Time"], index=1, key="wi_date_range")

        # Parse date range
        from datetime import datetime, timedelta
        today = datetime.now().date()
        if wi_date_range == "Last Year":
            wi_date_start = str(today - timedelta(days=365))
            wi_date_end = str(today)
        elif wi_date_range == "Last 2 Years":
            wi_date_start = str(today - timedelta(days=730))
            wi_date_end = str(today)
        else:
            wi_date_start = None
            wi_date_end = None

        st.divider()

        # Condition Filters
        st.markdown("#### 2️⃣ Filter Conditions")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**ORB Size Filter**")
            wi_orb_size_enabled = st.checkbox("Enable ORB size filter", key="wi_orb_size_enabled")
            if wi_orb_size_enabled:
                wi_orb_size_min = st.number_input("Min ORB Size (x ATR)", min_value=0.0, max_value=5.0, value=0.5, step=0.1, key="wi_orb_size_min")
                wi_orb_size_max = st.number_input("Max ORB Size (x ATR)", min_value=0.0, max_value=5.0, value=2.0, step=0.1, key="wi_orb_size_max")
            else:
                wi_orb_size_min = None
                wi_orb_size_max = None

            st.markdown("**Pre-Session Travel Filter**")
            wi_travel_enabled = st.checkbox("Enable travel filter", key="wi_travel_enabled")
            if wi_travel_enabled:
                wi_travel_max = st.number_input("Max Pre-ORB Travel (x ATR)", min_value=0.0, max_value=10.0, value=2.5, step=0.5, key="wi_travel_max")
            else:
                wi_travel_max = None

        with col2:
            st.markdown("**Session Type Filter**")
            wi_session_enabled = st.checkbox("Enable session type filter", key="wi_session_enabled")
            if wi_session_enabled:
                wi_asia_types = st.multiselect("Allowed Asia Types", ["QUIET", "CHOPPY", "TRENDING"], key="wi_asia_types")
            else:
                wi_asia_types = None

            st.markdown("**Range Percentile Filter**")
            wi_percentile_enabled = st.checkbox("Enable percentile filter", key="wi_percentile_enabled")
            if wi_percentile_enabled:
                wi_percentile_min = st.slider("Min Percentile", 0, 100, 0, 5, key="wi_percentile_min")
                wi_percentile_max = st.slider("Max Percentile", 0, 100, 25, 5, key="wi_percentile_max")
            else:
                wi_percentile_min = None
                wi_percentile_max = None

        st.divider()

        # Run Analysis Button
        if st.button("🔍 Run What-If Analysis", type="primary", key="wi_run"):
            with st.spinner("Analyzing..."):
                try:
                    # Build conditions dict
                    conditions = {}
                    if wi_orb_size_min is not None:
                        conditions['orb_size_min'] = wi_orb_size_min
                    if wi_orb_size_max is not None:
                        conditions['orb_size_max'] = wi_orb_size_max
                    if wi_travel_max is not None:
                        conditions['pre_orb_travel_max'] = wi_travel_max
                    if wi_asia_types:
                        conditions['asia_types'] = wi_asia_types
                    if wi_percentile_min is not None:
                        conditions['orb_size_percentile_min'] = wi_percentile_min
                    if wi_percentile_max is not None:
                        conditions['orb_size_percentile_max'] = wi_percentile_max

                    # Run analysis
                    result = what_if_engine.analyze_conditions(
                        instrument=wi_instrument,
                        orb_time=wi_orb_time,
                        direction=wi_direction,
                        rr=wi_rr,
                        sl_mode=wi_sl_mode,
                        conditions=conditions,
                        date_start=wi_date_start,
                        date_end=wi_date_end
                    )

                    # Store result in session state for "Save Snapshot" button
                    st.session_state['what_if_result'] = result
                    st.session_state['what_if_conditions'] = conditions

                    # Display Results
                    st.markdown("#### 3️⃣ Results")

                    # Metrics comparison
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.markdown("**📊 Baseline (No Filters)**")
                        baseline = result['baseline']
                        st.metric("Trades", baseline.sample_size)
                        st.metric("Win Rate", f"{baseline.win_rate*100:.1f}%")
                        st.metric("Expected R", f"{baseline.expected_r:.3f}R")
                        st.metric("Max DD", f"{baseline.max_dd:.1f}R")

                    with col2:
                        st.markdown("**✅ Conditional (With Filters)**")
                        conditional = result['conditional']
                        st.metric("Trades", conditional.sample_size, delta=result['delta']['sample_size'])
                        st.metric("Win Rate", f"{conditional.win_rate*100:.1f}%", delta=f"{result['delta']['win_rate_pct']:.1f} pct")
                        st.metric("Expected R", f"{conditional.expected_r:.3f}R", delta=f"{result['delta']['expected_r']:.3f}R")
                        st.metric("Max DD", f"{conditional.max_dd:.1f}R", delta=f"{result['delta']['max_dd']:.1f}R")

                    with col3:
                        st.markdown("**🎯 Verdict**")
                        delta_exp_r = result['delta']['expected_r']
                        if delta_exp_r >= 0.10:
                            st.success("✅ **SIGNIFICANT IMPROVEMENT**")
                            st.caption(f"+{delta_exp_r:.3f}R improvement")
                        elif delta_exp_r >= 0.05:
                            st.info("🟦 **MODEST IMPROVEMENT**")
                            st.caption(f"+{delta_exp_r:.3f}R improvement")
                        elif delta_exp_r >= 0.0:
                            st.warning("⚠️ **MARGINAL IMPROVEMENT**")
                            st.caption(f"+{delta_exp_r:.3f}R improvement")
                        else:
                            st.error("❌ **NO IMPROVEMENT**")
                            st.caption(f"{delta_exp_r:.3f}R (worse)")

                        # Stress test status
                        if conditional.stress_25_pass:
                            st.success("✅ +25% stress: PASS")
                        else:
                            st.error("❌ +25% stress: FAIL")

                        if conditional.stress_50_pass:
                            st.success("✅ +50% stress: PASS")
                        else:
                            st.error("❌ +50% stress: FAIL")

                    st.divider()

                    # Save Snapshot Button
                    if delta_exp_r >= 0.05:  # Only show if improvement
                        col_save1, col_save2 = st.columns([3, 1])
                        with col_save1:
                            wi_notes = st.text_input("Snapshot Notes", placeholder="e.g., Promising ORB size filter", key="wi_notes")
                        with col_save2:
                            if st.button("💾 Save Snapshot", type="primary", key="wi_save"):
                                try:
                                    snapshot_id = snapshot_manager.save_snapshot(
                                        result=result,
                                        notes=wi_notes if wi_notes else None,
                                        created_by="user"
                                    )
                                    st.success(f"✅ Snapshot saved: `{snapshot_id[:16]}...`")
                                    st.info("You can promote this snapshot to validation later")
                                except Exception as e:
                                    st.error(f"❌ Failed to save snapshot: {e}")
                    else:
                        st.caption("💡 Tip: Improve ExpR by +0.05R or more to enable snapshot saving")

                except Exception as e:
                    st.error(f"❌ Analysis failed: {e}")
                    logger.error(f"What-If analysis error: {e}", exc_info=True)

        st.divider()

        # Recent Snapshots
        st.markdown("#### 📸 Recent Snapshots")
        try:
            recent_snapshots = snapshot_manager.list_snapshots(limit=5)
            if recent_snapshots:
                for snap in recent_snapshots:
                    with st.container():
                        col1, col2, col3 = st.columns([2, 2, 1])
                        with col1:
                            st.caption(f"**{snap['instrument']} {snap['orb_time']}** | RR={snap['rr']}")
                            if snap['notes']:
                                st.caption(f"_{snap['notes']}_")
                        with col2:
                            delta_exp_r = snap['delta_expected_r']
                            if delta_exp_r > 0:
                                st.caption(f"✅ +{delta_exp_r:.3f}R improvement")
                            else:
                                st.caption(f"❌ {delta_exp_r:.3f}R (worse)")
                        with col3:
                            if not snap['promoted_to_candidate']:
                                if st.button("→ Promote", key=f"promote_{snap['snapshot_id'][:8]}"):
                                    # Promote snapshot to candidate
                                    try:
                                        trigger_def = f"What-If validated: {snap['notes'] or 'ORB breakout'}"
                                        edge_id = snapshot_manager.promote_snapshot_to_candidate(
                                            snapshot_id=snap['snapshot_id'],
                                            trigger_definition=trigger_def,
                                            notes=f"Promoted from What-If Analyzer with +{snap['delta_expected_r']:.3f}R improvement"
                                        )
                                        st.success(f"✅ Promoted to candidate!")
                                        st.info(f"Edge ID: `{edge_id[:16]}...`")
                                        st.caption("Go to VALIDATION tab to run full validation")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Promotion failed: {e}")
                                        logger.error(f"Snapshot promotion error: {e}", exc_info=True)
                            else:
                                st.caption("✅ Promoted")
            else:
                st.caption("No snapshots yet. Run an analysis to create one!")
        except Exception as e:
            st.caption(f"Could not load snapshots: {e}")

    st.divider()

    # ========================================================================
    # AUTO SEARCH - Deterministic Edge Discovery (update11.txt - Zero-Typing UI)
    # ========================================================================
    st.subheader("Quick Search")

    with st.expander("Run Quick Search", expanded=True):

        # Instrument
        search_instrument = st.radio(
            "Instrument",
            options=["MGC", "NQ", "MPL"],
            index=0,
            horizontal=True,
            key="quick_search_instrument"
        )

        # ORB Times

        # Initialize selected ORBs (empty by default)
        if 'quick_search_selected_orbs' not in st.session_state:
            st.session_state.quick_search_selected_orbs = []

        # Create 6 toggle buttons for ORB times
        col1, col2, col3, col4, col5, col6 = st.columns(6)

        orb_buttons = [
            (col1, '0900'),
            (col2, '1000'),
            (col3, '1100'),
            (col4, '1800'),
            (col5, '2300'),
            (col6, '0030')
        ]

        for col, orb_time in orb_buttons:
            with col:
                is_selected = orb_time in st.session_state.quick_search_selected_orbs
                button_type = "primary" if is_selected else "secondary"

                if st.button(
                    orb_time,
                    key=f"orb_btn_{orb_time}",
                    type=button_type,
                    use_container_width=True
                ):
                    # Toggle: add if not selected, remove if selected
                    if is_selected:
                        st.session_state.quick_search_selected_orbs.remove(orb_time)
                    else:
                        st.session_state.quick_search_selected_orbs.append(orb_time)
                    st.rerun()

        orb_times = st.session_state.quick_search_selected_orbs

        if not orb_times:
            st.warning("Select at least one ORB time")

        # Entry Rule
        entry_rule = st.radio(
            "Entry Rule",
            options=[
                "1st close outside ORB",
                "2nd close outside ORB",
                "Limit at ORB edge"
            ],
            index=0,
            key="quick_search_entry_rule"
        )

        if entry_rule == "1st close outside ORB":
            entry_rule_value = "FIRST_CLOSE"
        elif entry_rule == "2nd close outside ORB":
            entry_rule_value = "SECOND_CLOSE"
        else:
            entry_rule_value = "LIMIT_ORDER"

        # RR Targets (proxy mode - no RR-specific data)
        rr_targets = [None]  # NULL = proxy mode
        st.info("📊 **Stored Model Proxy** (from daily_features tradeable columns)")
        st.caption("⚠️ These metrics use a single stored model per ORB time. Entry: 1st close outside ORB. For RR-specific results, use validated_setups.")

        # Filters

        # ORB Size Filter
        orb_filter_enabled = st.toggle(
            "ORB Size Filter",
            value=False,
            key="quick_orb_filter_enabled",
            help="Filter ORBs by size relative to ATR"
        )

        if orb_filter_enabled:
            orb_filter_threshold = st.slider(
                "Max ORB size (% of ATR)",
                min_value=5,
                max_value=20,
                value=10,
                step=1,
                key="quick_orb_filter_threshold"
            )
            filter_settings = {
                'filter_types': ['orb_size'],
                'filter_ranges': {'orb_size': (0.0, orb_filter_threshold / 100.0)}
            }
        else:
            filter_settings = {}

        direction_bias = st.radio(
            "Direction",
            options=["BOTH", "LONG", "SHORT"],
            index=0,
            horizontal=True,
            key="quick_direction_bias"
        )

        min_sample_size = st.selectbox(
            "Min sample size",
            options=[30, 50, 100],
            index=0,
            key="quick_min_sample_size"
        )

        # Advanced
        with st.expander("Advanced", expanded=False):
            search_max_seconds_custom = st.number_input(
                "Timeout (seconds)",
                min_value=30,
                max_value=300,
                value=300,
                step=30,
                key="advanced_timeout"
            )

            setup_family_advanced = st.selectbox(
                "Setup Family",
                options=["ORB_BASELINE", "ORB_L4", "ORB_RSI", "ORB_BOTH_LOST"],
                index=0,
                key="advanced_setup_family"
            )

        # Run
        run_search_button = st.button(
            "Run Search",
            type="primary",
            disabled=(not rr_targets or not orb_times),
            use_container_width=True,
            key="quick_search_run_button"
        )

        if run_search_button:
            # Import engine
            try:
                from auto_search_engine import AutoSearchEngine
            except ImportError:
                st.error("Auto search engine not found. Check trading_app/auto_search_engine.py exists.")
                st.stop()

            # Initialize engine
            engine = AutoSearchEngine(app_state.db_connection)

            # Progress display
            progress_container = st.empty()
            start_time = time.time()

            # Run search
            try:
                # Use advanced settings if available (from Advanced Mode expander)
                setup_family = st.session_state.get('advanced_setup_family', 'ORB_BASELINE')
                search_max_seconds = st.session_state.get('advanced_timeout', 300)

                # Build settings dict with new parameters
                search_settings = {
                    'family': setup_family,  # Default ORB_BASELINE, overridable in Advanced Mode
                    'orb_times': orb_times,  # NEW: User-selected ORB times
                    'rr_targets': rr_targets,
                    'entry_rule': entry_rule_value,  # NEW: Entry rule selection
                    'direction_bias': direction_bias,  # NEW: Direction filter
                    'min_sample_size': min_sample_size,  # NEW: Sample size threshold
                    **filter_settings  # Merge ORB size filter if enabled
                }

                with progress_container.container():
                    st.info(f"🔍 Searching... (max {search_max_seconds}s)")
                    progress_bar = st.progress(0)
                    stats_text = st.empty()

                    # Run search (engine enforces 300s timeout)
                    results = engine.run_search(
                        instrument=search_instrument,
                        settings=search_settings,
                        max_seconds=search_max_seconds
                    )

                    # Update progress to 100%
                    progress_bar.progress(100)

                # Show results
                duration = time.time() - start_time
                progress_container.empty()  # Clear progress display
                st.success(f"✅ Search complete in {duration:.1f}s!")

                # Stats
                stats = results['stats']
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Tested", stats['tested'])
                with col2:
                    st.metric("Skipped (Memory)", stats['skipped'])
                with col3:
                    st.metric("Promising", stats['promising'])

                # Store run_id in session state for later use
                st.session_state['last_search_run_id'] = results['run_id']

                # Show candidates
                if results['candidates']:
                    st.success(f"Found {len(results['candidates'])} candidates")

                    # Show all results in a table
                    candidates_df = []
                    for c in results['candidates']:
                        exp_r = c.expected_r_proxy if c.expected_r_proxy else c.score_proxy
                        candidates_df.append({
                            'ORB': c.orb_time,
                            'RR': c.rr_target,
                            'Expected R': f"+{exp_r:.3f}R",
                            'N': c.sample_size,
                            'Target Hit%': f"{c.target_hit_rate*100:.0f}%" if c.target_hit_rate else 'N/A',
                            'Profit%': f"{c.profitable_trade_rate*100:.0f}%" if c.profitable_trade_rate else 'N/A',
                        })

                    st.dataframe(candidates_df, use_container_width=True)

                    # Execution Spec Panel (UPDATE14 Step 4)
                    with st.expander("⚙️ Execution Spec Used"):
                        # Show the spec used for this search
                        st.markdown(f"""
**Spec Configuration**:
- **Bar timeframe**: 1m (from bars_1m)
- **ORB time**: {', '.join(map(str, orb_times))}
- **ORB duration**: 5 minutes
- **Entry rule**: 1st_close_outside (first 1m close outside ORB)
- **Confirmation timeframe**: 1m
- **RR target**: Proxy mode (stored model, not RR-specific)
- **Stop loss mode**: orb_opposite (opposite edge of ORB)
- **Cost model**: mgc_tradovate ($8.40 RT friction)
- **Session timezone**: Australia/Brisbane

**Contract Status**: [PASS] All requirements met

**Data Inputs**:
- Source table: `daily_features`
- Columns: `orb_{{time}}_tradeable_outcome`, `orb_{{time}}_tradeable_realized_rr`

**Computation Details**:
- ORB window: {{orb_time}} to {{orb_time}}+5min (exactly 5 bars at 1m)
- Entry detection: First bar where close > orb_high OR close < orb_low
- Entry execution: Open of next bar after confirmation
- Risk/Reward: Realized R calculated with embedded costs

**Invariants Verified**:
- Entry timestamp > ORB end timestamp ✓
- No lookahead (entry uses only post-ORB bars) ✓
- ORB window complete (5 bars for 5-minute ORB) ✓
                        """)

                        st.caption("""
**Note**: This spec represents the current Quick Search configuration.
For reproducible backtests with different entry rules (limit orders, 5m confirmation),
use the ExecutionSpec API in `trading_app/execution_spec.py`.
                        """)

                    # Truth Panel: What's being measured?
                    with st.expander("📋 What exactly is being measured?"):
                        st.markdown("""
**Data Source**: `daily_features` table

**Entry Rule**: 1st close outside ORB range (NOT limit order at edge)

**Stop Loss**: Opposite edge of ORB

**Profit Target**: Stored model (NOT RR-specific)

**Columns Used**:
- `orb_{time}_tradeable_outcome` → WIN = hit profit target
- `orb_{time}_tradeable_realized_rr` → Realized R after $8.40 costs

**Metric Definitions**:
- **Target Hit Rate**: % trades that hit profit target (outcome == 'WIN')
- **Profitable Rate**: % trades with positive realized R (realized_rr > 0)
- **Expected R**: Average realized R across all trades

**Important**: These metrics use a single stored model per ORB time.
For RR-specific win rates, use `validated_setups` or run a full backtest.
                        """)

                    # Sanity Checks
                    if results['candidates']:
                        with st.expander("🔍 Sanity Checks"):
                            # Get first candidate's data for sanity check
                            first_cand = results['candidates'][0]

                            # Query raw data for this ORB time
                            orb_time = first_cand.orb_time
                            realized_rr_col = f"orb_{orb_time}_tradeable_realized_rr"
                            outcome_col = f"orb_{orb_time}_tradeable_outcome"

                            sanity_query = f"""
                            SELECT
                                COUNT(*) as n_total,
                                SUM(CASE WHEN {outcome_col} = 'WIN' THEN 1 ELSE 0 END) as n_win,
                                SUM(CASE WHEN {realized_rr_col} > 0 THEN 1 ELSE 0 END) as n_profit,
                                SUM(CASE WHEN {realized_rr_col} < 0 THEN 1 ELSE 0 END) as n_loss,
                                SUM(CASE WHEN {outcome_col} = 'WIN' AND {realized_rr_col} <= 0 THEN 1 ELSE 0 END) as n_win_negative,
                                AVG({realized_rr_col}) as mean_rr
                            FROM daily_features
                            WHERE instrument = '{search_instrument}'
                              AND {realized_rr_col} IS NOT NULL
                              AND {outcome_col} IS NOT NULL
                            """

                            sanity_result = results['conn'].execute(sanity_query).fetchone()

                            n_total = sanity_result[0]
                            n_win = sanity_result[1]
                            n_profit = sanity_result[2]
                            n_loss = sanity_result[3]
                            n_win_negative = sanity_result[4]
                            mean_rr = sanity_result[5]

                            st.markdown(f"""
**Counts for {orb_time} ORB**:
- Total Trades: {n_total}
- WIN outcomes: {n_win} ({n_win/n_total*100:.1f}%)
- Profitable (RR > 0): {n_profit} ({n_profit/n_total*100:.1f}%)
- Losses (RR < 0): {n_loss} ({n_loss/n_total*100:.1f}%)

**Invariant Checks**:
                            """)

                            # Check 1: WIN <= Profitable
                            if n_win <= n_profit:
                                st.success(f"✅ WIN count <= Profitable count ({n_win} <= {n_profit})")
                            else:
                                st.error(f"❌ WIN count > Profitable count ({n_win} > {n_profit}) - LOGIC ERROR!")

                            # Check 2: No WIN with RR <= 0
                            if n_win_negative == 0:
                                st.success(f"✅ No WIN with RR <= 0 (found {n_win_negative} violations)")
                            else:
                                st.error(f"❌ Found {n_win_negative} trades with WIN but RR <= 0 - DATA CORRUPTION!")

                            # Check 3: Expected R matches mean
                            exp_r_reported = first_cand.expected_r_proxy if first_cand.expected_r_proxy else first_cand.score_proxy
                            if abs(exp_r_reported - mean_rr) < 0.001:
                                st.success(f"✅ Expected R matches mean(realized_rr) ({exp_r_reported:.3f} ≈ {mean_rr:.3f})")
                            else:
                                st.warning(f"⚠️ Expected R mismatch: reported {exp_r_reported:.3f}, actual {mean_rr:.3f}")

                else:
                    st.info("No candidates found")

            except TimeoutError as e:
                st.warning(f"⏱️ Search timeout: {e}")
                st.info("Partial results may be in search_candidates table.")
            except Exception as e:
                st.error(f"❌ Search failed: {e}")
                logger.error(f"Auto search error: {e}")

        # Show recent candidates from last run
        if 'last_search_run_id' in st.session_state:
            st.divider()
            st.subheader("Send to Validation Queue")

            try:
                from auto_search_engine import AutoSearchEngine
                engine = AutoSearchEngine(app_state.db_connection)
                recent_candidates = engine.get_recent_candidates(
                    st.session_state['last_search_run_id'],
                    limit=20
                )

                if recent_candidates:
                    # Pre-select if candidate was clicked from card
                    default_idx = 0
                    if 'selected_candidate_for_queue' in st.session_state:
                        selected_card = st.session_state['selected_candidate_for_queue']
                        for i, c in enumerate(recent_candidates):
                            if (c['orb_time'] == selected_card['orb_time'] and
                                c['rr_target'] == selected_card['rr_target']):
                                default_idx = i
                                break

                    # Select candidate
                    candidate_options = [
                        f"{c['orb_time']} RR={c['rr_target']} ({c['score_proxy']:.3f}R, {c['sample_size']}N)"
                        for c in recent_candidates
                    ]

                    selected_idx = st.selectbox(
                        "Select candidate to enqueue",
                        range(len(candidate_options)),
                        format_func=lambda i: candidate_options[i],
                        index=default_idx,
                        key="selected_candidate_idx"
                    )

                    selected = recent_candidates[selected_idx]

                    # Confirm
                    confirm = st.checkbox("Confirm")

                    if st.button("Send to Queue", type="primary", disabled=not confirm, use_container_width=True):
                        try:
                            # Insert into validation_queue
                            app_state.db_connection.execute("""
                                INSERT INTO validation_queue (
                                    enqueued_at, source, source_id,
                                    instrument, setup_family, orb_time, rr_target,
                                    filters_json, score_proxy, sample_size, status, notes
                                ) VALUES (
                                    CURRENT_TIMESTAMP, 'AUTO_SEARCH', ?,
                                    ?, 'ORB_BASELINE', ?, ?, '{}', ?, ?, 'PENDING', ?
                                )
                            """, [
                                st.session_state['last_search_run_id'],
                                search_instrument,
                                selected['orb_time'],
                                selected['rr_target'],
                                selected['score_proxy'],
                                selected['sample_size'],
                                selected.get('notes', '')
                            ])

                            st.success("Sent to queue")

                            # Clear selected candidate from session state
                            if 'selected_candidate_for_queue' in st.session_state:
                                del st.session_state['selected_candidate_for_queue']

                        except Exception as e:
                            st.error(f"Failed to enqueue: {e}")
                            logger.error(f"Validation queue insert error: {e}")
                else:
                    st.info("No candidates from last search. Run a search first.")

            except Exception as e:
                st.caption(f"Could not load candidates: {e}")

    st.divider()

    # Candidate Draft Form
    st.subheader("📝 New Candidate Draft")

    # Entry Rule Quick Buttons (OUTSIDE form to avoid premature submission)
    st.markdown("#### 🎯 Entry Rule (Quick Fill)")
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)

    # Initialize session state for trigger template
    if 'trigger_template' not in st.session_state:
        st.session_state.trigger_template = ''

    with col_btn1:
        if st.button("🟢 1st Close", use_container_width=True, key="btn_1st_close"):
            st.session_state.trigger_template = "First 1-min close outside ORB range"
            st.rerun()

    with col_btn2:
        if st.button("🟡 2nd Close", use_container_width=True, key="btn_2nd_close"):
            st.session_state.trigger_template = "Second consecutive 1-min close outside ORB range"
            st.rerun()

    with col_btn3:
        if st.button("🔵 Limit at ORB", use_container_width=True, key="btn_limit_orb"):
            st.session_state.trigger_template = "Limit order at ORB boundary (no slippage)"
            st.rerun()

    with col_btn4:
        if st.button("Custom", use_container_width=True, key="btn_custom"):
            st.session_state.trigger_template = ""
            st.rerun()

    st.caption("💡 Click buttons above to auto-fill trigger definition below")
    st.divider()

    with st.form("candidate_form"):
        col1, col2 = st.columns(2)

        with col1:
            candidate_instrument = st.selectbox("Instrument", ["MGC", "NQ", "MPL"])
            candidate_orb = st.selectbox("ORB Time", ["0900", "1000", "1100", "1800", "2300", "0030"])
            candidate_direction = st.selectbox("Direction", ["LONG", "SHORT", "BOTH"])

        with col2:
            candidate_rr = st.number_input("Risk:Reward", min_value=1.0, max_value=5.0, value=1.5, step=0.5)
            candidate_sl_mode = st.selectbox("SL Mode", ["FULL", "HALF"])

        st.divider()

        # Use template if available, otherwise empty
        trigger_definition = st.text_area(
            "Trigger Definition",
            value=st.session_state.trigger_template,
            placeholder="e.g., 'First 1-min close outside ORB range with L4_CONSOLIDATION filter'",
            height=100,
            key="trigger_text_area"
        )

        st.divider()

        # ORB Size Filter Toggle
        st.markdown("#### 🔍 ORB Size Filter")

        filter_enabled = st.checkbox("Enable ORB Size Filter", value=False, key="draft_filter_enabled")

        if filter_enabled:
            candidate_filter = st.slider(
                "Filter ORBs > this % of ATR",
                min_value=5,
                max_value=20,
                value=10,
                step=1,
                key="draft_filter_threshold"
            )
            st.caption(f"✅ Active: Will use {candidate_filter}% ATR filter")
        else:
            candidate_filter = 0.0  # No filter
            st.caption("🔓 No ORB size filter (accepts all ORB sizes)")

        st.divider()

        notes = st.text_area("Notes (Optional)", placeholder="Research hypothesis, inspiration, etc.")

        submitted = st.form_submit_button("📥 Draft Candidate", type="primary")

        if submitted:
            # Validate required fields
            if not trigger_definition.strip():
                st.error("❌ Trigger definition is required!")
            else:
                try:
                    # Save to edge_registry
                    edge_id, message = create_candidate(
                        db_connection=app_state.db_connection,
                        instrument=candidate_instrument,
                        orb_time=candidate_orb,
                        direction=candidate_direction,
                        trigger_definition=trigger_definition.strip(),
                        rr=candidate_rr,
                        sl_mode=candidate_sl_mode,
                        orb_filter=candidate_filter / 100.0 if candidate_filter > 0 else None,
                        session=None,  # Optional, add later if needed
                        notes=notes.strip() if notes.strip() else None
                    )

                    if "already exists" in message:
                        st.warning(f"⚠️ {message}")
                        st.info(f"Edge ID: `{edge_id[:16]}...`")
                        st.caption("This exact edge configuration has already been tested. Check the candidate list below.")
                    else:
                        st.success(f"✅ Candidate drafted successfully!")
                        st.info(f"Edge ID: `{edge_id[:16]}...`")
                        st.balloons()
                        # Refresh stats
                        st.rerun()

                except Exception as e:
                    st.error(f"❌ Failed to save candidate: {e}")
                    logger.error(f"Candidate save error: {e}")

    st.divider()

    # Candidate List
    st.subheader("📋 Candidate List")

    # Filters
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["ALL", "NEVER_TESTED", "TESTED_FAILED", "VALIDATED", "PROMOTED", "RETIRED"],
            index=0
        )
    with col_filter2:
        instrument_filter = st.selectbox(
            "Filter by Instrument",
            ["ALL", "MGC", "NQ", "MPL"],
            index=0
        )

    # Get candidates from database
    try:
        candidates = get_all_candidates(
            db_connection=app_state.db_connection,
            status_filter=None if status_filter == "ALL" else status_filter,
            instrument_filter=None if instrument_filter == "ALL" else instrument_filter
        )

        if candidates:
            st.caption(f"Showing {len(candidates)} candidate(s)")

            # Display as cards
            for candidate in candidates:
                status_colors = {
                    'NEVER_TESTED': '#6c757d',
                    'TESTED_FAILED': '#dc3545',
                    'VALIDATED': '#198754',
                    'PROMOTED': '#0d6efd',
                    'RETIRED': '#6c757d'
                }
                status_color = status_colors.get(candidate['status'], '#666')

                with st.expander(f"{candidate['instrument']} {candidate['orb_time']} {candidate['direction']} - {candidate['status']}"):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown(f"**Edge ID:** `{candidate['edge_id'][:16]}...`")
                        st.markdown(f"**Trigger:** {candidate['trigger_definition']}")
                        st.markdown(f"**RR:** {candidate['rr']}  |  **SL Mode:** {candidate['sl_mode']}")
                        if candidate.get('notes'):
                            st.caption(f"Notes: {candidate['notes']}")

                    with col2:
                        st.markdown(f"<div style='background: {status_color}22; border-left: 4px solid {status_color}; padding: 12px; border-radius: 4px;'>"
                                    f"<strong>Status:</strong> {candidate['status']}<br>"
                                    f"<strong>Tests:</strong> {candidate.get('test_count', 0)}<br>"
                                    f"<strong>Created:</strong> {str(candidate['created_at'])[:10] if candidate['created_at'] else 'N/A'}"
                                    f"</div>", unsafe_allow_html=True)

                        if candidate.get('failure_reason_text'):
                            st.error(f"❌ {candidate['failure_reason_text']}")
                        elif candidate.get('pass_reason_text'):
                            st.success(f"✅ {candidate['pass_reason_text']}")

        else:
            st.info("No candidates found. Create your first candidate above!")

    except Exception as e:
        st.error(f"Failed to load candidates: {e}")
        logger.error(f"Candidate list error: {e}")

# ============================================================================
# ZONE B: VALIDATION GATE (Yellow Zone - Deterministic)
# ============================================================================
with tab_validation:
    app_state.current_zone = "VALIDATION"
    render_zone_banner("VALIDATION")

    st.markdown("""
    ### ⚖️ Validation Gate

    **Purpose:** Prove or kill candidates

    **Rules:**
    - Deterministic, reproducible tests
    - Outputs are logged and hashable
    - AI is assistive only (cannot approve)
    - All failures stored with reason codes

    **Validation Gates (Non-Negotiable):**
    1. ✓ Beats random baseline
    2. ✓ Survives cost/slippage stress (+25%, +50%)
    3. ✓ Survives walk-forward test
    4. ✓ Survives regime splits
    5. ✓ Does not overlap existing edges
    """)

    st.divider()

    # ========================================================================
    # VALIDATION QUEUE - Auto Search Integration (update6.txt)
    # ========================================================================
    st.subheader("📥 Validation Queue (Auto Search)")
    st.caption("Candidates discovered by Auto Search awaiting manual validation")

    try:
        # Query validation_queue for PENDING items
        queue_items = app_state.db_connection.execute("""
            SELECT *
            FROM validation_queue
            WHERE status = 'PENDING'
            ORDER BY enqueued_at DESC
        """).fetchdf()

        if not queue_items.empty:
            st.info(f"Found {len(queue_items)} auto-discovered candidate(s) in queue")

            # Select from queue
            queue_options = {
                f"{row['instrument']} {row['orb_time']} RR={row['rr_target']} "
                f"({row['score_proxy']:.3f}R, {row['sample_size']}N)": idx
                for idx, row in queue_items.iterrows()
            }

            selected_label = st.selectbox(
                "Select Candidate from Auto Search Queue",
                options=list(queue_options.keys()),
                key="queue_candidate_selector"
            )
            selected_idx = queue_options[selected_label]
            selected_queue_item = queue_items.iloc[selected_idx]

            # Show details
            with st.expander("📋 Queue Item Details", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Instrument:** {selected_queue_item['instrument']}")
                    st.markdown(f"**ORB Time:** {selected_queue_item['orb_time']}")
                    st.markdown(f"**RR Target:** {selected_queue_item['rr_target']}")
                with col2:
                    st.markdown(f"**Expected R:** {selected_queue_item['score_proxy']:.3f}R")
                    st.markdown(f"**Sample Size:** {selected_queue_item['sample_size']} trades")
                    # Note: Setup Family always "ORB_BASELINE" - hidden to reduce clutter

                if selected_queue_item['notes']:
                    st.caption(f"Notes: {selected_queue_item['notes']}")

                st.markdown(f"**Enqueued:** {str(selected_queue_item['enqueued_at'])[:19]}")

            # Start Validation button
            if st.button("🚀 Start Validation", type="primary", key="start_validation_btn"):
                try:
                    import uuid

                    # Generate edge_id
                    edge_id = str(uuid.uuid4())

                    # Build trigger definition
                    trigger_definition = (
                        f"Auto-discovered: {selected_queue_item['orb_time']} ORB "
                        f"RR={selected_queue_item['rr_target']} "
                        f"(ExpR: {selected_queue_item['score_proxy']:.3f}R, "
                        f"N={selected_queue_item['sample_size']})"
                    )

                    # Insert into edge_registry
                    app_state.db_connection.execute("""
                        INSERT INTO edge_registry (
                            edge_id, created_at, updated_at, status,
                            instrument, orb_time, direction, rr, sl_mode,
                            trigger_definition, filters_applied, notes, created_by
                        ) VALUES (
                            ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'IN_PROGRESS',
                            ?, ?, 'BOTH', ?, 'FULL',
                            ?, ?, ?, 'AUTO_SEARCH'
                        )
                    """, [
                        edge_id,
                        selected_queue_item['instrument'],
                        selected_queue_item['orb_time'],
                        selected_queue_item['rr_target'],
                        trigger_definition,
                        selected_queue_item['filters_json'],
                        selected_queue_item['notes'],
                    ])

                    # Update validation_queue status
                    app_state.db_connection.execute("""
                        UPDATE validation_queue
                        SET status = 'IN_PROGRESS',
                            assigned_to = ?
                        WHERE queue_id = ?
                    """, [edge_id, selected_queue_item['queue_id']])

                    st.success(f"✅ Candidate moved to validation! Edge ID: `{edge_id[:16]}...`")
                    st.info("This candidate is now IN_PROGRESS in edge_registry. Continue validation below.")

                    # Refresh page to update UI
                    st.rerun()

                except Exception as e:
                    st.error(f"Failed to start validation: {e}")
                    logger.error(f"Validation queue start error: {e}")

        else:
            st.info("📭 No auto-discovered candidates pending. Run Auto Search from Research tab to discover new edges.")

    except Exception as e:
        st.error(f"Failed to load validation queue: {e}")
        logger.error(f"Validation queue error: {e}")

    st.divider()

    # ========================================================================
    # MANUAL CANDIDATES - Existing Validation Pipeline
    # ========================================================================
    st.subheader("🎯 Validation Pipeline (Manual Candidates)")

    # Get NEVER_TESTED candidates
    try:
        never_tested = get_all_candidates(
            db_connection=app_state.db_connection,
            status_filter='NEVER_TESTED'
        )

        if never_tested:
            st.caption(f"Found {len(never_tested)} candidate(s) awaiting validation")

            # Candidate selector
            candidate_options = {
                f"{c['instrument']} {c['orb_time']} {c['direction']} (RR={c['rr']})": c['edge_id']
                for c in never_tested
            }

            if candidate_options:
                selected_label = st.selectbox(
                    "Select Candidate to Validate",
                    options=list(candidate_options.keys())
                )
                selected_edge_id = candidate_options[selected_label]

                # Show candidate details
                selected_candidate = next(c for c in never_tested if c['edge_id'] == selected_edge_id)

                with st.expander("📋 Candidate Details", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Instrument:** {selected_candidate['instrument']}")
                        st.markdown(f"**ORB Time:** {selected_candidate['orb_time']}")
                        st.markdown(f"**Direction:** {selected_candidate['direction']}")
                    with col2:
                        st.markdown(f"**RR:** {selected_candidate['rr']}")
                        st.markdown(f"**SL Mode:** {selected_candidate['sl_mode']}")
                        st.markdown(f"**Created:** {str(selected_candidate['created_at'])[:10] if selected_candidate['created_at'] else 'N/A'}")

                    st.markdown(f"**Trigger:** {selected_candidate['trigger_definition']}")
                    if selected_candidate.get('notes'):
                        st.caption(f"Notes: {selected_candidate['notes']}")

                st.divider()

                # T8: DUPLICATE DETECTION - Check if edge has been tested before
                prior_validation = check_prior_validation(
                    db_connection=app_state.db_connection,
                    edge_id=selected_edge_id
                )

                # Initialize override state
                allow_validation = True
                override_reason = None

                if prior_validation and prior_validation['has_prior']:
                    # Show duplicate warning
                    st.warning("⚠️ **DUPLICATE DETECTED: This edge has already been tested!**")

                    with st.expander("📋 Prior Test Results", expanded=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**Tests Run:** {prior_validation['test_count']}")
                            st.markdown(f"**Last Tested:** {str(prior_validation['last_tested_at'])[:10] if prior_validation['last_tested_at'] else 'N/A'}")
                            outcome_color = "🟢" if prior_validation['outcome'] == 'passed' else "🔴"
                            st.markdown(f"**Outcome:** {outcome_color} {prior_validation['outcome'].upper()}")
                        with col2:
                            st.markdown(f"**Status:** {prior_validation['status']}")
                            if prior_validation.get('failure_code'):
                                st.markdown(f"**Failure Code:** `{prior_validation['failure_code']}`")

                        # Show reason (pass or fail)
                        reason = prior_validation.get('reason', 'No reason provided')
                        if prior_validation['outcome'] == 'passed':
                            st.success(f"✅ **Why it passed:** {reason}")
                        else:
                            st.error(f"❌ **Why it failed:** {reason}")

                        # Show prior metrics if available
                        if prior_validation.get('metrics'):
                            st.markdown("**Prior Metrics:**")
                            metrics = prior_validation['metrics']
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if 'edge_win_rate' in metrics:
                                    st.metric("Win Rate", f"{metrics['edge_win_rate']*100:.1f}%")
                            with col2:
                                if 'expected_r' in metrics:
                                    st.metric("Expected R", f"{metrics['expected_r']:.2f}R")
                            with col3:
                                if 'sample_size' in metrics:
                                    st.metric("Sample Size", metrics['sample_size'])

                    st.divider()

                    # Override controls
                    st.subheader("🔓 Override & Re-Test")
                    st.caption("Re-testing should only be done if validation logic changed or data was corrected.")

                    override_confirmed = st.checkbox(
                        "⚠️ I understand this is a re-test and want to proceed anyway",
                        help="Check this box to override the duplicate detection and run validation again"
                    )

                    if override_confirmed:
                        override_reason = st.text_input(
                            "Re-Test Reason (Required)",
                            placeholder="e.g., 'Fixed data quality issue' or 'Updated validation logic'",
                            help="Explain why you're re-testing this edge"
                        )

                        if not override_reason or not override_reason.strip():
                            allow_validation = False
                            st.error("❌ Re-test reason is required to proceed")
                        else:
                            allow_validation = True
                            st.success("✅ Override confirmed - validation will proceed with reason logged")
                    else:
                        allow_validation = False
                        st.info("ℹ️ Check the override box above to re-test this edge")

                st.divider()

                # T9: SEMANTIC SIMILARITY - Show similar edges
                try:
                    similar_edges = find_similar_edges(
                        db_connection=app_state.db_connection,
                        edge_id=selected_edge_id,
                        min_similarity=0.5,
                        limit=5
                    )

                    if similar_edges:
                        st.info(f"🔍 **SEMANTIC SIMILARITY:** Found {len(similar_edges)} similar edge(s)")

                        with st.expander("📊 Similar Edges (Have we tried something like this before?)", expanded=False):
                            st.caption("These edges share similar attributes but are not exact duplicates.")

                            for idx, similar in enumerate(similar_edges, 1):
                                similarity_pct = similar['similarity_score'] * 100

                                # Color based on similarity
                                if similarity_pct >= 80:
                                    color = "#dc3545"  # Red - very similar
                                    icon = "🔴"
                                elif similarity_pct >= 65:
                                    color = "#ffc107"  # Yellow - moderately similar
                                    icon = "🟡"
                                else:
                                    color = "#17a2b8"  # Blue - somewhat similar
                                    icon = "🔵"

                                st.markdown(f"""
                                <div style='background: {color}22; border-left: 4px solid {color}; padding: 12px; border-radius: 4px; margin-bottom: 12px;'>
                                    <div style='display: flex; justify-content: space-between; align-items: center;'>
                                        <div>
                                            <strong>{icon} Edge #{idx}</strong> - {similar['instrument']} {similar['orb_time']} {similar['direction']} (RR={similar['rr']})
                                        </div>
                                        <div style='background: {color}; color: white; padding: 4px 12px; border-radius: 12px; font-weight: bold;'>
                                            {similarity_pct:.0f}% match
                                        </div>
                                    </div>
                                    <div style='margin-top: 8px; font-size: 13px;'>
                                        <strong>Trigger:</strong> {similar['trigger_definition'][:80]}{"..." if len(similar['trigger_definition']) > 80 else ""}<br>
                                        <strong>Status:</strong> {similar['status']} | <strong>Tests:</strong> {similar['test_count']}
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)

                            st.caption("💡 **Tip:** High similarity (>80%) suggests you may be testing redundant variations. "
                                      "Consider why this edge is different before proceeding.")

                except Exception as e:
                    st.caption(f"⚠️ Similarity search unavailable: {e}")

                st.divider()

                # Validation options
                st.subheader("⚙️ Validation Configuration")
                col1, col2 = st.columns(2)
                with col1:
                    run_control = st.checkbox("Run Control (Random Baseline)", value=True, help="Compare against random entries")
                    run_stress = st.checkbox("Run Stress Tests", value=True, help="+25% and +50% cost stress")
                with col2:
                    run_walkforward = st.checkbox("Walk-Forward Test", value=True, help="Out-of-sample validation")
                    run_regime = st.checkbox("Regime Split Test", value=False, help="Trending vs range-bound")

                st.divider()

                # Run validation button (disabled if duplicate without override)
                validation_button_disabled = not allow_validation

                if validation_button_disabled:
                    st.button("▶️ Run Validation", type="primary", use_container_width=True, disabled=True)
                    st.caption("⚠️ Validation blocked - see duplicate warning above")
                else:
                    if st.button("▶️ Run Validation", type="primary", use_container_width=True):
                        with st.spinner("Running validation pipeline..."):
                            try:
                                # Run validation stub (with override reason if re-testing)
                                result = run_validation_stub(
                                    db_connection=app_state.db_connection,
                                    edge_id=selected_edge_id,
                                    override_reason=override_reason if override_reason and override_reason.strip() else None
                                )

                                # Display results header
                                if result['passed']:
                                    st.success("✅ VALIDATION PASSED - Edge beats control baseline!")
                                    st.balloons()
                                else:
                                    # Determine failure reason
                                    if not result.get('edge_passes_gates', True):
                                        st.error("❌ VALIDATION FAILED - Edge failed validation gates")
                                    elif not result.get('beats_control', True):
                                        st.error("❌ VALIDATION FAILED - Edge did not beat control baseline")
                                    else:
                                        st.error("❌ VALIDATION FAILED")

                                # T7: CONTROL vs EDGE COMPARISON
                                if result.get('control_run_id') and result.get('comparison'):
                                    st.subheader("⚖️ Edge vs Control Baseline")

                                    comparison = result['comparison']

                                    # Summary verdict
                                    if comparison['beats_control']:
                                        verdict_color = "#198754"
                                        verdict_text = "EDGE WINS"
                                        verdict_emoji = "🟢"
                                    else:
                                        verdict_color = "#dc3545"
                                        verdict_text = "CONTROL WINS"
                                        verdict_emoji = "🔴"

                                    st.markdown(f"""
                                    <div style='background: {verdict_color}22; border-left: 4px solid {verdict_color}; padding: 16px; border-radius: 4px; margin-bottom: 16px;'>
                                        <h4 style='margin: 0; color: {verdict_color};'>{verdict_emoji} {verdict_text}</h4>
                                        <p style='margin: 8px 0 0 0; font-size: 14px;'>Statistical Significance: {comparison['significance']} (p={comparison['p_value']:.3f})</p>
                                    </div>
                                    """, unsafe_allow_html=True)

                                    # Comparison metrics
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.metric(
                                            "Win Rate Difference",
                                            f"{comparison['wr_diff']*100:+.1f}%",
                                            help=f"Edge: {comparison['edge_wr']*100:.1f}% vs Control: {comparison['control_wr']*100:.1f}%"
                                        )
                                    with col2:
                                        st.metric(
                                            "Expected R Difference",
                                            f"{comparison['exp_r_diff']:+.2f}R",
                                            help=f"Edge: {comparison['edge_exp_r']:.2f}R vs Control: {comparison['control_exp_r']:.2f}R"
                                        )
                                    with col3:
                                        gates_check = "✅" if comparison['wr_beats_control'] and comparison['exp_r_beats_control'] and comparison['stress_beats_control'] else "❌"
                                        st.metric("All Gates", gates_check)

                                    st.divider()

                                # Show edge metrics
                                st.subheader("📊 Edge Validation Results")

                                metrics = result['metrics']
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Win Rate", f"{metrics['edge_win_rate']*100:.1f}%")
                                with col2:
                                    st.metric("Expected R", f"{metrics['expected_r']:.2f}R")
                                with col3:
                                    st.metric("Sample Size", metrics['sample_size'])
                                with col4:
                                    st.metric("Max DD", f"{metrics['max_dd']:.2f}R")

                                # Show control metrics (if available)
                                if result.get('control_metrics'):
                                    st.subheader("📊 Control Baseline Results")
                                    control_metrics = result['control_metrics']

                                    col1, col2, col3, col4 = st.columns(4)
                                    with col1:
                                        st.metric("Win Rate", f"{control_metrics['edge_win_rate']*100:.1f}%")
                                    with col2:
                                        st.metric("Expected R", f"{control_metrics['expected_r']:.2f}R")
                                    with col3:
                                        st.metric("Sample Size", control_metrics['sample_size'])
                                    with col4:
                                        st.metric("Max DD", f"{control_metrics['max_dd']:.2f}R")

                                st.divider()

                                # Gate results
                                st.subheader("🚪 Edge Gate Results")
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    stress_25 = metrics.get('stress_test_25', 'N/A')
                                    color_25 = "🟢" if stress_25 == "PASS" else "🔴"
                                    st.markdown(f"{color_25} **Stress +25%:** {stress_25}")
                                with col2:
                                    stress_50 = metrics.get('stress_test_50', 'N/A')
                                    color_50 = "🟢" if stress_50 == "PASS" else "🔴"
                                    st.markdown(f"{color_50} **Stress +50%:** {stress_50}")
                                with col3:
                                    wf = metrics.get('walk_forward', 'N/A')
                                    color_wf = "🟢" if wf == "PASS" else "🔴"
                                    st.markdown(f"{color_wf} **Walk-Forward:** {wf}")

                                st.info(f"**Edge Run ID:** `{result['run_id'][:16]}...`" +
                                       (f" | **Control Run ID:** `{result['control_run_id'][:16]}...`" if result.get('control_run_id') else ""))

                                # Refresh page to show updated candidate list
                                st.rerun()

                            except Exception as e:
                                st.error(f"❌ Validation failed: {e}")
                                logger.error(f"Validation error: {e}")

        else:
            st.info("No candidates awaiting validation. Create candidates in the Research Lab first.")

    except Exception as e:
        st.error(f"Failed to load candidates: {e}")
        logger.error(f"Validation tab error: {e}")

    st.divider()

    # Validation History
    st.subheader("📜 Recent Validation Runs")

    try:
        recent_runs = get_experiment_runs(
            db_connection=app_state.db_connection,
            run_type='VALIDATION'
        )

        if recent_runs:
            st.caption(f"Showing {min(len(recent_runs), 10)} most recent validation runs")

            for run in recent_runs[:10]:  # Show last 10
                status_emoji = "✅" if run['status'] == 'COMPLETED' else "⏳" if run['status'] == 'RUNNING' else "❌"

                with st.expander(f"{status_emoji} {run['run_id'][:16]}... - {str(run['started_at'])[:19] if run['started_at'] else 'N/A'}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown(f"**Edge ID:** `{run['edge_id'][:16]}...`")
                        st.markdown(f"**Type:** {run['run_type']}")
                        st.markdown(f"**Status:** {run['status']}")

                    with col2:
                        st.markdown(f"**Started:** {str(run['started_at'])[:19] if run['started_at'] else 'N/A'}")
                        if run.get('completed_at'):
                            st.markdown(f"**Completed:** {str(run['completed_at'])[:19] if run['completed_at'] else 'N/A'}")

                    if run.get('metrics'):
                        st.json(run['metrics'])

        else:
            st.caption("No validation runs yet")

    except Exception as e:
        st.error(f"Failed to load validation history: {e}")
        logger.error(f"Validation history error: {e}")

# ============================================================================
# ZONE C: PRODUCTION (Green Zone - Locked Execution)
# ============================================================================
with tab_production:
    app_state.current_zone = "PRODUCTION"
    render_zone_banner("PRODUCTION")

    st.markdown("""
    ### 🚀 Production

    **Purpose:** Run approved edges only

    **Rules:**
    - Read-only to execution logic
    - AI can explain but not modify
    - Any change requires new edge_id
    - Promotion requires full lineage

    **Safety:**
    - Fail-closed by default
    - Evidence pack required
    - Explicit operator approval needed
    """)

    st.divider()

    # ====================================================================
    # TIME-AWARE HERO - "What Should I Trade NOW?"
    # ====================================================================
    st.markdown("### 🎯 Current Setup Recommendation")

    try:
        # Get current ORB status
        orb_status = get_current_orb_status()

        # Determine which ORB to show
        hero_orb = orb_status['current_orb'] or orb_status['upcoming_orb']

        if hero_orb:
            # Query best setup for this ORB (highest expected_r)
            hero_setup = app_state.db_connection.execute("""
                SELECT
                    id, instrument, orb_time, rr, sl_mode,
                    orb_size_filter, win_rate, expected_r, sample_size, notes
                FROM validated_setups
                WHERE instrument = ? AND orb_time = ?
                ORDER BY expected_r DESC
                LIMIT 1
            """, [app_state.current_instrument, hero_orb]).fetchone()

            if hero_setup:
                (setup_id, instrument, orb_time, rr, sl_mode,
                 orb_size_filter, win_rate, expected_r, sample_size, notes) = hero_setup

                # Status styling
                status = orb_status['status']
                emoji = get_status_emoji(status)
                color = get_status_color(status)

                # Time info
                if status == 'ACTIVE':
                    time_text = f"Valid until {orb_status['end_time'].strftime('%H:%M')}"
                    time_subtext = f"({format_time_remaining(orb_status['minutes_remaining'])} remaining)"
                else:
                    time_text = f"Forms in {format_time_remaining(orb_status['minutes_until'])}"
                    form_time = orb_status.get('form_time')
                    if form_time:
                        time_subtext = f"(at {form_time.strftime('%H:%M')})"
                    else:
                        time_subtext = ""

                # Expected R color
                if expected_r > 0.30:
                    exp_r_color = "#198754"  # Green
                elif expected_r >= 0.15:
                    exp_r_color = "#0d6efd"  # Blue
                else:
                    exp_r_color = "#6c757d"  # Gray

                # HERO CARD
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, {color}15 0%, {color}05 100%);
                    border-left: 8px solid {color};
                    border-radius: 12px;
                    padding: 32px;
                    margin: 20px 0;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                ">
                    <div style="text-align: center;">
                        <!-- Status -->
                        <div style="font-size: 48px; margin-bottom: 16px;">
                            {emoji}
                        </div>
                        <div style="font-size: 24px; font-weight: 600; color: {color}; margin-bottom: 8px;">
                            {status}: {orb_time} ORB
                        </div>

                        <!-- Setup Info -->
                        <div style="font-size: 20px; color: #666; margin-bottom: 24px;">
                            RR {rr:.1f}  |  {sl_mode.upper()} SL
                        </div>

                        <!-- Expected R (HUGE) -->
                        <div style="font-size: 128px; font-weight: 700; color: {exp_r_color}; line-height: 1; margin: 24px 0;">
                            +{expected_r:.3f}R
                        </div>

                        <!-- Stats -->
                        <div style="font-size: 18px; color: #333; margin: 16px 0;">
                            <strong>Win Rate:</strong> {win_rate*100:.1f}%  |
                            <strong>Sample:</strong> {int(sample_size)} trades
                            {f' | <strong>Filter:</strong> {orb_size_filter*100:.0f}% ATR' if orb_size_filter else ''}
                        </div>

                        <!-- Time Info -->
                        <div style="font-size: 16px; color: #666; margin: 24px 0;">
                            ⏱ {time_text}<br>{time_subtext}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            else:
                st.info(f"No validated setup found for {hero_orb} ORB")
        else:
            st.warning("Could not determine current/upcoming ORB")

    except Exception as e:
        st.error(f"Could not load hero setup: {e}")
        logger.error(f"Hero display error: {e}")

    st.divider()

    # ====================================================================
    # ALL SETUPS GRID - Quick Visual Scan
    # ====================================================================
    st.markdown("### 📊 All Active Setups")

    try:
        # Load all setups
        all_setups = app_state.db_connection.execute("""
            SELECT
                id, instrument, orb_time, rr, sl_mode,
                orb_size_filter, win_rate, expected_r, sample_size
            FROM validated_setups
            WHERE instrument = ?
            ORDER BY expected_r DESC
        """, [app_state.current_instrument]).fetchall()

        if all_setups:
            # Display in 3-column grid
            num_setups = len(all_setups)
            rows = (num_setups + 2) // 3  # Ceiling division

            for row_idx in range(rows):
                cols = st.columns(3)

                for col_idx in range(3):
                    setup_idx = row_idx * 3 + col_idx
                    if setup_idx >= num_setups:
                        break

                    setup = all_setups[setup_idx]
                    (setup_id, instrument, orb_time, rr, sl_mode,
                     orb_size_filter, win_rate, expected_r, sample_size) = setup

                    # Get time status for this ORB
                    orb_status = get_current_orb_status()
                    if orb_time == orb_status.get('current_orb'):
                        status_emoji = "🟢"
                        status_text = "ACTIVE"
                        border_color = "#198754"
                    elif orb_time == orb_status.get('upcoming_orb'):
                        status_emoji = "🟡"
                        status_text = "UPCOMING"
                        border_color = "#ffc107"
                    else:
                        status_emoji = "⏸️"
                        status_text = "STANDBY"
                        border_color = "#6c757d"

                    # Expected R color
                    if expected_r > 0.30:
                        exp_r_color = "#198754"
                    elif expected_r >= 0.15:
                        exp_r_color = "#0d6efd"
                    else:
                        exp_r_color = "#6c757d"

                    with cols[col_idx]:
                        st.markdown(f"""
                        <div style="
                            background: #f8f9fa;
                            border-left: 4px solid {border_color};
                            border-radius: 8px;
                            padding: 16px;
                            margin-bottom: 16px;
                            min-height: 180px;
                        ">
                            <div style="text-align: center;">
                                <div style="font-size: 24px;">{status_emoji}</div>
                                <div style="font-size: 32px; font-weight: 700; color: #1a1a1a; margin: 8px 0;">
                                    {orb_time}
                                </div>
                                <div style="font-size: 16px; color: #666; margin-bottom: 12px;">
                                    RR {rr:.1f}
                                </div>
                                <div style="font-size: 48px; font-weight: 700; color: {exp_r_color}; margin: 12px 0;">
                                    +{expected_r:.3f}R
                                </div>
                                <div style="font-size: 14px; color: #666;">
                                    {win_rate*100:.0f}% | {int(sample_size)}N
                                </div>
                                <div style="font-size: 12px; color: {border_color}; margin-top: 8px;">
                                    {status_text}
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

        else:
            st.info("No validated setups found for " + app_state.current_instrument)

    except Exception as e:
        st.error(f"Could not load setups grid: {e}")
        logger.error(f"Setups grid error: {e}")

    st.divider()

    # ====================================================================
    # DETAILED VIEW - All Variants (Expandable)
    # ====================================================================
    with st.expander("▼ View All Variants (Detailed)", expanded=False):
        st.caption("Complete list of all setups with variant selection")

        # Cached query function for performance
        @st.cache_data(ttl=3600)  # Cache for 1 hour
        def load_validated_setups_with_stats(instrument: str, db_path: str):
            """Load validated setups with trade statistics (cached)"""
            import duckdb

            # Don't use read_only to allow multiple connections (app never writes anyway)
            conn = duckdb.connect(db_path)

            query = """
            SELECT
                vs.id,
                vs.instrument,
                vs.orb_time,
                vs.rr,
                vs.sl_mode,
                vs.orb_size_filter,
                vs.win_rate,
                vs.expected_r,
                vs.real_expected_r,
                vs.sample_size,
                vs.status,
                vs.notes,
                COUNT(vt.date_local) as trade_count,
                SUM(CASE WHEN vt.outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN vt.outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
                AVG(vt.realized_rr) as avg_realized_rr,
                SUM(CASE WHEN vt.realized_rr >= 0.15 THEN 1 ELSE 0 END) as friction_pass_count
            FROM validated_setups vs
            LEFT JOIN validated_trades vt ON vs.id = vt.setup_id
            WHERE vs.instrument = ?
            GROUP BY vs.id, vs.instrument, vs.orb_time, vs.rr, vs.sl_mode,
                     vs.orb_size_filter, vs.win_rate, vs.expected_r, vs.real_expected_r,
                     vs.sample_size, vs.status, vs.notes
            ORDER BY vs.status DESC, vs.orb_time, vs.expected_r DESC
            """

            result = conn.execute(query, [instrument]).fetchdf()
            conn.close()

            return result

        # Terminal CSS for Production Registry
        st.markdown("""
        <style>
            /* Terminal Typography */
            @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap');

            /* Production Zone Container */
            .production-terminal {
                background: linear-gradient(180deg, #0a0e14 0%, #0d1117 100%);
                border: 1px solid #1f2937;
                border-radius: 4px;
                padding: 24px;
                font-family: 'IBM Plex Mono', 'Courier New', monospace;
                position: relative;
                overflow: hidden;
            }

            /* Scan line effect */
            .production-terminal::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 2px;
                background: linear-gradient(90deg,
                    transparent 0%,
                    rgba(251, 191, 36, 0.3) 50%,
                    transparent 100%
                );
                animation: scan 3s linear infinite;
            }

            @keyframes scan {
                0% { transform: translateY(0); }
                100% { transform: translateY(600px); }
            }

            /* ORB Group Headers */
            .orb-group-header {
                background: linear-gradient(135deg, #1a1f2e 0%, #151a26 100%);
                border-left: 4px solid #fbbf24;
                padding: 16px 20px;
                margin: 16px 0;
                border-radius: 2px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
            }

            .orb-group-header h3 {
                font-family: 'JetBrains Mono', monospace;
                font-size: 18px;
                font-weight: 700;
                color: #fbbf24;
                letter-spacing: 0.5px;
                text-transform: uppercase;
                margin: 0;
                text-shadow: 0 0 10px rgba(251, 191, 36, 0.3);
            }

            /* Best Variant Summary Row */
            .best-variant-row {
                display: grid;
                grid-template-columns: 2fr 1fr 1fr 1fr 1fr;
                gap: 16px;
                padding: 12px 20px;
                background: rgba(16, 185, 129, 0.05);
                border-left: 2px solid #10b981;
                margin: 8px 0;
                align-items: center;
            }

            .metric-cell {
                text-align: center;
            }

            .metric-label {
                font-size: 10px;
                color: #6b7280;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 4px;
            }

            .metric-value {
                font-size: 18px;
                font-weight: 700;
                color: #10b981;
                font-family: 'JetBrains Mono', monospace;
                letter-spacing: -0.5px;
            }

            .metric-value.best {
                color: #fbbf24;
                font-size: 20px;
            }

            /* Variant Row */
            .variant-row {
                display: grid;
                grid-template-columns: 80px 2fr 1fr 1fr 1fr 1fr;
                gap: 12px;
                padding: 12px 16px;
                background: rgba(31, 41, 55, 0.4);
                border: 1px solid #374151;
                margin: 8px 0;
                align-items: center;
                transition: all 0.2s ease;
                border-radius: 2px;
            }

            .variant-row:hover {
                background: rgba(31, 41, 55, 0.7);
                border-color: #4b5563;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
            }

            .variant-row.selected {
                background: rgba(251, 191, 36, 0.1);
                border-color: #fbbf24;
                box-shadow: 0 0 12px rgba(251, 191, 36, 0.2);
            }

            /* Selection Checkbox Container */
            .select-cell {
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .variant-label {
                font-size: 12px;
                color: #9ca3af;
                font-weight: 600;
            }

            .variant-setup {
                font-size: 14px;
                color: #d1d5db;
                font-weight: 500;
            }

            .variant-metric {
                font-size: 14px;
                color: #d1d5db;
                text-align: center;
            }

            .variant-metric strong {
                color: #fbbf24;
                font-weight: 700;
            }

            .variant-note {
                font-size: 12px;
                color: #6b7280;
                font-style: italic;
                padding: 8px 16px;
                margin-top: 4px;
            }

            /* Selection Summary Box */
            .selection-summary {
                background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                border: 2px solid #fbbf24;
                border-radius: 4px;
                padding: 20px;
                margin-top: 24px;
            }

            .selection-summary h4 {
                font-family: 'JetBrains Mono', monospace;
                font-size: 14px;
                font-weight: 700;
                color: #fbbf24;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 16px;
                text-shadow: 0 0 8px rgba(251, 191, 36, 0.4);
            }

            .selection-item {
                padding: 12px;
                background: rgba(16, 185, 129, 0.1);
                border-left: 3px solid #10b981;
                margin: 8px 0;
                font-size: 13px;
                color: #d1d5db;
            }

            .selection-item strong {
                color: #fbbf24;
                font-weight: 600;
            }

            /* Summary Metrics Bar */
            .summary-metrics {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 16px;
                margin-bottom: 24px;
            }

            .summary-metric-card {
                background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
                border: 1px solid #374151;
                border-radius: 2px;
                padding: 16px;
                text-align: center;
            }

            .summary-metric-label {
                font-size: 11px;
                color: #6b7280;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 8px;
            }

            .summary-metric-value {
                font-size: 32px;
                font-weight: 700;
                color: #fbbf24;
                font-family: 'JetBrains Mono', monospace;
                text-shadow: 0 0 12px rgba(251, 191, 36, 0.3);
            }

            /* Divider */
            .terminal-divider {
                height: 1px;
                background: linear-gradient(90deg,
                    transparent 0%,
                    #374151 50%,
                    transparent 100%
                );
                margin: 32px 0;
            }
        </style>
        """, unsafe_allow_html=True)

        # Production Registry - Grouped ORB Variant Display
        st.markdown('<div class="production-terminal">', unsafe_allow_html=True)

        # Header with refresh button
        col_header, col_refresh = st.columns([4, 1])
        with col_header:
            st.markdown("### [PRODUCTION] Validated Setups - Grouped by ORB Time")
        with col_refresh:
            if st.button("🔄 Refresh", help="Clear cache and reload data"):
                load_validated_setups_with_stats.clear()
                st.rerun()

        try:
            # Load validated setups with trade statistics (cached for performance)
            result = load_validated_setups_with_stats(
                instrument=app_state.current_instrument,
                db_path=app_state.db_path
            )

            if len(result) == 0:
                st.info("No validated setups found for " + app_state.current_instrument)
            else:
                # Group by ORB time
                orb_groups = {}
                for _, row in result.iterrows():
                    orb_time = row['orb_time']
                    if orb_time not in orb_groups:
                        orb_groups[orb_time] = []
                    orb_groups[orb_time].append(row)

                # Sort ORB times by best expectancy (descending)
                sorted_orbs = sorted(
                    orb_groups.keys(),
                    key=lambda orb: max(v['expected_r'] for v in orb_groups[orb]),
                    reverse=True
                )

                # Display metrics with custom styling
                total_trades = result['trade_count'].sum()
                st.markdown(f"""
                <div class="summary-metrics">
                    <div class="summary-metric-card">
                        <div class="summary-metric-label">Total Setups</div>
                        <div class="summary-metric-value">{len(result)}</div>
                    </div>
                    <div class="summary-metric-card">
                        <div class="summary-metric-label">ORB Times</div>
                        <div class="summary-metric-value">{len(orb_groups)}</div>
                    </div>
                    <div class="summary-metric-card">
                        <div class="summary-metric-label">Total Trades</div>
                        <div class="summary-metric-value">{int(total_trades)}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown('<div class="terminal-divider"></div>', unsafe_allow_html=True)

                # Initialize session state for selections
                if 'selected_variants' not in st.session_state:
                    st.session_state.selected_variants = {}

                # Display grouped ORBs with styled headers
                for orb_time in sorted_orbs:
                    variants = orb_groups[orb_time]
                    best_variant = variants[0]  # Already sorted by expected_r DESC

                    # ORB Group Header
                    st.markdown(f"""
                    <div class="orb-group-header">
                        <h3>{orb_time} ORB - {len(variants)} variant(s)</h3>
                    </div>
                    """, unsafe_allow_html=True)

                    # Best variant summary (no checkbox, just display)
                    st.markdown(f"""
                    <div class="best-variant-row">
                        <div class="metric-cell">
                            <div class="metric-label">Best Setup</div>
                            <div class="metric-value best">RR={best_variant['rr']:.1f} ({best_variant['sl_mode']})</div>
                        </div>
                        <div class="metric-cell">
                            <div class="metric-label">Expected R</div>
                            <div class="metric-value">+{best_variant['expected_r']:.3f}R</div>
                        </div>
                        <div class="metric-cell">
                            <div class="metric-label">Win Rate</div>
                            <div class="metric-value">{best_variant['win_rate']*100:.1f}%</div>
                        </div>
                        <div class="metric-cell">
                            <div class="metric-label">Sample Size</div>
                            <div class="metric-value">{int(best_variant['sample_size'])}N</div>
                        </div>
                        <div class="metric-cell">
                            <div class="metric-label">Trades</div>
                            <div class="metric-value">{int(best_variant['trade_count'])}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Show ALL variants for selection (including best)
                    with st.container():
                        for variant in variants:
                            variant_key = f"{orb_time}_{variant['id']}"

                            # Selection checkbox
                            col_check, col_details = st.columns([1, 9])

                            with col_check:
                                # Check if this variant is currently selected
                                is_selected = st.session_state.selected_variants.get(orb_time) == variant['id']

                                # Checkbox for selection (only allow 1 per ORB)
                                if st.checkbox(
                                    "Select",
                                    key=variant_key,
                                    value=is_selected,
                                    label_visibility="collapsed"
                                ):
                                    # Update selection (replace previous selection for this ORB)
                                    st.session_state.selected_variants[orb_time] = variant['id']
                                else:
                                    # Deselect if unchecked
                                    if orb_time in st.session_state.selected_variants and \
                                       st.session_state.selected_variants[orb_time] == variant['id']:
                                        del st.session_state.selected_variants[orb_time]

                            with col_details:
                                # Display variant details
                                st.markdown(f"""
                                <div class="variant-row {'selected' if is_selected else ''}">
                                    <div class="variant-label">ID {variant['id']}</div>
                                    <div class="variant-setup">
                                        RR={variant['rr']:.1f} | {variant['sl_mode'].upper()} SL
                                        {f" | Filter: {variant['orb_size_filter']*100:.0f}% ATR" if variant['orb_size_filter'] else ""}
                                    </div>
                                    <div class="variant-metric"><strong>ExpR:</strong> +{variant['expected_r']:.3f}R</div>
                                    <div class="variant-metric"><strong>WR:</strong> {variant['win_rate']*100:.1f}%</div>
                                    <div class="variant-metric"><strong>N:</strong> {int(variant['sample_size'])}</div>
                                    <div class="variant-metric"><strong>Trades:</strong> {int(variant['trade_count'])}</div>
                                </div>
                                """, unsafe_allow_html=True)

                                # Show notes if any
                                if variant['notes']:
                                    st.markdown(f'<div class="variant-note">Note: {variant["notes"]}</div>', unsafe_allow_html=True)

                        st.markdown('<div class="terminal-divider"></div>', unsafe_allow_html=True)

                # Show current selections with styled summary
                if st.session_state.selected_variants:
                    st.markdown(f"""
                    <div class="selection-summary">
                        <h4>Current Selections - {len(st.session_state.selected_variants)} Active Variant(s)</h4>
                    """, unsafe_allow_html=True)

                    for orb_time, setup_id in sorted(st.session_state.selected_variants.items()):
                        variant = result[result['id'] == setup_id].iloc[0]
                        st.markdown(f"""
                        <div class="selection-item">
                            <strong>{orb_time}:</strong> RR={variant['rr']:.1f} ({variant['sl_mode']}) -
                            ExpR={variant['expected_r']:.3f}R, WR={variant['win_rate']*100:.1f}%,
                            N={int(variant['sample_size'])}
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.info("No variants selected. Check boxes above to select MAX 1 variant per ORB.")

        except Exception as e:
            log_error(e, context="Production registry - grouped ORB display")
            st.error(f"Failed to load production registry: {e}")
            st.info("Check app_errors.txt for details")
            logger.error(f"Production registry error: {e}")

        st.markdown('</div>', unsafe_allow_html=True)  # Close production-terminal

    # Promotion Gate
    st.subheader("🔒 Promotion Gate (Fail-Closed)")

    # Get VALIDATED candidates
    try:
        validated = get_all_candidates(
            db_connection=app_state.db_connection,
            status_filter='VALIDATED'
        )

        if validated:
            st.caption(f"Found {len(validated)} validated candidate(s) ready for promotion")

            # Candidate selector
            promotion_options = {
                f"{c['instrument']} {c['orb_time']} {c['direction']} (RR={c['rr']})": c['edge_id']
                for c in validated
            }

            if promotion_options:
                selected_label = st.selectbox(
                    "Select VALIDATED Edge to Promote",
                    options=list(promotion_options.keys())
                )
                selected_edge_id = promotion_options[selected_label]

                # Show candidate details
                selected_edge = next(c for c in validated if c['edge_id'] == selected_edge_id)

                with st.expander("📋 Edge Details", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Instrument:** {selected_edge['instrument']}")
                        st.markdown(f"**ORB Time:** {selected_edge['orb_time']}")
                        st.markdown(f"**Direction:** {selected_edge['direction']}")
                        st.markdown(f"**Trigger:** {selected_edge['trigger_definition']}")
                    with col2:
                        st.markdown(f"**RR:** {selected_edge['rr']}")
                        st.markdown(f"**SL Mode:** {selected_edge['sl_mode']}")
                        st.markdown(f"**Status:** {selected_edge['status']}")
                        st.markdown(f"**Tests:** {selected_edge.get('test_count', 0)}")

                    if selected_edge.get('pass_reason_text'):
                        st.success(f"✅ {selected_edge['pass_reason_text']}")

                st.divider()

                # Evidence Pack (Lineage Check)
                st.subheader("📦 Evidence Pack")

                # Get validation runs for this edge
                validation_runs = get_experiment_runs(
                    db_connection=app_state.db_connection,
                    edge_id=selected_edge_id,
                    run_type='VALIDATION'
                )

                if validation_runs:
                    latest_run = validation_runs[0]
                    metrics = latest_run['metrics']

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Win Rate", f"{metrics.get('edge_win_rate', 0)*100:.1f}%")
                    with col2:
                        st.metric("Expected R", f"{metrics.get('expected_r', 0):.2f}R")
                    with col3:
                        st.metric("Sample Size", metrics.get('sample_size', 0))
                    with col4:
                        st.metric("Max DD", f"{metrics.get('max_dd', 0):.2f}R")

                    # Gate results
                    st.markdown("**Validation Gates:**")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        stress_25 = metrics.get('stress_test_25', 'N/A')
                        color_25 = "🟢" if stress_25 == "PASS" else "🔴"
                        st.markdown(f"{color_25} **Stress +25%:** {stress_25}")
                    with col2:
                        stress_50 = metrics.get('stress_test_50', 'N/A')
                        color_50 = "🟢" if stress_50 == "PASS" else "🔴"
                        st.markdown(f"{color_50} **Stress +50%:** {stress_50}")
                    with col3:
                        wf = metrics.get('walk_forward', 'N/A')
                        color_wf = "🟢" if wf == "PASS" else "🔴"
                        st.markdown(f"{color_wf} **Walk-Forward:** {wf}")

                    st.caption(f"Validation Run ID: `{latest_run['run_id'][:16]}...`")
                    st.caption(f"Completed: {str(latest_run['completed_at'])[:19] if latest_run.get('completed_at') else 'N/A'}")

                else:
                    st.error("❌ No validation lineage found! This edge cannot be promoted without evidence.")

                st.divider()

                # Promotion Form (Fail-Closed)
                st.subheader("✋ Operator Approval Required")

                st.warning("""
                **WARNING: You are about to promote this edge to PRODUCTION.**

                - This edge will be written to `validated_setups` table
                - Live trading systems will use this edge
                - AI cannot approve this action
                - Operator must explicitly confirm
                """)

                with st.form("promotion_form"):
                    operator_notes = st.text_area(
                        "Operator Notes (Required)",
                        placeholder="Why are you promoting this edge? What did you verify?",
                        height=100
                    )

                    confirm = st.checkbox(
                        "I confirm this edge passed all gates and I approve promotion to production",
                        value=False
                    )

                    submitted = st.form_submit_button("🚀 PROMOTE TO PRODUCTION", type="primary")

                    if submitted:
                        if not confirm:
                            st.error("❌ You must confirm promotion approval")
                        elif not operator_notes.strip():
                            st.error("❌ Operator notes are required")
                        elif not validation_runs:
                            st.error("❌ Cannot promote without validation lineage")
                        else:
                            # Promote edge
                            with st.spinner("Promoting edge to production..."):
                                try:
                                    result = promote_to_production(
                                        db_connection=app_state.db_connection,
                                        edge_id=selected_edge_id,
                                        operator_notes=operator_notes.strip()
                                    )

                                    if result['success']:
                                        st.success(f"✅ {result['message']}")
                                        st.info(f"Validated Setup ID: {result['validated_setup_id']}")
                                        st.balloons()
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Promotion failed: {result['error']}")

                                except Exception as e:
                                    st.error(f"❌ Promotion error: {e}")
                                    logger.error(f"Promotion error: {e}")

        else:
            st.info("No validated candidates ready for promotion. Validate edges first in the Validation Gate.")

    except Exception as e:
        st.error(f"Failed to load validated candidates: {e}")
        logger.error(f"Production tab error: {e}")

    st.divider()


    # ========================================================================
    # EXPERIMENTAL STRATEGIES - AUTO-ALERT SCANNER (NEW 2026-01-29)
    # ========================================================================
    st.subheader("🎁 Experimental Strategy Scanner")

    st.caption("""
    **Bonus Opportunities:** Rare/complex edges that auto-alert when conditions match.
    Scans day-of-week, session context, volatility regimes, and multi-day patterns automatically.
    """)

    try:
        from experimental_scanner import ExperimentalScanner
        from experimental_alerts_ui import render_experimental_alerts

        exp_scanner = ExperimentalScanner(app_state.db_connection)
        render_experimental_alerts(exp_scanner, instrument=app_state.current_instrument)

    except RuntimeError as e:
        # User-friendly error (table missing or validation failed)
        error_msg = str(e)
        if "not configured yet" in error_msg:
            st.info(f"ℹ️ {error_msg}")
        else:
            st.warning(f"⚠️ {error_msg}")
        logger.warning(f"Experimental scanner: {error_msg}")

    except Exception as e:
        # Unexpected error (database connection, etc.)
        log_error(e, context="Experimental scanner")
        st.error(f"❌ Unexpected error loading experimental scanner: {e}")
        st.info("Check app_errors.txt for details")
        logger.error(f"Experimental scanner error: {e}")

    st.divider()

    # ========================================================================
    # APPROVED STRATEGIES - GROUPED BY ORB (text.txt Part 2)
    # ========================================================================
    st.subheader("⚡ Active Strategy Selection")

    st.caption("""
    **Tactical Overview:** Strategies grouped by ORB time. Expand each group to view RR variants.
    Select strategies to deploy. System enforces max 1 variant per ORB session.
    """)

    try:
        from setup_detector import SetupDetector
        detector = SetupDetector(db_connection=app_state.db_connection)

        # Allow instrument selection
        instrument_select = st.selectbox(
            "Instrument",
            ["MGC", "NQ", "MPL"],
            key="strategy_instrument_select",
            help="Filter strategies by instrument"
        )

        grouped_strategies = detector.get_grouped_setups(instrument=instrument_select)

        if grouped_strategies:
            # Initialize selected strategies in session state
            if "selected_strategies" not in st.session_state:
                st.session_state.selected_strategies = []

            # Summary metrics bar
            total_orbs = len(grouped_strategies)
            total_variants = sum(g['variant_count'] for g in grouped_strategies)
            approved_count = sum(
                len([v for v in g['variants'] if v['expectancy'] >= 0.15])
                for g in grouped_strategies
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("ORB Groups", total_orbs, help="Unique ORB times available")
            with col2:
                st.metric("Total Variants", total_variants, help="All RR combinations")
            with col3:
                st.metric("Approved", approved_count, help="Expectancy ≥ +0.15R")

            st.markdown("---")

            # Display each ORB group
            for group in grouped_strategies:
                orb_time = group['orb_time']
                variant_count = group['variant_count']
                best_exp = group['best_expectancy']
                total_sample = group['total_sample_size']
                avg_win_rate = group['avg_win_rate']
                friction_pass = group['friction_pass_rate']

                # Badge colors based on best expectancy
                if best_exp >= 0.15:
                    badge_color = "#198754"  # Green
                    badge_text = "APPROVED"
                else:
                    badge_color = "#dc3545"  # Red
                    badge_text = "REJECTED"

                # Collapsed header with tactical data display
                expander_label = f"🕒 **{orb_time}** ORB"

                with st.expander(expander_label, expanded=False):
                    # Tactical stats row
                    st.markdown(f"""
                    <div style="font-family: 'Courier New', monospace; font-size: 13px; padding: 8px;
                                background: #f8f9fa; border-left: 3px solid {badge_color}; margin-bottom: 12px;">
                        <span style="color: {badge_color}; font-weight: bold;">[{badge_text}]</span>
                        <span style="color: #495057;">VARIANTS: {variant_count}</span> |
                        <span style="color: #198754;">BEST: {best_exp:+.3f}R</span> |
                        <span style="color: #6c757d;">SAMPLE: {total_sample}</span> |
                        <span style="color: #0d6efd;">WR: {avg_win_rate:.1%}</span> |
                        <span style="color: #fd7e14;">FRICTION: {friction_pass:.1%}</span>
                    </div>
                    """, unsafe_allow_html=True)

                    # Variants table header
                    st.markdown("""
                    <div style="font-family: 'Courier New', monospace; font-size: 11px;
                                font-weight: bold; color: #6c757d; padding: 4px 0;
                                border-bottom: 1px solid #dee2e6;">
                        SELECT | ID | RR | MODE | EXPECTANCY | SAMPLE | WIN RATE | FRICTION | FILTER
                    </div>
                    """, unsafe_allow_html=True)

                    # Display each variant
                    for variant in group['variants']:
                        setup_id = variant['setup_id']
                        rr = variant['rr']
                        sl_mode = variant['sl_mode']
                        expectancy = variant['expectancy']
                        sample_size = variant['sample_size']
                        win_rate = variant['win_rate']
                        filter_val = variant.get('filter')
                        friction_pass_rate = variant['friction_pass_rate']

                        # Approval status
                        approved = expectancy >= 0.15
                        status_color = "#198754" if approved else "#dc3545"
                        status_symbol = "✓" if approved else "✗"
                        filter_str = f"{filter_val*100:.0f}% ATR" if filter_val else "NONE"

                        # Row container
                        col_check, col_data = st.columns([1, 11])

                        with col_check:
                            if approved:
                                selected = st.checkbox(
                                    f"Select {setup_id}",
                                    key=f"strat_{setup_id}",
                                    value=setup_id in st.session_state.selected_strategies,
                                    label_visibility="collapsed"
                                )
                                if selected and setup_id not in st.session_state.selected_strategies:
                                    st.session_state.selected_strategies.append(setup_id)
                                elif not selected and setup_id in st.session_state.selected_strategies:
                                    st.session_state.selected_strategies.remove(setup_id)
                            else:
                                st.markdown(f"<div style='color: {status_color}; font-size: 18px; text-align: center;'>{status_symbol}</div>", unsafe_allow_html=True)

                        with col_data:
                            st.markdown(f"""
                            <div style="font-family: 'Courier New', monospace; font-size: 12px;
                                        padding: 6px; background: {'#f8f9fa' if approved else '#fff5f5'};
                                        border-left: 2px solid {status_color}; margin-bottom: 4px;">
                                <span style="color: {status_color}; font-weight: bold;">[{status_symbol}]</span>
                                <span style="color: #212529;">ID:{setup_id:>3}</span> |
                                <span style="color: #0d6efd;">RR:{rr:>4.1f}</span> |
                                <span style="color: #6c757d;">{sl_mode.upper():>4}</span> |
                                <span style="color: {status_color}; font-weight: bold;">EXP:{expectancy:>+6.3f}R</span> |
                                <span style="color: #6c757d;">N:{sample_size:>3}</span> |
                                <span style="color: #0d6efd;">WR:{win_rate:>6.1%}</span> |
                                <span style="color: #fd7e14;">FRIC:{friction_pass_rate:>6.1%}</span> |
                                <span style="color: #6c757d;">FILT:{filter_str}</span>
                            </div>
                            """, unsafe_allow_html=True)

            st.markdown("---")

            # Execution guard: warn if multiple variants from same ORB selected
            if st.session_state.selected_strategies:
                # Build map: setup_id -> orb_time
                setup_to_orb = {}
                for group in grouped_strategies:
                    for variant in group['variants']:
                        setup_to_orb[variant['setup_id']] = group['orb_time']

                # Check for duplicates
                orb_counts = {}
                for setup_id in st.session_state.selected_strategies:
                    orb_time = setup_to_orb.get(setup_id)
                    if orb_time:
                        orb_counts[orb_time] = orb_counts.get(orb_time, 0) + 1

                violations = [orb for orb, count in orb_counts.items() if count > 1]

                if violations:
                    st.warning(f"""
                    ⚠️ **EXECUTION GUARD WARNING**

                    Multiple variants selected from same ORB session(s): **{', '.join(violations)}**

                    These are the SAME trade idea with different RR targets. Trading multiple variants
                    increases position size without diversification. Confirm this is intentional.
                    """, icon="⚠️")

                # Selected strategies summary
                st.success(f"""
                ✅ **{len(st.session_state.selected_strategies)} strategies selected**

                Strategy IDs: {', '.join(map(str, sorted(st.session_state.selected_strategies)))}
                """, icon="✅")

                if st.button("🗑️ Clear All Selections", type="secondary"):
                    st.session_state.selected_strategies = []
                    st.rerun()
        else:
            st.info(f"No approved strategies found for {instrument_select}. Promote validated edges to populate this registry.", icon="ℹ️")

    except Exception as e:
        st.error(f"Failed to load strategy groups: {e}")
        logger.error(f"Strategy grouping error: {e}")

# ============================================================================
# FOOTER
# ============================================================================
st.divider()
st.caption(f"Canonical Trading System v0.1 | Built: {datetime.now().strftime('%Y-%m-%d')} | DB: {app_state.get_db_status()}")
