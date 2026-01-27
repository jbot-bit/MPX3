"""
TERMINAL COMPONENTS - Professional Trading UI Elements

Reusable components with professional trading terminal aesthetic.
Each component follows the Matrix-inspired, Bloomberg-style design system.
"""

import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any


def render_terminal_header(title: str, subtitle: str = ""):
    """Render professional terminal header with glowing title"""
    st.markdown(f"""
    <div class="terminal-header">
        <h1 class="terminal-title">{title}</h1>
        {f'<div class="terminal-subtitle">{subtitle}</div>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)


def render_metric_card(
    label: str,
    value: str,
    change: Optional[str] = None,
    sentiment: str = "neutral"  # "positive", "negative", "neutral"
):
    """
    Render terminal-style metric card with optional change indicator

    Args:
        label: Metric label (e.g., "DAILY P&L")
        value: Main value to display (e.g., "+2.5R")
        change: Optional change indicator (e.g., "+15%", "↑ 0.3R")
        sentiment: "positive", "negative", or "neutral"
    """
    change_html = f'<div class="metric-change">{change}</div>' if change else ''

    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value {sentiment}">{value}</div>
        {change_html}
    </div>
    """, unsafe_allow_html=True)


def render_status_indicator(
    status: str,
    color: str = "green",  # "green", "red", "yellow", "blue"
    label: Optional[str] = None
):
    """
    Render status indicator with pulsing dot

    Args:
        status: Status text (e.g., "TRADE", "NO TRADE", "MONITOR")
        color: "green", "red", "yellow", or "blue"
        label: Optional label to show before status
    """
    label_html = f'<span style="color: var(--text-tertiary); margin-right: 8px;">{label}</span>' if label else ''

    st.markdown(f"""
    <div class="status-indicator {color}">
        <div class="status-dot"></div>
        {label_html}<span class="status-text">{status}</span>
    </div>
    """, unsafe_allow_html=True)


def render_price_display(
    price: float,
    direction: str = "neutral",  # "up", "down", "neutral"
    symbol: str = "$"
):
    """
    Render large price display with animation

    Args:
        price: Price value
        direction: "up" for green, "down" for red, "neutral" for default
        symbol: Currency/prefix symbol
    """
    formatted_price = f"{price:,.2f}"

    st.markdown(f"""
    <div class="price-display {direction}">
        {symbol}{formatted_price}
    </div>
    """, unsafe_allow_html=True)


def render_terminal_panel(
    content: str,
    title: Optional[str] = None,
    data_title: Optional[str] = None
):
    """
    Render terminal-style panel with optional title bar

    Args:
        content: HTML content to display
        title: Optional title to show in panel
        data_title: Optional data-title attribute for CSS ::before styling
    """
    data_attr = f'data-title="{data_title}"' if data_title else ''
    title_html = f'<div style="margin-bottom: 16px; font-family: var(--font-mono); color: var(--green-dark); text-transform: uppercase; letter-spacing: 1px; font-size: 12px;">{title}</div>' if title else ''

    st.markdown(f"""
    <div class="terminal-panel" {data_attr}>
        {title_html}
        {content}
    </div>
    """, unsafe_allow_html=True)


def render_countdown_timer(seconds_remaining: int, urgent_threshold: int = 60):
    """
    Render countdown timer with urgent animation when time is low

    Args:
        seconds_remaining: Seconds until event
        urgent_threshold: Seconds at which timer becomes urgent (default 60)
    """
    minutes = seconds_remaining // 60
    seconds = seconds_remaining % 60

    urgent_class = "urgent" if seconds_remaining <= urgent_threshold else ""

    st.markdown(f"""
    <div class="countdown-timer {urgent_class}">
        {minutes:02d}:{seconds:02d}
    </div>
    """, unsafe_allow_html=True)


def render_data_grid(
    df,
    highlight_column: Optional[str] = None,
    color_column: Optional[str] = None
):
    """
    Render data as terminal-style grid with optional highlighting

    Args:
        df: DataFrame to display
        highlight_column: Column name to highlight
        color_column: Column name to apply color coding (positive/negative)
    """
    # Apply styling if requested
    if color_column and color_column in df.columns:
        def color_values(val):
            try:
                num_val = float(val)
                if num_val > 0:
                    return 'color: var(--profit-green); font-weight: 600;'
                elif num_val < 0:
                    return 'color: var(--loss-red); font-weight: 600;'
            except:
                pass
            return ''

        styled_df = df.style.applymap(color_values, subset=[color_column])
        st.dataframe(styled_df, use_container_width=True)
    else:
        st.dataframe(df, use_container_width=True)


def render_alert_message(
    message: str,
    alert_type: str = "info",  # "info", "success", "warning", "error"
    slide_in: bool = True
):
    """
    Render alert message with optional slide-in animation

    Args:
        message: Alert message text
        alert_type: "info", "success", "warning", or "error"
        slide_in: Whether to animate slide-in
    """
    color_map = {
        "info": "var(--neutral-blue)",
        "success": "var(--profit-green)",
        "warning": "var(--warning-amber)",
        "error": "var(--loss-red)"
    }

    color = color_map.get(alert_type, "var(--neutral-blue)")
    slide_class = "alert-slide" if slide_in else ""

    st.markdown(f"""
    <div class="{slide_class}" style="
        background: var(--bg-panel);
        border-left: 4px solid {color};
        padding: 16px;
        margin: 16px 0;
        font-family: var(--font-mono);
        color: var(--text-primary);
        box-shadow: 0 0 20px rgba(0, 255, 65, 0.1);
    ">
        {message}
    </div>
    """, unsafe_allow_html=True)


