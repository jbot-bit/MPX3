"""
TRADING TERMINAL - Professional Trading Interface

Aesthetic: Industrial/Utilitarian with Retro-Futuristic Elements
- Bloomberg Terminal meets refined Cyberpunk
- Matrix-inspired aesthetics with military precision
- Information density without chaos
- Real-time decision support

This is what the app was always meant to be.
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
from datetime import datetime, timedelta
import time
import logging
import uuid
from streamlit_autorefresh import st_autorefresh

# Import configuration and utilities
from config import *
from data_loader import LiveDataLoader
from strategy_engine import StrategyEngine, ActionType, StrategyState
from utils import calculate_position_size, format_price
from ai_memory import AIMemoryManager
from ai_assistant import TradingAIAssistant
from cloud_mode import is_cloud_deployment, get_database_path
from setup_scanner import SetupScanner
from enhanced_charting import ChartTimeframe, resample_bars
from data_quality_monitor import DataQualityMonitor
from market_hours_monitor import MarketHoursMonitor, MarketConditions
from risk_manager import RiskManager, RiskLimits, RiskMetrics, Position
from position_tracker import PositionTracker

# Import terminal theme and components
from terminal_theme import inject_terminal_theme
from terminal_components import *

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="TRADING TERMINAL",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Inject terminal theme CSS
inject_terminal_theme()

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

UPDATE_INTERVAL_MS = 5000  # 5 second refresh

def init_session_state():
    """Initialize all session state variables"""
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "current_symbol" not in st.session_state:
        st.session_state.current_symbol = DEFAULT_SYMBOL
    if "account_size" not in st.session_state:
        st.session_state.account_size = 10000.0
    if "risk_per_trade" not in st.session_state:
        st.session_state.risk_per_trade = 1.0
    if "data_loader" not in st.session_state:
        st.session_state.data_loader = None
    if "strategy_engine" not in st.session_state:
        st.session_state.strategy_engine = None
    if "last_evaluation" not in st.session_state:
        st.session_state.last_evaluation = None
    if "ai_memory" not in st.session_state:
        st.session_state.ai_memory = AIMemoryManager()
    if "ai_assistant" not in st.session_state:
        st.session_state.ai_assistant = TradingAIAssistant(
            memory_manager=st.session_state.ai_memory
        )
    if "setup_scanner" not in st.session_state:
        db_path = get_database_path()
        st.session_state.setup_scanner = SetupScanner(db_path)
    if "chart_timeframe" not in st.session_state:
        st.session_state.chart_timeframe = ChartTimeframe.M1
    if "data_quality_monitor" not in st.session_state:
        st.session_state.data_quality_monitor = DataQualityMonitor()
    if "market_hours" not in st.session_state:
        st.session_state.market_hours = MarketHoursMonitor(TZ_LOCAL)
    if "risk_manager" not in st.session_state:
        # Create default risk limits
        default_limits = RiskLimits(
            daily_loss_dollars=500.0,  # Max $500 daily loss
            daily_loss_r=3.0,          # Max 3R daily loss
            weekly_loss_dollars=1500.0,  # Max $1500 weekly loss
            weekly_loss_r=7.0,         # Max 7R weekly loss
            max_concurrent_positions=3,  # Max 3 positions
            max_position_size_pct=2.0,   # Max 2% risk per trade
            max_correlated_positions=1   # Max 1 position per instrument
        )
        st.session_state.risk_manager = RiskManager(
            account_size=st.session_state.account_size,
            limits=default_limits
        )
    if "position_tracker" not in st.session_state:
        st.session_state.position_tracker = PositionTracker()
    if "view_mode" not in st.session_state:
        st.session_state.view_mode = "COMMAND"  # COMMAND, MONITOR, ANALYSIS, INTELLIGENCE

init_session_state()

# ============================================================================
# AUTO-REFRESH (Real-time terminal updates)
# ============================================================================
count = st_autorefresh(interval=UPDATE_INTERVAL_MS, key="terminal_refresh")

# ============================================================================
# MAIN TERMINAL INTERFACE
# ============================================================================

def render_command_center():
    """Main command center - trading decision interface"""

    # TERMINAL HEADER
    now = datetime.now(TZ_LOCAL)
    render_terminal_header(
        "TRADING TERMINAL",
        f"SYSTEM LIVE // {now.strftime('%Y-%m-%d %H:%M:%S %Z')} // SESSION {st.session_state.session_id[:8]}"
    )

    # TOP STATUS BAR
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        # Market hours status
        market_conditions = st.session_state.market_hours.get_market_conditions(st.session_state.current_symbol)
        market_status_text = market_conditions.get_status_text()
        market_color = {
            "EXCELLENT": "green",
            "GOOD": "green",
            "THIN": "yellow",
            "VERY_THIN": "orange",
            "CLOSED": "red"
        }.get(market_conditions.liquidity_level, "yellow")
        render_status_indicator(market_status_text, color=market_color, label="MARKET")

    with col2:
        # Data connection status
        data_connected = st.session_state.data_loader is not None
        render_status_indicator(
            "CONNECTED" if data_connected else "OFFLINE",
            color="green" if data_connected else "red",
            label="DATA"
        )

    with col3:
        # Strategy engine status
        engine_active = st.session_state.strategy_engine is not None
        render_status_indicator(
            "ACTIVE" if engine_active else "STANDBY",
            color="green" if engine_active else "yellow",
            label="ENGINE"
        )

    with col4:
        # AI Assistant status (check if API key is configured)
        ai_available = bool(ANTHROPIC_API_KEY)
        render_status_indicator(
            "ONLINE" if ai_available else "OFFLINE",
            color="green" if ai_available else "red",
            label="AI"
        )

    with col5:
        # Risk manager status
        risk_metrics = st.session_state.risk_manager.get_risk_metrics()
        risk_ok = risk_metrics.is_safe_to_trade()
        render_status_indicator(
            "OK" if risk_ok else "WARNING",
            color="green" if risk_ok else "red",
            label="RISK"
        )

    render_section_divider()

    # METRICS ROW - Key Performance Indicators
    met_col1, met_col2, met_col3, met_col4 = st.columns(4)

    with met_col1:
        # Daily P&L from risk manager
        daily_pnl_dollars, daily_pnl_r = st.session_state.risk_manager.get_daily_pnl()
        render_metric_card(
            "DAILY P&L",
            f"{daily_pnl_r:+.2f}R",
            change=f"${daily_pnl_dollars:+.0f}",
            sentiment="positive" if daily_pnl_dollars > 0 else "negative" if daily_pnl_dollars < 0 else "neutral"
        )

    with met_col2:
        # Account size
        render_metric_card(
            "ACCOUNT",
            f"${st.session_state.account_size:,.0f}",
            change=None,
            sentiment="neutral"
        )

    with met_col3:
        # Active positions from risk manager
        active_positions = len(st.session_state.risk_manager.active_positions)
        render_metric_card(
            "POSITIONS",
            f"{active_positions}",
            change=None,
            sentiment="neutral"
        )

    with met_col4:
        # Win rate from closed positions
        closed_positions = st.session_state.risk_manager.closed_positions
        if closed_positions:
            wins = sum(1 for p in closed_positions if p.current_pnl_dollars > 0)
            win_rate = (wins / len(closed_positions)) * 100
        else:
            win_rate = 0.0
        render_metric_card(
            "WIN RATE",
            f"{win_rate:.1f}%",
            change=None,
            sentiment="positive" if win_rate > 50 else "negative" if win_rate < 50 else "neutral"
        )

    render_section_divider("PRICE ACTION")

    # PRICE DISPLAY & CHART
    price_col, chart_col = st.columns([1, 3])

    with price_col:
        # Large price display
        if st.session_state.data_loader:
            try:
                latest_data = st.session_state.data_loader.get_latest_data()
                if latest_data is not None and not latest_data.empty:
                    current_price = latest_data['close'].iloc[-1]
                    prev_price = latest_data['close'].iloc[-2] if len(latest_data) > 1 else current_price
                    direction = "up" if current_price > prev_price else "down" if current_price < prev_price else "neutral"

                    st.markdown("<div style='text-align: center; padding: 24px;'>", unsafe_allow_html=True)
                    render_price_display(current_price, direction=direction, symbol="$")
                    st.markdown(f"""
                    <div style='text-align: center; margin-top: 16px; font-family: var(--font-mono); color: var(--text-secondary);'>
                        {st.session_state.current_symbol} // 1M
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                    # Quick stats
                    st.markdown("<div style='margin-top: 32px;'>", unsafe_allow_html=True)
                    render_info_row("HIGH", f"${latest_data['high'].max():.2f}", "var(--profit-green)")
                    render_info_row("LOW", f"${latest_data['low'].min():.2f}", "var(--loss-red)")
                    render_info_row("RANGE", f"${(latest_data['high'].max() - latest_data['low'].min()):.2f}")
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    render_loading_spinner("AWAITING DATA...")
            except Exception as e:
                logger.error(f"Error loading price data: {e}")
                st.markdown("<div style='text-align: center; padding: 48px; color: var(--loss-red); font-family: var(--font-mono);'>DATA ERROR</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='text-align: center; padding: 48px; color: var(--text-secondary); font-family: var(--font-mono);'>DATA OFFLINE</div>", unsafe_allow_html=True)

    with chart_col:
        # Main trading chart
        if st.session_state.data_loader:
            try:
                latest_data = st.session_state.data_loader.get_latest_data()
                if latest_data is not None and not latest_data.empty:
                    # Prepare chart data
                    chart_df = latest_data.tail(200).copy()
                    chart_df['timestamp'] = pd.to_datetime(chart_df['ts_local']) if 'ts_local' in chart_df.columns else pd.to_datetime(chart_df.index)

                    # Create terminal-styled chart
                    fig = create_terminal_chart(chart_df, title=f"{st.session_state.current_symbol} // LIVE", height=400)

                    # Add ORB overlays if available
                    # TODO: Add ORB boxes from strategy engine

                    st.plotly_chart(fig, use_container_width=True, key="main_chart")
                else:
                    render_loading_spinner("LOADING CHART...")
            except Exception as e:
                logger.error(f"Error creating chart: {e}")
                st.info("⚡ Chart data unavailable", icon="ℹ️")
        else:
            st.info("⚡ Connect data source to display chart", icon="ℹ️")

    render_section_divider("STRATEGY ENGINE")

    # STRATEGY EVALUATION
    if st.session_state.strategy_engine:
        eval_result = st.session_state.last_evaluation

        if eval_result:
            # Display strategy recommendation
            action = eval_result.action
            state = eval_result.state

            if action == ActionType.ENTER_LONG or action == ActionType.ENTER_SHORT:
                direction = "LONG" if action == ActionType.ENTER_LONG else "SHORT"
                render_alert_message(
                    f"🎯 {direction} SIGNAL DETECTED // {eval_result.selected_strategy.name if eval_result.selected_strategy else 'N/A'}",
                    alert_type="success",
                    slide_in=True
                )

                # Trade details
                setup_col1, setup_col2 = st.columns(2)

                with setup_col1:
                    st.markdown("""
                    <div class="info-panel">
                        <h3>SETUP DETAILS</h3>
                    """, unsafe_allow_html=True)

                    if eval_result.selected_strategy:
                        render_info_row("STRATEGY", eval_result.selected_strategy.name)
                        render_info_row("DIRECTION", direction)
                        render_info_row("CONFIDENCE", f"{eval_result.confidence:.1%}")

                        if hasattr(eval_result, 'entry_price') and eval_result.entry_price:
                            render_info_row("ENTRY", f"${eval_result.entry_price:.2f}")
                        if hasattr(eval_result, 'stop_price') and eval_result.stop_price:
                            render_info_row("STOP", f"${eval_result.stop_price:.2f}")
                        if hasattr(eval_result, 'target_price') and eval_result.target_price:
                            render_info_row("TARGET", f"${eval_result.target_price:.2f}")

                    st.markdown("</div>", unsafe_allow_html=True)

                with setup_col2:
                    st.markdown("""
                    <div class="info-panel">
                        <h3>RISK MANAGEMENT</h3>
                    """, unsafe_allow_html=True)

                    # Calculate position size
                    if hasattr(eval_result, 'entry_price') and hasattr(eval_result, 'stop_price'):
                        if eval_result.entry_price and eval_result.stop_price:
                            risk_amount = st.session_state.account_size * (st.session_state.risk_per_trade / 100)
                            risk_points = abs(eval_result.entry_price - eval_result.stop_price)

                            # Tick values
                            tick_values = {"MGC": 10.0, "NQ": 2.0, "MPL": 50.0}
                            tick_value = tick_values.get(st.session_state.current_symbol, 10.0)

                            position_size = calculate_position_size(
                                entry_price=eval_result.entry_price,
                                stop_price=eval_result.stop_price,
                                risk_amount=risk_amount,
                                tick_value=tick_value
                            )

                            render_info_row("POSITION SIZE", f"{position_size} contracts")
                            render_info_row("RISK AMOUNT", f"${risk_amount:.0f}")
                            render_info_row("RISK POINTS", f"{risk_points:.2f}pts")
                            render_info_row("R:R RATIO", f"1:{eval_result.selected_strategy.rr_target:.1f}")

                    st.markdown("</div>", unsafe_allow_html=True)

                # Trade execution button
                if st.button("⚡ EXECUTE TRADE", type="primary", use_container_width=True):
                    st.success("✅ Trade execution initiated (simulation mode)")
                    # TODO: Implement actual trade execution

            elif action == ActionType.HOLD:
                render_alert_message(
                    "⏸ NO SIGNAL // MONITORING",
                    alert_type="info",
                    slide_in=False
                )

                if state == StrategyState.NO_SETUP:
                    st.info("No valid setup detected. Waiting for ORB formation...")
                elif state == StrategyState.FILTERS_FAILED:
                    st.warning("Setup detected but failed filters. Standing by...")
                elif state == StrategyState.MISSED_ENTRY:
                    st.warning("Entry missed. Monitoring for next opportunity...")
        else:
            st.info("⚡ Strategy engine initialized. Awaiting data...", icon="ℹ️")
    else:
        st.warning("⚠ Strategy engine offline. Initialize data connection to activate.", icon="⚠️")

    render_section_divider("DATA SOURCE")

    # DATA SOURCE CONTROLS
    control_col1, control_col2, control_col3 = st.columns(3)

    with control_col1:
        symbol = st.selectbox(
            "INSTRUMENT",
            ["MGC", "NQ", "MPL"],
            index=["MGC", "NQ", "MPL"].index(st.session_state.current_symbol)
        )
        if symbol != st.session_state.current_symbol:
            st.session_state.current_symbol = symbol
            st.rerun()

    with control_col2:
        if st.button("🔌 INITIALIZE DATA CONNECTION", type="primary", use_container_width=True):
            try:
                with st.spinner("Connecting to data source..."):
                    db_path = get_database_path()
                    st.session_state.data_loader = LiveDataLoader(
                        db_path=db_path,
                        symbol=st.session_state.current_symbol
                    )
                    st.session_state.strategy_engine = StrategyEngine(
                        data_loader=st.session_state.data_loader,
                        symbol=st.session_state.current_symbol
                    )
                    st.success("✅ Data connection established")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                logger.error(f"Failed to initialize data: {e}")
                st.error(f"❌ Connection failed: {str(e)}")

    with control_col3:
        if st.session_state.data_loader:
            if st.button("🔄 REFRESH DATA", use_container_width=True):
                st.session_state.data_loader.refresh()
                st.success("✅ Data refreshed")
                st.rerun()


