"""
Filter Library - Reusable filter definitions

Store commonly-used filters here so you can reference them in:
- filter_optimizer.py (systematic testing)
- market_scanner.py (real-time validation)
- populate_validated_setups.py (database updates)

USAGE:
    from filter_library import FILTERS

    # Apply trending market filter:
    if FILTERS['trending_market'](session_data):
        # Take the trade
        pass
"""

# Filter definitions (query strings for pandas)
FILTER_QUERIES = {
    # ORB size filters
    'orb_size_small': 'orb_size >= 0.05',
    'orb_size_medium': 'orb_size >= 0.10',
    'orb_size_large': 'orb_size >= 0.15',

    # Asia session filters
    'asia_trending': 'asia_travel > 2.0',
    'asia_quiet': 'asia_travel < 1.0',
    'asia_expanded': "asia_type == 'EXPANDED'",
    'asia_tight': "asia_type == 'TIGHT'",

    # London session filters
    'london_sweep_high': "london_type == 'SWEEP_HIGH'",
    'london_sweep_low': "london_type == 'SWEEP_LOW'",
    'london_expansion': "london_type == 'EXPANSION'",
    'london_consolidation': "london_type == 'CONSOLIDATION'",

    # Momentum filters
    'rsi_oversold': 'rsi < 30',
    'rsi_overbought': 'rsi > 70',

    # Volatility filters
    'high_volatility': 'orb_size > (atr * 1.5)',
    'low_volatility': 'orb_size < (atr * 0.5)',

    # Day of week filters
    'exclude_monday': "day_of_week != 'Monday'",
    'exclude_friday': "day_of_week != 'Friday'",

    # Combination filters (proven winners from optimization)
    'quality_setup': 'orb_size >= 0.10 and asia_travel > 1.5',
    'trending_market': 'asia_travel > 2.0 and london_range > 1.5',
    'range_bound': 'asia_travel < 1.5 and london_range < 1.0',
}

# Filter metadata (descriptions, parameters, confidence levels)
FILTER_METADATA = {
    'quality_setup': {
        'description': 'ORB >= 0.10 AND Asia travel > 1.5',
        'tested_on': ['0900', '1000', '1100'],
        'performance': {
            '0900': {'train_wr': 68, 'test_wr': 66, 'validated': True, 'confidence': 'HIGH'},
            '1000': {'train_wr': 62, 'test_wr': 60, 'validated': True, 'confidence': 'MEDIUM'},
        },
        'notes': 'Consistently improves WR by 8-10% across multiple ORBs'
    },
    'trending_market': {
        'description': 'Asia travel > 2.0 AND London range > 1.5',
        'tested_on': ['0900', '1000'],
        'performance': {
            '0900': {'train_wr': 72, 'test_wr': 68, 'validated': True, 'confidence': 'HIGH'},
        },
        'notes': 'Works best in trending regimes, may overfit in range-bound markets'
    },
}


def get_filter_query(filter_name: str) -> str:
    """Get pandas query string for a filter"""
    return FILTER_QUERIES.get(filter_name, "")


def get_filter_metadata(filter_name: str) -> dict:
    """Get metadata for a filter (performance, notes, etc.)"""
    return FILTER_METADATA.get(filter_name, {})


def list_all_filters():
    """Print all available filters"""
    print("\n" + "="*70)
    print("AVAILABLE FILTERS")
    print("="*70 + "\n")

    for name, query in FILTER_QUERIES.items():
        print(f"{name}:")
        print(f"  Query: {query}")

        metadata = FILTER_METADATA.get(name)
        if metadata:
            print(f"  Description: {metadata['description']}")
            print(f"  Tested on: {', '.join(metadata['tested_on'])}")
            if 'notes' in metadata:
                print(f"  Notes: {metadata['notes']}")
        print()


if __name__ == "__main__":
    list_all_filters()
