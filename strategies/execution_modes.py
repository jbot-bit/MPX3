"""
Execution modes for ORB trading strategies.

Separates signal detection from fill logic to model realistic execution:
- MARKET_ON_CLOSE: Market order when signal fires (has slippage)
- LIMIT_AT_ORB: Limit order at ORB boundary (no slippage, touch-based)
- LIMIT_RETRACE: Limit order only if price retraces after signal

Each mode has different:
- Fill conditions (guaranteed vs conditional)
- Fill prices (close + slippage vs ORB edge)
- Trade counts (LIMIT_AT_ORB gets more, LIMIT_RETRACE gets fewer)
- Slippage costs (MARKET only)
"""

from enum import Enum
from typing import Optional, Tuple, List
from dataclasses import dataclass


class ExecutionMode(Enum):
    """
    Execution modes for ORB trades.

    MARKET_ON_CLOSE: Market order filled immediately when signal fires
    - Signal: N consecutive closes outside ORB
    - Fill: Guaranteed at close + slippage
    - Slippage: Yes (configurable, default 1.5 ticks)
    - Use case: Fast markets, need guaranteed fill

    LIMIT_AT_ORB: Limit order at ORB boundary (touch-based)
    - Signal: Price touches ORB high or low
    - Fill: At ORB boundary (exact)
    - Slippage: No
    - Use case: Patient entry, best price, no confirmation needed

    LIMIT_RETRACE: Limit order only if price retraces after signal
    - Signal: N consecutive closes outside ORB, then price retraces
    - Fill: At ORB boundary if retrace occurs
    - Slippage: No
    - Use case: Cherry-pick only trades that show weakness
    """
    MARKET_ON_CLOSE = "market_on_close"
    LIMIT_AT_ORB = "limit_at_orb"
    LIMIT_RETRACE = "limit_retrace"


@dataclass
class FillResult:
    """
    Result of attempting to fill an order.

    filled: Whether fill occurred
    fill_price: Price at which fill occurred (None if no fill)
    fill_ts: Timestamp when fill occurred (None if no fill)
    fill_idx: Bar index where fill occurred (None if no fill)
    slippage_ticks: Slippage incurred (0 for limit orders)
    direction: 'UP' or 'DOWN' (None if no fill)
    """
    filled: bool
    fill_price: Optional[float]
    fill_ts: Optional[str]
    fill_idx: Optional[int]
    slippage_ticks: float
    direction: Optional[str]


def attempt_market_on_close_fill(
    bars: List[Tuple],
    orb_high: float,
    orb_low: float,
    confirm_bars: int,
    slippage_ticks: float,
    tick_size: float
) -> FillResult:
    """
    MARKET_ON_CLOSE execution mode.

    Signal: N consecutive 1-min bar closes outside ORB
    Fill: Immediate at close + slippage (guaranteed)
    Slippage: Applied in direction of trade (degrades entry)

    Returns FillResult with fill details or filled=False if no signal.
    """
    consec = 0
    direction = None

    for i, (ts_local, high, low, close) in enumerate(bars):
        close = float(close)

        # Check if close is outside ORB
        if close > orb_high:
            if direction != "UP":
                direction = "UP"
                consec = 0
            consec += 1
        elif close < orb_low:
            if direction != "DOWN":
                direction = "DOWN"
                consec = 0
            consec += 1
        else:
            # Close inside ORB - reset
            direction = None
            consec = 0

        # Signal fires after N consecutive closes
        if consec >= confirm_bars:
            # Fill at close + slippage (market order)
            slippage_price = slippage_ticks * tick_size

            if direction == "UP":
                fill_price = close + slippage_price  # Pay up
            else:
                fill_price = close - slippage_price  # Sell lower

            return FillResult(
                filled=True,
                fill_price=fill_price,
                fill_ts=str(ts_local),
                fill_idx=i,
                slippage_ticks=slippage_ticks,
                direction=direction
            )

    # No signal fired
    return FillResult(
        filled=False,
        fill_price=None,
        fill_ts=None,
        fill_idx=None,
        slippage_ticks=0.0,
        direction=None
    )