def render_monitor_view():
    """Position monitoring view"""
    render_terminal_header("POSITION MONITOR", "REAL-TIME TRACKING")

    # Risk metrics overview
    risk_metrics = st.session_state.risk_manager.get_risk_metrics()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card(
            "DAILY P&L",
            f"${risk_metrics.daily_pnl_dollars:+.0f}",
            change=f"{risk_metrics.daily_pnl_r:+.2f}R",
            sentiment="positive" if risk_metrics.daily_pnl_dollars > 0 else "negative" if risk_metrics.daily_pnl_dollars < 0 else "neutral"
        )
    with col2:
        render_metric_card(
            "WEEKLY P&L",
            f"${risk_metrics.weekly_pnl_dollars:+.0f}",
            change=f"{risk_metrics.weekly_pnl_r:+.2f}R",
            sentiment="positive" if risk_metrics.weekly_pnl_dollars > 0 else "negative" if risk_metrics.weekly_pnl_dollars < 0 else "neutral"
        )
    with col3:
        render_metric_card(
            "RISK STATUS",
            risk_metrics.status,
            change=None,
            sentiment="positive" if risk_metrics.status == "SAFE" else "negative"
        )
    with col4:
        render_metric_card(
            "ACTIVE POSITIONS",
            str(risk_metrics.total_positions),
            change=f"${risk_metrics.total_risk_dollars:.0f} at risk",
            sentiment="neutral"
        )

    render_section_divider("ACTIVE POSITIONS")

    # Display active positions
    active_positions = st.session_state.risk_manager.get_active_positions()

    if active_positions:
        for pos in active_positions:
            # Get current price (mock for now)
            current_price = pos['entry_price'] + 5.0  # TODO: Get real current price

            # Update P&L
            st.session_state.risk_manager.update_position_pnl(pos['id'], current_price)

            # Render position panel
            from position_tracker import render_position_panel
            html = render_position_panel(pos, current_price, st.session_state.position_tracker, pos.get('strategy', 'UNKNOWN'))
            st.markdown(html, unsafe_allow_html=True)
    else:
        from position_tracker import render_empty_position_panel
        html = render_empty_position_panel()
        st.markdown(html, unsafe_allow_html=True)

    # Warnings and alerts
    if risk_metrics.warnings:
        render_section_divider("WARNINGS")
        for warning in risk_metrics.warnings:
            render_alert_message(f"⚠ {warning}", alert_type="warning", slide_in=False)

    if risk_metrics.limits_breached:
        render_section_divider("LIMITS BREACHED")
        for breach in risk_metrics.limits_breached:
            render_alert_message(f"🚨 {breach}", alert_type="error", slide_in=False)


