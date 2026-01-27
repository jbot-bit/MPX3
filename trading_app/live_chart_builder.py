"""
Live Chart Builder with Trade Zones
Builds professional trading charts with clear trade entry zones
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from enhanced_charting import EnhancedChart, ORBOverlay, ChartTimeframe


def build_live_trading_chart(
    bars_df: pd.DataFrame,
    orb_high: Optional[float] = None,
    orb_low: Optional[float] = None,
    orb_name: str = "0900",
    orb_start: Optional[datetime] = None,
    orb_end: Optional[datetime] = None,
    current_price: Optional[float] = None,
    filter_passed: bool = True,
    tier: str = "B",
    entry_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    target_price: Optional[float] = None,
    direction: Optional[str] = None,
    height: int = 700
) -> go.Figure:
    """
    Build a live trading chart with clear trade zones.

    Args:
        bars_df: DataFrame with OHLCV data
        orb_high: ORB high price
        orb_low: ORB low price
        orb_name: ORB name (e.g., "0900")
        orb_start: ORB window start time
        orb_end: ORB window end time
        current_price: Current market price
        filter_passed: Whether ORB passed size filter
        tier: Setup tier (S+, S, A, B, C)
        entry_price: Trade entry price
        stop_price: Stop loss price
        target_price: Target profit price
        direction: Trade direction ("LONG" or "SHORT")
        height: Chart height in pixels

    Returns:
        Plotly Figure with trade zones
    """

    # Create base chart with volume
    chart = EnhancedChart(ChartTimeframe.M1)
    fig = chart.create_chart(
        bars_df,
        title=f"🔴 LIVE - {orb_name} ORB",
        height=height,
        show_volume=True
    )

    chart.fig = fig  # Set figure for overlay methods

    # Update layout for dark theme
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#1a1d26',
        plot_bgcolor='#0f1117',
        font=dict(color='#e5e7eb', family='Inter, sans-serif'),
        title_font=dict(size=20, color='#f9fafb'),
        xaxis=dict(
            gridcolor='rgba(255, 255, 255, 0.05)',
            showgrid=True
        ),
        yaxis=dict(
            gridcolor='rgba(255, 255, 255, 0.05)',
            showgrid=True
        )
    )

    # If ORB data available, add overlays
    if orb_high and orb_low and orb_start and orb_end:

        # Add ORB overlay
        orb = ORBOverlay(
            orb_name=orb_name,
            high=orb_high,
            low=orb_low,
            start_time=orb_start,
            end_time=orb_end,
            filter_passed=filter_passed,
            tier=tier
        )

        chart.add_orb_overlay(orb, extend_right=True)

        # Add LONG ZONE (above ORB high)
        if filter_passed:
            # Calculate zone height (about 2x ORB size)
            orb_size = orb_high - orb_low
            long_zone_top = orb_high + (orb_size * 2)

            fig.add_shape(
                type="rect",
                x0=bars_df["ts_local"].iloc[0],
                x1=bars_df["ts_local"].iloc[-1],
                y0=orb_high,
                y1=long_zone_top,
                fillcolor="rgba(16, 185, 129, 0.08)",  # Green
                line=dict(width=0),
                layer="below"
            )

            # LONG label
            fig.add_annotation(
                x=bars_df["ts_local"].iloc[-1],
                y=(orb_high + long_zone_top) / 2,
                text="<b>🚀 LONG ZONE</b><br>Enter above ORB high",
                showarrow=False,
                font=dict(size=14, color="#10b981"),
                bgcolor="rgba(16, 185, 129, 0.2)",
                bordercolor="#10b981",
                borderwidth=2,
                borderpad=8,
                xanchor="right"
            )

            # Add SHORT ZONE (below ORB low)
            short_zone_bottom = orb_low - (orb_size * 2)

            fig.add_shape(
                type="rect",
                x0=bars_df["ts_local"].iloc[0],
                x1=bars_df["ts_local"].iloc[-1],
                y0=short_zone_bottom,
                y1=orb_low,
                fillcolor="rgba(239, 68, 68, 0.08)",  # Red
                line=dict(width=0),
                layer="below"
            )

            # SHORT label
            fig.add_annotation(
                x=bars_df["ts_local"].iloc[-1],
                y=(orb_low + short_zone_bottom) / 2,
                text="<b>🔻 SHORT ZONE</b><br>Enter below ORB low",
                showarrow=False,
                font=dict(size=14, color="#ef4444"),
                bgcolor="rgba(239, 68, 68, 0.2)",
                bordercolor="#ef4444",
                borderwidth=2,
                borderpad=8,
                xanchor="right"
            )

    # Add current price line
    if current_price:
        fig.add_hline(
            y=current_price,
            line_dash="solid",
            line_color="#6366f1",  # Indigo
            line_width=3,
            annotation_text=f"Current: ${current_price:.2f}",
            annotation_position="left",
            annotation_font=dict(size=14, color="#6366f1")
        )

    # Add trade markers if there's an active trade
    if entry_price and direction:

        # Entry line
        fig.add_hline(
            y=entry_price,
            line_dash="dash",
            line_color="#fbbf24",  # Amber
            line_width=2,
            annotation_text=f"Entry: ${entry_price:.2f}",
            annotation_position="right",
            annotation_font=dict(size=12, color="#fbbf24")
        )

        # Stop loss line
        if stop_price:
            fig.add_hline(
                y=stop_price,
                line_dash="dash",
                line_color="#ef4444",  # Red
                line_width=2,
                annotation_text=f"Stop: ${stop_price:.2f}",
                annotation_position="right",
                annotation_font=dict(size=12, color="#ef4444")
            )

        # Target line
        if target_price:
            fig.add_hline(
                y=target_price,
                line_dash="dash",
                line_color="#10b981",  # Green
                line_width=2,
                annotation_text=f"Target: ${target_price:.2f}",
                annotation_position="right",
                annotation_font=dict(size=12, color="#10b981")
            )

        # Add entry marker
        last_time = bars_df["ts_local"].iloc[-1]

        fig.add_annotation(
            x=last_time,
            y=entry_price,
            text="▶" if direction == "LONG" else "◀",
            showarrow=True,
            arrowhead=2,
            arrowsize=2,
            arrowwidth=3,
            arrowcolor="#fbbf24",
            ax=40 if direction == "LONG" else -40,
            ay=0,
            font=dict(size=20, color="#fbbf24")
        )

    return fig


def build_simple_price_chart(
    bars_df: pd.DataFrame,
    current_price: Optional[float] = None,
    title: str = "Live Price",
    height: int = 400
) -> go.Figure:
    """
    Build a simple price chart without ORB overlays.

    Args:
        bars_df: DataFrame with OHLCV data
        current_price: Current market price
        title: Chart title
        height: Chart height

    Returns:
        Plotly Figure
    """

    fig = go.Figure()

    # Add candlestick
    fig.add_trace(go.Candlestick(
        x=bars_df["ts_local"],
        open=bars_df["open"],
        high=bars_df["high"],
        low=bars_df["low"],
        close=bars_df["close"],
        name="Price",
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350'
    ))

    # Add current price
    if current_price:
        fig.add_hline(
            y=current_price,
            line_dash="solid",
            line_color="#6366f1",
            line_width=3,
            annotation_text=f"${current_price:.2f}",
            annotation_position="left"
        )

    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title="Price",
        height=height,
        xaxis_rangeslider_visible=False,
        hovermode='x unified',
        template='plotly_dark',
        paper_bgcolor='#1a1d26',
        plot_bgcolor='#0f1117',
        font=dict(color='#e5e7eb'),
        xaxis=dict(gridcolor='rgba(255, 255, 255, 0.05)'),
        yaxis=dict(gridcolor='rgba(255, 255, 255, 0.05)')
    )

    return fig


def calculate_trade_levels(
    orb_high: float,
    orb_low: float,
    direction: str,
    rr: float = 1.0,
    sl_mode: str = "FULL"
) -> Dict[str, float]:
    """
    Calculate entry, stop, and target levels for a trade.

    Args:
        orb_high: ORB high price
        orb_low: ORB low price
        direction: "LONG" or "SHORT"
        rr: Risk/reward ratio
        sl_mode: "FULL" or "HALF"

    Returns:
        Dictionary with entry, stop, target prices
    """

    orb_mid = (orb_high + orb_low) / 2

    if direction == "LONG":
        entry = orb_high
        stop = orb_mid if sl_mode == "HALF" else orb_low
        risk = entry - stop
        target = entry + (risk * rr)
    else:  # SHORT
        entry = orb_low
        stop = orb_mid if sl_mode == "HALF" else orb_high
        risk = stop - entry
        target = entry - (risk * rr)

    return {
        "entry": entry,
        "stop": stop,
        "target": target,
        "risk_points": abs(risk),
        "reward_points": abs(target - entry)
    }


def build_mobile_chart(
    bars_df: pd.DataFrame,
    orb_high: Optional[float] = None,
    orb_low: Optional[float] = None,
    height: int = 350
) -> go.Figure:
    """
    Build a mobile-optimized chart - compact, touch-friendly.

    Args:
        bars_df: DataFrame with OHLCV data
        orb_high: ORB high price
        orb_low: ORB low price
        height: Chart height in pixels (default 350 for mobile)

    Returns:
        Plotly Figure optimized for mobile viewing
    """

    fig = go.Figure()

    # Candlesticks - thinner bars for mobile
    fig.add_trace(go.Candlestick(
        x=bars_df['ts_local'],
        open=bars_df['open'],
        high=bars_df['high'],
        low=bars_df['low'],
        close=bars_df['close'],
        name='Price',
        increasing_line_color='#10b981',  # Green
        decreasing_line_color='#ef4444',  # Red
        increasing_line_width=1,
        decreasing_line_width=1
    ))

    # ORB lines - simple, high contrast
    if orb_high:
        fig.add_hline(
            y=orb_high,
            line_color="#10b981",
            line_width=2,
            annotation_text=f"ORB High: ${orb_high:.2f}",
            annotation_position="right",
            annotation_font=dict(size=10, color="#10b981")
        )

    if orb_low:
        fig.add_hline(
            y=orb_low,
            line_color="#ef4444",
            line_width=2,
            annotation_text=f"ORB Low: ${orb_low:.2f}",
            annotation_position="right",
            annotation_font=dict(size=10, color="#ef4444")
        )

    # Mobile layout
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=50, t=20, b=10),  # Tight margins
        paper_bgcolor='#1a1d26',
        plot_bgcolor='#0f1117',
        font=dict(size=11, color='#e5e7eb'),  # Smaller font
        showlegend=False,  # Save space
        xaxis=dict(
            rangeslider=dict(visible=False),  # Remove range slider
            gridcolor='#374151',
            showgrid=True
        ),
        yaxis=dict(
            side='right',  # Price on right (thumb friendly)
            gridcolor='#374151',
            showgrid=True
        ),
        hovermode='x unified',
        template='plotly_dark'
    )

    # Touch interactions
    fig.update_xaxes(fixedrange=False)  # Allow pinch-zoom
    fig.update_yaxes(fixedrange=False)

    return fig
