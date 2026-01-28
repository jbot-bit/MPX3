"""
Walk-Forward Validation Configuration

Defines train/validation/test splits and rolling window configurations
for robust out-of-sample testing.

CRITICAL: These splits prevent curve-fitting by ensuring:
1. Concept tested on held-out validation data FIRST
2. Parameters optimized on training data ONLY
3. Final verification on test data NEVER seen before
"""

from datetime import datetime, timedelta
from typing import List, Tuple, Dict
import duckdb


# ============================================================================
# Data Split Strategy
# ============================================================================

def get_simple_split(con: duckdb.DuckDBPyConnection, instrument: str = 'MGC') -> Dict[str, List[str]]:
    """
    Simple 3-way split: 60% train, 20% validation, 20% test

    Returns:
        {
            'train': [dates...],      # 60% - optimize parameters here
            'validation': [dates...], # 20% - test concept here FIRST
            'test': [dates...]        # 20% - final verification (unseen)
        }
    """
    query = f"""
    SELECT DISTINCT date_local
    FROM daily_features
    WHERE instrument = '{instrument}'
    ORDER BY date_local
    """

    dates = [row[0] for row in con.execute(query).fetchall()]

    n = len(dates)
    train_end = int(n * 0.60)
    valid_end = int(n * 0.80)

    return {
        'train': dates[:train_end],
        'validation': dates[train_end:valid_end],
        'test': dates[valid_end:]
    }


def get_rolling_windows(
    con: duckdb.DuckDBPyConnection,
    instrument: str = 'MGC',
    n_windows: int = 4
) -> List[Dict[str, List[str]]]:
    """
    Rolling window walk-forward splits

    Returns list of windows, each with train/validation/test splits:
    [
        {
            'train': ['2020-01-01', ...],
            'validation': ['2023-01-01', ...],
            'test': ['2023-07-01', ...]
        },
        ...
    ]

    Standard in quantitative finance - tests edge across multiple time periods.
    Edge must pass 50%+ of windows to be promoted.
    """
    query = f"""
    SELECT DISTINCT date_local
    FROM daily_features
    WHERE instrument = '{instrument}'
    ORDER BY date_local
    """

    dates = [row[0] for row in con.execute(query).fetchall()]

    if len(dates) < 365 * 2:  # Need at least 2 years
        raise ValueError(f"Insufficient data for rolling windows: {len(dates)} days < 730")

    windows = []

    # Create overlapping windows that grow over time
    # Each window: 60% train, 20% validation, 20% test
    window_size = len(dates) // n_windows

    for i in range(n_windows):
        start_idx = 0  # Always start from beginning (growing window)
        end_idx = min(len(dates), (i + 1) * window_size + window_size)

        window_dates = dates[start_idx:end_idx]

        n = len(window_dates)
        train_end = int(n * 0.60)
        valid_end = int(n * 0.80)

        windows.append({
            'train': window_dates[:train_end],
            'validation': window_dates[train_end:valid_end],
            'test': window_dates[valid_end:],
            'period': f"{window_dates[0]} to {window_dates[-1]}"
        })

    return windows


# ============================================================================
# Strategy Family Filtering (CRITICAL)
# ============================================================================

def filter_by_strategy_family(
    con: duckdb.DuckDBPyConnection,
    dates: List[str],
    orb_time: str,
    instrument: str = 'MGC'
) -> List[str]:
    """
    Filter dates to match strategy family rules

    CRITICAL: Walk-forward MUST respect strategy families:
    - ORB_L4 (0900, 1000) → L4_CONSOLIDATION filter only
    - ORB_BOTH_LOST (1100) → BOTH_LOST filter only
    - ORB_RSI (1800) → RSI filter only
    - ORB_NIGHT (2300, 0030) → RESEARCH ONLY

    This prevents cross-family contamination during validation.

    NOTE: If strategy family columns don't exist in database yet,
    this returns all dates (graceful fallback).
    """
    if len(dates) == 0:
        return []

    if orb_time in ['2300', '0030']:
        # ORB_NIGHT family - RESEARCH ONLY
        raise ValueError(f"ORB {orb_time} is RESEARCH ONLY (ORB_NIGHT family)")

    # Check if strategy family columns exist
    columns = [row[0] for row in con.execute("DESCRIBE daily_features").fetchall()]

    # Determine filter column
    if orb_time in ['0900', '1000']:
        filter_col = 'l4_consolidation'
    elif orb_time == '1100':
        filter_col = 'both_lost'
    elif orb_time == '1800':
        filter_col = 'rsi_at_0030'  # RSI column that exists
    else:
        raise ValueError(f"Unknown ORB time: {orb_time}")

    # If filter column doesn't exist, return all dates (graceful fallback)
    if filter_col not in columns:
        print(f"  WARNING: Strategy family column '{filter_col}' not found in database")
        print(f"  Falling back to all dates (no family filtering)")
        return dates

    # Filter dates where family condition exists
    date_str = "', '".join(dates)

    if orb_time in ['0900', '1000']:
        query = f"""
        SELECT date_local
        FROM daily_features
        WHERE instrument = '{instrument}'
          AND date_local IN ('{date_str}')
          AND {filter_col} = 1
        ORDER BY date_local
        """
    elif orb_time == '1100':
        query = f"""
        SELECT date_local
        FROM daily_features
        WHERE instrument = '{instrument}'
          AND date_local IN ('{date_str}')
          AND {filter_col} = 1
        ORDER BY date_local
        """
    elif orb_time == '1800':
        query = f"""
        SELECT date_local
        FROM daily_features
        WHERE instrument = '{instrument}'
          AND date_local IN ('{date_str}')
          AND {filter_col} IS NOT NULL
        ORDER BY date_local
        """

    try:
        filtered = [row[0] for row in con.execute(query).fetchall()]
        return filtered
    except Exception as e:
        print(f"  WARNING: Strategy family filtering failed: {e}")
        print(f"  Falling back to all dates (no family filtering)")
        return dates


