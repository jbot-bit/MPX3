"""
MOBILE TRADING HUB - Streamlit Application
Card-based, swipeable, mobile-first trading interface
"""

import sys
from pathlib import Path

# Add trading_app directory and repo root to Python path (for Streamlit Cloud)
if __name__ == "__main__" or "streamlit" in sys.modules:
    current_dir = Path(__file__).parent
    repo_root = current_dir.parent
    # Add both paths for proper imports
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import logging
import uuid
import os
from streamlit_autorefresh import st_autorefresh

from config import *
from data_loader import LiveDataLoader
from strategy_engine import StrategyEngine, ActionType, StrategyState
from utils import calculate_position_size, format_price, log_to_journal
from ai_memory import AIMemoryManager
from ai_assistant import TradingAIAssistant
from cloud_mode import is_cloud_deployment, show_cloud_setup_instructions
from alert_system import AlertSystem, render_alert_settings, render_audio_player, render_desktop_notification
from setup_scanner import SetupScanner, render_setup_scanner_tab
from enhanced_charting import EnhancedChart, ORBOverlay, TradeMarker, ChartTimeframe, resample_bars
from live_chart_builder import build_live_trading_chart, calculate_trade_levels
from data_quality_monitor import DataQualityMonitor, render_data_quality_panel
from market_hours_monitor import MarketHoursMonitor, render_market_hours_indicator
from risk_manager import RiskManager, RiskLimits, render_risk_dashboard
from position_tracker import PositionTracker, render_position_panel, render_empty_position_panel
from directional_bias import DirectionalBiasDetector, render_directional_bias_indicator
from strategy_discovery import StrategyDiscovery, DiscoveryConfig, add_setup_to_production, generate_config_snippet
# Removed MarketIntelligence - not used in mobile app (skeleton code)
# Removed render_intelligence_panel - not used in mobile app
from professional_ui import (
    inject_professional_css,
    render_pro_metric,
    render_status_badge,
    render_intelligence_card,
    render_countdown_timer,
    render_price_display
)
from mobile_ui import (
    inject_mobile_css,
    render_card_navigation,
    render_dashboard_card,
    render_chart_card,
    render_trade_entry_card,
    render_positions_card,
    render_chart_analysis_card,
    render_ai_chat_card
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CANONICAL ENVIRONMENT CHECK (STARTUP GATE)
# ============================================================================
try:
    from trading_app.canonical import assert_canonical_environment
    assert_canonical_environment()
except Exception as e:
    # Import Streamlit error handling
    import streamlit as st
    st.error(f"""
    **CANONICAL ENVIRONMENT ERROR**

    The application failed to start due to environment validation errors:

    ```
    {str(e)}
    ```

    **How to Fix:**
    1. Ensure CANONICAL.json exists in repository root
    2. Remove any shadow database files (check trading_app/ directory)
    3. Verify data/db/gold.db exists or set CLOUD_MODE=1
    4. Run: `python tools/preflight.py` for detailed diagnostics

    **Contact:** Check README.md for setup instructions
    """)
    st.stop()

# ============================================================================
# DATABASE BOOTSTRAP (Ensure required tables exist)
# ============================================================================
try:
    from db_bootstrap import bootstrap_database
    bootstrap_success = bootstrap_database()
    if not bootstrap_success:
        logger.warning("Database bootstrap completed with warnings (some tables may be missing)")
except Exception as e:
    logger.error(f"Database bootstrap error: {e}")
    # Don't stop app - continue with best effort

# ============================================================================
# PAGE CONFIG - MOBILE OPTIMIZED
# ============================================================================
st.set_page_config(
    page_title="myprojectx",
    page_icon="📱",
    layout="wide",  # Use wide for card layout
    initial_sidebar_state="collapsed"  # Hide sidebar on mobile
)

# Inject mobile CSS
inject_mobile_css()

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================
if "data_loader" not in st.session_state:
    st.session_state.data_loader = None
if "strategy_engine" not in st.session_state:
    st.session_state.strategy_engine = None
if "last_evaluation" not in st.session_state:
    st.session_state.last_evaluation = None
if "account_size" not in st.session_state:
    st.session_state.account_size = DEFAULT_ACCOUNT_SIZE
if "current_symbol" not in st.session_state:
    st.session_state.current_symbol = PRIMARY_INSTRUMENT
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "memory_manager" not in st.session_state:
    st.session_state.memory_manager = AIMemoryManager()  # Uses canonical DB routing
if "ai_assistant" not in st.session_state:
    st.session_state.ai_assistant = TradingAIAssistant(st.session_state.memory_manager)
if "chat_history" not in st.session_state:
    # Load persistent history from database
    try:
        loaded_history = st.session_state.memory_manager.load_session_history(
            session_id=st.session_state.session_id,
            limit=50
        )
        st.session_state.chat_history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in loaded_history
        ]
        if loaded_history:
            logger.info(f"Loaded {len(loaded_history)} messages from persistent memory")
    except Exception as e:
        logger.warning(f"Could not load chat history: {e}")
        st.session_state.chat_history = []
