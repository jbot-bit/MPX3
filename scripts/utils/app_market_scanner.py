"""
MARKET SCANNER APP - Streamlit Application

Real-time market scanner that tells you which setups are valid TODAY.

Features:
- Auto-updates data gaps (data bridge)
- Scans all validated setups
- Shows TAKE / CAUTION / SKIP recommendations
- Real-time ORB status and conditions

Usage:
    streamlit run app_market_scanner.py
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, date

# Add trading_app to path
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from trading_app.market_scanner import MarketScanner
from trading_app.data_bridge import DataBridge
from trading_app.config import TZ_LOCAL, MGC_ORB_CONFIGS

# Page config
st.set_page_config(
    page_title="Market Scanner",
    page_icon="🎯",
    layout="wide"
)

# Title
st.title("🎯 Market Scanner - Real-Time Setup Validator")
st.caption("Scans current market conditions and tells you which setups are tradeable TODAY")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")

    # Auto-update toggle
    auto_update = st.toggle(
        "Auto-update data",
        value=True,
        help="Automatically fill data gaps before scanning"
    )

    # Date selection
    scan_today = st.toggle(
        "Scan today",
        value=True,
        help="Scan current market conditions"
    )

    if not scan_today:
        selected_date = st.date_input(
            "Select date",
            value=date.today()
        )
    else:
        selected_date = None

    st.divider()

    # Scan button
    if st.button("🔍 SCAN MARKET", type="primary", use_container_width=True):
        st.session_state.trigger_scan = True

    st.divider()

    # Status section
    st.subheader("📊 Data Status")

    # Initialize data bridge
    if 'data_bridge' not in st.session_state:
        st.session_state.data_bridge = DataBridge()

    bridge = st.session_state.data_bridge
    status = bridge.get_status()

    # Show status
    st.metric("Last DB Date", str(status['last_db_date']) if status['last_db_date'] else "No data")
    st.metric("Current Date", str(status['current_date']))

    if status['gap_days'] > 0:
        st.warning(f"⚠️ Gap: {status['gap_days']} days")
    elif status['gap_days'] == 0:
        st.success("✅ Data current")
    elif status['gap_days'] == -1:
        st.error("❌ No data")

    if status['needs_update']:
        if st.button("Update Now", use_container_width=True):
            with st.spinner("Updating data..."):
                success = bridge.update_to_current()
                if success:
                    st.success("Data updated!")
                    st.rerun()
                else:
                    st.error("Update failed")

# Main content
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    st.metric("Valid Setups", 0, delta=None, help="High confidence - TAKE TRADE")
with col2:
    st.metric("Caution Setups", 0, delta=None, help="Medium confidence - trade with care")
with col3:
    st.metric("Invalid Setups", 0, delta=None, help="Skip today")

st.divider()

# Trigger scan
if 'trigger_scan' in st.session_state and st.session_state.trigger_scan:
    st.session_state.trigger_scan = False

    with st.spinner("Scanning market..."):
        try:
            # Initialize scanner
            scanner = MarketScanner()

            # Run scan
            results = scanner.scan_all_setups(
                date_local=selected_date,
                auto_update=auto_update
            )

            # Update metrics
            col1.metric("Valid Setups", results['valid_count'], help="High confidence - TAKE TRADE")
            col2.metric("Caution Setups", results['caution_count'], help="Medium confidence - trade with care")
            col3.metric("Invalid Setups", results['invalid_count'], help="Skip today")

            # Store results in session state
            st.session_state.scan_results = results

        except Exception as e:
            st.error(f"Scan failed: {e}")
            st.exception(e)

# Display results
if 'scan_results' in st.session_state:
    results = st.session_state.scan_results

    st.header(f"📅 Scan Results - {results['date_local']}")
    st.caption(f"Scanned at: {results['scan_time'].strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # Summary banner
    st.info(f"**Summary:** {results['summary']}")

    # Valid setups
    if results['valid_setups']:
        st.subheader("✅ VALID SETUPS (High Confidence - TAKE TRADE)")

        for setup in results['valid_setups']:
            with st.expander(f"**{setup['orb_time']} ORB** - {setup['confidence']} confidence", expanded=True):
                orb_size = setup['conditions']['orb_sizes'].get(setup['orb_time'])

                col1, col2, col3 = st.columns([1, 1, 2])

                with col1:
                    st.metric("ORB Size", f"{orb_size:.3f}" if orb_size else "Not formed")

                with col2:
                    st.metric("Confidence", setup['confidence'])

                with col3:
                    st.metric("Recommendation", setup['recommendation'])

                st.write("**Reasons:**")
                for reason in setup['reasons']:
                    st.write(f"- {reason}")

                # Show session conditions
                if setup['conditions']['asia_travel']:
                    st.write(f"**Asia Travel:** {setup['conditions']['asia_travel']:.2f} points")

    # Caution setups
    if results['caution_setups']:
        st.subheader("⚠️ CAUTION SETUPS (Medium Confidence - Trade with Care)")

        for setup in results['caution_setups']:
            with st.expander(f"**{setup['orb_time']} ORB** - {setup['confidence']} confidence"):
                orb_size = setup['conditions']['orb_sizes'].get(setup['orb_time'])

                col1, col2, col3 = st.columns([1, 1, 2])

                with col1:
                    st.metric("ORB Size", f"{orb_size:.3f}" if orb_size else "Not formed")

                with col2:
                    st.metric("Confidence", setup['confidence'])

                with col3:
                    st.metric("Recommendation", setup['recommendation'])

                st.write("**Reasons:**")
                for reason in setup['reasons']:
                    st.write(f"- {reason}")

    # Invalid setups
    if results['invalid_setups']:
        with st.expander(f"❌ INVALID SETUPS ({len(results['invalid_setups'])} setups - skip today)"):
            for setup in results['invalid_setups']:
                orb_size = setup['conditions']['orb_sizes'].get(setup['orb_time'])
                size_str = f"{orb_size:.3f}" if orb_size is not None else "Not formed"

                st.write(f"**{setup['orb_time']} ORB** - {setup['recommendation']}")
                st.write(f"  - ORB size: {size_str}")
                for reason in setup['reasons']:
                    st.write(f"  - {reason}")
                st.divider()

else:
    # No results yet
    st.info("👆 Click 'SCAN MARKET' in sidebar to start")

    # Show ORB schedule
    st.subheader("📅 ORB Schedule")

    for orb_time, config in MGC_ORB_CONFIGS.items():
        hour = int(orb_time[:2])
        minute = int(orb_time[2:])

        with st.expander(f"{orb_time} ORB ({hour:02d}:{minute:02d} local time)"):
            st.write(f"**RR Target:** {config['rr']}")
            st.write(f"**Stop Loss Mode:** {config['sl_mode']}")
            st.write(f"**Window:** 5 minutes")

# Footer
st.divider()
st.caption("Market Scanner v1.0 - Powered by institutional-grade data and validation logic")