def render_trade_button(
    label: str,
    button_type: str = "primary",  # "primary", "danger", "secondary"
    key: Optional[str] = None,
    disabled: bool = False
):
    """
    Render terminal-style trade action button

    Args:
        label: Button label
        button_type: "primary" (green), "danger" (red), or "secondary" (neutral)
        key: Streamlit button key
        disabled: Whether button is disabled

    Returns:
        bool: True if button was clicked
    """
    # Wrap button in styled container
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if button_type == "primary":
            st.markdown('<div class="stButton primary">', unsafe_allow_html=True)
        elif button_type == "danger":
            st.markdown('<div class="stButton danger">', unsafe_allow_html=True)
        else:
            st.markdown('<div class="stButton">', unsafe_allow_html=True)

        clicked = st.button(label, key=key, disabled=disabled, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    return clicked


def render_info_row(label: str, value: str, value_color: Optional[str] = None):
    """
    Render label-value info row in terminal style

    Args:
        label: Label text
        value: Value text
        value_color: Optional CSS color for value
    """
    value_style = f'color: {value_color};' if value_color else ''

    st.markdown(f"""
    <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid var(--border-dim); font-family: var(--font-terminal);">
        <span style="color: var(--text-secondary); font-size: 13px;">{label}</span>
        <span style="{value_style} font-weight: 600; font-size: 14px;">{value}</span>
    </div>
    """, unsafe_allow_html=True)


def create_terminal_chart(
    df,
    title: str = "",
    height: int = 500
) -> go.Figure:
    """
    Create Plotly chart with terminal theme styling

    Args:
        df: DataFrame with OHLC data (requires: timestamp, open, high, low, close)
        title: Chart title
        height: Chart height in pixels

    Returns:
        Plotly figure with terminal styling
    """
    fig = go.Figure()

    # Add candlestick
    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='OHLC',
        increasing_line_color='#00ff41',  # Matrix green
        decreasing_line_color='#ff0844',  # Loss red
        increasing_fillcolor='rgba(0, 255, 65, 0.3)',
        decreasing_fillcolor='rgba(255, 8, 68, 0.3)'
    ))

    # Terminal theme layout
    fig.update_layout(
        title={
            'text': title,
            'font': {'family': 'Rajdhani, sans-serif', 'size': 20, 'color': '#00ff41'}
        },
        xaxis_title="",
        yaxis_title="Price",
        height=height,

        # Dark terminal theme
        plot_bgcolor='#0d1117',
        paper_bgcolor='#161b22',
        font={'family': 'JetBrains Mono, monospace', 'color': '#e6edf3'},

        # Grid styling
        xaxis={
            'gridcolor': '#21262d',
            'showgrid': True,
            'zeroline': False,
        },
        yaxis={
            'gridcolor': '#21262d',
            'showgrid': True,
            'zeroline': False,
        },

        # Hover styling
        hoverlabel={
            'bgcolor': '#161b22',
            'font_family': 'JetBrains Mono, monospace',
            'font_color': '#e6edf3',
            'bordercolor': '#30363d'
        },

        # Remove range slider (cleaner terminal look)
        xaxis_rangeslider_visible=False,

        # Margins
        margin=dict(l=60, r=20, t=60, b=40)
    )

    return fig


def render_loading_spinner(message: str = "LOADING..."):
    """Render terminal-style loading spinner"""
    st.markdown(f"""
    <div style="text-align: center; padding: 32px;">
        <div class="loading-spinner"></div>
        <div style="margin-top: 16px; font-family: var(--font-mono); color: var(--text-secondary); font-size: 12px; letter-spacing: 2px;">
            {message}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_section_divider(label: Optional[str] = None):
    """Render terminal-style section divider with optional label"""
    if label:
        st.markdown(f"""
        <div style="display: flex; align-items: center; margin: 32px 0 24px 0;">
            <div style="flex: 1; height: 1px; background: var(--border-bright);"></div>
            <div style="padding: 0 16px; font-family: var(--font-mono); font-size: 11px; color: var(--green-dark); text-transform: uppercase; letter-spacing: 2px;">
                {label}
            </div>
            <div style="flex: 1; height: 1px; background: var(--border-bright);"></div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="height: 1px; background: var(--border-bright); margin: 32px 0;"></div>
        """, unsafe_allow_html=True)


def render_glitch_text(text: str, data_text: Optional[str] = None):
    """
    Render text with subtle glitch effect (use sparingly for emphasis)

    Args:
        text: Text to display
        data_text: Optional data attribute for glitch effect (defaults to text)
    """
    data_attr = data_text or text

    st.markdown(f"""
    <div class="glitch" data-text="{data_attr}" style="
        font-family: var(--font-display);
        font-size: 32px;
        font-weight: 700;
        color: var(--green-bright);
        text-transform: uppercase;
        letter-spacing: 2px;
        margin: 24px 0;
    ">
        {text}
    </div>
    """, unsafe_allow_html=True)