if "alert_system" not in st.session_state:
    st.session_state.alert_system = AlertSystem()
if "data_quality_monitor" not in st.session_state:
    st.session_state.data_quality_monitor = DataQualityMonitor()
if "market_hours_monitor" not in st.session_state:
    st.session_state.market_hours_monitor = MarketHoursMonitor()
if "risk_manager" not in st.session_state:
    limits = RiskLimits(
        daily_loss_dollars=1000.0,
        daily_loss_r=10.0,
        weekly_loss_dollars=3000.0,
        weekly_loss_r=30.0,
        max_concurrent_positions=3,
        max_position_size_pct=2.0
    )
    st.session_state.risk_manager = RiskManager(DEFAULT_ACCOUNT_SIZE, limits)
if "position_tracker" not in st.session_state:
    st.session_state.position_tracker = PositionTracker()
if "setup_scanner" not in st.session_state:
    # Use cloud-aware path (None = auto-detect)
    st.session_state.setup_scanner = SetupScanner(None)
if "chart_timeframe" not in st.session_state:
    st.session_state.chart_timeframe = ChartTimeframe.M1
if "indicators_enabled" not in st.session_state:
    st.session_state.indicators_enabled = {
        "ema_9": False,
        "ema_20": False,
        "vwap": True,
        "rsi": False,
        "orb_overlays": True,
    }
if "directional_bias_detector" not in st.session_state:
    # Use cloud-aware path (None = auto-detect)
    st.session_state.directional_bias_detector = DirectionalBiasDetector(None)
if "strategy_discovery" not in st.session_state:
    # Use cloud-aware path (None = auto-detect)
    st.session_state.strategy_discovery = StrategyDiscovery()
# MarketIntelligence removed - was skeleton code (initialized but never used)
if "mobile_current_card" not in st.session_state:
    st.session_state.mobile_current_card = 0  # Start at Dashboard

# ============================================================================
# AUTO-REFRESH SETUP
# ============================================================================
now = datetime.now(TZ_LOCAL)
is_market_hours = 9 <= now.hour < 17

if 'auto_refresh_enabled' not in st.session_state:
    st.session_state.auto_refresh_enabled = is_market_hours

# Auto-refresh (faster during market hours)
if st.session_state.auto_refresh_enabled:
    refresh_interval = 10 if is_market_hours else 30
    count = st_autorefresh(interval=refresh_interval * 1000, key="mobile_refresh")