def attempt_limit_at_orb_fill(
    bars: List[Tuple],
    orb_high: float,
    orb_low: float,
    tick_size: float,
    penetration_ticks: float = 1.0  # Require price to trade THROUGH by this many ticks
) -> FillResult:
    """
    LIMIT_AT_ORB execution mode.

    Signal: Price PENETRATES ORB boundary (not just touches)
    Fill: At ORB boundary (exact) - requires penetration_ticks through level
    Slippage: None (limit order)

    REALISM: Requires price to trade THROUGH the ORB edge by penetration_ticks
    to count as filled. This models queue position and ensures you're not just
    touched but actually filled.

    Default: penetration_ticks=1.0 (price must trade 1 tick through to fill)

    If both boundaries touched same bar: Use first touch (high vs low comparison).
    If indeterminate: skip trade (conservative).

    Returns FillResult with fill details or filled=False if never filled.
    """
    penetration_price = penetration_ticks * tick_size

    for i, (ts_local, high, low, close) in enumerate(bars):
        high = float(high)
        low = float(low)

        # Check if ORB high PENETRATED (not just touched)
        # Require price to trade THROUGH the level by penetration_ticks
        touched_high = high >= orb_high + penetration_price
        # Check if ORB low PENETRATED
        touched_low = low <= orb_low - penetration_price

        if touched_high and touched_low:
            # Both boundaries touched same bar - EDGE CASE
            # Rule: First touch wins
            # If high came first (low was lower), ORB high touched first → UP
            # If low came first (high was higher), ORB low touched first → DOWN
            # If indeterminate (bar contains ORB completely): SKIP (conservative)

            if low < orb_low and high > orb_high:
                # Bar completely contains ORB - ambiguous, skip
                continue
            elif abs(high - orb_high) < abs(low - orb_low):
                # High touch was closer to ORB boundary → touched first
                direction = "UP"
                fill_price = orb_high
            else:
                # Low touch was closer → touched first
                direction = "DOWN"
                fill_price = orb_low
        elif touched_high:
            direction = "UP"
            fill_price = orb_high
        elif touched_low:
            direction = "DOWN"
            fill_price = orb_low
        else:
            # ORB not touched this bar
            continue

        # Limit order filled at ORB boundary
        return FillResult(
            filled=True,
            fill_price=fill_price,
            fill_ts=str(ts_local),
            fill_idx=i,
            slippage_ticks=0.0,
            direction=direction
        )

    # ORB never touched
    return FillResult(
        filled=False,
        fill_price=None,
        fill_ts=None,
        fill_idx=None,
        slippage_ticks=0.0,
        direction=None
    )


def attempt_limit_retrace_fill(
    bars: List[Tuple],
    orb_high: float,
    orb_low: float,
    confirm_bars: int,
    tick_size: float,
    adverse_slippage_ticks: float = 0.0  # Adverse slippage on limit fills (models queue effects)
) -> FillResult:
    """
    LIMIT_RETRACE execution mode.

    Signal: N consecutive closes outside ORB (confirms breakout)
    Fill: Only if price retraces back to ORB boundary AFTER signal
    Slippage: None (limit order at ORB boundary)

    Logic:
    1. Wait for close-based signal (same as MARKET_ON_CLOSE)
    2. After signal, check if price retraces to ORB boundary
    3. Fill at ORB boundary if retrace occurs
    4. No fill if price runs away (never retraces)

    This mode cherry-picks only trades that show post-signal weakness.

    Returns FillResult with fill details or filled=False if no signal or no retrace.
    """
    consec = 0
    direction = None
    signal_fired = False
    signal_idx = None

    for i, (ts_local, high, low, close) in enumerate(bars):
        close = float(close)
        high = float(high)
        low = float(low)

        if not signal_fired:
            # PHASE 1: Wait for signal (N consecutive closes outside ORB)
            if close > orb_high:
                if direction != "UP":
                    direction = "UP"
                    consec = 0
                consec += 1
            elif close < orb_low:
                if direction != "DOWN":
                    direction = "DOWN"
                    consec = 0
                consec += 1
            else:
                direction = None
                consec = 0

            if consec >= confirm_bars:
                signal_fired = True
                signal_idx = i
                # Signal confirmed - now wait for retrace
        else:
            # PHASE 2: Signal fired, wait for retrace to ORB boundary
            if direction == "UP":
                # Waiting for retrace to ORB high
                if low <= orb_high:
                    # Limit order filled at ORB high + adverse slippage
                    # Adverse slippage models imperfect fills, queue effects
                    adverse_slippage_price = adverse_slippage_ticks * tick_size
                    fill_price = orb_high + adverse_slippage_price
                    return FillResult(
                        filled=True,
                        fill_price=fill_price,
                        fill_ts=str(ts_local),
                        fill_idx=i,
                        slippage_ticks=adverse_slippage_ticks,
                        direction=direction
                    )
            else:  # DOWN
                # Waiting for retrace to ORB low
                if high >= orb_low:
                    # Limit order filled at ORB low - adverse slippage
                    adverse_slippage_price = adverse_slippage_ticks * tick_size
                    fill_price = orb_low - adverse_slippage_price
                    return FillResult(
                        filled=True,
                        fill_price=fill_price,
                        fill_ts=str(ts_local),
                        fill_idx=i,
                        slippage_ticks=adverse_slippage_ticks,
                        direction=direction
                    )

    # Either no signal fired, or signal fired but no retrace
    return FillResult(
        filled=False,
        fill_price=None,
        fill_ts=None,
        fill_idx=None,
        slippage_ticks=0.0,
        direction=direction if signal_fired else None
    )