def render_analysis_view():
    """Market analysis and charting view"""
    render_terminal_header("MARKET ANALYSIS", "CHARTS & DATA")

    if not st.session_state.data_loader:
        st.warning("⚠ Data connection required. Switch to COMMAND view to initialize.", icon="⚠️")
        return

    # Timeframe selector
    tf_col1, tf_col2, tf_col3 = st.columns([1, 1, 2])
    with tf_col1:
        timeframe = st.selectbox("TIMEFRAME", ["1M", "5M", "15M", "1H", "4H"], index=0)
    with tf_col2:
        lookback = st.selectbox("LOOKBACK", ["1H", "4H", "1D", "1W"], index=2)
    with tf_col3:
        indicators = st.multiselect("INDICATORS", ["ORB", "RSI", "VWAP", "Support/Resistance"], default=["ORB"])

    render_section_divider()

    try:
        latest_data = st.session_state.data_loader.get_latest_data()
        if latest_data is not None and not latest_data.empty:
            # Prepare chart data based on lookback
            lookback_bars = {"1H": 60, "4H": 240, "1D": 1440, "1W": 10080}
            bars = lookback_bars.get(lookback, 1440)

            chart_df = latest_data.tail(bars).copy()
            chart_df['timestamp'] = pd.to_datetime(chart_df['ts_local']) if 'ts_local' in chart_df.columns else pd.to_datetime(chart_df.index)

            # Create chart
            fig = create_terminal_chart(chart_df, title=f"{st.session_state.current_symbol} // {timeframe}", height=600)

            st.plotly_chart(fig, use_container_width=True, key="analysis_chart")

            # Statistics panel
            render_section_divider("STATISTICS")

            stat_col1, stat_col2, stat_col3, stat_col4, stat_col5 = st.columns(5)

            with stat_col1:
                render_metric_card("HIGH", f"${chart_df['high'].max():.2f}", change=None, sentiment="neutral")
            with stat_col2:
                render_metric_card("LOW", f"${chart_df['low'].min():.2f}", change=None, sentiment="neutral")
            with stat_col3:
                range_val = chart_df['high'].max() - chart_df['low'].min()
                render_metric_card("RANGE", f"${range_val:.2f}", change=None, sentiment="neutral")
            with stat_col4:
                avg_vol = chart_df['volume'].mean() if 'volume' in chart_df.columns else 0
                render_metric_card("AVG VOLUME", f"{avg_vol:.0f}", change=None, sentiment="neutral")
            with stat_col5:
                current = chart_df['close'].iloc[-1]
                prev = chart_df['close'].iloc[0]
                change_pct = ((current - prev) / prev) * 100
                render_metric_card("CHANGE", f"{change_pct:+.2f}%", change=None, sentiment="positive" if change_pct > 0 else "negative")
        else:
            st.info("⚡ No data available", icon="ℹ️")
    except Exception as e:
        logger.error(f"Error in analysis view: {e}")
        st.error(f"❌ Error loading analysis data: {str(e)}")


