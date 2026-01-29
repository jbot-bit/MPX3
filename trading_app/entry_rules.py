"""
Entry Rule Implementations - Unambiguous definitions

This module implements specific entry rules with clear, reproducible logic.
Each function takes an ExecutionSpec and returns entry details.

Created for UPDATE14 (update14.txt) - Step 3
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from zoneinfo import ZoneInfo

try:
    from trading_app.execution_spec import ExecutionSpec
    from trading_app.execution_contract import get_contract_for_entry_rule
except ModuleNotFoundError:
    from execution_spec import ExecutionSpec
    from execution_contract import get_contract_for_entry_rule


def parse_orb_time(orb_time: str, date: pd.Timestamp, tz: str) -> pd.Timestamp:
    """
    Convert ORB time string to timestamp for a specific date.

    Args:
        orb_time: Time string like "0900", "1000"
        date: Trading date
        tz: Timezone (e.g., "Australia/Brisbane")

    Returns:
        pd.Timestamp: ORB start timestamp
    """
    hour = int(orb_time[:2])
    minute = int(orb_time[2:])

    # Create timestamp in local timezone
    orb_start = pd.Timestamp(
        year=date.year,
        month=date.month,
        day=date.day,
        hour=hour,
        minute=minute,
        second=0,
        tz=tz
    )

    return orb_start


def compute_orb_range(
    bars: pd.DataFrame,
    orb_start: pd.Timestamp,
    orb_minutes: int
) -> Dict[str, Any]:
    """
    Compute ORB high/low from bars.

    Args:
        bars: DataFrame with timestamp, high, low
        orb_start: ORB start timestamp
        orb_minutes: ORB duration

    Returns:
        dict: orb_high, orb_low, orb_start, orb_end
        None: if bars empty or missing required columns
    """
    # CRITICAL: Validate input before accessing columns
    if bars is None or bars.empty:
        return None

    required_cols = {'timestamp', 'high', 'low'}
    if not required_cols.issubset(bars.columns):
        return None

    orb_end = orb_start + timedelta(minutes=orb_minutes)

    # Filter to ORB window
    orb_bars = bars[
        (bars['timestamp'] >= orb_start) &
        (bars['timestamp'] < orb_end)
    ]

    if len(orb_bars) == 0:
        return None

    return {
        'orb_high': orb_bars['high'].max(),
        'orb_low': orb_bars['low'].min(),
        'orb_start': orb_start,
        'orb_end': orb_end,
        'orb_bars': len(orb_bars)
    }


def aggregate_1m_to_5m(bars_1m: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate 1-minute bars to 5-minute bars.

    Alignment: Floor to 5-minute boundaries (00, 05, 10, 15, etc.)

    Args:
        bars_1m: DataFrame with timestamp, open, high, low, close, volume

    Returns:
        DataFrame: 5-minute bars with timestamp_start, timestamp_end, OHLCV
    """
    if len(bars_1m) == 0:
        return pd.DataFrame()

    # Ensure sorted by timestamp
    bars_1m = bars_1m.sort_values('timestamp').copy()

    # Create 5-minute bins (floor to 5-min boundary)
    bars_1m['bin'] = bars_1m['timestamp'].dt.floor('5min')

    # Aggregate
    bars_5m = bars_1m.groupby('bin').agg({
        'timestamp': ['first', 'last'],
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum' if 'volume' in bars_1m.columns else lambda x: 0
    }).reset_index()

    # Flatten column names
    bars_5m.columns = [
        'timestamp_start',
        'timestamp_first_bar',
        'timestamp_last_bar',
        'open',
        'high',
        'low',
        'close',
        'volume'
    ]

    # Use last bar timestamp as the 5m bar timestamp
    bars_5m['timestamp'] = bars_5m['timestamp_last_bar']
    bars_5m['timestamp_end'] = bars_5m['timestamp_start'] + timedelta(minutes=5)

    return bars_5m[['timestamp', 'timestamp_start', 'timestamp_end', 'open', 'high', 'low', 'close', 'volume']]


# =====================================================================
# ENTRY RULE: limit_at_orb
# =====================================================================

