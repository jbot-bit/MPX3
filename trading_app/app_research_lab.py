"""
RESEARCH LAB - Strategy Discovery & Backtesting Command Center

The MAIN app for:
- Discovering new profitable edge setups
- Running comprehensive backtests
- Validating strategies with robustness checks
- Promoting winners to production

This is where the real work happens.
"""

import sys
from pathlib import Path

# Add paths for imports
if __name__ == "__main__" or "streamlit" in sys.modules:
    current_dir = Path(__file__).parent
    repo_root = current_dir.parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Optional, Any

# Import research infrastructure
from cloud_mode import get_database_connection, get_database_path
from research_runner import ResearchRunner, BacktestMetrics
from edge_candidate_utils import parse_json_field, approve_edge_candidate, set_candidate_status
from edge_pipeline import promote_candidate_to_validated_setups, create_edge_candidate
from strategy_discovery import StrategyDiscovery, DiscoveryConfig

# Import terminal theme
from terminal_theme import inject_terminal_theme
from terminal_components import *

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="RESEARCH LAB",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Inject terminal theme
inject_terminal_theme()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_pipeline_summary() -> Dict[str, int]:
    """Load candidate pipeline status summary"""
    try:
        conn = get_database_connection(read_only=True)

        df = conn.execute("""
            SELECT status, COUNT(*) as count
            FROM edge_candidates
            GROUP BY status
        """).df()

        summary = {"DRAFT": 0, "TESTED": 0, "PENDING": 0, "APPROVED": 0, "REJECTED": 0}
        for _, row in df.iterrows():
            summary[row['status']] = int(row['count'])

        promoted = conn.execute("""
            SELECT COUNT(*) FROM edge_candidates WHERE promoted_validated_setup_id IS NOT NULL
        """).fetchone()[0]
        summary["PROMOTED"] = promoted

        conn.close()
        return summary
    except Exception as e:
        logger.error(f"Error loading pipeline summary: {e}")
        return {"DRAFT": 0, "TESTED": 0, "PENDING": 0, "APPROVED": 0, "REJECTED": 0, "PROMOTED": 0}


def load_candidates(status_filter: str = "ALL", instrument_filter: str = "ALL") -> Optional[pd.DataFrame]:
    """Load edge candidates from database"""
    try:
        conn = get_database_connection(read_only=True)

        sql = """
            SELECT
                candidate_id, created_at_utc, instrument, name, hypothesis_text,
                status, test_window_start, test_window_end,
                approved_at, approved_by, promoted_validated_setup_id,
                metrics_json, robustness_json, filter_spec_json, notes
            FROM edge_candidates
            WHERE 1=1
        """
        params = []

        if status_filter != "ALL":
            sql += " AND status = ?"
            params.append(status_filter)

        if instrument_filter != "ALL":
            sql += " AND instrument = ?"
            params.append(instrument_filter)

        sql += " ORDER BY created_at_utc DESC LIMIT 100"

        df = conn.execute(sql, params).df()
        conn.close()
        return df
    except Exception as e:
        logger.error(f"Error loading candidates: {e}")
        return None


def parse_metrics(metrics_json: Any) -> Dict:
    """Parse metrics JSON field"""
    if metrics_json is None:
        return {}
    if isinstance(metrics_json, dict):
        return metrics_json
    try:
        return json.loads(metrics_json)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to parse metrics JSON: {e}")
        return {}


# ============================================================================
# VIEW: DISCOVERY
# ============================================================================

