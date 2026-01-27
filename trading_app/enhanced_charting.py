"""
ENHANCED CHARTING - Multi-timeframe charts with indicators and ORB overlays
Professional-grade charting for trading application.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from zoneinfo import ZoneInfo
import numpy as np


class ChartTimeframe:
    """Chart timeframe constants"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    D1 = "1d"


class Indicator:
    """Technical indicator implementations"""

    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return data.ewm(span=period, adjust=False).mean()

    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return data.rolling(window=period).mean()

    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average True Range"""
        high_low = high - low
        high_close = (high - close.shift()).abs()
        low_close = (low - close.shift()).abs()

        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(window=period).mean()
        return atr

    @staticmethod
    def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        """Volume Weighted Average Price"""
        typical_price = (high + low + close) / 3
        return (typical_price * volume).cumsum() / volume.cumsum()

    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands (middle, upper, lower)"""
        middle = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return middle, upper, lower


class ORBOverlay:
    """ORB visualization overlay for charts"""

    def __init__(self, orb_name: str, high: float, low: float, start_time: datetime,
                 end_time: datetime, filter_passed: bool = True, tier: str = "B"):
        self.orb_name = orb_name
        self.high = high
        self.low = low
        self.start_time = start_time
        self.end_time = end_time
        self.filter_passed = filter_passed
        self.tier = tier
        self.mid = (high + low) / 2
        self.size = high - low

    def get_color(self) -> str:
        """Get color based on filter status and tier"""
        if not self.filter_passed:
            return "rgba(220, 53, 69, 0.3)"  # Red (failed filter)
        elif self.tier in ["S+", "S"]:
            return "rgba(25, 135, 84, 0.3)"  # Green (elite)
        elif self.tier == "A":
            return "rgba(13, 110, 253, 0.3)"  # Blue (good)
        else:
            return "rgba(108, 117, 125, 0.3)"  # Gray (ok)

    def get_border_color(self) -> str:
        """Get border color"""
        if not self.filter_passed:
            return "rgb(220, 53, 69)"
        elif self.tier in ["S+", "S"]:
            return "rgb(25, 135, 84)"
        elif self.tier == "A":
            return "rgb(13, 110, 253)"
        else:
            return "rgb(108, 117, 125)"


class TradeMarker:
    """Trade visualization marker for charts"""

    def __init__(self, entry_time: datetime, entry_price: float, direction: str,
                 stop_price: Optional[float] = None, target_price: Optional[float] = None,
                 exit_time: Optional[datetime] = None, exit_price: Optional[float] = None):
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.direction = direction.upper()  # LONG or SHORT
        self.stop_price = stop_price
        self.target_price = target_price
        self.exit_time = exit_time
        self.exit_price = exit_price

    def is_long(self) -> bool:
        return self.direction == "LONG"


