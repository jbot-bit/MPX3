"""
Mobile-First UI Components
Card-based swipeable navigation optimized for mobile devices
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import duckdb
from pathlib import Path
from config import TZ_LOCAL
from live_chart_builder import build_live_trading_chart, calculate_trade_levels


# ============================================================================
# MOBILE CSS - Touch-Optimized, Card-Based Layout
# ============================================================================

MOBILE_CSS = """
<style>
    /* Mobile-First Base Styles */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        -webkit-tap-highlight-color: transparent;
        touch-action: manipulation;
    }

    /* Root Variables for Dark Theme */
    :root {
        --bg-primary: #0a0b0d;
        --bg-card: #1a1d26;
        --bg-elevated: #252933;
        --text-primary: #f9fafb;
        --text-secondary: #9ca3af;
        --accent-green: #10b981;
        --accent-red: #ef4444;
        --accent-indigo: #6366f1;
        --border-subtle: #374151;
    }

    /* Main Container - Constrained for desktop */
    .main .block-container {
        padding: 0 !important;
        max-width: 600px !important;  /* Max width on desktop monitors */
        margin: 0 auto !important;  /* Center on large screens */
    }

    /* On actual mobile, use full width */
    @media (max-width: 768px) {
        .main .block-container {
            max-width: 100% !important;
            margin: 0 !important;
        }
    }

    /* Hide Desktop Elements */
    #MainMenu, footer, header {visibility: hidden;}
    [data-testid="stSidebar"] {display: none !important;}

    /* Card Container - Horizontal Scroll */
    .card-container {
        display: flex;
        overflow-x: auto;
        scroll-snap-type: x mandatory;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
        height: 100vh;
    }

    .card-container::-webkit-scrollbar {
        display: none;
    }

    /* Individual Card */
    .card {
        min-width: 100vw;
        max-width: 100vw;
        height: 100vh;
        scroll-snap-align: start;
        padding: 16px;
        overflow-y: auto;
        background: var(--bg-primary);
    }

    /* Navigation Dots */
    .nav-dots {
        position: fixed;
        top: 12px;
        left: 50%;
        transform: translateX(-50%);
        display: flex;
        gap: 8px;
        z-index: 1000;
        background: rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(10px);
        padding: 8px 16px;
        border-radius: 20px;
    }

    .nav-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--text-secondary);
        opacity: 0.5;
        transition: all 0.3s ease;
    }

    .nav-dot.active {
        width: 24px;
        border-radius: 4px;
        background: var(--accent-indigo);
        opacity: 1;
    }

    /* Navigation Arrows */
    .nav-arrows {
        position: fixed;
        top: 12px;
        width: 100%;
        display: flex;
        justify-content: space-between;
        padding: 0 12px;
        z-index: 999;
        pointer-events: none;
    }

    .nav-arrow {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(10px);
        color: var(--text-primary);
        border: 1px solid var(--border-subtle);
        font-size: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        pointer-events: auto;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .nav-arrow:active {
        transform: scale(0.95);
        background: rgba(0, 0, 0, 0.7);
    }

    .nav-arrow:disabled {
        opacity: 0.3;
        pointer-events: none;
    }

    /* Mobile Buttons - Touch Optimized */
    .mobile-btn {
        min-height: 48px;
        min-width: 48px;
        border-radius: 12px;
        padding: 12px 24px;
        font-size: 16px;
        font-weight: 600;
        border: none;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .mobile-btn-primary {
        background: linear-gradient(135deg, var(--accent-indigo) 0%, #4f46e5 100%);
        color: white;
    }

    .mobile-btn-success {
        background: var(--accent-green);
        color: white;
    }

    .mobile-btn-danger {
        background: var(--accent-red);
        color: white;
    }

    /* Large Touch Targets */
    .stButton > button {
        min-height: 48px !important;
        font-size: 16px !important;
        border-radius: 12px !important;
    }

    /* Metric Cards - Mobile Optimized */
    .mobile-metric {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        margin: 8px 0;
    }

    .mobile-metric-label {
        font-size: 12px;
        font-weight: 600;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }

    .mobile-metric-value {
        font-size: 24px;
        font-weight: 800;
        color: var(--text-primary);
        line-height: 1.2;
        font-variant-numeric: tabular-nums;
    }

    .mobile-metric-value-large {
        font-size: 36px;
    }

    .mobile-metric-subtitle {
        font-size: 16px;
        color: var(--text-secondary);
        margin-top: 4px;
    }

    /* Countdown Timer - Large */
    .mobile-countdown {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 2px solid var(--accent-indigo);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        margin: 12px 0;
    }

    .mobile-countdown-value {
        font-size: 32px;
        font-weight: 800;
        color: var(--accent-indigo);
        font-variant-numeric: tabular-nums;
        letter-spacing: -1px;
    }

    .mobile-countdown-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 6px;
    }

    /* Status Card */
    .mobile-status {
        background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-elevated) 100%);
        border-left: 6px solid var(--accent-indigo);
        border-radius: 12px;
        padding: 20px;
        margin: 16px 0;
    }

    .mobile-status-header {
        font-size: 24px;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 12px;
    }

    .mobile-status-reasons {
        list-style: none;
        padding: 0;
        margin: 0;
    }

    .mobile-status-reasons li {
        padding: 8px 0;
        font-size: 16px;
        color: var(--text-secondary);
        border-left: 3px solid var(--accent-indigo);
        padding-left: 12px;
        margin: 4px 0;
    }

    .mobile-status-action {
        background: rgba(99, 102, 241, 0.2);
        border: 2px solid var(--accent-indigo);
        border-radius: 8px;
        padding: 16px;
        font-size: 18px;
        font-weight: 700;
        color: var(--accent-indigo);
        text-align: center;
        margin-top: 16px;
    }

    /* Collapsible Section */
    .mobile-collapsible {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        margin: 12px 0;
        overflow: hidden;
    }

    .mobile-collapsible-header {
        padding: 16px;
        font-size: 18px;
        font-weight: 600;
        color: var(--text-primary);
        cursor: pointer;
        display: flex;
        justify-content: space-between;
        align-items: center;
        min-height: 56px;
    }

    .mobile-collapsible-content {
        padding: 16px;
        border-top: 1px solid var(--border-subtle);
    }

    /* Chart Container - Mobile */
    .mobile-chart {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 8px;
        margin: 12px 0;
        overflow: hidden;
    }

    /* Trade Calculator */
    .mobile-trade-calc {
        background: var(--bg-card);
        border: 2px solid var(--accent-indigo);
        border-radius: 16px;
        padding: 20px;
        margin: 16px 0;
    }

    .mobile-trade-toggle {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        margin-bottom: 20px;
    }

    .mobile-trade-toggle-btn {
        min-height: 56px;
        border-radius: 12px;
        font-size: 18px;
        font-weight: 700;
        border: 2px solid transparent;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .mobile-trade-toggle-btn.active {
        border-color: var(--accent-indigo);
        background: rgba(99, 102, 241, 0.2);
    }

    .mobile-trade-input {
        margin: 12px 0;
    }

    .mobile-trade-input label {
        font-size: 14px;
        font-weight: 600;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
        display: block;
    }

    .mobile-trade-input input {
        width: 100%;
        min-height: 48px;
        padding: 12px 16px;
        font-size: 18px;
        font-weight: 600;
        background: var(--bg-elevated);
        border: 1px solid var(--border-subtle);
        border-radius: 8px;
        color: var(--text-primary);
    }

    .mobile-trade-result {
        background: var(--bg-elevated);
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
    }

    .mobile-trade-result-label {
        font-size: 12px;
        color: var(--text-secondary);
        text-transform: uppercase;
        margin-bottom: 4px;
    }

    .mobile-trade-result-value {
        font-size: 24px;
        font-weight: 700;
        color: var(--text-primary);
    }

    /* Chat Interface */
    .mobile-chat {
        height: calc(100vh - 32px);
        display: flex;
        flex-direction: column;
    }

    .mobile-chat-history {
        flex: 1;
        overflow-y: auto;
        padding: 16px;
        margin-bottom: 12px;
    }

    .mobile-chat-message {
        margin: 12px 0;
        padding: 12px 16px;
        border-radius: 12px;
        max-width: 85%;
    }

    .mobile-chat-message-user {
        background: var(--accent-indigo);
        color: white;
        margin-left: auto;
    }

    .mobile-chat-message-ai {
        background: var(--bg-card);
        color: var(--text-primary);
        border: 1px solid var(--border-subtle);
    }

    .mobile-chat-input-container {
        padding: 12px;
        background: var(--bg-card);
        border-top: 1px solid var(--border-subtle);
    }

    .mobile-chat-input {
        width: 100%;
        min-height: 48px;
        padding: 12px 16px;
        font-size: 16px;
        background: var(--bg-elevated);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        color: var(--text-primary);
        resize: none;
    }

    .mobile-chat-quick-actions {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-top: 8px;
    }

    /* Position Card */
    .mobile-position {
        background: var(--bg-card);
        border-left: 4px solid var(--accent-green);
        border-radius: 12px;
        padding: 20px;
        margin: 12px 0;
    }

    .mobile-position-header {
        font-size: 20px;
        font-weight: 700;
        color: var(--text-primary);
        margin-bottom: 12px;
    }

    .mobile-position-pnl {
        font-size: 28px;
        font-weight: 800;
        color: var(--accent-green);
        margin: 8px 0;
    }

    .mobile-position-pnl.negative {
        color: var(--accent-red);
    }

    .mobile-position-progress {
        height: 8px;
        background: var(--bg-elevated);
        border-radius: 4px;
        overflow: hidden;
        margin: 12px 0;
    }

    .mobile-position-progress-bar {
        height: 100%;
        background: var(--accent-green);
        transition: width 0.3s ease;
    }

    /* Responsive Fonts */
    @media (max-width: 375px) {
        .mobile-metric-value {
            font-size: 28px;
        }
        .mobile-metric-value-large {
            font-size: 40px;
        }
        .mobile-countdown-value {
            font-size: 40px;
        }
    }

    /* Landscape Adjustments */
    @media (orientation: landscape) {
        .card {
            padding: 12px;
        }
        .mobile-metric {
            padding: 12px;
        }
    }
</style>
"""


def inject_mobile_css():
    """Inject mobile-optimized CSS into Streamlit app"""
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)


def get_setup_config(instrument: str, orb_time: str, db_path: str = None):
    """
    Query validated_setups to get RR and SL_MODE for a specific setup

    Args:
        instrument: e.g., 'MGC', 'NQ', 'MPL'
        orb_time: e.g., '0900', '1000', '1100'
        db_path: Path to gold.db (auto-detected if None)

    Returns:
        dict with 'rr', 'sl_mode', 'tier', 'win_rate', 'avg_r', or None if not found
    """
    try:
        if db_path is None:
            # Auto-detect gold.db (use canonical path)
            db_path = Path(__file__).parent.parent / "data/db/gold.db"
            if not db_path.exists():
                return None

        conn = duckdb.connect(str(db_path), read_only=True)

        # Query for HALF setup first (preferred), then FULL as fallback
        query = """
        SELECT rr, sl_mode, tier, win_rate, avg_r
        FROM validated_setups
        WHERE instrument = ? AND orb_time = ?
        ORDER BY CASE WHEN sl_mode = 'HALF' THEN 1 ELSE 2 END
        LIMIT 1
        """

        result = conn.execute(query, [instrument, orb_time]).fetchone()
        conn.close()

        if result:
            return {
                'rr': result[0],
                'sl_mode': result[1],
                'tier': result[2],
                'win_rate': result[3],
                'avg_r': result[4]
            }
        else:
            # Fallback defaults if not in database
            return {
                'rr': 1.0,
                'sl_mode': 'HALF',
                'tier': 'C',
                'win_rate': 50.0,
                'avg_r': 0.5
            }
    except Exception as e:
        # Fallback defaults on error
        return {
            'rr': 1.0,
            'sl_mode': 'HALF',
            'tier': 'C',
            'win_rate': 50.0,
            'avg_r': 0.5
        }


# ============================================================================
# CARD NAVIGATION
# ============================================================================

def render_card_navigation(current_card: int, total_cards: int, card_names: list):
    """
    Render card navigation with dots and arrows

    Args:
        current_card: Index of current card (0-based)
        total_cards: Total number of cards
        card_names: List of card display names
    """

    # Navigation arrows
    col1, col2, col3 = st.columns([1, 6, 1])

    with col1:
        if st.button("◄", key="nav_prev", disabled=(current_card == 0), width='stretch'):
            st.session_state.mobile_current_card = current_card - 1
            st.rerun()

    with col2:
        # Dots indicator
        dots_html = '<div class="nav-dots">'
        for i in range(total_cards):
            active_class = "active" if i == current_card else ""
            dots_html += f'<div class="nav-dot {active_class}"></div>'
        dots_html += '</div>'
        st.markdown(dots_html, unsafe_allow_html=True)

        # Card name
        st.markdown(f"<div style='text-align: center; color: #9ca3af; font-size: 14px; margin-top: 8px;'>{card_names[current_card]} ({current_card + 1}/{total_cards})</div>", unsafe_allow_html=True)

    with col3:
        if st.button("►", key="nav_next", disabled=(current_card == total_cards - 1), width='stretch'):
            st.session_state.mobile_current_card = current_card + 1
            st.rerun()


# ============================================================================
# CARD 1: DASHBOARD (Quick Glance)
# ============================================================================

def render_dashboard_card(data_loader, strategy_engine, latest_evaluation, current_symbol="MGC"):
    """
    Dashboard Card - Most important info at a glance

    Shows:
    - Live status indicator
    - Current price (large)
    - ATR + filter status
    - Next ORB countdown
    - Status + reasons
    - Next action
    - Market intelligence
    - Safety status
    - Setup scanner results
    """
    # Ensure datetime is available in function scope
    from datetime import datetime as dt

    st.markdown("## 🔴 LIVE Dashboard")

    # Get current data
    latest_bar = data_loader.get_latest_bar() if data_loader else None
    current_price = latest_bar['close'] if latest_bar else 0

    # Handle None from get_today_atr() (happens on weekends/holidays)
    atr_raw = data_loader.get_today_atr() if data_loader else None
    current_atr = atr_raw if atr_raw is not None else 40.0

    # Check if we have live data
    has_data = latest_bar is not None and current_price > 0

    # Large price display
    if has_data:
        st.markdown(f"""
        <div class="mobile-metric">
            <div class="mobile-metric-label">MGC Price</div>
            <div class="mobile-metric-value mobile-metric-value-large">${current_price:.2f}</div>
            <div class="mobile-metric-subtitle">{dt.now(TZ_LOCAL).strftime('%H:%M:%S')}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Show last available data timestamp if exists
        if latest_bar and 'ts_local' in latest_bar:
            last_time = latest_bar['ts_local'].strftime('%Y-%m-%d %H:%M')
            subtitle = f"Last: {last_time}"
        else:
            subtitle = "Market Closed / No Data"

        st.markdown(f"""
        <div class="mobile-metric">
            <div class="mobile-metric-label">MGC Price</div>
            <div class="mobile-metric-value mobile-metric-value-large">--</div>
            <div class="mobile-metric-subtitle">{subtitle}</div>
        </div>
        """, unsafe_allow_html=True)

    # ATR + Filter Status
    col1, col2 = st.columns(2)
    with col1:
        atr_display = f"{current_atr:.2f}" if current_atr else "--"
        st.markdown(f"""
        <div class="mobile-metric">
            <div class="mobile-metric-label">ATR (20)</div>
            <div class="mobile-metric-value">{atr_display}</div>
            <div class="mobile-metric-subtitle">points</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        # Check if next ORB has filter
        if current_atr:
            filter_2300 = 0.155 * current_atr
            filter_passed = "✅" if filter_2300 > 0 else "⏭️"
            filter_display = f"&lt;{filter_2300:.1f}pts"
        else:
            filter_passed = "⏸️"
            filter_display = "N/A"

        st.markdown(f"""
        <div class="mobile-metric">
            <div class="mobile-metric-label">Filter Status</div>
            <div class="mobile-metric-value" style="font-size: 40px;">{filter_passed}</div>
            <div class="mobile-metric-subtitle">{filter_display}</div>
        </div>
        """, unsafe_allow_html=True)

    # Next ORB Countdown
    st.markdown("### ⏰ Next ORB")

    now = dt.now(TZ_LOCAL)
    orb_times = {
        "0900": (9, 0, 5),
        "1000": (10, 0, 5),
        "1100": (11, 0, 5),
        "1800": (18, 0, 5),
        "2300": (23, 0, 5),
        "0030": (0, 30, 35),
    }

    # Find next ORB
    next_orb_name = None
    next_orb_start = None
    min_delta = timedelta(days=1)

    for orb_name, (hour, minute, end_minute) in orb_times.items():
        orb_start = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if hour == 0 and now.hour >= 12:
            orb_start += timedelta(days=1)

        if now > orb_start:
            orb_start += timedelta(days=1)

        delta = orb_start - now
        if delta < min_delta and delta > timedelta(0):
            min_delta = delta
            next_orb_name = orb_name
            next_orb_start = orb_start

    if next_orb_name and next_orb_start:
        time_until = (next_orb_start - now).total_seconds()
        hours = int(time_until // 3600)
        minutes = int((time_until % 3600) // 60)
        seconds = int(time_until % 60)

        st.markdown(f"""
        <div class="mobile-countdown">
            <div style="font-size: 18px; font-weight: 600; color: #9ca3af; margin-bottom: 8px;">{next_orb_name} ORB</div>
            <div class="mobile-countdown-value">{hours:02d}:{minutes:02d}:{seconds:02d}</div>
            <div class="mobile-countdown-label">Until Window Opens</div>
        </div>
        """, unsafe_allow_html=True)

    # Status Card (ENHANCED with complete explanations)
    if latest_evaluation:
        st.markdown("### 🎯 Status")

        action = latest_evaluation.action.value
        reasons = latest_evaluation.reasons[:4]  # Show 4 reasons now (expanded)
        next_action = latest_evaluation.next_instruction

        # Get new fields
        setup_name = getattr(latest_evaluation, 'setup_name', None)
        setup_tier = getattr(latest_evaluation, 'setup_tier', None)
        orb_high = getattr(latest_evaluation, 'orb_high', None)
        orb_low = getattr(latest_evaluation, 'orb_low', None)
        direction = getattr(latest_evaluation, 'direction', None)
        rr = getattr(latest_evaluation, 'rr', None)
        win_rate = getattr(latest_evaluation, 'win_rate', None)
        avg_r = getattr(latest_evaluation, 'avg_r', None)
        annual_trades = getattr(latest_evaluation, 'annual_trades', None)
        entry_price = getattr(latest_evaluation, 'entry_price', None)
        stop_price = getattr(latest_evaluation, 'stop_price', None)
        target_price = getattr(latest_evaluation, 'target_price', None)

        # Setup header with tier badge
        if setup_name and setup_tier:
            tier_colors = {
                "S+": "#ffd700",  # Gold
                "S": "#c0c0c0",   # Silver
                "A": "#cd7f32",   # Bronze
                "B": "#9ca3af",   # Gray
                "C": "#6b7280"    # Darker gray
            }
            tier_color = tier_colors.get(setup_tier, "#9ca3af")
            setup_header = f'<div style="font-size: 16px; margin-bottom: 8px;"><strong>{setup_name}</strong> <span style="background: {tier_color}; color: #000; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 700;">{setup_tier}</span></div>'
        else:
            setup_header = ""

        # ORB range display
        if orb_high and orb_low:
            orb_size = orb_high - orb_low
            orb_range_html = f'<div style="font-size: 14px; color: #9ca3af; margin-bottom: 8px;">ORB: ${orb_low:.2f} - ${orb_high:.2f} ({orb_size:.2f} pts)</div>'
        else:
            orb_range_html = ""

        # Direction indicator
        if direction:
            direction_color = "#10b981" if direction == "LONG" else "#ef4444"
            direction_emoji = "🚀" if direction == "LONG" else "🔻"
            direction_html = f'<div style="font-size: 14px; color: {direction_color}; font-weight: 600; margin-bottom: 8px;">{direction_emoji} {direction}</div>'
        else:
            direction_html = ""

        reasons_html = "".join([f"<li style='font-size: 13px;'>• {reason}</li>" for reason in reasons])

        st.markdown(f"""
        <div class="mobile-status">
            <div class="mobile-status-header">{action}</div>
            {setup_header}
            {direction_html}
            {orb_range_html}
            <ul class="mobile-status-reasons">
                {reasons_html}
            </ul>
            <div class="mobile-status-action">
                {next_action}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Setup Statistics (if available)
        if win_rate is not None and avg_r is not None and annual_trades is not None:
            annual_expectancy = avg_r * annual_trades

            st.markdown("### 📊 Setup Stats")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"""
                <div class="mobile-metric">
                    <div class="mobile-metric-label">Win Rate</div>
                    <div class="mobile-metric-value" style="font-size: 24px;">{win_rate:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"""
                <div class="mobile-metric">
                    <div class="mobile-metric-label">Avg R</div>
                    <div class="mobile-metric-value" style="font-size: 24px;">+{avg_r:.2f}</div>
                </div>
                """, unsafe_allow_html=True)

            with col3:
                st.markdown(f"""
                <div class="mobile-metric">
                    <div class="mobile-metric-label">Frequency</div>
                    <div class="mobile-metric-value" style="font-size: 24px;">{annual_trades}</div>
                    <div class="mobile-metric-subtitle">trades/year</div>
                </div>
                """, unsafe_allow_html=True)

            # Annual expectancy display
            exp_color = "#10b981" if annual_expectancy > 0 else "#ef4444"
            st.markdown(f"""
            <div class="mobile-metric" style="margin-top: 12px;">
                <div class="mobile-metric-label">Annual Expectancy</div>
                <div class="mobile-metric-value" style="font-size: 28px; color: {exp_color};">+{annual_expectancy:.0f}R</div>
                <div class="mobile-metric-subtitle">per year</div>
            </div>
            """, unsafe_allow_html=True)

        # Trade Setup Details - Show for ALL actions
        if setup_name and orb_high and orb_low:
            st.markdown("### 📋 Trade Setup")

            # Extract ORB time from setup name (e.g., "2300 ORB HALF" -> "2300")
            orb_time = setup_name.split()[0] if setup_name else None

            # ORB Window timing
            if orb_time and orb_time.isdigit():
                hour = int(orb_time[:2])
                minute = int(orb_time[2:]) if len(orb_time) == 4 else 0

                # Format time display
                orb_start = dt.now(TZ_LOCAL).replace(hour=hour, minute=minute, second=0, microsecond=0)
                orb_end = orb_start + timedelta(minutes=5)
                time_display = f"{orb_start.strftime('%H:%M')} - {orb_end.strftime('%H:%M')}"

                st.markdown(f"""
                <div class="mobile-metric">
                    <div class="mobile-metric-label">ORB Window</div>
                    <div class="mobile-metric-value" style="font-size: 20px;">{time_display}</div>
                    <div class="mobile-metric-subtitle">{orb_time} ORB (5 minutes)</div>
                </div>
                """, unsafe_allow_html=True)

            # Entry Conditions
            if direction:
                if direction == "LONG":
                    entry_condition = f"First 1m close ABOVE ${orb_high:.2f}"
                    entry_trigger = f"Enter at market when 1m close > ${orb_high:.2f}"
                else:
                    entry_condition = f"First 1m close BELOW ${orb_low:.2f}"
                    entry_trigger = f"Enter at market when 1m close < ${orb_low:.2f}"

                st.markdown(f"""
                <div class="mobile-metric" style="background: rgba(99, 102, 241, 0.1); border-left: 4px solid #6366f1;">
                    <div class="mobile-metric-label">Entry Condition</div>
                    <div style="font-size: 14px; color: #f9fafb; font-weight: 600; margin-bottom: 4px;">{entry_condition}</div>
                    <div style="font-size: 13px; color: #9ca3af;">{entry_trigger}</div>
                </div>
                """, unsafe_allow_html=True)

        # Trade Levels - Show for ENTER or if we have calculated levels
        if entry_price and stop_price and target_price:
            st.markdown("### 📍 Trade Levels")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"""
                <div class="mobile-metric">
                    <div class="mobile-metric-label">Entry</div>
                    <div class="mobile-metric-value" style="font-size: 20px;">${entry_price:.2f}</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                # Show stop placement logic
                if orb_high and orb_low:
                    orb_mid = (orb_high + orb_low) / 2
                    if "HALF" in setup_name:
                        stop_logic = "ORB Midpoint"
                    elif "FULL" in setup_name:
                        stop_logic = "ORB Low" if direction == "LONG" else "ORB High"
                    else:
                        stop_logic = ""
                else:
                    stop_logic = ""

                st.markdown(f"""
                <div class="mobile-metric">
                    <div class="mobile-metric-label">Stop Loss</div>
                    <div class="mobile-metric-value" style="font-size: 20px; color: #ef4444;">${stop_price:.2f}</div>
                    <div class="mobile-metric-subtitle">{stop_logic}</div>
                </div>
                """, unsafe_allow_html=True)

            with col3:
                risk_points = abs(entry_price - stop_price)
                rr_display = f"{rr:.1f}R" if rr else ""
                st.markdown(f"""
                <div class="mobile-metric">
                    <div class="mobile-metric-label">Take Profit</div>
                    <div class="mobile-metric-value" style="font-size: 20px; color: #10b981;">${target_price:.2f}</div>
                    <div class="mobile-metric-subtitle">{rr_display}</div>
                </div>
                """, unsafe_allow_html=True)

            # Risk/Reward summary
            reward_points = abs(target_price - entry_price)
            st.markdown(f"""
            <div style="background: rgba(16, 185, 129, 0.1); border-radius: 8px; padding: 12px; margin-top: 12px;">
                <div style="font-size: 13px; color: #9ca3af; text-align: center;">
                    Risk: {risk_points:.2f} pts → Reward: {reward_points:.2f} pts
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ML Insights (if available) - only when we have evaluation
        from config import ML_ENABLED, ML_SHADOW_MODE
        if ML_ENABLED and ML_SHADOW_MODE and reasons:
            ml_reason = None
            for reason in reasons:
                if reason.startswith("ML:"):
                    ml_reason = reason
                    break

            if ml_reason:
                st.markdown("### 🤖 ML Insights")
                import re
                match = re.search(r'ML: (?:(HIGH|MEDIUM|LOW) confidence )?(\w+)(?: \((\d+)% confidence\))?', ml_reason)

                if match:
                    confidence_level = match.group(1) if match.group(1) else "UNKNOWN"
                    direction = match.group(2)
                    confidence_pct = match.group(3)

                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"""
                        <div class="mobile-metric">
                            <div class="mobile-metric-label">Direction</div>
                            <div class="mobile-metric-value" style="font-size: 24px;">{direction}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with col2:
                        conf_value = f"{confidence_pct}%" if confidence_pct else confidence_level
                        conf_emoji = "🟢" if confidence_level == "HIGH" else "🟡" if confidence_level == "MEDIUM" else "🔴"
                        st.markdown(f"""
                        <div class="mobile-metric">
                            <div class="mobile-metric-label">Confidence</div>
                            <div class="mobile-metric-value" style="font-size: 24px;">{conf_emoji} {conf_value}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.caption("⚠️ Shadow Mode: ML predictions shown for monitoring only")

    else:
        # No evaluation available (market closed, weekend, or error)
        st.markdown("### 🎯 Status")
        st.markdown(f"""
        <div class="mobile-status">
            <div class="mobile-status-header">STANDBY</div>
            <ul class="mobile-status-reasons">
                <li>• Market closed or no evaluation available</li>
                <li>• Historical data accessible for analysis</li>
                <li>• Use Trade Calculator for manual setups</li>
            </ul>
            <div class="mobile-status-action">
                Check back during market hours (09:00-02:00 AEST)
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Session Info (Basic - not full Market Intelligence)
    st.markdown("### 📊 Session & Time")
    try:
        # datetime and TZ_LOCAL already imported at module level

        # Determine current session based on hour (simple time-based)
        now = dt.now(TZ_LOCAL)
        hour = now.hour
        if 9 <= hour < 18:
            session = "ASIA"
        elif 18 <= hour < 23:
            session = "LONDON"
        else:
            session = "NY"

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="mobile-metric">
                <div class="mobile-metric-label">Session</div>
                <div class="mobile-metric-value" style="font-size: 20px;">{session}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="mobile-metric">
                <div class="mobile-metric-label">Local Time</div>
                <div class="mobile-metric-value" style="font-size: 20px;">{now.strftime('%H:%M')}</div>
            </div>
            """, unsafe_allow_html=True)

        st.caption("💡 Basic session info - Full Market Intelligence available in desktop app")
    except Exception as e:
        st.caption(f"Session info unavailable: {e}")

    # Safety Status
    st.markdown("### 🛡️ Safety Status")
    try:
        # Data quality
        is_data_safe = st.session_state.data_quality_monitor.is_safe_to_trade(current_symbol)[0] if hasattr(st.session_state, 'data_quality_monitor') else True
        # Market hours
        market_safe = st.session_state.market_hours_monitor.get_market_conditions(current_symbol).is_safe_to_trade() if hasattr(st.session_state, 'market_hours_monitor') else True
        # Risk limits
        risk_safe = st.session_state.risk_manager.is_trading_allowed()[0] if hasattr(st.session_state, 'risk_manager') else True

        all_safe = is_data_safe and market_safe and risk_safe
        status_color = "#10b981" if all_safe else "#ef4444"
        status_text = "✅ SAFE" if all_safe else "⚠️ BLOCKED"

        st.markdown(f"""
        <div class="mobile-metric">
            <div class="mobile-metric-value" style="font-size: 32px; color: {status_color};">{status_text}</div>
            <div class="mobile-metric-subtitle">
                Data: {'[OK]' if is_data_safe else '[X]'} |
                Market: {'[OK]' if market_safe else '[X]'} |
                Risk: {'[OK]' if risk_safe else '[X]'}
            </div>
        </div>
        """, unsafe_allow_html=True)
    except Exception as e:
        st.caption(f"Safety check unavailable: {e}")

    # Setup Scanner Results
    st.markdown("### 🔍 Active Setups")
    try:
        if hasattr(st.session_state, 'setup_scanner'):
            scanner = st.session_state.setup_scanner
            now = dt.now(TZ_LOCAL)
            setups = scanner.scan_for_setups(
                instrument=current_symbol,
                current_date=now,
                lookahead_hours=24
            )

            if setups:
                for setup in setups[:3]:  # Show top 3
                    orb_time = setup.get('orb_time', 'N/A')
                    entry_quality = setup.get('entry_quality', 'N/A')
                    st.info(f"**{orb_time} ORB** - Quality: {entry_quality}")
            else:
                st.caption("No high-quality setups in next 24h")
        else:
            st.caption("Setup scanner not available")
    except Exception as e:
        st.caption(f"Setup scanner unavailable: {e}")


# ============================================================================
# CARD 2: CHART (Collapsible)
# ============================================================================

def render_chart_card(data_loader, strategy_engine, latest_evaluation):
    """
    Chart Card - Collapsible chart with ORB levels

    Shows:
    - Expandable chart (hidden by default on mobile)
    - ORB high/low/size
    - Fullscreen option
    """

    st.markdown("## 📈 Chart & Levels")

    # Collapsible chart
    with st.expander("📊 Show Chart", expanded=False):
        try:
            # Get recent bars
            bars_df = data_loader.fetch_latest_bars(lookback_minutes=120)

            if bars_df.empty:
                st.warning("No bar data available")
            else:
                # Get ORB data
                state = latest_evaluation.state if latest_evaluation else None
                orb_high = state.current_orb_high if hasattr(state, 'current_orb_high') else None
                orb_low = state.current_orb_low if hasattr(state, 'current_orb_low') else None
                orb_name = state.active_orb_name if hasattr(state, 'active_orb_name') else "0900"

                # Get current price
                latest_bar = data_loader.get_latest_bar()
                current_price = latest_bar['close'] if latest_bar else None

                # Calculate ORB times
                if orb_name and latest_evaluation and hasattr(latest_evaluation, 'strategy_name') and latest_evaluation.strategy_name:
                    orb_hour = int(orb_name[:2])
                    orb_min = int(orb_name[2:]) if len(orb_name) == 4 else 0
                    now_local = datetime.now(TZ_LOCAL)
                    orb_start = now_local.replace(hour=orb_hour, minute=orb_min, second=0, microsecond=0)
                    orb_end = orb_start + timedelta(minutes=5)
                    if orb_hour == 0 and now_local.hour >= 12:
                        orb_start += timedelta(days=1)
                        orb_end += timedelta(days=1)
                else:
                    orb_start = None
                    orb_end = None

                # Get trade details if ENTER action
                entry_price = None
                stop_price = None
                target_price = None
                direction = None

                if latest_evaluation and hasattr(latest_evaluation, 'action') and latest_evaluation.action.value == "ENTER" and orb_high and orb_low:
                    if current_price and current_price > orb_high:
                        direction = "LONG"
                    elif current_price and current_price < orb_low:
                        direction = "SHORT"

                    if direction:
                        orb_config = strategy_engine.orb_configs.get(orb_name, {})
                        levels = calculate_trade_levels(
                            orb_high=orb_high,
                            orb_low=orb_low,
                            direction=direction,
                            rr=orb_config.get('rr', 1.0),
                            sl_mode=orb_config.get('sl_mode', 'FULL')
                        )
                        entry_price = levels['entry']
                        stop_price = levels['stop']
                        target_price = levels['target']

                # Check filter
                filter_passed = True
                tier = "B"
                if orb_high and orb_low and orb_name:
                    orb_config = strategy_engine.orb_configs.get(orb_name, {})
                    tier = orb_config.get('tier', 'B')
                    filter_result = data_loader.check_orb_size_filter(orb_high, orb_low, orb_name)
                    filter_passed = filter_result.get('pass', True)

                # Build enhanced chart with trade levels
                fig = build_live_trading_chart(
                    bars_df=bars_df,
                    orb_high=orb_high,
                    orb_low=orb_low,
                    orb_name=orb_name,
                    orb_start=orb_start,
                    orb_end=orb_end,
                    current_price=current_price,
                    filter_passed=filter_passed,
                    tier=tier,
                    entry_price=entry_price,
                    stop_price=stop_price,
                    target_price=target_price,
                    direction=direction,
                    height=350  # Mobile height
                )

                st.plotly_chart(fig, width='stretch')

        except Exception as e:
            st.error(f"Chart error: {e}")

    # ORB Metrics Summary
    if latest_evaluation and hasattr(latest_evaluation, 'state') and latest_evaluation.state:
        state = latest_evaluation.state
        orb_high = state.current_orb_high if hasattr(state, 'current_orb_high') else None
        orb_low = state.current_orb_low if hasattr(state, 'current_orb_low') else None

        if orb_high and orb_low:
            orb_size = orb_high - orb_low

            st.markdown("### ORB Levels")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"""
                <div class="mobile-metric">
                    <div class="mobile-metric-label">ORB High</div>
                    <div class="mobile-metric-value" style="font-size: 20px;">${orb_high:.2f}</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"""
                <div class="mobile-metric">
                    <div class="mobile-metric-label">ORB Low</div>
                    <div class="mobile-metric-value" style="font-size: 20px;">${orb_low:.2f}</div>
                </div>
                """, unsafe_allow_html=True)

            with col3:
                st.markdown(f"""
                <div class="mobile-metric">
                    <div class="mobile-metric-label">Size</div>
                    <div class="mobile-metric-value" style="font-size: 20px;">{orb_size:.2f}pts</div>
                </div>
                """, unsafe_allow_html=True)

            # Directional Bias (for 1100 ORB only)
            if orb_name == "1100":
                st.markdown("### 🎯 Directional Bias")
                try:
                    if hasattr(st.session_state, 'directional_bias_detector'):
                        bias = st.session_state.directional_bias_detector.get_directional_bias(
                            instrument="MGC",
                            orb_time="1100",
                            orb_high=orb_high,
                            orb_low=orb_low,
                            current_date=datetime.now()
                        )

                        if bias.has_bias():
                            direction = bias.preferred_direction
                            strength = bias.confidence
                            bias_color = "#10b981" if direction == "UP" else "#ef4444"

                            st.markdown(f"""
                            <div class="mobile-metric">
                                <div class="mobile-metric-label">Predicted Break</div>
                                <div class="mobile-metric-value" style="font-size: 24px; color: {bias_color};">
                                    {'🚀 ' if direction == 'UP' else '🔻 '}{direction}
                                </div>
                                <div class="mobile-metric-subtitle">Confidence: {strength:.0%}</div>
                            </div>
                            """, unsafe_allow_html=True)

                            st.info(f"💡 Consider focusing on {direction} breakout based on market structure")
                        else:
                            st.caption("No strong directional bias detected")
                    else:
                        st.caption("Directional bias detector not available")
                except Exception as e:
                    st.caption(f"Bias detection unavailable: {e}")


# ============================================================================
# CARD 3: TRADE ENTRY CALCULATOR
# ============================================================================

def render_trade_entry_card(data_loader, strategy_engine):
    """
    Trade Entry Calculator Card

    Shows:
    - Direction toggle (LONG/SHORT)
    - ORB high/low inputs
    - Calculated entry/stop/target
    - Position sizing
    """

    st.markdown("## 🎯 Trade Calculator")

    # Direction toggle
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 LONG", key="trade_long", width='stretch'):
            st.session_state.trade_direction = "LONG"

    with col2:
        if st.button("🔻 SHORT", key="trade_short", width='stretch'):
            st.session_state.trade_direction = "SHORT"

    # Get or initialize direction
    if 'trade_direction' not in st.session_state:
        st.session_state.trade_direction = "LONG"

    direction = st.session_state.trade_direction
    st.info(f"Selected: **{direction}**")

    # Input fields
    st.markdown("### ORB Levels")

    orb_high = st.number_input(
        "ORB High ($)",
        min_value=0.0,
        max_value=10000.0,
        value=2655.20,
        step=0.10,
        key="calc_orb_high"
    )

    orb_low = st.number_input(
        "ORB Low ($)",
        min_value=0.0,
        max_value=10000.0,
        value=2652.40,
        step=0.10,
        key="calc_orb_low"
    )

    # RR and SL mode
    col1, col2 = st.columns(2)
    with col1:
        rr = st.number_input("Risk/Reward (R)", min_value=1.0, max_value=10.0, value=4.0, step=0.5)
    with col2:
        sl_mode = st.selectbox("Stop Loss Mode", ["FULL", "HALF"])

    # Calculate button
    if st.button("📊 Calculate Trade", width='stretch', type="primary"):
        if orb_high > orb_low:
            levels = calculate_trade_levels(orb_high, orb_low, direction, rr, sl_mode)

            st.markdown("### 📍 Results")

            # Display results
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"""
                <div class="mobile-metric">
                    <div class="mobile-metric-label">Entry</div>
                    <div class="mobile-metric-value" style="font-size: 24px;">${levels['entry']:.2f}</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown(f"""
                <div class="mobile-metric">
                    <div class="mobile-metric-label">Stop</div>
                    <div class="mobile-metric-value" style="font-size: 24px; color: #ef4444;">${levels['stop']:.2f}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="mobile-metric">
                <div class="mobile-metric-label">Target ({rr:.1f}R)</div>
                <div class="mobile-metric-value" style="font-size: 28px; color: #10b981;">${levels['target']:.2f}</div>
                <div class="mobile-metric-subtitle">Risk: {levels['risk_points']:.2f}pts | Reward: {levels['reward_points']:.2f}pts</div>
            </div>
            """, unsafe_allow_html=True)

            # Position sizing
            account_size = st.session_state.get('account_size', 100000)
            risk_pct = 0.25
            risk_dollars = account_size * (risk_pct / 100)

            st.markdown(f"""
            <div class="mobile-metric">
                <div class="mobile-metric-label">Position Risk</div>
                <div class="mobile-metric-value" style="font-size: 24px;">${risk_dollars:.0f}</div>
                <div class="mobile-metric-subtitle">{risk_pct}% of ${account_size:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)

            # Copy levels button
            if st.button("📋 Copy Levels", width='stretch'):
                levels_text = f"Entry: ${levels['entry']:.2f} | Stop: ${levels['stop']:.2f} | Target: ${levels['target']:.2f}"
                st.code(levels_text)
                st.success("Copy the text above!")
        else:
            st.error("ORB High must be greater than ORB Low")


# ============================================================================
# CARD 4: POSITIONS
# ============================================================================

def render_positions_card(risk_manager, data_loader):
    """
    Active Positions Card

    Shows:
    - Active positions with P&L
    - Progress to target
    - Close position button
    - Empty state if no positions
    """

    st.markdown("## 📊 Active Positions")

    # Get active positions
    active_positions = risk_manager.get_active_positions() if risk_manager else []

    if active_positions:
        # Get current price
        latest_bar = data_loader.get_latest_bar() if data_loader else None
        current_price = latest_bar['close'] if latest_bar else 0

        for i, position in enumerate(active_positions):
            direction = "LONG" if position.get('direction') == 'LONG' else "SHORT"
            entry = position.get('entry_price', 0)
            stop = position.get('stop_price', 0)
            target = position.get('target_price', 0)

            # Calculate P&L
            if direction == "LONG":
                pnl_points = current_price - entry
            else:
                pnl_points = entry - current_price

            risk_points = abs(entry - stop)
            pnl_r = pnl_points / risk_points if risk_points > 0 else 0
            pnl_dollars = pnl_points * 10  # $10 per point for MGC

            # Calculate progress to target
            if direction == "LONG":
                progress = (current_price - entry) / (target - entry) * 100
            else:
                progress = (entry - current_price) / (entry - target) * 100

            progress = max(0, min(100, progress))

            # Position card
            pnl_color = "#10b981" if pnl_dollars >= 0 else "#ef4444"
            border_color = "#10b981" if direction == "LONG" else "#ef4444"

            st.markdown(f"""
            <div class="mobile-position" style="border-left-color: {border_color};">
                <div class="mobile-position-header">{'🚀' if direction == 'LONG' else '🔻'} {direction} MGC</div>
                <div style="font-size: 16px; color: #9ca3af;">Entry: ${entry:.2f}</div>
                <div style="font-size: 16px; color: #9ca3af;">Current: ${current_price:.2f} ({'+' if pnl_points >= 0 else ''}{pnl_points:.2f}pts)</div>
                <div class="mobile-position-pnl" style="color: {pnl_color};">
                    {'+' if pnl_dollars >= 0 else ''}${pnl_dollars:.0f} ({'+' if pnl_r >= 0 else ''}{pnl_r:.2f}R)
                </div>
                <div style="margin: 12px 0;">
                    <div style="font-size: 14px; color: #9ca3af; margin-bottom: 4px;">Stop: ${stop:.2f} | Target: ${target:.2f}</div>
                    <div class="mobile-position-progress">
                        <div class="mobile-position-progress-bar" style="width: {progress}%; background: {pnl_color};"></div>
                    </div>
                    <div style="text-align: center; font-size: 14px; color: #9ca3af;">Progress: {progress:.0f}%</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Close button
            if st.button(f"🚪 Close Position #{i+1}", key=f"close_pos_{i}", width='stretch', type="secondary"):
                st.warning("Position closed (simulated)")

    else:
        # Empty state
        st.markdown("""
        <div class="mobile-metric" style="padding: 40px;">
            <div style="font-size: 48px; margin-bottom: 12px;">📭</div>
            <div class="mobile-metric-label">No Positions Open</div>
            <div class="mobile-metric-subtitle" style="margin-top: 8px;">Wait for next setup</div>
        </div>
        """, unsafe_allow_html=True)


# ============================================================================
# CARD 5: CHART ANALYSIS (CSV Upload)
# ============================================================================

def render_chart_analysis_card(instrument="MGC"):
    """
    Chart Analysis Card - Upload and analyze TradingView charts

    Shows:
    - CSV file upload
    - Analysis results (ORBs, indicators, market structure)
    - Top 5 strategy recommendations
    - Setup quality and reasoning
    """

    st.markdown("## 📊 Chart Analysis")

    st.info("💡 Upload a TradingView CSV export to analyze potential setups")

    # Instructions
    with st.expander("📖 How to Export from TradingView", expanded=False):
        st.markdown("""
        **Export OHLCV data from TradingView:**

        1. Open your chart in TradingView
        2. Click the "..." menu on the chart
        3. Select "Export chart data..."
        4. Save the CSV file
        5. Upload it here

        **CSV Format Expected:**
        ```
        time,open,high,low,close,volume
        2024-01-15 09:00,2650.0,2652.0,2649.5,2651.5,1234
        ```

        **Timeframe:** Any timeframe works (1m, 5m, 1h, etc.)

        **Best Results:** At least 24 hours of data with ORB windows (0900, 1000, 1100, 1800, 2300, 0030)
        """)

    # File uploader
    uploaded_file = st.file_uploader(
        "Choose CSV file",
        type=['csv'],
        help="Upload TradingView chart export (CSV format)",
        key="chart_csv_upload"
    )

    if uploaded_file is not None:
        try:
            # Read CSV bytes
            csv_data = uploaded_file.read()

            with st.spinner("🔍 Analyzing chart..."):
                # Import analyzer
                from csv_chart_analyzer import analyze_csv_and_recommend

                # Analyze
                analysis, recommendations = analyze_csv_and_recommend(
                    csv_data=csv_data,
                    instrument=instrument,
                    top_n=5
                )

            if not analysis or not analysis.get("success"):
                st.error("❌ Failed to analyze CSV. Check format and try again.")
                return

            # Show analysis results
            st.success("✅ Analysis complete!")

            # Data Summary
            st.markdown("### 📈 Data Summary")
            data_summary = analysis.get("data_summary", {})

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""
                <div class="mobile-metric">
                    <div class="mobile-metric-label">Total Bars</div>
                    <div class="mobile-metric-value" style="font-size: 20px;">{data_summary.get('total_bars', 0)}</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                duration = data_summary.get('duration_hours', 0)
                st.markdown(f"""
                <div class="mobile-metric">
                    <div class="mobile-metric-label">Duration</div>
                    <div class="mobile-metric-value" style="font-size: 20px;">{duration:.1f}h</div>
                </div>
                """, unsafe_allow_html=True)

            with col3:
                price_range = data_summary.get('price_range', {}).get('range', 0)
                st.markdown(f"""
                <div class="mobile-metric">
                    <div class="mobile-metric-label">Range</div>
                    <div class="mobile-metric-value" style="font-size: 20px;">{price_range:.2f}</div>
                    <div class="mobile-metric-subtitle">points</div>
                </div>
                """, unsafe_allow_html=True)

            # Current State
            current_state = analysis.get("current_state", {})
            current_price = current_state.get("current_price", 0)

            st.markdown(f"""
            <div class="mobile-metric" style="margin-top: 12px;">
                <div class="mobile-metric-label">Current Price</div>
                <div class="mobile-metric-value" style="font-size: 28px;">${current_price:.2f}</div>
            </div>
            """, unsafe_allow_html=True)

            # ORB Analysis with States
            st.markdown("### 🎯 ORB Status")
            orb_analysis = analysis.get("orb_analysis", {})

            if orb_analysis:
                for orb_name, orb_data in orb_analysis.items():
                    orb_state = orb_data.get("state", "UNKNOWN")

                    # State-based display
                    if orb_state == "PENDING":
                        # Future ORB - show as upcoming
                        note = orb_data.get("note", "")

                        # Get setup config for this ORB
                        setup_config = get_setup_config(instrument, orb_name)

                        upcoming_info = ""
                        if setup_config:
                            rr = setup_config['rr']
                            sl_mode = setup_config['sl_mode']
                            tier = setup_config['tier']

                            upcoming_info = f"""
                            <div style="font-size: 11px; color: #6b7280; margin-top: 6px;">
                                Setup ready: {tier} tier, {rr:.1f}R target, {sl_mode} stop
                            </div>
                            """

                        st.markdown(f"""
                        <div class="mobile-metric" style="border-left: 4px solid #6b7280; margin-bottom: 8px; opacity: 0.7;">
                            <div style="font-size: 12px; font-weight: 700; color: #9ca3af; text-transform: uppercase;">
                                ⏰ UPCOMING
                            </div>
                            <div class="mobile-metric-label" style="margin-top: 4px;">{orb_name} ORB</div>
                            <div style="font-size: 12px; color: #9ca3af; margin-top: 4px;">
                                {note}
                            </div>
                            {upcoming_info}
                        </div>
                        """, unsafe_allow_html=True)

                    elif orb_state == "FORMING":
                        # ORB forming now
                        note = orb_data.get("note", "")

                        # Get setup config
                        setup_config = get_setup_config(instrument, orb_name)

                        forming_info = ""
                        if setup_config:
                            rr = setup_config['rr']
                            sl_mode = setup_config['sl_mode']
                            tier = setup_config['tier']

                            forming_info = f"""
                            <div style="font-size: 11px; color: #9ca3af; margin-top: 6px; background: rgba(0,0,0,0.3); padding: 6px; border-radius: 4px;">
                                When formed: {tier} tier, {rr:.1f}R target, {sl_mode} stop
                            </div>
                            """

                        st.markdown(f"""
                        <div class="mobile-metric" style="border-left: 4px solid #f59e0b; margin-bottom: 8px;">
                            <div style="font-size: 13px; font-weight: 800; color: #f59e0b; text-transform: uppercase;">
                                ⏳ FORMING NOW
                            </div>
                            <div class="mobile-metric-label" style="margin-top: 4px;">{orb_name} ORB</div>
                            <div style="font-size: 12px; color: #f9fafb; font-weight: 600; margin-top: 6px;">
                                Don't enter yet. Wait for 5-minute window to complete.
                            </div>
                            <div style="font-size: 12px; color: #9ca3af; margin-top: 4px;">
                                {note}
                            </div>
                            {forming_info}
                        </div>
                        """, unsafe_allow_html=True)

                    elif orb_state == "ACTIVE":
                        # ORB formed, waiting for break
                        orb_high = orb_data.get("high", 0)
                        orb_low = orb_data.get("low", 0)
                        orb_size = orb_data.get("size", 0)
                        current_pos = orb_data.get("current_price_position", "INSIDE")
                        potential_direction = orb_data.get("potential_direction", "WAIT")

                        # Determine clear action status
                        if current_pos == "INSIDE":
                            action_status = "⏳ WAIT FOR BREAKOUT"
                            action_color = "#f59e0b"
                            action_instruction = "Don't enter yet. Wait for FIRST 1m close outside ORB range."
                        elif current_pos == "ABOVE":
                            action_status = "🚀 READY TO TRADE LONG"
                            action_color = "#10b981"
                            action_instruction = "Price broke above ORB. Enter LONG if not already in."
                        elif current_pos == "BELOW":
                            action_status = "🔻 READY TO TRADE SHORT"
                            action_color = "#ef4444"
                            action_instruction = "Price broke below ORB. Enter SHORT if not already in."
                        else:
                            action_status = "⏸️ STANDBY"
                            action_color = "#6b7280"
                            action_instruction = "Monitor price action."

                        # Get setup config from validated_setups
                        setup_config = get_setup_config(instrument, orb_name)

                        # Calculate trade levels
                        trade_plan_html = ""
                        if orb_high and orb_low and setup_config and potential_direction != "WAIT":
                            rr = setup_config['rr']
                            sl_mode = setup_config['sl_mode']
                            tier = setup_config['tier']

                            # Direction indicators
                            if potential_direction == "LONG":
                                direction_emoji = "🚀"
                                direction_color = "#10b981"
                            elif potential_direction == "SHORT":
                                direction_emoji = "🔻"
                                direction_color = "#ef4444"
                            else:
                                direction_emoji = "↔️"
                                direction_color = "#6366f1"

                            # Calculate levels for the recommended direction
                            if potential_direction in ["LONG", "SHORT"]:
                                levels = calculate_trade_levels(orb_high, orb_low, potential_direction, rr, sl_mode)

                                # Stop logic description
                                if sl_mode == "HALF":
                                    stop_logic = "ORB Mid"
                                else:
                                    stop_logic = "ORB Low" if potential_direction == "LONG" else "ORB High"

                                # Clear trade instructions
                                if current_pos == "INSIDE":
                                    when_to_enter = f"WAIT for 1m candle to close {'ABOVE' if potential_direction == 'LONG' else 'BELOW'} ${orb_high if potential_direction == 'LONG' else orb_low:.2f}"
                                else:
                                    when_to_enter = "ENTER NOW (breakout confirmed)"

                                trade_plan_html = f"""
                                <div style="background: rgba(99, 102, 241, 0.08); border-radius: 8px; padding: 10px; margin-top: 8px;">
                                    <div style="font-size: 13px; font-weight: 800; color: {action_color}; margin-bottom: 8px; text-transform: uppercase;">
                                        {action_status}
                                    </div>
                                    <div style="font-size: 12px; color: #f9fafb; margin-bottom: 8px; font-weight: 600;">
                                        {action_instruction}
                                    </div>
                                    <div style="font-size: 11px; color: #9ca3af; line-height: 1.8; background: rgba(0,0,0,0.3); padding: 8px; border-radius: 6px;">
                                        <div style="color: #6366f1; font-weight: 700; margin-bottom: 4px;">📋 TRADE PLAN ({potential_direction}):</div>
                                        <strong>When:</strong> {when_to_enter}<br>
                                        <strong>Entry:</strong> ${levels['entry']:.2f}<br>
                                        <strong>Stop:</strong> ${levels['stop']:.2f} ({stop_logic})<br>
                                        <strong>Target:</strong> ${levels['target']:.2f} ({rr:.1f}R)<br>
                                        <strong>Risk:</strong> {levels['risk_points']:.2f} pts → <strong>Reward:</strong> {levels['reward_points']:.2f} pts
                                    </div>
                                </div>
                                """

                        st.markdown(f"""
                        <div class="mobile-metric" style="border-left: 4px solid {action_color}; margin-bottom: 8px;">
                            <div class="mobile-metric-label">{orb_name} ORB</div>
                            <div style="font-size: 14px; color: #9ca3af; margin-top: 4px;">
                                Range: ${orb_low:.2f} - ${orb_high:.2f} ({orb_size:.2f} pts)
                            </div>
                            {trade_plan_html}
                        </div>
                        """, unsafe_allow_html=True)

                    elif orb_state in ["BROKEN_UP", "BROKEN_DOWN"]:
                        # ORB broken - LOCKED
                        orb_high = orb_data.get("high", 0)
                        orb_low = orb_data.get("low", 0)
                        orb_size = orb_data.get("size", 0)
                        direction = "LONG" if orb_state == "BROKEN_UP" else "SHORT"
                        break_time = orb_data.get("break_time")
                        break_price = orb_data.get("break_price", 0)
                        locked = orb_data.get("locked", False)

                        # Color based on direction
                        if orb_state == "BROKEN_UP":
                            state_color = "#10b981"
                            state_emoji = "🚀"
                            action_status = "✅ TRADE IN PROGRESS (LONG)"
                        else:
                            state_color = "#ef4444"
                            state_emoji = "🔻"
                            action_status = "✅ TRADE IN PROGRESS (SHORT)"

                        lock_icon = "🔒" if locked else ""

                        break_time_str = ""
                        if break_time:
                            if hasattr(break_time, 'strftime'):
                                break_time_str = break_time.strftime('%H:%M')
                            else:
                                break_time_str = str(break_time)

                        # Get setup config and calculate trade levels
                        setup_config = get_setup_config(instrument, orb_name)
                        trade_plan_html = ""

                        if orb_high and orb_low and setup_config:
                            rr = setup_config['rr']
                            sl_mode = setup_config['sl_mode']
                            tier = setup_config['tier']

                            levels = calculate_trade_levels(orb_high, orb_low, direction, rr, sl_mode)

                            # Stop logic description
                            if sl_mode == "HALF":
                                stop_logic = "ORB Mid"
                            else:
                                stop_logic = "ORB Low" if direction == "LONG" else "ORB High"

                            trade_plan_html = f"""
                            <div style="background: rgba({'16, 185, 129' if orb_state == 'BROKEN_UP' else '239, 68, 68'}, 0.08); border-radius: 8px; padding: 10px; margin-top: 8px;">
                                <div style="font-size: 13px; font-weight: 800; color: {state_color}; margin-bottom: 8px; text-transform: uppercase;">
                                    {action_status}
                                </div>
                                <div style="font-size: 12px; color: #f9fafb; margin-bottom: 8px; font-weight: 600;">
                                    Breakout happened at {break_time_str}. If you entered, hold to target.
                                </div>
                                <div style="font-size: 11px; color: #9ca3af; line-height: 1.8; background: rgba(0,0,0,0.3); padding: 8px; border-radius: 6px;">
                                    <div style="color: {state_color}; font-weight: 700; margin-bottom: 4px;">📋 TRADE LEVELS:</div>
                                    <strong>Entry:</strong> ${levels['entry']:.2f} (breakout price)<br>
                                    <strong>Stop:</strong> ${levels['stop']:.2f} ({stop_logic})<br>
                                    <strong>Target:</strong> ${levels['target']:.2f} ({rr:.1f}R)<br>
                                    <strong>Risk:</strong> {levels['risk_points']:.2f} pts → <strong>Reward:</strong> {levels['reward_points']:.2f} pts
                                </div>
                            </div>
                            """

                        st.markdown(f"""
                        <div class="mobile-metric" style="border-left: 4px solid {state_color}; margin-bottom: 8px; background: rgba({'16, 185, 129' if orb_state == 'BROKEN_UP' else '239, 68, 68'}, 0.05);">
                            <div class="mobile-metric-label">{orb_name} ORB {state_emoji}</div>
                            <div style="font-size: 14px; color: #9ca3af; margin-top: 4px;">
                                Range: ${orb_low:.2f} - ${orb_high:.2f} ({orb_size:.2f} pts)
                            </div>
                            {trade_plan_html}
                        </div>
                        """, unsafe_allow_html=True)

                    elif orb_state == "NOT_DETECTED":
                        # No data for this ORB
                        pass  # Skip display

            else:
                st.caption("No ORB data available")

            # Indicators
            indicators = analysis.get("indicators", {})
            if indicators:
                st.markdown("### 📐 Indicators")

                col1, col2, col3 = st.columns(3)

                with col1:
                    atr_20 = indicators.get("atr_20")
                    if atr_20:
                        st.markdown(f"""
                        <div class="mobile-metric">
                            <div class="mobile-metric-label">ATR (20)</div>
                            <div class="mobile-metric-value" style="font-size: 18px;">{atr_20:.2f}</div>
                        </div>
                        """, unsafe_allow_html=True)

                with col2:
                    rsi_14 = indicators.get("rsi_14")
                    if rsi_14:
                        rsi_color = "#10b981" if 40 <= rsi_14 <= 60 else "#ef4444" if rsi_14 > 70 or rsi_14 < 30 else "#9ca3af"
                        st.markdown(f"""
                        <div class="mobile-metric">
                            <div class="mobile-metric-label">RSI (14)</div>
                            <div class="mobile-metric-value" style="font-size: 18px; color: {rsi_color};">{rsi_14:.1f}</div>
                        </div>
                        """, unsafe_allow_html=True)

                with col3:
                    volatility = indicators.get("recent_volatility")
                    if volatility:
                        st.markdown(f"""
                        <div class="mobile-metric">
                            <div class="mobile-metric-label">Volatility</div>
                            <div class="mobile-metric-value" style="font-size: 18px;">{volatility:.2f}</div>
                        </div>
                        """, unsafe_allow_html=True)

            # Market Structure
            structure = analysis.get("market_structure", {})
            if structure:
                st.markdown("### 🏗️ Market Structure")

                trend = structure.get("trend", "UNKNOWN")
                trend_colors = {
                    "TRENDING_UP": "#10b981",
                    "TRENDING_DOWN": "#ef4444",
                    "RANGING": "#9ca3af"
                }
                trend_color = trend_colors.get(trend, "#9ca3af")

                st.markdown(f"""
                <div class="mobile-metric">
                    <div class="mobile-metric-label">Trend</div>
                    <div class="mobile-metric-value" style="font-size: 20px; color: {trend_color};">{trend.replace('_', ' ')}</div>
                </div>
                """, unsafe_allow_html=True)

            # AI Market Analysis
            st.markdown("### 🤖 AI Market Analysis")

            # Generate AI analysis based on data
            analysis_points = []

            # Trend analysis
            if structure:
                trend = structure.get("trend", "UNKNOWN")
                if trend == "TRENDING_UP":
                    analysis_points.append("📈 Market is **trending upward** - favor LONG setups on pullbacks or breakouts")
                elif trend == "TRENDING_DOWN":
                    analysis_points.append("📉 Market is **trending downward** - favor SHORT setups on rallies or breakdowns")
                else:
                    analysis_points.append("↔️ Market is **ranging** - look for breakouts from ORB levels")

            # ORB analysis - filter for detected ORBs only (exclude PENDING, NOT_DETECTED)
            detected_orbs = {
                name: data for name, data in orb_analysis.items()
                if data.get("state") not in ["PENDING", "NOT_DETECTED"]
            } if orb_analysis else {}

            detected_count = len(detected_orbs)
            if detected_count > 0:
                above_count = sum(1 for orb in detected_orbs.values() if orb.get("price_position") == "ABOVE")
                below_count = sum(1 for orb in detected_orbs.values() if orb.get("price_position") == "BELOW")

                if above_count > below_count:
                    analysis_points.append(f"🚀 Price is **above {above_count} ORB(s)** - bullish breakout momentum")
                elif below_count > above_count:
                    analysis_points.append(f"🔻 Price is **below {below_count} ORB(s)** - bearish breakdown momentum")
                else:
                    analysis_points.append(f"⏳ Price is **inside ORB range** - wait for breakout confirmation")

            # Volatility analysis
            if indicators:
                atr_20 = indicators.get("atr_20")
                if atr_20:
                    if atr_20 > 20:
                        analysis_points.append(f"⚡ **High volatility** (ATR: {atr_20:.1f}) - larger stops needed, bigger profit potential")
                    elif atr_20 < 10:
                        analysis_points.append(f"😴 **Low volatility** (ATR: {atr_20:.1f}) - tighter stops okay, smaller targets expected")
                    else:
                        analysis_points.append(f"✅ **Normal volatility** (ATR: {atr_20:.1f}) - standard position sizing applies")

                rsi_14 = indicators.get("rsi_14")
                if rsi_14:
                    if rsi_14 > 70:
                        analysis_points.append(f"⚠️ RSI **overbought** ({rsi_14:.1f}) - consider taking profits or waiting for pullback")
                    elif rsi_14 < 30:
                        analysis_points.append(f"⚠️ RSI **oversold** ({rsi_14:.1f}) - consider buying dips or waiting for bounce")

            # Display analysis
            if analysis_points:
                for point in analysis_points:
                    st.markdown(f"- {point}")
            else:
                st.caption("Insufficient data for market analysis")

            st.markdown("---")

            # Strategy Recommendations
            st.markdown("### 🏆 Top 5 Recommended Strategies")

            if recommendations:
                for i, rec in enumerate(recommendations, 1):
                    setup = rec.get("setup", {})
                    score = rec.get("score", 0)
                    reasoning = rec.get("reasoning", "")

                    # Setup details
                    setup_name = setup.get("setup_name", "Unknown")
                    tier = setup.get("tier", "C")
                    win_rate = setup.get("win_rate", 0)
                    avg_r = setup.get("avg_r", 0)
                    annual_trades = setup.get("annual_trades", 0)

                    # Tier badge color
                    tier_colors = {
                        "S+": "#ffd700",
                        "S": "#c0c0c0",
                        "A": "#cd7f32",
                        "B": "#9ca3af",
                        "C": "#6b7280"
                    }
                    tier_color = tier_colors.get(tier, "#9ca3af")

                    # Score color (gradient from red to green)
                    if score >= 70:
                        score_color = "#10b981"
                    elif score >= 50:
                        score_color = "#fbbf24"
                    else:
                        score_color = "#9ca3af"

                    # Get trade details from setup
                    orb_time = setup.get("orb_time", "")
                    sl_mode = setup.get("sl_mode", "HALF")
                    rr = setup.get("rr", 1.0)

                    # Get ORB data from analysis
                    orb_data = orb_analysis.get(orb_time, {}) if orb_time else {}
                    orb_state = orb_data.get("state", "UNKNOWN")
                    orb_high = orb_data.get("high")
                    orb_low = orb_data.get("low")
                    orb_direction = orb_data.get("potential_direction", "WAIT")
                    current_pos = orb_data.get("current_price_position", "UNKNOWN")

                    # Determine clear action status
                    if orb_state == "PENDING":
                        action_status = "⏰ UPCOMING"
                        action_color = "#6b7280"
                        action_instruction = "Not time yet. This ORB window hasn't opened."
                    elif orb_state == "FORMING":
                        action_status = "⏳ FORMING NOW"
                        action_color = "#f59e0b"
                        action_instruction = "ORB is building right now. Wait for 5-minute window to complete."
                    elif orb_state == "ACTIVE":
                        if current_pos == "INSIDE":
                            action_status = "⏳ WAIT FOR BREAKOUT"
                            action_color = "#f59e0b"
                            action_instruction = "ORB formed. Price is inside range. Wait for breakout."
                        elif current_pos == "ABOVE":
                            action_status = "🚀 READY TO TRADE LONG"
                            action_color = "#10b981"
                            action_instruction = "Price broke above! Enter LONG if not already in."
                        elif current_pos == "BELOW":
                            action_status = "🔻 READY TO TRADE SHORT"
                            action_color = "#ef4444"
                            action_instruction = "Price broke below! Enter SHORT if not already in."
                        else:
                            action_status = "⏸️ STANDBY"
                            action_color = "#6b7280"
                            action_instruction = "Monitor price action."
                    elif orb_state in ["BROKEN_UP", "BROKEN_DOWN"]:
                        action_status = "✅ TRADE IN PROGRESS"
                        action_color = "#10b981" if orb_state == "BROKEN_UP" else "#ef4444"
                        action_instruction = "Breakout already happened. If you entered, hold to target."
                    else:
                        action_status = "⏸️ NO DATA"
                        action_color = "#6b7280"
                        action_instruction = "ORB data not available for this time."

                    # Calculate trade levels if ORB detected
                    trade_levels_html = ""
                    if orb_high and orb_low and orb_direction in ["LONG", "SHORT"]:
                        # Entry
                        entry = orb_high if orb_direction == "LONG" else orb_low

                        # Stop loss
                        orb_mid = (orb_high + orb_low) / 2
                        if sl_mode == "HALF":
                            stop = orb_mid
                            stop_logic = "ORB Mid"
                        else:
                            stop = orb_low if orb_direction == "LONG" else orb_high
                            stop_logic = "ORB Low" if orb_direction == "LONG" else "ORB High"

                        # Target
                        risk = abs(entry - stop)
                        target = entry + (risk * rr) if orb_direction == "LONG" else entry - (risk * rr)

                        # ORB timing
                        if orb_time and orb_time.isdigit():
                            hour = int(orb_time[:2])
                            minute = int(orb_time[2:]) if len(orb_time) == 4 else 0
                            time_str = f"{hour:02d}:{minute:02d}-{hour:02d}:{minute+5:02d}"
                        else:
                            time_str = "N/A"

                        # When to enter
                        if orb_state == "PENDING":
                            when_to_enter = f"WAIT - Window opens at {time_str}"
                        elif orb_state == "FORMING":
                            when_to_enter = "WAIT - ORB forming (don't enter yet)"
                        elif current_pos == "INSIDE":
                            when_to_enter = f"WAIT for 1m close {'ABOVE' if orb_direction == 'LONG' else 'BELOW'} ${entry:.2f}"
                        elif current_pos in ["ABOVE", "BELOW"]:
                            when_to_enter = "ENTER NOW (breakout confirmed)"
                        elif orb_state in ["BROKEN_UP", "BROKEN_DOWN"]:
                            when_to_enter = "ALREADY HAPPENED (hold if in trade)"
                        else:
                            when_to_enter = "Monitor price action"

                        trade_levels_html = f"""
                        <div style="background: rgba(99, 102, 241, 0.08); border-radius: 8px; padding: 10px; margin-top: 8px;">
                            <div style="font-size: 13px; font-weight: 800; color: {action_color}; margin-bottom: 8px; text-transform: uppercase;">
                                {action_status}
                            </div>
                            <div style="font-size: 12px; color: #f9fafb; margin-bottom: 8px; font-weight: 600;">
                                {action_instruction}
                            </div>
                            <div style="font-size: 11px; color: #9ca3af; line-height: 1.8; background: rgba(0,0,0,0.3); padding: 8px; border-radius: 6px;">
                                <div style="color: #6366f1; font-weight: 700; margin-bottom: 4px;">📋 TRADE PLAN ({'🚀 LONG' if orb_direction == 'LONG' else '🔻 SHORT'}):</div>
                                <strong>Time:</strong> {time_str}<br>
                                <strong>When:</strong> {when_to_enter}<br>
                                <strong>Entry:</strong> ${entry:.2f}<br>
                                <strong>Stop:</strong> ${stop:.2f} ({stop_logic})<br>
                                <strong>Target:</strong> ${target:.2f} ({rr:.1f}R)<br>
                                <strong>Risk:</strong> {risk:.2f} pts → <strong>Reward:</strong> {risk * rr:.2f} pts
                            </div>
                        </div>
                        """

                    # Render header and score
                    st.markdown(f"""
                    <div class="mobile-metric" style="border-left: 4px solid {tier_color}; margin-bottom: 8px; padding-bottom: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <div style="font-size: 18px; font-weight: 700;">#{i} {setup_name}</div>
                            <span style="background: {tier_color}; color: #000; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 700;">{tier}</span>
                        </div>
                        <div style="font-size: 14px; color: #9ca3af; margin-bottom: 8px;">
                            Score: <span style="color: {score_color}; font-weight: 700;">{score:.0f}/100</span>
                        </div>
                        <div style="font-size: 13px; color: #9ca3af; line-height: 1.4; margin-bottom: 8px;">
                            {reasoning}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Render trade plan separately to avoid HTML escaping
                    if trade_levels_html:
                        st.markdown(trade_levels_html, unsafe_allow_html=True)

                    # Render stats
                    st.markdown(f"""
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-top: 12px; margin-bottom: 16px;">
                        <div style="text-align: center;">
                            <div style="font-size: 10px; color: #6b7280; text-transform: uppercase;">Win Rate</div>
                            <div style="font-size: 16px; font-weight: 700; color: #f9fafb;">{win_rate:.1f}%</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 10px; color: #6b7280; text-transform: uppercase;">Avg R</div>
                            <div style="font-size: 16px; font-weight: 700; color: #f9fafb;">+{avg_r:.2f}</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="font-size: 10px; color: #6b7280; text-transform: uppercase;">Trades/Yr</div>
                            <div style="font-size: 16px; font-weight: 700; color: #f9fafb;">{annual_trades}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("No recommendations available")

            # Help text
            st.markdown("---")
            st.caption("💡 **Tip:** Higher scores indicate better setup match for current conditions. S+ and S tier setups are most profitable.")

        except Exception as e:
            st.error(f"❌ Error analyzing chart: {e}")
            import traceback
            st.code(traceback.format_exc())


# ============================================================================
# CARD 6: AI CHAT
# ============================================================================

def render_ai_chat_card(ai_assistant, chat_history, current_symbol, data_loader, compact=False):
    """
    AI Chat Assistant Card

    Args:
        compact (bool): If True, show compact version with last 3 messages only

    Shows:
    - Chat history (scrollable)
    - Input field
    - Quick action buttons
    - Compact message bubbles
    """

    if not compact:
        st.markdown("## 🤖 AI Assistant")

    # Check if AI is available
    if not ai_assistant or not ai_assistant.is_available():
        st.error("⚠️ AI Assistant not available. Add ANTHROPIC_API_KEY to .env file.")
        st.info("Get your API key from: https://console.anthropic.com/")
        return

    if not compact:
        st.success("✅ Claude Sonnet 4.5 ready!")

    # Chat history
    message_limit = 3 if compact else 10

    chat_container = st.container()
    with chat_container:
        if not chat_history:
            st.info("💡 Ask about strategies, risk, or setups")
        else:
            for msg in chat_history[-message_limit:]:  # Show last N messages
                if msg["role"] == "user":
                    st.markdown(f"**You:** {msg['content']}")
                else:
                    st.markdown(f"**AI:** {msg['content']}")
                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # Input (minimum 68px for Streamlit)
    input_height = 70 if compact else 100

    user_input = st.text_area(
        "Your question:",
        key=f"ai_chat_input_mobile_{'compact' if compact else 'full'}",
        placeholder="Ask me anything..." if compact else "Example: ORB is 2700-2706, I want to go LONG, what's my stop and target?",
        height=input_height,
        label_visibility="collapsed" if compact else "visible"
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        if st.button("📤 Send", type="primary", width='stretch'):
            if user_input.strip():
                with st.spinner("Thinking..."):
                    # Get current price
                    current_price = 0
                    if data_loader:
                        latest = data_loader.get_latest_bar()
                        if latest:
                            current_price = latest.get('close', 0)

                    # Call AI
                    response = ai_assistant.chat(
                        user_message=user_input,
                        conversation_history=chat_history,
                        session_id=st.session_state.session_id,
                        instrument=current_symbol,
                        current_price=current_price,
                        strategy_state=None,
                        session_levels={},
                        orb_data={},
                        backtest_stats={}
                    )

                    # Update history
                    chat_history.append({"role": "user", "content": user_input})
                    chat_history.append({"role": "assistant", "content": response})

                st.rerun()

    with col2:
        if st.button("🗑️ Clear", width='stretch'):
            chat_history.clear()
            st.rerun()

    # Quick actions (only in full mode)
    if not compact:
        st.markdown("### 💡 Quick Actions")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("📊 Calculate Trade", key="quick_calc", width='stretch'):
                chat_history.append({"role": "user", "content": "How do I calculate my stop and target for an ORB trade?"})
                st.rerun()

        with col2:
            if st.button("❓ Why Good?", key="quick_why", width='stretch'):
                chat_history.append({"role": "user", "content": "Why is the current setup a good trade?"})
                st.rerun()