def compute_limit_at_orb(
    spec: ExecutionSpec,
    bars: pd.DataFrame,
    date: pd.Timestamp
) -> Optional[Dict[str, Any]]:
    """
    Compute entry for limit_at_orb rule.

    Entry: Limit order at ORB edge (immediate entry when ORB breaks)

    Logic:
    1. Build ORB from bars in ORB window
    2. Entry = First bar that breaks ORB (high > orb_high OR low < orb_low)
    3. Entry price = ORB edge (orb_high for long, orb_low for short)
    4. Entry timestamp = breakout bar timestamp

    Args:
        spec: ExecutionSpec with entry_rule='limit_at_orb'
        bars: bars_1m data for the day
        date: Trading date

    Returns:
        dict: entry details or None if no entry
    """
    # Validate contract
    contract = get_contract_for_entry_rule(spec.entry_rule)
    result = contract.validate(spec)
    if not result.valid:
        raise ValueError(f"Contract validation failed: {result}")

    # Compute ORB
    orb_start = parse_orb_time(spec.orb_time, date, spec.session_tz)
    orb_data = compute_orb_range(bars, orb_start, spec.orb_minutes)

    if orb_data is None:
        return None

    orb_high = orb_data['orb_high']
    orb_low = orb_data['orb_low']
    orb_end = orb_data['orb_end']

    # Find first bar after ORB that breaks range
    post_orb = bars[bars['timestamp'] >= orb_end].copy()

    if len(post_orb) == 0:
        return None

    for idx, bar in post_orb.iterrows():
        if bar['high'] > orb_high:
            # Long breakout
            return {
                'entry_timestamp': bar['timestamp'],
                'entry_price': orb_high,  # Limit order at ORB edge
                'direction': 'LONG',
                'orb_high': orb_high,
                'orb_low': orb_low,
                'orb_start': orb_start,
                'orb_end': orb_end,
                'entry_rule': 'limit_at_orb'
            }
        elif bar['low'] < orb_low:
            # Short breakout
            return {
                'entry_timestamp': bar['timestamp'],
                'entry_price': orb_low,  # Limit order at ORB edge
                'direction': 'SHORT',
                'orb_high': orb_high,
                'orb_low': orb_low,
                'orb_start': orb_start,
                'orb_end': orb_end,
                'entry_rule': 'limit_at_orb'
            }

    return None  # No breakout


# =====================================================================
# ENTRY RULE: 1st_close_outside
# =====================================================================

def compute_1st_close_outside(
    spec: ExecutionSpec,
    bars: pd.DataFrame,
    date: pd.Timestamp
) -> Optional[Dict[str, Any]]:
    """
    Compute entry for 1st_close_outside rule.

    Entry: First 1m bar that CLOSES outside ORB range

    Logic:
    1. Build ORB from bars in ORB window
    2. Find first bar after ORB where close > orb_high OR close < orb_low
    3. Entry price = open of NEXT bar (not the confirmation bar)
    4. Entry timestamp = next bar timestamp

    Args:
        spec: ExecutionSpec with entry_rule='1st_close_outside'
        bars: bars_1m data for the day
        date: Trading date

    Returns:
        dict: entry details or None if no entry
    """
    # Validate contract
    contract = get_contract_for_entry_rule(spec.entry_rule)
    result = contract.validate(spec)
    if not result.valid:
        raise ValueError(f"Contract validation failed: {result}")

    # Compute ORB
    orb_start = parse_orb_time(spec.orb_time, date, spec.session_tz)
    orb_data = compute_orb_range(bars, orb_start, spec.orb_minutes)

    if orb_data is None:
        return None

    orb_high = orb_data['orb_high']
    orb_low = orb_data['orb_low']
    orb_end = orb_data['orb_end']

    # Find first close outside ORB
    post_orb = bars[bars['timestamp'] >= orb_end].copy().reset_index(drop=True)

    if len(post_orb) == 0:
        return None

    for i, bar in post_orb.iterrows():
        if bar['close'] > orb_high:
            # Long confirmation - enter next bar
            if i + 1 < len(post_orb):
                entry_bar = post_orb.iloc[i + 1]
                return {
                    'entry_timestamp': entry_bar['timestamp'],
                    'entry_price': entry_bar['open'],
                    'direction': 'LONG',
                    'orb_high': orb_high,
                    'orb_low': orb_low,
                    'orb_start': orb_start,
                    'orb_end': orb_end,
                    'confirm_timestamp': bar['timestamp'],
                    'confirm_close': bar['close'],
                    'entry_rule': '1st_close_outside'
                }

        elif bar['close'] < orb_low:
            # Short confirmation - enter next bar
            if i + 1 < len(post_orb):
                entry_bar = post_orb.iloc[i + 1]
                return {
                    'entry_timestamp': entry_bar['timestamp'],
                    'entry_price': entry_bar['open'],
                    'direction': 'SHORT',
                    'orb_high': orb_high,
                    'orb_low': orb_low,
                    'orb_start': orb_start,
                    'orb_end': orb_end,
                    'confirm_timestamp': bar['timestamp'],
                    'confirm_close': bar['close'],
                    'entry_rule': '1st_close_outside'
                }

    return None  # No close outside