def render_intelligence_view():
    """AI intelligence and market insights"""
    render_terminal_header("MARKET INTELLIGENCE", "AI-POWERED ANALYSIS")

    if not ANTHROPIC_API_KEY:
        st.warning("⚠ AI Assistant requires Anthropic API key. Configure in .env file.", icon="⚠️")
        return

    # Market conditions summary
    market_conditions = st.session_state.market_hours.get_market_conditions(st.session_state.current_symbol)

    col1, col2 = st.columns(2)
    with col1:
        from market_hours_monitor import render_market_hours_indicator
        html = render_market_hours_indicator(market_conditions)
        st.markdown(html, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="info-panel">
            <h3>TRADING CONDITIONS</h3>
        """, unsafe_allow_html=True)
        render_info_row("SESSION", market_conditions.current_session)
        render_info_row("LIQUIDITY", market_conditions.liquidity_level)
        render_info_row("SAFE TO TRADE", "YES" if market_conditions.is_safe_to_trade() else "NO")
        st.markdown("</div>", unsafe_allow_html=True)

    render_section_divider("AI ASSISTANT")

    # Chat interface
    st.markdown("""
    <div style="font-family: var(--font-mono); color: var(--text-secondary); margin-bottom: 16px;">
        Ask questions about market conditions, strategy evaluation, or trade analysis.
    </div>
    """, unsafe_allow_html=True)

    user_query = st.text_input("QUERY", placeholder="e.g., What's the market outlook for MGC today?", label_visibility="collapsed")

    if st.button("🤖 ASK AI", type="primary", use_container_width=True):
        if user_query:
            with st.spinner("Processing query..."):
                try:
                    response = st.session_state.ai_assistant.get_response(user_query)

                    st.markdown("""
                    <div class="terminal-response">
                        <div style="color: var(--profit-green); font-weight: bold; margin-bottom: 8px;">AI RESPONSE:</div>
                    """, unsafe_allow_html=True)

                    st.markdown(response)

                    st.markdown("</div>", unsafe_allow_html=True)
                except Exception as e:
                    logger.error(f"AI Assistant error: {e}")
                    st.error(f"❌ AI request failed: {str(e)}")
        else:
            st.warning("⚠ Please enter a query", icon="⚠️")

    # Recent insights (mock data)
    render_section_divider("RECENT INSIGHTS")

    st.markdown("""
    <div class="info-panel">
        <h4>Market Overview</h4>
        <p>Liquidity conditions are optimal for trading during London/NY sessions.
        ORB setups have 65% win rate over last 30 days.</p>

        <h4>Risk Assessment</h4>
        <p>Current volatility is within normal ranges. Position sizing recommendations are standard.</p>

        <h4>Strategy Performance</h4>
        <p>0900 ORB strategy performing well. 1000 ORB showing strong results in trending markets.</p>
    </div>
    """, unsafe_allow_html=True)


# ============================================================================
# VIEW ROUTER
# ============================================================================

# View selector in sidebar
with st.sidebar:
    st.markdown("<h2 style='color: var(--profit-green); font-family: var(--font-display);'>⚡ TERMINAL</h2>", unsafe_allow_html=True)

    view = st.radio(
        "VIEW MODE",
        ["COMMAND", "MONITOR", "ANALYSIS", "INTELLIGENCE"],
        index=["COMMAND", "MONITOR", "ANALYSIS", "INTELLIGENCE"].index(st.session_state.view_mode)
    )

    if view != st.session_state.view_mode:
        st.session_state.view_mode = view
        st.rerun()

    st.markdown("---")

    st.markdown("""
    <div style="font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary);">
        <div><strong>COMMAND</strong> - Trading decisions</div>
        <div><strong>MONITOR</strong> - Position tracking</div>
        <div><strong>ANALYSIS</strong> - Charts & data</div>
        <div><strong>INTELLIGENCE</strong> - AI insights</div>
    </div>
    """, unsafe_allow_html=True)

# Render selected view
if st.session_state.view_mode == "COMMAND":
    render_command_center()
elif st.session_state.view_mode == "MONITOR":
    render_monitor_view()
elif st.session_state.view_mode == "ANALYSIS":
    render_analysis_view()
elif st.session_state.view_mode == "INTELLIGENCE":
    render_intelligence_view()

# Footer
st.markdown("<div style='text-align: center; margin-top: 48px; padding: 24px; font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary);'>⚡ TRADING TERMINAL // SYSTEM LIVE // {}</div>".format(datetime.now(TZ_LOCAL).strftime('%H:%M:%S')), unsafe_allow_html=True)