def render_discovery_view():
    """Strategy discovery - find new profitable setups"""
    render_terminal_header("STRATEGY DISCOVERY", "SCAN FOR PROFITABLE EDGES")

    st.markdown("""
    <div class="info-panel">
        <p>Systematically scan for profitable ORB configurations across instruments, timeframes, and filter combinations.
        Discovery engine will test hundreds of variations and surface the best performers.</p>
    </div>
    """, unsafe_allow_html=True)

    render_section_divider("SCAN PARAMETERS")

    col1, col2, col3 = st.columns(3)

    with col1:
        instrument = st.selectbox("INSTRUMENT", ["MGC", "NQ", "MPL"], key="disc_instrument")

    with col2:
        orb_times = st.multiselect(
            "ORB TIMES",
            ["0900", "1000", "1100", "1800", "2300", "0030"],
            default=["0900", "1000", "1100"],
            key="disc_orb_times"
        )

    with col3:
        min_trades = st.number_input("MIN TRADES", min_value=10, value=50, key="disc_min_trades")

    render_section_divider()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        min_win_rate = st.slider("MIN WIN RATE", 0.0, 1.0, 0.50, 0.01)
    with col2:
        min_avg_r = st.slider("MIN AVG R", 0.0, 5.0, 1.0, 0.1)
    with col3:
        max_drawdown = st.slider("MAX DRAWDOWN R", 0.0, 10.0, 5.0, 0.5)
    with col4:
        min_sharpe = st.slider("MIN SHARPE", 0.0, 3.0, 0.5, 0.1)

    render_section_divider("FILTER TESTING")

    st.markdown("""
    <div style="font-family: var(--font-mono); color: var(--text-secondary); margin-bottom: 16px;">
        Test multiple filter combinations to find optimal entry conditions:
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        test_orb_size = st.checkbox("Test ORB Size Filters", value=True, help="Scan for optimal min/max ORB size")
        test_atr = st.checkbox("Test ATR Filters", value=True, help="Filter by average true range")
        test_rsi = st.checkbox("Test RSI Filters", value=False, help="Filter by RSI levels")

    with col2:
        test_session_move = st.checkbox("Test Session Travel", value=True, help="Filter by prior session movement")
        test_time_windows = st.checkbox("Test Extended Windows", value=False, help="Test longer profit windows")
        test_rr_targets = st.checkbox("Test R:R Ratios", value=True, help="Optimize reward:risk targets")

    render_section_divider()

    # Discovery button
    if st.button("🔬 START DISCOVERY SCAN", type="primary", use_container_width=True):
        st.warning("⚠ Discovery scan will run multiple backtests. This may take a few minutes...", icon="⚠️")

        with st.spinner("Running discovery scan..."):
            try:
                # Initialize discovery engine
                discovery = StrategyDiscovery()

                # Generate all configuration combinations to test
                configs = []

                # R:R targets to test
                rr_targets = [1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0] if test_rr_targets else [4.0]

                # Stop loss modes to test
                sl_modes = ["FULL", "HALF"]

                # ORB size filters to test (percentage of ATR)
                orb_filters = [None, 0.10, 0.15, 0.20] if test_orb_size else [None]

                # Generate all combinations
                for orb_time in orb_times:
                    for rr in rr_targets:
                        for sl_mode in sl_modes:
                            for orb_filter in orb_filters:
                                config = DiscoveryConfig(
                                    instrument=instrument,
                                    orb_time=orb_time,
                                    rr=rr,
                                    sl_mode=sl_mode,
                                    orb_size_filter=orb_filter
                                )
                                configs.append(config)

                st.info(f"Testing {len(configs)} configurations...", icon="ℹ️")

                # Run backtests
                results = []
                progress_bar = st.progress(0)
                for i, config in enumerate(configs):
                    result = discovery.backtest_configuration(config)

                    # Filter by criteria
                    if result.total_trades >= min_trades:
                        if (result.win_rate/100) >= min_win_rate:
                            if result.avg_r >= min_avg_r:
                                results.append(result)

                    progress_bar.progress((i + 1) / len(configs))

                progress_bar.empty()

                # Display results
                if results:
                    st.success(f"✅ Discovery complete! Found {len(results)} profitable configurations")

                    # Convert to DataFrame
                    results_data = []
                    for result in results:
                        results_data.append({
                            "Instrument": result.config.instrument,
                            "ORB Time": result.config.orb_time,
                            "R:R": result.config.rr,
                            "SL Mode": result.config.sl_mode,
                            "Filter": f"{result.config.orb_size_filter*100:.0f}%" if result.config.orb_size_filter else "None",
                            "Trades": result.total_trades,
                            "Win Rate": f"{result.win_rate:.1f}%",
                            "Avg R": result.avg_r,
                            "Total R": result.total_r,
                            "Tier": result.tier
                        })

                    df = pd.DataFrame(results_data)

                    # Sort by Total R
                    df = df.sort_values('Total R', ascending=False)

                    # Display top results
                    st.markdown("### TOP PERFORMERS")
                    st.dataframe(
                        df.head(20),
                        use_container_width=True
                    )

                    # Show summary
                    render_section_divider("SUMMARY")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Configs Tested", len(configs))
                    with col2:
                        st.metric("Profitable", len(results))
                    with col3:
                        tier_s = len([r for r in results if r.tier in ["S+", "S"]])
                        st.metric("Tier S/S+", tier_s)
                    with col4:
                        if results:
                            best_r = max(r.total_r for r in results)
                            st.metric("Best Total R", f"{best_r:.1f}")

                else:
                    st.warning("⚠ No strategies found matching criteria. Try relaxing filters.", icon="⚠️")

            except Exception as e:
                logger.error(f"Discovery error: {e}")
                st.error(f"❌ Discovery failed: {str(e)}")


# ============================================================================
# VIEW: PIPELINE
# ============================================================================

def render_pipeline_view():
    """Pipeline dashboard - manage candidates through workflow"""
    render_terminal_header("RESEARCH PIPELINE", "CANDIDATE WORKFLOW MANAGEMENT")

    # Load summary
    summary = load_pipeline_summary()

    # Status overview
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        render_metric_card("DRAFT", str(summary.get("DRAFT", 0)), change="Awaiting test", sentiment="neutral")
    with col2:
        render_metric_card("TESTED", str(summary.get("TESTED", 0)), change="Ready for review", sentiment="neutral")
    with col3:
        render_metric_card("PENDING", str(summary.get("PENDING", 0)), change="Under review", sentiment="neutral")
    with col4:
        render_metric_card("APPROVED", str(summary.get("APPROVED", 0)), change="Ready for prod", sentiment="positive")
    with col5:
        render_metric_card("REJECTED", str(summary.get("REJECTED", 0)), change="Failed validation", sentiment="negative")
    with col6:
        render_metric_card("PROMOTED", str(summary.get("PROMOTED", 0)), change="Live in prod", sentiment="positive")

    render_section_divider()

    st.markdown("""
    <div style="font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary); text-align: center;">
        WORKFLOW: Draft → Tested → Pending → Approved → Promoted to Production
    </div>
    """, unsafe_allow_html=True)

    render_section_divider("FILTER & VIEW")

    col1, col2 = st.columns(2)

    with col1:
        status_filter = st.selectbox(
            "STATUS",
            ["ALL", "DRAFT", "TESTED", "PENDING", "APPROVED", "REJECTED"],
            key="pipeline_status_filter"
        )

    with col2:
        instrument_filter = st.selectbox(
            "INSTRUMENT",
            ["ALL", "MGC", "NQ", "MPL"],
            key="pipeline_instrument_filter"
        )

    # Load candidates
    df = load_candidates(status_filter, instrument_filter)

    if df is not None and not df.empty:
        render_section_divider(f"CANDIDATES ({len(df)})")

        # Display candidates
        for idx, row in df.iterrows():
            with st.expander(f"📊 {row['name']} ({row['instrument']}) - {row['status']}", expanded=False):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(f"**ID:** {row['candidate_id']}")
                    st.markdown(f"**Hypothesis:** {row['hypothesis_text']}")
                    st.markdown(f"**Test Window:** {row['test_window_start']} to {row['test_window_end']}")

                    # Metrics
                    metrics = parse_metrics(row['metrics_json'])
                    if metrics:
                        st.markdown("**Performance Metrics:**")
                        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                        with m_col1:
                            st.metric("Win Rate", f"{metrics.get('win_rate', 0)*100:.1f}%")
                        with m_col2:
                            st.metric("Avg R", f"{metrics.get('avg_r', 0):.2f}")
                        with m_col3:
                            st.metric("Total R", f"{metrics.get('total_r', 0):.1f}")
                        with m_col4:
                            st.metric("Trades", metrics.get('n_trades', 0))

                with col2:
                    st.markdown(f"**Created:** {row['created_at_utc']}")
                    st.markdown(f"**Status:** `{row['status']}`")

                    if row['approved_at']:
                        st.markdown(f"**Approved:** {row['approved_at']}")
                        st.markdown(f"**By:** {row['approved_by']}")

                    if row['promoted_validated_setup_id']:
                        st.markdown(f"**✅ PROMOTED** (ID: {row['promoted_validated_setup_id']})")

                    # Action buttons
                    st.markdown("---")

                    if row['status'] == "DRAFT":
                        if st.button("🧪 RUN BACKTEST", key=f"test_{row['candidate_id']}"):
                            with st.spinner("Running backtest..."):
                                try:
                                    runner = ResearchRunner()
                                    runner.run_candidate(candidate_id=row['candidate_id'])
                                    st.success("✅ Backtest complete")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Backtest failed: {str(e)}")

                    elif row['status'] == "TESTED":
                        if st.button("👀 REVIEW", key=f"review_{row['candidate_id']}"):
                            set_candidate_status(row['candidate_id'], "PENDING")
                            st.success("✅ Moved to PENDING")
                            st.rerun()

                    elif row['status'] == "PENDING":
                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            if st.button("✅ APPROVE", key=f"approve_{row['candidate_id']}", type="primary"):
                                approve_edge_candidate(row['candidate_id'], approved_by="user")
                                st.success("✅ Approved!")
                                st.rerun()
                        with btn_col2:
                            if st.button("❌ REJECT", key=f"reject_{row['candidate_id']}"):
                                set_candidate_status(row['candidate_id'], "REJECTED")
                                st.success("❌ Rejected")
                                st.rerun()

                    elif row['status'] == "APPROVED" and not row['promoted_validated_setup_id']:
                        if st.button("🚀 PROMOTE TO PRODUCTION", key=f"promote_{row['candidate_id']}", type="primary"):
                            with st.spinner("Promoting to production..."):
                                try:
                                    setup_id = promote_candidate_to_validated_setups(row['candidate_id'])
                                    st.success(f"✅ Promoted! Setup ID: {setup_id}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Promotion failed: {str(e)}")
    else:
        st.info("⚡ No candidates found. Start a discovery scan to create new candidates.", icon="ℹ️")


# ============================================================================
# VIEW: BACKTESTER
# ============================================================================

def render_backtester_view():
    """Interactive backtest runner"""
    render_terminal_header("BACKTEST ENGINE", "TEST STRATEGIES ON HISTORICAL DATA")

    st.markdown("""
    <div class="info-panel">
        <p>Run comprehensive backtests on any strategy configuration. Test different instruments, ORB times,
        filter combinations, and R:R targets to validate edge profitability.</p>
    </div>
    """, unsafe_allow_html=True)

    render_section_divider("BACKTEST CONFIGURATION")

    col1, col2, col3 = st.columns(3)

    with col1:
        instrument = st.selectbox("INSTRUMENT", ["MGC", "NQ", "MPL"], key="bt_instrument")
    with col2:
        orb_time = st.selectbox("ORB TIME", ["0900", "1000", "1100", "1800", "2300", "0030"], key="bt_orb_time")
    with col3:
        rr_target = st.number_input("R:R TARGET", min_value=1.0, max_value=20.0, value=8.0, step=0.5, key="bt_rr")

    render_section_divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### ENTRY FILTERS")
        orb_min = st.number_input("Min ORB Size", min_value=0.0, max_value=10.0, value=0.0, step=0.05)
        orb_max = st.number_input("Max ORB Size", min_value=0.0, max_value=20.0, value=99.0, step=0.05)
        atr_min = st.number_input("Min ATR", min_value=0.0, max_value=10.0, value=0.0, step=0.1)
        atr_max = st.number_input("Max ATR", min_value=0.0, max_value=20.0, value=99.0, step=0.1)

    with col2:
        st.markdown("### TEST WINDOW")
        start_date = st.date_input("Start Date", value=datetime(2021, 1, 1))
        end_date = st.date_input("End Date", value=datetime.now())

        st.markdown("### ADVANCED")
        half_sl = st.checkbox("Use Half Stop Loss", value=False, help="Use 50% of ORB as stop")
        extended_window = st.checkbox("Extended Profit Window", value=False, help="Allow 24h for targets")

    render_section_divider()

    if st.button("🧪 RUN BACKTEST", type="primary", use_container_width=True):
        with st.spinner("Running backtest..."):
            try:
                # Create candidate for this backtest
                filter_spec = {
                    "orb_time": orb_time,
                    "orb_min_size": orb_min,
                    "orb_max_size": orb_max,
                    "atr_min": atr_min,
                    "atr_max": atr_max,
                    "half_sl": half_sl,
                    "extended_window": extended_window,
                    "rr_target": rr_target
                }

                candidate_id = create_edge_candidate(
                    instrument=instrument,
                    name=f"{instrument}_{orb_time}_RR{rr_target}",
                    hypothesis_text=f"Ad-hoc backtest: {instrument} {orb_time} ORB with {rr_target}R target",
                    feature_spec={},
                    filter_spec=filter_spec,
                    test_window_start=start_date.strftime('%Y-%m-%d'),
                    test_window_end=end_date.strftime('%Y-%m-%d')
                )

                # Run backtest
                runner = ResearchRunner()
                runner.run_candidate(candidate_id=candidate_id)

                # Load results
                conn = get_database_connection(read_only=True)
                result = conn.execute("""
                    SELECT metrics_json, robustness_json
                    FROM edge_candidates
                    WHERE candidate_id = ?
                """, [candidate_id]).fetchone()
                conn.close()

                if result and result[0]:
                    metrics = parse_metrics(result[0])

                    st.success("✅ Backtest complete!")

                    render_section_divider("RESULTS")

                    # Metrics display
                    col1, col2, col3, col4, col5 = st.columns(5)
                    with col1:
                        render_metric_card("WIN RATE", f"{metrics.get('win_rate', 0)*100:.1f}%", change=None, sentiment="positive" if metrics.get('win_rate', 0) > 0.5 else "negative")
                    with col2:
                        render_metric_card("AVG R", f"{metrics.get('avg_r', 0):.2f}", change=None, sentiment="positive" if metrics.get('avg_r', 0) > 1 else "negative")
                    with col3:
                        render_metric_card("TOTAL R", f"{metrics.get('total_r', 0):.1f}", change=None, sentiment="positive" if metrics.get('total_r', 0) > 0 else "negative")
                    with col4:
                        render_metric_card("TRADES", str(metrics.get('n_trades', 0)), change=None, sentiment="neutral")
                    with col5:
                        render_metric_card("MAX DD", f"{metrics.get('max_drawdown_r', 0):.1f}R", change=None, sentiment="negative" if metrics.get('max_drawdown_r', 0) > 5 else "neutral")

                    # Additional metrics
                    st.markdown("### DETAILED METRICS")
                    detail_col1, detail_col2, detail_col3, detail_col4 = st.columns(4)
                    with detail_col1:
                        st.metric("Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.2f}")
                    with detail_col2:
                        st.metric("Profit Factor", f"{metrics.get('profit_factor', 0):.2f}")
                    with detail_col3:
                        st.metric("MAE (Avg)", f"{metrics.get('mae_avg', 0):.2f}R")
                    with detail_col4:
                        st.metric("MFE (Avg)", f"{metrics.get('mfe_avg', 0):.2f}R")

                    # Verdict
                    is_profitable = metrics.get('total_r', 0) > 0
                    verdict = "✅ PROFITABLE EDGE DETECTED" if is_profitable else "❌ NO EDGE DETECTED"
                    render_alert_message(verdict, alert_type="success" if is_profitable else "error", slide_in=False)

                else:
                    st.error("❌ No results returned from backtest")

            except Exception as e:
                logger.error(f"Backtest error: {e}")
                st.error(f"❌ Backtest failed: {str(e)}")


# ============================================================================
# VIEW: PRODUCTION
# ============================================================================

def render_production_view():
    """View promoted strategies in production"""
    render_terminal_header("PRODUCTION STRATEGIES", "LIVE VALIDATED SETUPS")

    try:
        conn = get_database_connection(read_only=True)

        # Load validated setups
        df = conn.execute("""
            SELECT
                id, instrument, orb_time, break_direction,
                rr_target, orb_size_filter, stop_loss_mode,
                win_rate, avg_r, total_r, n_trades, max_drawdown_r,
                promoted_from_candidate_id, promoted_at_utc
            FROM validated_setups
            ORDER BY instrument, orb_time
        """).df()

        conn.close()

        if not df.empty:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                render_metric_card("TOTAL SETUPS", str(len(df)), change=None, sentiment="neutral")
            with col2:
                mgc_count = len(df[df['instrument'] == 'MGC'])
                render_metric_card("MGC SETUPS", str(mgc_count), change=None, sentiment="neutral")
            with col3:
                nq_count = len(df[df['instrument'] == 'NQ'])
                render_metric_card("NQ SETUPS", str(nq_count), change=None, sentiment="neutral")
            with col4:
                mpl_count = len(df[df['instrument'] == 'MPL'])
                render_metric_card("MPL SETUPS", str(mpl_count), change=None, sentiment="neutral")

            render_section_divider("ACTIVE STRATEGIES")

            # Group by instrument
            for instrument in ["MGC", "NQ", "MPL"]:
                inst_df = df[df['instrument'] == instrument]
                if not inst_df.empty:
                    st.markdown(f"### {instrument}")

                    for idx, row in inst_df.iterrows():
                        with st.expander(f"📈 {row['orb_time']} ORB ({row['break_direction']}) - {row['rr_target']}R", expanded=False):
                            col1, col2, col3 = st.columns(3)

                            with col1:
                                st.markdown("**CONFIGURATION**")
                                st.markdown(f"ID: {row['id']}")
                                st.markdown(f"ORB Time: {row['orb_time']}")
                                st.markdown(f"Direction: {row['break_direction']}")
                                st.markdown(f"R:R Target: {row['rr_target']}")
                                st.markdown(f"Stop Mode: {row['stop_loss_mode']}")
                                if row['orb_size_filter']:
                                    st.markdown(f"ORB Filter: {row['orb_size_filter']}")

                            with col2:
                                st.markdown("**PERFORMANCE**")
                                st.metric("Win Rate", f"{row['win_rate']*100:.1f}%")
                                st.metric("Avg R", f"{row['avg_r']:.2f}")
                                st.metric("Total R", f"{row['total_r']:.1f}")

                            with col3:
                                st.markdown("**STATISTICS**")
                                st.metric("Trades", row['n_trades'])
                                st.metric("Max Drawdown", f"{row['max_drawdown_r']:.1f}R")
                                if row['promoted_at_utc']:
                                    st.markdown(f"Promoted: {row['promoted_at_utc']}")
        else:
            st.info("⚡ No production strategies yet. Approve and promote candidates to add them here.", icon="ℹ️")

    except Exception as e:
        logger.error(f"Error loading production strategies: {e}")
        st.error(f"❌ Error loading production data: {str(e)}")


# ============================================================================
# VIEW ROUTER
# ============================================================================

# Session state
if "research_view" not in st.session_state:
    st.session_state.research_view = "DISCOVERY"

# Sidebar navigation
with st.sidebar:
    st.markdown("<h2 style='color: var(--profit-green); font-family: var(--font-display);'>🔬 RESEARCH LAB</h2>", unsafe_allow_html=True)

    view = st.radio(
        "RESEARCH MODE",
        ["DISCOVERY", "PIPELINE", "BACKTESTER", "PRODUCTION"],
        index=["DISCOVERY", "PIPELINE", "BACKTESTER", "PRODUCTION"].index(st.session_state.research_view)
    )

    if view != st.session_state.research_view:
        st.session_state.research_view = view
        st.rerun()

    st.markdown("---")

    st.markdown("""
    <div style="font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary);">
        <div><strong>DISCOVERY</strong> - Find new edges</div>
        <div><strong>PIPELINE</strong> - Manage candidates</div>
        <div><strong>BACKTESTER</strong> - Test strategies</div>
        <div><strong>PRODUCTION</strong> - Live setups</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Database info
    db_path = get_database_path()
    st.markdown(f"""
    <div style="font-family: var(--font-mono); font-size: 10px; color: var(--text-secondary);">
        <div><strong>DATABASE</strong></div>
        <div>{db_path}</div>
    </div>
    """, unsafe_allow_html=True)

# Render selected view
if st.session_state.research_view == "DISCOVERY":
    render_discovery_view()
elif st.session_state.research_view == "PIPELINE":
    render_pipeline_view()
elif st.session_state.research_view == "BACKTESTER":
    render_backtester_view()
elif st.session_state.research_view == "PRODUCTION":
    render_production_view()

# Footer
st.markdown("<div style='text-align: center; margin-top: 48px; padding: 24px; font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary);'>🔬 RESEARCH LAB // STRATEGY DISCOVERY ENGINE // {}</div>".format(datetime.now().strftime('%H:%M:%S')), unsafe_allow_html=True)