class EnhancedChart:
    """
    Enhanced chart builder with multiple timeframes, indicators, and overlays.
    """

    def __init__(self, timeframe: str = ChartTimeframe.M1):
        self.timeframe = timeframe
        self.fig = None
        self.indicators_enabled = {
            "ema_9": False,
            "ema_20": False,
            "ema_50": False,
            "sma_200": False,
            "vwap": False,
            "rsi": False,
            "atr_bands": False,
            "bollinger": False,
            "volume": False,
        }

    def create_chart(
        self,
        bars_df: pd.DataFrame,
        title: str = "Price Chart",
        height: int = 600,
        show_volume: bool = False
    ) -> go.Figure:
        """
        Create base candlestick chart.

        Args:
            bars_df: DataFrame with OHLCV data and ts_local column
            title: Chart title
            height: Chart height in pixels
            show_volume: Whether to show volume subplot

        Returns:
            Plotly Figure object
        """
        # Create subplot structure
        if show_volume:
            self.fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                row_heights=[0.7, 0.3],
                subplot_titles=(title, "Volume")
            )
        else:
            self.fig = go.Figure()

        # Add candlestick
        candlestick = go.Candlestick(
            x=bars_df["ts_local"],
            open=bars_df["open"],
            high=bars_df["high"],
            low=bars_df["low"],
            close=bars_df["close"],
            name="Price",
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350'
        )

        if show_volume:
            self.fig.add_trace(candlestick, row=1, col=1)

            # Add volume bars
            colors = ['#26a69a' if c >= o else '#ef5350'
                      for c, o in zip(bars_df['close'], bars_df['open'])]

            volume = go.Bar(
                x=bars_df["ts_local"],
                y=bars_df["volume"],
                name="Volume",
                marker_color=colors,
                showlegend=False
            )
            self.fig.add_trace(volume, row=2, col=1)
        else:
            self.fig.add_trace(candlestick)

        # Update layout
        self.fig.update_layout(
            title=title,
            xaxis_title="Time",
            yaxis_title="Price",
            height=height,
            xaxis_rangeslider_visible=False,
            hovermode='x unified',
            template='plotly_white'
        )

        return self.fig

    def add_ema(self, bars_df: pd.DataFrame, period: int, name: str = None, color: str = None):
        """Add EMA indicator to chart"""
        if self.fig is None:
            raise ValueError("Create chart first")

        ema = Indicator.ema(bars_df["close"], period)
        name = name or f"EMA({period})"

        self.fig.add_trace(go.Scatter(
            x=bars_df["ts_local"],
            y=ema,
            name=name,
            line=dict(color=color or 'blue', width=1),
            mode='lines'
        ))

    def add_sma(self, bars_df: pd.DataFrame, period: int, name: str = None, color: str = None):
        """Add SMA indicator to chart"""
        if self.fig is None:
            raise ValueError("Create chart first")

        sma = Indicator.sma(bars_df["close"], period)
        name = name or f"SMA({period})"

        self.fig.add_trace(go.Scatter(
            x=bars_df["ts_local"],
            y=sma,
            name=name,
            line=dict(color=color or 'purple', width=1),
            mode='lines'
        ))

    def add_vwap(self, bars_df: pd.DataFrame):
        """Add VWAP indicator to chart"""
        if self.fig is None:
            raise ValueError("Create chart first")

        vwap = Indicator.vwap(
            bars_df["high"],
            bars_df["low"],
            bars_df["close"],
            bars_df["volume"]
        )

        self.fig.add_trace(go.Scatter(
            x=bars_df["ts_local"],
            y=vwap,
            name="VWAP",
            line=dict(color='orange', width=2, dash='dash'),
            mode='lines'
        ))

    def add_bollinger_bands(self, bars_df: pd.DataFrame, period: int = 20, std_dev: float = 2.0):
        """Add Bollinger Bands to chart"""
        if self.fig is None:
            raise ValueError("Create chart first")

        middle, upper, lower = Indicator.bollinger_bands(bars_df["close"], period, std_dev)

        # Upper band
        self.fig.add_trace(go.Scatter(
            x=bars_df["ts_local"],
            y=upper,
            name="BB Upper",
            line=dict(color='rgba(173, 216, 230, 0.5)', width=1),
            mode='lines'
        ))

        # Lower band
        self.fig.add_trace(go.Scatter(
            x=bars_df["ts_local"],
            y=lower,
            name="BB Lower",
            line=dict(color='rgba(173, 216, 230, 0.5)', width=1),
            fill='tonexty',
            fillcolor='rgba(173, 216, 230, 0.1)',
            mode='lines'
        ))

        # Middle band
        self.fig.add_trace(go.Scatter(
            x=bars_df["ts_local"],
            y=middle,
            name="BB Middle",
            line=dict(color='rgba(173, 216, 230, 0.8)', width=1, dash='dot'),
            mode='lines'
        ))

    def add_atr_bands(self, bars_df: pd.DataFrame, period: int = 14, multiplier: float = 2.0):
        """Add ATR bands around price"""
        if self.fig is None:
            raise ValueError("Create chart first")

        atr = Indicator.atr(bars_df["high"], bars_df["low"], bars_df["close"], period)
        close = bars_df["close"]

        upper = close + (atr * multiplier)
        lower = close - (atr * multiplier)

        # Upper band
        self.fig.add_trace(go.Scatter(
            x=bars_df["ts_local"],
            y=upper,
            name=f"ATR Upper ({multiplier}x)",
            line=dict(color='rgba(255, 99, 71, 0.3)', width=1),
            mode='lines'
        ))

        # Lower band
        self.fig.add_trace(go.Scatter(
            x=bars_df["ts_local"],
            y=lower,
            name=f"ATR Lower ({multiplier}x)",
            line=dict(color='rgba(255, 99, 71, 0.3)', width=1),
            mode='lines'
        ))

    def add_session_levels(self, high: float, low: float, session_name: str, color: str = "green"):
        """Add session high/low horizontal lines"""
        if self.fig is None:
            raise ValueError("Create chart first")

        self.fig.add_hline(
            y=high,
            line_dash="dash",
            line_color=color,
            annotation_text=f"{session_name} High",
            annotation_position="right"
        )

        self.fig.add_hline(
            y=low,
            line_dash="dash",
            line_color=color,
            annotation_text=f"{session_name} Low",
            annotation_position="right"
        )

    def add_orb_overlay(self, orb: ORBOverlay, extend_right: bool = True):
        """
        Add ORB visualization overlay.

        Args:
            orb: ORBOverlay object
            extend_right: Whether to extend lines to right edge of chart
        """
        if self.fig is None:
            raise ValueError("Create chart first")

        # ORB rectangle (only during ORB window)
        self.fig.add_shape(
            type="rect",
            x0=orb.start_time,
            x1=orb.end_time,
            y0=orb.low,
            y1=orb.high,
            fillcolor=orb.get_color(),
            line=dict(color=orb.get_border_color(), width=2),
            layer="below"
        )

        # ORB high horizontal line (extends right)
        if extend_right:
            self.fig.add_hline(
                y=orb.high,
                line_dash="dot",
                line_color=orb.get_border_color(),
                line_width=1,
                annotation_text=f"{orb.orb_name} High ({orb.high:.1f})",
                annotation_position="right"
            )

            # ORB low horizontal line (extends right)
            self.fig.add_hline(
                y=orb.low,
                line_dash="dot",
                line_color=orb.get_border_color(),
                line_width=1,
                annotation_text=f"{orb.orb_name} Low ({orb.low:.1f})",
                annotation_position="right"
            )

            # ORB midpoint (for HALF stop loss)
            self.fig.add_hline(
                y=orb.mid,
                line_dash="dashdot",
                line_color=orb.get_border_color(),
                line_width=1,
                opacity=0.5,
                annotation_text=f"{orb.orb_name} Mid ({orb.mid:.1f})",
                annotation_position="right"
            )

        # Add label inside box
        self.fig.add_annotation(
            x=orb.start_time,
            y=orb.high,
            text=f"{orb.orb_name}<br>{orb.size:.1f}pts",
            showarrow=False,
            xshift=5,
            yshift=-10,
            bgcolor=orb.get_color(),
            bordercolor=orb.get_border_color(),
            borderwidth=1,
            font=dict(size=10, color="black")
        )

    def add_trade_marker(self, trade: TradeMarker):
        """
        Add trade visualization markers.

        Args:
            trade: TradeMarker object
        """
        if self.fig is None:
            raise ValueError("Create chart first")

        # Entry arrow
        if trade.is_long():
            # Long entry (green arrow up)
            self.fig.add_annotation(
                x=trade.entry_time,
                y=trade.entry_price,
                text="LONG",
                showarrow=True,
                arrowhead=2,
                arrowsize=1.5,
                arrowwidth=2,
                arrowcolor="green",
                ax=0,
                ay=30,
                bgcolor="rgba(25, 135, 84, 0.8)",
                bordercolor="green",
                font=dict(size=10, color="white")
            )
        else:
            # Short entry (red arrow down)
            self.fig.add_annotation(
                x=trade.entry_time,
                y=trade.entry_price,
                text="SHORT",
                showarrow=True,
                arrowhead=2,
                arrowsize=1.5,
                arrowwidth=2,
                arrowcolor="red",
                ax=0,
                ay=-30,
                bgcolor="rgba(220, 53, 69, 0.8)",
                bordercolor="red",
                font=dict(size=10, color="white")
            )

        # Stop loss line
        if trade.stop_price:
            self.fig.add_hline(
                y=trade.stop_price,
                line_dash="dash",
                line_color="red",
                line_width=2,
                annotation_text=f"Stop ({trade.stop_price:.1f})",
                annotation_position="left"
            )

        # Target line
        if trade.target_price:
            self.fig.add_hline(
                y=trade.target_price,
                line_dash="dash",
                line_color="green",
                line_width=2,
                annotation_text=f"Target ({trade.target_price:.1f})",
                annotation_position="left"
            )

        # Exit marker (if closed)
        if trade.exit_time and trade.exit_price:
            pnl_color = "green" if (
                (trade.is_long() and trade.exit_price > trade.entry_price) or
                (not trade.is_long() and trade.exit_price < trade.entry_price)
            ) else "red"

            self.fig.add_annotation(
                x=trade.exit_time,
                y=trade.exit_price,
                text="EXIT",
                showarrow=True,
                arrowhead=1,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor=pnl_color,
                ax=0,
                ay=0,
                bgcolor=f"rgba({'25, 135, 84' if pnl_color == 'green' else '220, 53, 69'}, 0.8)",
                bordercolor=pnl_color,
                font=dict(size=10, color="white")
            )

    def add_previous_levels(self, prev_day_high: float, prev_day_low: float,
                           prev_week_high: float = None, prev_week_low: float = None):
        """Add previous day/week high/low levels"""
        if self.fig is None:
            raise ValueError("Create chart first")

        # Previous day levels
        self.fig.add_hline(
            y=prev_day_high,
            line_dash="dot",
            line_color="rgba(128, 128, 128, 0.5)",
            annotation_text="Prev Day High",
            annotation_position="left"
        )

        self.fig.add_hline(
            y=prev_day_low,
            line_dash="dot",
            line_color="rgba(128, 128, 128, 0.5)",
            annotation_text="Prev Day Low",
            annotation_position="left"
        )

        # Previous week levels (if provided)
        if prev_week_high:
            self.fig.add_hline(
                y=prev_week_high,
                line_dash="dashdot",
                line_color="rgba(128, 128, 128, 0.3)",
                annotation_text="Prev Week High",
                annotation_position="left"
            )

        if prev_week_low:
            self.fig.add_hline(
                y=prev_week_low,
                line_dash="dashdot",
                line_color="rgba(128, 128, 128, 0.3)",
                annotation_text="Prev Week Low",
                annotation_position="left"
            )

    def get_figure(self) -> go.Figure:
        """Get the current figure"""
        return self.fig


def resample_bars(bars_df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """
    Resample 1-minute bars to different timeframe.

    Args:
        bars_df: DataFrame with 1-minute bars
        timeframe: Target timeframe (5m, 15m, 1h, 1d)

    Returns:
        Resampled DataFrame
    """
    # Ensure index is datetime
    df = bars_df.copy()
    df.set_index('ts_local', inplace=True)

    # Resample rules
    resample_map = {
        ChartTimeframe.M5: '5min',
        ChartTimeframe.M15: '15min',
        ChartTimeframe.H1: '1H',
        ChartTimeframe.D1: '1D'
    }

    rule = resample_map.get(timeframe)
    if not rule:
        return bars_df

    # Resample OHLCV
    resampled = df.resample(rule).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    resampled.reset_index(inplace=True)

    return resampled