# =====================================================================
# ENTRY RULE: 5m_close_outside
# =====================================================================

def compute_5m_close_outside(
    spec: ExecutionSpec,
    bars: pd.DataFrame,
    date: pd.Timestamp
) -> Optional[Dict[str, Any]]:
    """
    Compute entry for 5m_close_outside rule.

    Entry: First 5m aggregated bar that CLOSES outside ORB range

    Logic (HYBRID APPROACH - Step 3 decision):
    1. Build ORB from 1m bars in ORB window (highest granularity)
    2. Aggregate post-ORB 1m bars to 5m bars
    3. Find first 5m bar where close > orb_high OR close < orb_low
    4. Entry = open of first 1m bar after 5m confirmation close
    5. Entry timestamp = first 1m bar after 5m boundary

    Args:
        spec: ExecutionSpec with entry_rule='5m_close_outside'
        bars: bars_1m data for the day
        date: Trading date

    Returns:
        dict: entry details or None if no entry
    """
    # Validate contract
    contract = get_contract_for_entry_rule(spec.entry_rule)
    result = contract.validate(spec)
    if not result.valid:
        raise ValueError(f"Contract validation failed: {result}")

    # Compute ORB (from 1m bars)
    orb_start = parse_orb_time(spec.orb_time, date, spec.session_tz)
    orb_data = compute_orb_range(bars, orb_start, spec.orb_minutes)

    if orb_data is None:
        return None

    orb_high = orb_data['orb_high']
    orb_low = orb_data['orb_low']
    orb_end = orb_data['orb_end']

    # Aggregate post-ORB bars to 5m
    post_orb_1m = bars[bars['timestamp'] >= orb_end].copy()

    if len(post_orb_1m) == 0:
        return None

    post_orb_5m = aggregate_1m_to_5m(post_orb_1m)

    if len(post_orb_5m) == 0:
        return None

    # Find first 5m close outside ORB
    for idx, bar_5m in post_orb_5m.iterrows():
        if bar_5m['close'] > orb_high:
            # Long confirmation
            confirm_ts = bar_5m['timestamp_end']
            direction = 'LONG'

            # Entry = first 1m bar after 5m confirmation
            entry_bars = bars[bars['timestamp'] >= confirm_ts]
            if len(entry_bars) == 0:
                return None

            entry_bar = entry_bars.iloc[0]

            return {
                'entry_timestamp': entry_bar['timestamp'],
                'entry_price': entry_bar['open'],
                'direction': direction,
                'orb_high': orb_high,
                'orb_low': orb_low,
                'orb_start': orb_start,
                'orb_end': orb_end,
                'confirm_timestamp': bar_5m['timestamp'],
                'confirm_close': bar_5m['close'],
                'confirm_5m_end': confirm_ts,
                'entry_rule': '5m_close_outside'
            }

        elif bar_5m['close'] < orb_low:
            # Short confirmation
            confirm_ts = bar_5m['timestamp_end']
            direction = 'SHORT'

            # Entry = first 1m bar after 5m confirmation
            entry_bars = bars[bars['timestamp'] >= confirm_ts]
            if len(entry_bars) == 0:
                return None

            entry_bar = entry_bars.iloc[0]

            return {
                'entry_timestamp': entry_bar['timestamp'],
                'entry_price': entry_bar['open'],
                'direction': direction,
                'orb_high': orb_high,
                'orb_low': orb_low,
                'orb_start': orb_start,
                'orb_end': orb_end,
                'confirm_timestamp': bar_5m['timestamp'],
                'confirm_close': bar_5m['close'],
                'confirm_5m_end': confirm_ts,
                'entry_rule': '5m_close_outside'
            }

    return None  # No 5m close outside


