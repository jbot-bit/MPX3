"""
UNIFIED TRADING APP - Market Scanner + AI Chat + Edge Tracker

All-in-one trading intelligence platform:
1. Market Scanner - Which setups are valid TODAY?
2. AI Assistant - Ask questions about performance, patterns, edge health
3. Edge Tracker - Monitor edge performance over time
4. Tradovate Sync - Auto-import trades from broker
5. Data Status - Check database health

Usage:
    streamlit run trading_app/app_simple.py
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
import os

# Setup paths
current_dir = Path(__file__).parent
repo_root = current_dir.parent
for p in [current_dir, repo_root]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from trading_app.market_scanner import MarketScanner
from trading_app.data_bridge import DataBridge
from trading_app.ai_chat import TradingAssistant
from trading_app.edge_tracker import EdgeTracker
from trading_app.memory import TradingMemory
from trading_app.config import TZ_LOCAL, MGC_ORB_CONFIGS

# Page config
st.set_page_config(
    page_title="Trading Intelligence Platform",
    page_icon="🎯",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main { background-color: #0e1117; color: #fafafa; }
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-family: 'Courier New', monospace;
    }
    h1, h2, h3 { color: #fafafa; font-family: 'Courier New', monospace; }
    .valid-setup {
        background-color: #1a3d2a;
        border: 2px solid #2ed573;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .caution-setup {
        background-color: #3d3d1a;
        border: 2px solid #d5d573;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'data_bridge' not in st.session_state:
    st.session_state.data_bridge = DataBridge()
if 'scanner' not in st.session_state:
    st.session_state.scanner = MarketScanner()
if 'assistant' not in st.session_state:
    st.session_state.assistant = TradingAssistant()
if 'edge_tracker' not in st.session_state:
    st.session_state.edge_tracker = EdgeTracker()
if 'memory' not in st.session_state:
    st.session_state.memory = TradingMemory()

# ==============================================================================
# HEADER
# ==============================================================================
st.title("🎯 Trading Intelligence Platform")
now = datetime.now(TZ_LOCAL)
st.caption(f"{now.strftime('%Y-%m-%d %H:%M:%S')} AEST")
st.divider()

# ==============================================================================
# TABS
# ==============================================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Market Scanner",
    "🤖 AI Assistant",
    "📈 Edge Tracker",
    "🔄 Tradovate Sync",
    "⚙️ Data Status"
])

# ==============================================================================
# TAB 1: MARKET SCANNER
# ==============================================================================
with tab1:
    st.header("Market Scanner - Valid Setups Today")

    # Show data status (manual only - saves API calls)
    status = st.session_state.data_bridge.get_status()
    if status['needs_update']:
        st.warning(f"⚠️ Data is {status['gap_days']} days behind. Manual update required - go to 'Data Status' tab.")

    # Scan market
    if st.button("🔍 SCAN NOW", type="primary"):
        st.session_state.scan_results = None  # Force re-scan

    if 'scan_results' not in st.session_state or st.session_state.scan_results is None:
        with st.spinner("Scanning market..."):
            scanner = st.session_state.scanner
            results = scanner.scan_all_setups()
            st.session_state.scan_results = results

    results = st.session_state.scan_results

    # Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("✅ VALID SETUPS", results['valid_count'])
    with col2:
        st.metric("⚠️ CAUTION SETUPS", results['caution_count'])
    with col3:
        st.metric("❌ INVALID SETUPS", results['invalid_count'])

    st.divider()

    # Valid setups
    if results['valid_setups']:
        st.subheader("✅ VALID SETUPS - TAKE THESE TRADES")
        for setup in results['valid_setups']:
            orb_time = setup['orb_time']
            orb_size = setup['conditions']['orb_sizes'].get(orb_time)

            with st.container():
                st.markdown(f"""
                <div class="valid-setup">
                    <h2>{orb_time} ORB - {setup['confidence']} CONFIDENCE</h2>
                </div>
                """, unsafe_allow_html=True)

                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    st.metric("ORB SIZE", f"{orb_size:.3f}" if orb_size else "Not formed")
                with col2:
                    rr = MGC_ORB_CONFIGS[orb_time]['rr']
                    st.metric("RR TARGET", f"{rr}")
                with col3:
                    if setup['conditions']['asia_travel']:
                        st.metric("ASIA TRAVEL", f"{setup['conditions']['asia_travel']:.2f} pts")

                st.write("**Reasons:**")
                for reason in setup['reasons']:
                    st.write(f"• {reason}")

    elif results['caution_setups']:
        st.warning("⚠️ No high-confidence setups. Caution setups available below.")
    else:
        st.error("❌ No valid setups today. Skip trading or wait for conditions to improve.")

    # Caution setups
    if results['caution_setups']:
        with st.expander(f"⚠️ CAUTION SETUPS ({len(results['caution_setups'])})"):
            for setup in results['caution_setups']:
                st.write(f"**{setup['orb_time']} ORB** - {setup['confidence']}")
                for reason in setup['reasons']:
                    st.write(f"• {reason}")
                st.divider()

# ==============================================================================
# TAB 2: AI ASSISTANT
# ==============================================================================
with tab2:
    st.header("🤖 AI Trading Assistant")
    st.caption("Ask about performance, patterns, edge health, or market regime")

    assistant = st.session_state.assistant

    # Pre-defined quick questions
    st.subheader("Quick Questions")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📊 System Health"):
            response = assistant.get_system_health_summary()
            st.markdown(response)

    with col2:
        if st.button("📈 Market Regime"):
            response = assistant.get_regime_summary()
            st.markdown(response)

    with col3:
        if st.button("🎯 Analyze Today"):
            response = assistant.analyze_today()
            st.markdown(response)

    st.divider()

    # Custom question input
    st.subheader("Ask Custom Question")
    question = st.text_input(
        "Question:",
        placeholder="How did 0900 ORB perform last 30 days?"
    )

    if st.button("Ask") and question:
        with st.spinner("Thinking..."):
            response = assistant.ask(question)
            st.markdown(response)

    # Help
    with st.expander("ℹ️ Available Commands"):
        st.markdown("""
        **Performance Queries:**
        - "How did 0900 ORB perform recently?"
        - "1100 ORB performance last 60 days"

        **Edge Health:**
        - "Edge health for 0900 ORB"
        - "System health"

        **Market Analysis:**
        - "Market regime"
        - "Analyze today"

        **Patterns:**
        - "Learned patterns"
        - "What patterns do I know?"
        """)

# ==============================================================================
# TAB 3: EDGE TRACKER
# ==============================================================================
with tab3:
    st.header("📈 Edge Evolution Tracker")
    st.caption("Monitor edge performance over time")

    tracker = st.session_state.edge_tracker

    if st.button("🔄 Refresh Edge Health"):
        st.session_state.system_status = None

    # Get system status
    if 'system_status' not in st.session_state or st.session_state.system_status is None:
        with st.spinner("Analyzing edge health..."):
            status = tracker.get_system_status()
            st.session_state.system_status = status

    status = st.session_state.system_status

    if status['status'] != 'NO_DATA':
        # Overall status
        status_emoji = {
            'EXCELLENT': '🟢',
            'HEALTHY': '✅',
            'CAUTION': '⚠️',
            'DEGRADED': '🔴'
        }
        emoji = status_emoji.get(status['status'], '❓')

        st.markdown(f"### {emoji} System Status: {status['status']}")
        st.info(status['message'])

        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Edges", status['total_edges'])
        with col2:
            st.metric("Excellent", len(status['excellent']))
        with col3:
            st.metric("Watch", len(status['watch']))
        with col4:
            st.metric("Degraded", len(status['degraded']))

        st.divider()

        # Individual edge health
        st.subheader("Individual Edge Health")

        for edge in status['edge_health']:
            orb_time = edge['orb_time']
            edge_status = edge['status']

            # Get detailed health
            health = tracker.check_edge_health(orb_time)

            if health['has_baseline']:
                status_color = {
                    'EXCELLENT': '🟢',
                    'HEALTHY': '✅',
                    'WATCH': '⚠️',
                    'DEGRADED': '🔴'
                }
                emoji = status_color.get(edge_status, '❓')

                with st.expander(f"{emoji} {orb_time} ORB - {edge_status}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write("**Baseline:**")
                        st.write(f"Win Rate: {health['baseline']['win_rate']:.1f}%")
                        st.write(f"Expected R: {health['baseline']['expected_r']:.2f}")

                    with col2:
                        # Check if performance data exists (avoid KeyError)
                        if 'performance' in health and health['performance']['30d']['has_data']:
                            perf = health['performance']['30d']
                            st.write("**Recent (30 days):**")
                            st.write(f"Win Rate: {perf['win_rate']:.1f}%")
                            st.write(f"Avg R: {perf['avg_r']:.2f}")
                            st.write(f"Trades: {perf['total_trades']}")
                        else:
                            st.write("**Recent (30 days):**")
                            st.write("Insufficient data")

                    st.write("**Recommendations:**")
                    if 'recommendations' in health:
                        for rec in health['recommendations']:
                            st.write(f"• {rec}")

        # Market regime
        st.divider()
        st.subheader("Market Regime Analysis")
        regime = tracker.detect_regime()

        regime_emoji = {
            'TRENDING': '📈',
            'RANGE_BOUND': '↔️',
            'VOLATILE': '⚡',
            'QUIET': '🔇'
        }
        emoji = regime_emoji.get(regime['regime'], '❓')

        st.markdown(f"### {emoji} {regime['regime']} ({regime['confidence']:.0%} confidence)")
        st.info(regime['message'])

    else:
        st.warning("No edge data available. Run edge discovery to populate validated_setups.")

# ==============================================================================
# TAB 4: TRADOVATE SYNC
# ==============================================================================
with tab4:
    st.header("🔄 Tradovate Integration")
    st.caption("Auto-import trades from your Tradovate account")

    # Check if credentials are set
    username = os.getenv('TRADOVATE_USERNAME')
    password = os.getenv('TRADOVATE_PASSWORD')

    if username and password:
        st.success("✅ Tradovate credentials found")

        demo_mode = os.getenv('TRADOVATE_DEMO', 'true').lower() == 'true'
        st.info(f"Mode: {'DEMO' if demo_mode else 'LIVE'} account")

        days_back = st.slider("Days to sync:", min_value=1, max_value=90, value=30)

        if st.button("🔄 SYNC TRADES NOW", type="primary"):
            with st.spinner("Syncing trades from Tradovate..."):
                try:
                    from trading_app.tradovate_integration import TradovateIntegration

                    tv = TradovateIntegration()
                    synced_count = tv.sync_trades(days_back=days_back)

                    if synced_count > 0:
                        st.success(f"✅ Synced {synced_count} trades!")
                    else:
                        st.warning("No new trades to sync")

                except Exception as e:
                    st.error(f"Sync failed: {e}")
                    st.exception(e)

        st.divider()

        # Show recent trades from memory
        st.subheader("Recent Trades (from memory)")
        memory = st.session_state.memory
        trades = memory.query_trades(days_back=30, limit=10)

        if trades:
            for trade in trades:
                outcome_color = {
                    'WIN': '🟢',
                    'LOSS': '🔴',
                    'SKIP': '⚪',
                    'BREAKEVEN': '🟡'
                }
                emoji = outcome_color.get(trade['outcome'], '❓')

                with st.expander(f"{emoji} {trade['date_local']} - {trade['orb_time']} ORB - {trade['outcome']}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Outcome:** {trade['outcome']}")
                        st.write(f"**R-Multiple:** {trade['r_multiple']:.2f}" if trade['r_multiple'] else "")
                    with col2:
                        st.write(f"**Asia Travel:** {trade['asia_travel']:.2f}" if trade['asia_travel'] else "")
                        st.write(f"**London Reversals:** {trade['london_reversals']}" if trade['london_reversals'] else "")
                    with col3:
                        if trade['lesson_learned']:
                            st.write(f"**Lesson:** {trade['lesson_learned']}")
        else:
            st.info("No trades in memory yet. Sync from Tradovate to populate.")

    else:
        st.warning("⚠️ Tradovate credentials not configured")

        with st.expander("📝 Setup Instructions"):
            st.markdown("""
            To enable Tradovate integration, add these to your `.env` file:

            ```
            TRADOVATE_USERNAME=your_username
            TRADOVATE_PASSWORD=your_password
            TRADOVATE_DEMO=true
            ```

            **Get credentials:**
            1. Go to https://trader.tradovate.com
            2. Log in to your account
            3. API credentials are your login username/password

            **Demo vs Live:**
            - Set `TRADOVATE_DEMO=true` for demo account
            - Set `TRADOVATE_DEMO=false` for live account

            **After setup:**
            - Restart this app
            - Click "SYNC TRADES NOW" to import your trades
            - Trades will be enriched with session context automatically
            """)

# ==============================================================================
# TAB 5: DATA STATUS
# ==============================================================================
with tab5:
    st.header("⚙️ Data Status")

    bridge = st.session_state.data_bridge
    status = bridge.get_status()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Last DB Date", str(status['last_db_date']) if status['last_db_date'] else "No data")

    with col2:
        st.metric("Current Date", str(status['current_date']))

    with col3:
        if status['gap_days'] == 0:
            st.metric("Status", "CURRENT", delta="✅")
        elif status['gap_days'] > 0:
            st.metric("Gap", f"{status['gap_days']} days", delta="⚠️")
        else:
            st.metric("Status", "NO DATA", delta="❌")

    st.divider()

    if status['needs_update']:
        st.warning(f"⚠️ Data is {status['gap_days']} days behind")

        if st.button("🔄 UPDATE DATA NOW", type="primary"):
            with st.spinner("Updating data..."):
                success = bridge.update_to_current()
                if success:
                    st.success("✅ Data updated!")
                    st.rerun()
                else:
                    st.error("❌ Update failed")
    else:
        st.success("✅ Data is current")

    # Database info
    with st.expander("📊 Database Details"):
        st.write(f"**Database:** {bridge.db_path}")
        st.write(f"**Timezone:** {bridge.tz_local}")
        st.write(f"**Instrument:** MGC (Micro Gold)")

# ==============================================================================
# FOOTER
# ==============================================================================
st.divider()
st.caption("""
**Trading Intelligence Platform v1.0**
Market Scanner | AI Assistant | Edge Tracker | Tradovate Sync
Powered by institutional-grade data and machine learning
""")