# ============================================================================
# DATA INITIALIZATION CHECK
# ============================================================================
if not st.session_state.data_loader or not st.session_state.strategy_engine:
    # Show initialization screen - FIXED positioning
    st.markdown("""
    <div style="
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 60vh;
        padding: 20px;
        text-align: center;
    ">
        <div style="font-size: 64px; margin-bottom: 24px;">📱</div>
        <div style="font-size: 28px; font-weight: 700; color: #f9fafb; margin-bottom: 16px;">
            myprojectx
        </div>
        <div style="font-size: 16px; color: #9ca3af; margin-bottom: 32px;">
            Swipeable cards • Dark mode • Touch optimized
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 Start myprojectx", width='stretch', type="primary"):
        with st.spinner("Loading data..."):
            try:
                # Initialize data loader
                loader = LiveDataLoader(PRIMARY_INSTRUMENT)

                # Fetch data (cloud-aware)
                if is_cloud_deployment():
                    if os.getenv("PROJECTX_API_KEY"):
                        st.info("Connecting to ProjectX API...")
                        try:
                            loader.refresh()
                            st.success("[OK] Fetched live data from ProjectX API")
                        except Exception as e:
                            st.error(f"ProjectX API error: {str(e)[:100]}")
                            logger.error(f"ProjectX refresh failed: {e}", exc_info=True)
                            st.stop()
                    else:
                        st.error("No PROJECTX_API_KEY found. Add it in Streamlit Cloud secrets.")
                        st.stop()
                else:
                    # Local: check if we need to backfill
                    latest_bar = loader.get_latest_bar()
                    needs_backfill = True

                    if latest_bar:
                        latest_time = latest_bar['ts_utc']
                        time_since_last = datetime.now(TZ_UTC) - latest_time
                        if time_since_last.total_seconds() < 6 * 3600:
                            needs_backfill = False

                    if needs_backfill:
                        gold_db_path = str(Path(__file__).parent.parent / "data/db/gold.db")
                        loader.backfill_from_gold_db(gold_db_path, days=2)

                    loader.refresh()

                st.session_state.data_loader = loader

                # Initialize ML engine if enabled (with timeout protection)
                ml_engine = None
                if ML_ENABLED:
                    try:
                        st.info("Loading ML models...")
                        import sys
                        sys.path.insert(0, str(Path(__file__).parent.parent))
                        from ml_inference.inference_engine import MLInferenceEngine
                        ml_engine = MLInferenceEngine()
                        logger.info("ML engine initialized successfully")
                        st.success("ML models loaded [OK]")
                    except ImportError:
                        logger.error("ML enabled but ml_inference module not found. Install ML dependencies or disable with ENABLE_ML=0")
                        st.error("⚠️ ML enabled but not installed. Set ENABLE_ML=0 or install ML dependencies.")
                    except Exception as e:
                        logger.error(f"ML engine initialization failed: {e}")
                        st.error(f"⚠️ ML initialization failed: {e}")
                else:
                    logger.info("ML disabled (ENABLE_ML not set)")

                # Initialize strategy engine
                st.info("Initializing strategy engine...")
                st.session_state.strategy_engine = StrategyEngine(loader, ml_engine=ml_engine)

                st.success(f"[OK] Loaded data for {PRIMARY_INSTRUMENT}")
                logger.info(f"Data initialized for {PRIMARY_INSTRUMENT}")

                # Small delay to show success message
                time.sleep(0.5)
                st.rerun()

            except Exception as e:
                st.error(f"Error loading data: {e}")
                logger.error(f"Data load error: {e}", exc_info=True)

    st.info("☁️ Cloud Mode: Data will be fetched from ProjectX API" if is_cloud_deployment() else "💻 Local Mode: Data loaded from local database")

    st.stop()

# ============================================================================
# EVALUATE STRATEGIES
# ============================================================================
try:
    evaluation = st.session_state.strategy_engine.evaluate_all()
    st.session_state.last_evaluation = evaluation
    log_to_journal(evaluation)
except Exception as e:
    st.error(f"Strategy evaluation error: {e}")
    logger.error(f"Evaluation error: {e}", exc_info=True)
    evaluation = None

# ============================================================================
# CARD-BASED NAVIGATION
# ============================================================================

# Card definitions - 4 cards with integrated AI chat
CARDS = [
    {"name": "Dashboard", "icon": "📊", "render": render_dashboard_card},
    {"name": "Chart", "icon": "📈", "render": render_chart_card},
    {"name": "Trade", "icon": "🎯", "render": render_trade_entry_card},
    {"name": "Analyze", "icon": "🔍", "render": render_chart_analysis_card},
]

card_names = [f"{card['icon']} {card['name']}" for card in CARDS]
current_card = st.session_state.mobile_current_card

# Bounds check (in case we reduced cards from 5 to 3)
if current_card >= len(CARDS):
    st.session_state.mobile_current_card = 0
    current_card = 0

# WRAP ENTIRE CARD SECTION IN TRY-EXCEPT
try:
    # Navigation
    render_card_navigation(current_card, len(CARDS), card_names)

    # Render current card
    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)  # Spacer
    # Debug: Log which card we're rendering
    card_name = CARDS[current_card]['name']
    logger.info(f"Rendering card: {card_name}")

    if current_card == 0:
        # Dashboard
        render_dashboard_card(
            st.session_state.data_loader,
            st.session_state.strategy_engine,
            evaluation,
            st.session_state.current_symbol
        )
    elif current_card == 1:
        # Chart
        render_chart_card(
            st.session_state.data_loader,
            st.session_state.strategy_engine,
            evaluation
        )
    elif current_card == 2:
        # Trade Entry
        render_trade_entry_card(
            st.session_state.data_loader,
            st.session_state.strategy_engine
        )
    elif current_card == 3:
        # Chart Analysis
        render_chart_analysis_card(
            instrument=st.session_state.current_symbol
        )

    # AI Chat integrated at bottom of every card
    st.markdown("---")
    st.markdown("### 🤖 AI Assistant")

    # Compact AI chat for all cards
    try:
        render_ai_chat_card(
            st.session_state.ai_assistant,
            st.session_state.chat_history,
            st.session_state.current_symbol,
            st.session_state.data_loader,
            compact=True  # New parameter for compact mode
        )
    except Exception as ai_error:
        st.warning(f"AI Assistant temporarily unavailable: {ai_error}")
        st.info("You can still use all other features. Chart and Trade Calculator work normally.")

except Exception as e:
    card_name = CARDS[current_card]['name']
    st.error(f"❌ Error rendering {card_name} card: {e}")

    # Show more details for debugging
    import traceback
    with st.expander("🔍 Error Details (for debugging)"):
        st.code(traceback.format_exc())
        st.json({
            "card": card_name,
            "card_index": current_card,
            "error": str(e),
            "error_type": type(e).__name__
        })

    logger.error(f"Card render error ({card_name}): {e}", exc_info=True)

    st.warning("Try refreshing the page or switching to a different card.")

    # Fallback: Show basic trade calculator
    st.markdown("### 📊 Trade Calculator (Fallback)")
    st.info("While we fix the issue, you can use the basic calculator:")

    orb_high = st.number_input("ORB High", value=2655.0, step=0.1)
    orb_low = st.number_input("ORB Low", value=2650.0, step=0.1)

    if orb_high > orb_low:
        orb_size = orb_high - orb_low
        st.metric("ORB Size", f"{orb_size:.2f} points")

# ============================================================================
# RESEARCH WORKBENCH (Discovery + Pipeline)
# ============================================================================

st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

with st.expander("🔬 Research Workbench", expanded=False):
    try:
        from research_workbench import render_research_workbench
        render_research_workbench()
    except Exception as e:
        st.error(f"Error loading Research Workbench: {e}")
        logger.error(f"Research Workbench error: {e}")

# ============================================================================
# SETTINGS MODAL (OPTIONAL - ACCESSIBLE VIA BOTTOM BUTTON)
# ============================================================================

# Small settings button at bottom
st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)

with st.expander("⚙️ Settings", expanded=False):
    st.markdown("### App Settings")

    # Account size
    account_size = st.number_input(
        "Account Size ($)",
        min_value=1000.0,
        max_value=10000000.0,
        value=st.session_state.account_size,
        step=1000.0,
        key="mobile_account_size"
    )
    st.session_state.account_size = account_size

    # Auto-refresh toggle
    auto_refresh = st.checkbox(
        "Auto-refresh",
        value=st.session_state.auto_refresh_enabled,
        key="mobile_auto_refresh"
    )
    st.session_state.auto_refresh_enabled = auto_refresh

    if auto_refresh:
        st.info(f"Refreshing every {refresh_interval}s")

    # Refresh data button
    if st.button("🔄 Refresh Data Now", width='stretch'):
        with st.spinner("Refreshing..."):
            try:
                st.session_state.data_loader.refresh()
                st.success("Data refreshed!")
                st.rerun()
            except Exception as e:
                st.error(f"Refresh error: {e}")

    # Reset button
    if st.button("🔄 Reset App", width='stretch', type="secondary"):
        st.session_state.clear()
        st.success("App reset! Reloading...")
        st.rerun()

# Footer
st.markdown("""
<div style="
    text-align: center;
    padding: 20px;
    color: #6b7280;
    font-size: 12px;
">
    Trading Hub Mobile v2.0 • Swipe to navigate • {time}
</div>
""".format(time=datetime.now(TZ_LOCAL).strftime('%H:%M:%S')), unsafe_allow_html=True)