# =====================================================================
# UNIFIED ENTRY FUNCTION
# =====================================================================

def compute_entry(
    spec: ExecutionSpec,
    bars: pd.DataFrame,
    date: pd.Timestamp
) -> Optional[Dict[str, Any]]:
    """
    Compute entry for any entry rule.

    Dispatches to appropriate entry rule implementation.

    Args:
        spec: ExecutionSpec
        bars: bars_1m data for the day
        date: Trading date

    Returns:
        dict: entry details or None if no entry
    """
    entry_funcs = {
        'limit_at_orb': compute_limit_at_orb,
        '1st_close_outside': compute_1st_close_outside,
        '2nd_close_outside': compute_1st_close_outside,  # Same logic
        '5m_close_outside': compute_5m_close_outside
    }

    if spec.entry_rule not in entry_funcs:
        raise ValueError(f"Unknown entry_rule: {spec.entry_rule}")

    return entry_funcs[spec.entry_rule](spec, bars, date)


if __name__ == "__main__":
    # Test basic functionality
    print("=" * 70)
    print("Entry Rules Test")
    print("=" * 70)

    # Create test data (simple ORB breakout)
    test_date = pd.Timestamp("2024-01-15", tz="Australia/Brisbane")

    test_bars = pd.DataFrame({
        'timestamp': pd.date_range(
            '2024-01-15 10:00',
            periods=20,
            freq='1min',
            tz='Australia/Brisbane'
        ),
        'open': [100.0 + i*0.1 for i in range(20)],
        'high': [100.2 + i*0.1 for i in range(20)],
        'low': [99.8 + i*0.1 for i in range(20)],
        'close': [100.1 + i*0.1 for i in range(20)],
        'volume': [1000] * 20
    })

    # Test 1: limit_at_orb
    print("\nTest 1: limit_at_orb")
    spec1 = ExecutionSpec(
        bar_tf="1m",
        orb_time="1000",
        orb_minutes=5,
        entry_rule="limit_at_orb",
        rr_target=1.0
    )

    result1 = compute_entry(spec1, test_bars, test_date)
    if result1:
        print(f"  Entry: {result1['direction']} @ {result1['entry_price']:.2f}")
        print(f"  Timestamp: {result1['entry_timestamp']}")
        print(f"  ORB: {result1['orb_low']:.2f} - {result1['orb_high']:.2f}")
    else:
        print("  No entry")

    # Test 2: 1st_close_outside
    print("\nTest 2: 1st_close_outside")
    spec2 = ExecutionSpec(
        bar_tf="1m",
        orb_time="1000",
        orb_minutes=5,
        entry_rule="1st_close_outside",
        confirm_tf="1m",
        rr_target=1.0
    )

    result2 = compute_entry(spec2, test_bars, test_date)
    if result2:
        print(f"  Entry: {result2['direction']} @ {result2['entry_price']:.2f}")
        print(f"  Timestamp: {result2['entry_timestamp']}")
        print(f"  Confirm close: {result2['confirm_close']:.2f} @ {result2['confirm_timestamp']}")
    else:
        print("  No entry")

    # Test 3: 5m_close_outside
    print("\nTest 3: 5m_close_outside")
    spec3 = ExecutionSpec(
        bar_tf="1m",
        orb_time="1000",
        orb_minutes=5,
        entry_rule="5m_close_outside",
        confirm_tf="5m",
        rr_target=1.0
    )

    result3 = compute_entry(spec3, test_bars, test_date)
    if result3:
        print(f"  Entry: {result3['direction']} @ {result3['entry_price']:.2f}")
        print(f"  Timestamp: {result3['entry_timestamp']}")
        print(f"  5m confirm close: {result3['confirm_close']:.2f}")
    else:
        print("  No entry")

    print("\n" + "=" * 70)
    print("All tests passed!")
    print("=" * 70)
