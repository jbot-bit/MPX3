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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
            self.db_connection = duckdb.connect(self.db_path)
            logger.info(f"Connected to database: {self.db_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
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

        # Get current market state
        market_state = scanner.get_current_market_state(instrument='MGC')

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
        # ACTIVE SETUPS
        # ====================================================================
        if active_setups:
            st.subheader(f"🟢 Active Setups ({len(active_setups)})")
            st.caption("These setups have all filters passed and are ready to trade")

            for setup in active_setups:
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
                    <div style="font-size: 14px; color: #333; margin-bottom: 8px;">
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
        # INVALID SETUPS
        # ====================================================================
        if invalid_setups:
            with st.expander(f"🔴 Invalid Setups ({len(invalid_setups)})", expanded=False):
                st.caption("These setups failed filter conditions today")

                for setup in invalid_setups:
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
                            {setup['reason']}
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

    # Candidate Draft Form
    st.subheader("📝 New Candidate Draft")

    with st.form("candidate_form"):
        col1, col2 = st.columns(2)

        with col1:
            candidate_instrument = st.selectbox("Instrument", ["MGC", "NQ", "MPL"])
            candidate_orb = st.selectbox("ORB Time", ["0900", "1000", "1100", "1800", "2300", "0030"])
            candidate_direction = st.selectbox("Direction", ["LONG", "SHORT", "BOTH"])

        with col2:
            candidate_rr = st.number_input("Risk:Reward", min_value=1.0, max_value=5.0, value=1.5, step=0.5)
            candidate_sl_mode = st.selectbox("SL Mode", ["FULL", "HALF"])
            candidate_filter = st.number_input("ORB Size Filter (% ATR)", min_value=0.0, max_value=100.0, value=15.0, step=1.0)

        trigger_definition = st.text_area(
            "Trigger Definition",
            placeholder="e.g., 'First 1-min close outside ORB range with L4_CONSOLIDATION filter'",
            height=100
        )

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
                                    f"<strong>Created:</strong> {candidate['created_at'][:10]}"
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

    st.subheader("🎯 Validation Pipeline")

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
                        st.markdown(f"**Created:** {selected_candidate['created_at'][:10]}")

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
                            st.markdown(f"**Last Tested:** {prior_validation['last_tested_at'][:10] if prior_validation['last_tested_at'] else 'N/A'}")
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

                with st.expander(f"{status_emoji} {run['run_id'][:16]}... - {run['started_at'][:19]}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown(f"**Edge ID:** `{run['edge_id'][:16]}...`")
                        st.markdown(f"**Type:** {run['run_type']}")
                        st.markdown(f"**Status:** {run['status']}")

                    with col2:
                        st.markdown(f"**Started:** {run['started_at'][:19]}")
                        if run.get('completed_at'):
                            st.markdown(f"**Completed:** {run['completed_at'][:19]}")

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
                    st.caption(f"Completed: {latest_run['completed_at'][:19] if latest_run.get('completed_at') else 'N/A'}")

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

    # Production Registry (Read-Only)
    st.subheader("📋 Production Registry (Read-Only)")

    try:
        # Get promoted edges from edge_registry
        promoted = get_all_candidates(
            db_connection=app_state.db_connection,
            status_filter='PROMOTED'
        )

        # Get validated_setups count
        setup_count = app_state.db_connection.execute("SELECT COUNT(*) FROM validated_setups").fetchone()[0]

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Promoted Edges", len(promoted), help="Edges in PROMOTED status")
        with col2:
            st.metric("Validated Setups", setup_count, help="Entries in validated_setups table")
        with col3:
            st.metric("Active Today", "0", help="Edges that signaled today")

        if promoted:
            st.caption(f"Showing {len(promoted)} promoted edge(s)")

            for edge in promoted:
                with st.expander(f"🟢 {edge['instrument']} {edge['orb_time']} {edge['direction']} (RR={edge['rr']})"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown(f"**Edge ID:** `{edge['edge_id'][:16]}...`")
                        st.markdown(f"**Trigger:** {edge['trigger_definition']}")
                        st.markdown(f"**SL Mode:** {edge['sl_mode']}")

                    with col2:
                        st.markdown(f"**Status:** {edge['status']}")
                        st.markdown(f"**Promoted:** {edge['updated_at'][:10] if edge.get('updated_at') else 'N/A'}")
                        st.markdown(f"**Tests:** {edge.get('test_count', 0)}")

                    if edge.get('pass_reason_text'):
                        st.info(f"📝 {edge['pass_reason_text']}")

                    # Retirement button
                    with st.form(f"retire_{edge['edge_id'][:8]}"):
                        st.caption("⚠️ Retire this edge from production?")
                        retire_reason = st.text_input("Retirement Reason", placeholder="Why retire?")
                        retire_btn = st.form_submit_button("🛑 Retire", type="secondary")

                        if retire_btn:
                            if not retire_reason.strip():
                                st.error("Retirement reason required")
                            else:
                                retire_from_production(
                                    db_connection=app_state.db_connection,
                                    edge_id=edge['edge_id'],
                                    retirement_reason=retire_reason.strip()
                                )
                                st.success("Edge retired")
                                st.rerun()

        else:
            st.info("No promoted edges yet. Promote validated edges above.")

    except Exception as e:
        st.error(f"Failed to load production registry: {e}")
        logger.error(f"Production registry error: {e}")

# ============================================================================
# FOOTER
# ============================================================================
st.divider()
st.caption(f"Canonical Trading System v0.1 | Built: {datetime.now().strftime('%Y-%m-%d')} | DB: {app_state.get_db_status()}")