# ============================================================================
# Search Space Definitions
# ============================================================================

def get_search_space(orb_time: str) -> Dict:
    """
    Define parameter search space for optimization

    Returns:
        {
            'rr_values': [1.5, 2.0, ...],
            'filters': [None, 0.05, ...],
            'sl_modes': ['full', 'half']
        }
    """
    # Standard search space for all ORBs
    return {
        'rr_values': [1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
        'filters': [None, 0.05, 0.10, 0.112, 0.15, 0.20, 0.25, 0.30],
        'sl_modes': ['full', 'half']
    }


# ============================================================================
# Validation Thresholds
# ============================================================================

THRESHOLDS = {
    'stage_1_concept': {
        'min_expr': 0.10,  # Concept must be profitable on validation data
        'min_sample': 20,   # Minimum trades to trust result
        'min_wr': 0.10     # At least 10% win rate
    },
    'stage_2_optimization': {
        'min_expr': 0.15,  # Training result threshold
        'min_sample': 30   # Minimum training sample
    },
    'stage_3_out_of_sample': {
        'min_expr': 0.15,          # Test result threshold
        'max_degradation': 0.50,   # Max 50% drop from train
        'min_sample': 30           # Minimum test sample
    },
    'stage_4_stress': {
        'stress_25_min': 0.15,  # Must survive +25% costs
        'stress_50_min': 0.15,  # Preferred: survive +50%
        'stress_100_min': 0.00  # Still positive at +100%
    },
    'stage_5_monte_carlo': {
        'p_value_max': 0.05,  # Must be statistically significant
        'n_simulations': 10000
    },
    'stage_6_regime': {
        'min_expr_per_regime': 0.00,  # Positive in all regimes
        'min_sample_per_regime': 10
    },
    'stage_7_walkforward': {
        'min_pass_rate': 0.50,  # Pass 50%+ of windows
        'min_avg_expr': 0.15
    },
    'stage_8_statistical': {
        'min_sample': 30,
        'p_value_max': 0.05,
        'ci_must_exclude_zero': True
    }
}


# ============================================================================
# Cost Model Parameters
# ============================================================================

COST_MODELS = {
    'MGC': {
        'base_friction': 8.40,  # Honest double-spread accounting
        'stress_25': 10.50,     # +25%
        'stress_50': 12.60,     # +50%
        'stress_100': 16.80     # +100%
    },
    'NQ': {
        'base_friction': 8.40,  # TODO: Update with NQ actual costs
        'stress_25': 10.50,
        'stress_50': 12.60,
        'stress_100': 16.80
    },
    'MPL': {
        'base_friction': 4.20,  # TODO: Update with MPL actual costs
        'stress_25': 5.25,
        'stress_50': 6.30,
        'stress_100': 8.40
    }
}


# ============================================================================
# Reporting
# ============================================================================

def print_split_summary(splits: Dict[str, List[str]], title: str = "Data Split"):
    """Print summary of train/validation/test split"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")

    for split_name, dates in splits.items():
        if len(dates) > 0:
            print(f"{split_name.upper():12} | {len(dates):4} days | {dates[0]} to {dates[-1]}")
        else:
            print(f"{split_name.upper():12} | {len(dates):4} days | (empty)")

    print(f"{'='*60}\n")


def print_rolling_summary(windows: List[Dict]):
    """Print summary of rolling window configuration"""
    print(f"\n{'='*60}")
    print("Rolling Window Walk-Forward Configuration")
    print(f"{'='*60}")

    for i, window in enumerate(windows, 1):
        print(f"\nWindow {i}: {window['period']}")
        print(f"  Train:      {len(window['train']):4} days")
        print(f"  Validation: {len(window['validation']):4} days")
        print(f"  Test:       {len(window['test']):4} days")

    print(f"{'='*60}\n")


if __name__ == '__main__':
    """Test configuration"""
    import sys
    sys.path.append('.')

    con = duckdb.connect('gold.db')

    print("\n" + "="*60)
    print("WALK-FORWARD CONFIGURATION TEST")
    print("="*60)

    # Test simple split
    splits = get_simple_split(con, 'MGC')
    print_split_summary(splits, "Simple 60/20/20 Split")

    # Test rolling windows
    try:
        windows = get_rolling_windows(con, 'MGC', n_windows=4)
        print_rolling_summary(windows)
    except ValueError as e:
        print(f"\nRolling windows: {e}")

    # Test strategy family filtering
    print("\nTesting Strategy Family Filtering:")
    print("-" * 60)

    for orb_time in ['0900', '1000', '1100', '1800']:
        filtered = filter_by_strategy_family(con, splits['train'][:100], orb_time, 'MGC')
        print(f"ORB {orb_time}: {len(filtered):3} / 100 dates pass family filter")

    con.close()

    print("\n[OK] Configuration test complete")
