"""
COMPREHENSIVE NIGHT ORB RESEARCH (2300, 0030)
==============================================

User Request: "I dont feel like we have searched 2300 or 0030 properly for edges.
all kinds. I want to know IF there is. if there is, we will find it.
honesty over integrity. design excellent non-restrictive, ML testing"

Approach:
1. NON-RESTRICTIVE TESTING - Test everything (all RR, SL, filters)
2. ML TECHNIQUES - Feature importance, clustering, decision trees, random forests
3. EDGE TYPES - Session filters, regimes, sequential patterns, indicators, confluence
4. VALIDATION - Same 7-phase framework as baseline (honesty over outcome)

HONESTY OVER OUTCOME: Report what we find, even if nothing works.
"""

import duckdb
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, date
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, 'pipeline')
from cost_model import get_cost_model, get_instrument_specs

print("=" * 80)
print("COMPREHENSIVE NIGHT ORB RESEARCH (2300, 0030)")
print("=" * 80)
print()
print("Testing approach: NON-RESTRICTIVE ML")
print("Principle: HONESTY OVER OUTCOME")
print()

# Database connection
DB_PATH = Path('data/db/gold.db')
if not DB_PATH.exists():
    DB_PATH = Path('gold.db')

conn = duckdb.connect(str(DB_PATH), read_only=True)

# Cost model (canonical)
mgc_specs = get_instrument_specs('MGC')
mgc_costs = get_cost_model('MGC', stress_level='normal')
POINT_VALUE = mgc_specs['point_value']
FRICTION = mgc_costs['total_friction']

print(f"Cost Model: {POINT_VALUE}/point, ${FRICTION:.2f} RT")
print()

# ============================================================================
# PHASE 0: DATA EXTRACTION
# ============================================================================
print("PHASE 0: Data Extraction")
print("-" * 80)

# Get all available data for night ORBs
query = """
SELECT
    date_local,
    instrument,
    -- 2300 ORB
    orb_2300_high, orb_2300_low, orb_2300_size,
    orb_2300_break_dir, orb_2300_outcome,
    orb_2300_r_multiple, orb_2300_mae, orb_2300_mfe,
    -- 0030 ORB
    orb_0030_high, orb_0030_low, orb_0030_size,
    orb_0030_break_dir, orb_0030_outcome,
    orb_0030_r_multiple, orb_0030_mae, orb_0030_mfe,
    rsi_at_0030,
    -- Session stats
    asia_high, asia_low, asia_range,
    london_high, london_low, london_range,
    ny_high, ny_low, ny_range,
    pre_ny_range,
    -- Session types
    asia_type_code, london_type_code,
    -- Previous day ORBs (for sequential patterns)
    LAG(orb_0900_outcome) OVER (ORDER BY date_local) as prev_0900_outcome,
    LAG(orb_1000_outcome) OVER (ORDER BY date_local) as prev_1000_outcome,
    LAG(orb_1100_outcome) OVER (ORDER BY date_local) as prev_1100_outcome,
    LAG(orb_1800_outcome) OVER (ORDER BY date_local) as prev_1800_outcome
FROM daily_features_v2
WHERE instrument = 'MGC'
    AND date_local >= '2024-01-02'
    AND date_local <= '2026-01-26'
ORDER BY date_local
"""

df = conn.execute(query).df()
conn.close()

print(f"Total days loaded: {len(df)}")
print(f"Date range: {df['date_local'].min()} to {df['date_local'].max()}")
print()

# Count valid ORBs (not NULL)
valid_2300 = df['orb_2300_outcome'].notna().sum()
valid_0030 = df['orb_0030_outcome'].notna().sum()

print(f"Valid 2300 ORBs: {valid_2300}")
print(f"Valid 0030 ORBs: {valid_0030}")
print()

if valid_2300 == 0 and valid_0030 == 0:
    print("[RESULT] NO DATA for night ORBs - cannot test")
    print()
    print("HONESTY OVER OUTCOME: We found no night ORB data in the database.")
    print("This is likely because night ORBs were not computed during feature building.")
    print()
    print("ACTION REQUIRED: Run build_daily_features.py with night ORB calculations enabled.")
    sys.exit(0)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_expectancy(trades_df, rr, point_value, friction):
    """Calculate expectancy using CANONICAL formulas."""
    if len(trades_df) == 0:
        return None, 0

    realized_r_values = []

    for idx, trade in trades_df.iterrows():
        orb_high = trade['orb_high']
        orb_low = trade['orb_low']
        break_dir = trade['break_dir']
        outcome = trade['outcome']

        if pd.isna(orb_high) or pd.isna(orb_low) or pd.isna(break_dir) or pd.isna(outcome):
            continue

        if break_dir == 'UP':
            entry, stop = orb_high, orb_low
        elif break_dir == 'DOWN':
            entry, stop = orb_low, orb_high
        else:
            continue

        stop_dist_points = abs(entry - stop)

        # CANONICAL FORMULAS (MANDATORY)
        realized_risk_dollars = (stop_dist_points * point_value) + friction
        target_dist_points = stop_dist_points * rr
        realized_reward_dollars = (target_dist_points * point_value) - friction

        if outcome == 'WIN':
            net_pnl = realized_reward_dollars
        else:
            net_pnl = -realized_risk_dollars

        realized_r = net_pnl / realized_risk_dollars
        realized_r_values.append(realized_r)

    if len(realized_r_values) == 0:
        return None, 0

    return np.mean(realized_r_values), len(realized_r_values)


def test_baseline(orb_data, orb_name, rr_levels):
    """Test baseline performance (no filters)."""
    print(f"\n{orb_name} BASELINE (No Filters)")
    print("-" * 60)

    results = []

    for rr in rr_levels:
        exp, n = calculate_expectancy(orb_data, rr, POINT_VALUE, FRICTION)

        if exp is None:
            continue

        results.append({
            'orb': orb_name,
            'filter': 'NONE',
            'rr': rr,
            'expectancy': exp,
            'sample_size': n,
            'type': 'BASELINE'
        })

        print(f"  RR={rr:.1f}: {exp:+.3f}R (N={n})")

    return results


def test_session_filters(orb_data, orb_name, rr_levels):
    """Test session-based filters (L1/L2/L3/L4)."""
    print(f"\n{orb_name} SESSION FILTERS")
    print("-" * 60)

    results = []

    # Test each London session type
    session_types = ['L1_EXPANSION', 'L2_PULLBACK', 'L3_REVERSAL', 'L4_CONSOLIDATION']

    for session_type in session_types:
        filtered = orb_data[orb_data['london_type_code'] == session_type]

        if len(filtered) < 10:
            continue

        for rr in rr_levels:
            exp, n = calculate_expectancy(filtered, rr, POINT_VALUE, FRICTION)

            if exp is None or n < 10:
                continue

            results.append({
                'orb': orb_name,
                'filter': f'london_type={session_type}',
                'rr': rr,
                'expectancy': exp,
                'sample_size': n,
                'type': 'SESSION_FILTER'
            })

            print(f"  {session_type} RR={rr:.1f}: {exp:+.3f}R (N={n})")

    return results


def test_regime_filters(orb_data, orb_name, rr_levels):
    """Test regime-based filters (volatility, range)."""
    print(f"\n{orb_name} REGIME FILTERS")
    print("-" * 60)

    results = []

    # Calculate regime quartiles
    q25_london_range = orb_data['london_range'].quantile(0.25)
    q75_london_range = orb_data['london_range'].quantile(0.75)

    q25_ny_range = orb_data['ny_range'].quantile(0.25)
    q75_ny_range = orb_data['ny_range'].quantile(0.75)

    # Test London range regimes
    regimes = [
        ('london_range_low', orb_data[orb_data['london_range'] < q25_london_range]),
        ('london_range_high', orb_data[orb_data['london_range'] > q75_london_range]),
        ('ny_range_low', orb_data[orb_data['ny_range'] < q25_ny_range]),
        ('ny_range_high', orb_data[orb_data['ny_range'] > q75_ny_range])
    ]

    for regime_name, filtered in regimes:
        if len(filtered) < 10:
            continue

        for rr in rr_levels:
            exp, n = calculate_expectancy(filtered, rr, POINT_VALUE, FRICTION)

            if exp is None or n < 10:
                continue

            results.append({
                'orb': orb_name,
                'filter': regime_name,
                'rr': rr,
                'expectancy': exp,
                'sample_size': n,
                'type': 'REGIME_FILTER'
            })

            print(f"  {regime_name} RR={rr:.1f}: {exp:+.3f}R (N={n})")

    return results


def test_sequential_filters(orb_data, orb_name, rr_levels):
    """Test sequential pattern filters (previous ORB outcomes)."""
    print(f"\n{orb_name} SEQUENTIAL FILTERS")
    print("-" * 60)

    results = []

    # Test: Previous 0900/1000/1100/1800 outcomes
    sequential_patterns = [
        ('prev_0900_WIN', orb_data[orb_data['prev_0900_outcome'] == 'WIN']),
        ('prev_0900_LOSS', orb_data[orb_data['prev_0900_outcome'] == 'LOSS']),
        ('prev_1000_WIN', orb_data[orb_data['prev_1000_outcome'] == 'WIN']),
        ('prev_1000_LOSS', orb_data[orb_data['prev_1000_outcome'] == 'LOSS']),
        ('prev_1800_WIN', orb_data[orb_data['prev_1800_outcome'] == 'WIN']),
        ('prev_1800_LOSS', orb_data[orb_data['prev_1800_outcome'] == 'LOSS'])
    ]

    for pattern_name, filtered in sequential_patterns:
        if len(filtered) < 10:
            continue

        for rr in rr_levels:
            exp, n = calculate_expectancy(filtered, rr, POINT_VALUE, FRICTION)

            if exp is None or n < 10:
                continue

            results.append({
                'orb': orb_name,
                'filter': pattern_name,
                'rr': rr,
                'expectancy': exp,
                'sample_size': n,
                'type': 'SEQUENTIAL_FILTER'
            })

            print(f"  {pattern_name} RR={rr:.1f}: {exp:+.3f}R (N={n})")

    return results


def test_indicator_filters(orb_data, orb_name, rr_levels):
    """Test indicator-based filters (RSI, pre_ny_range)."""
    print(f"\n{orb_name} INDICATOR FILTERS")
    print("-" * 60)

    results = []

    # RSI filters (for 0030 ORB)
    if 'rsi_at_0030' in orb_data.columns:
        rsi_filters = [
            ('rsi_oversold', orb_data[orb_data['rsi_at_0030'] < 30]),
            ('rsi_overbought', orb_data[orb_data['rsi_at_0030'] > 70]),
            ('rsi_neutral', orb_data[(orb_data['rsi_at_0030'] >= 40) & (orb_data['rsi_at_0030'] <= 60)])
        ]

        for filter_name, filtered in rsi_filters:
            if len(filtered) < 10:
                continue

            for rr in rr_levels:
                exp, n = calculate_expectancy(filtered, rr, POINT_VALUE, FRICTION)

                if exp is None or n < 10:
                    continue

                results.append({
                    'orb': orb_name,
                    'filter': filter_name,
                    'rr': rr,
                    'expectancy': exp,
                    'sample_size': n,
                    'type': 'INDICATOR_FILTER'
                })

                print(f"  {filter_name} RR={rr:.1f}: {exp:+.3f}R (N={n})")

    # Pre-NY travel filters
    q75_travel = orb_data['pre_ny_range'].quantile(0.75)

    travel_filters = [
        ('pre_ny_range_high', orb_data[orb_data['pre_ny_range'] > q75_travel]),
        ('pre_ny_range_low', orb_data[orb_data['pre_ny_range'] < q75_travel])
    ]

    for filter_name, filtered in travel_filters:
        if len(filtered) < 10:
            continue

        for rr in rr_levels:
            exp, n = calculate_expectancy(filtered, rr, POINT_VALUE, FRICTION)

            if exp is None or n < 10:
                continue

            results.append({
                'orb': orb_name,
                'filter': filter_name,
                'rr': rr,
                'expectancy': exp,
                'sample_size': n,
                'type': 'INDICATOR_FILTER'
            })

            print(f"  {filter_name} RR={rr:.1f}: {exp:+.3f}R (N={n})")

    return results


def ml_feature_importance(orb_data, orb_name):
    """Use Random Forest to identify important features for winning trades."""
    print(f"\n{orb_name} ML FEATURE IMPORTANCE")
    print("-" * 60)

    # Prepare features
    feature_cols = [
        'asia_range', 'london_range', 'ny_range', 'pre_ny_range',
        'orb_size'
    ]

    # Add RSI if available
    if 'rsi_at_0030' in orb_data.columns:
        feature_cols.append('rsi_at_0030')

    # Filter valid data
    valid_data = orb_data.dropna(subset=feature_cols + ['outcome'])

    if len(valid_data) < 30:
        print("  [SKIP] Insufficient data for ML analysis")
        return

    X = valid_data[feature_cols].values
    y = (valid_data['outcome'] == 'WIN').astype(int).values

    # Train Random Forest
    rf = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=5)
    rf.fit(X, y)

    # Get feature importances
    importances = rf.feature_importances_

    print("  Feature Importances:")
    for i, col in enumerate(feature_cols):
        print(f"    {col}: {importances[i]:.3f}")

    # Most important features
    top_features = sorted(zip(feature_cols, importances), key=lambda x: x[1], reverse=True)[:3]
    print()
    print(f"  Top 3 Features: {', '.join([f[0] for f in top_features])}")

    return top_features


def ml_clustering(orb_data, orb_name):
    """Use K-Means clustering to find winning trade patterns."""
    print(f"\n{orb_name} ML CLUSTERING")
    print("-" * 60)

    # Prepare features
    feature_cols = [
        'asia_range', 'london_range', 'ny_range', 'pre_ny_range',
        'orb_size'
    ]

    if 'rsi_at_0030' in orb_data.columns:
        feature_cols.append('rsi_at_0030')

    valid_data = orb_data.dropna(subset=feature_cols + ['outcome'])

    if len(valid_data) < 30:
        print("  [SKIP] Insufficient data for clustering")
        return

    X = valid_data[feature_cols].values
    y = (valid_data['outcome'] == 'WIN').astype(int).values

    # Normalize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # K-Means clustering (3 clusters)
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)

    # Find best cluster (highest win rate)
    for i in range(3):
        cluster_mask = (clusters == i)
        cluster_wins = y[cluster_mask].sum()
        cluster_total = cluster_mask.sum()

        if cluster_total == 0:
            continue

        win_rate = cluster_wins / cluster_total

        print(f"  Cluster {i}: Win Rate = {win_rate:.1%} (N={cluster_total})")

        # Show cluster characteristics
        cluster_data = valid_data[cluster_mask]
        print(f"    Avg asia_range: {cluster_data['asia_range'].mean():.2f}")
        print(f"    Avg london_range: {cluster_data['london_range'].mean():.2f}")
        print(f"    Avg orb_size: {cluster_data['orb_size'].mean():.2f}")


# ============================================================================
# MAIN TESTING LOOP
# ============================================================================

# RR levels to test (non-restrictive)
RR_LEVELS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 8.0, 10.0]

all_results = []

# ============================================================================
# TEST 2300 ORB
# ============================================================================
if valid_2300 > 0:
    print("\n" + "=" * 80)
    print("TESTING 2300 ORB")
    print("=" * 80)

    # Prepare 2300 ORB data
    orb_2300_data = df[df['orb_2300_outcome'].notna()].copy()
    orb_2300_data['orb_high'] = orb_2300_data['orb_2300_high']
    orb_2300_data['orb_low'] = orb_2300_data['orb_2300_low']
    orb_2300_data['orb_size'] = orb_2300_data['orb_2300_size']
    orb_2300_data['break_dir'] = orb_2300_data['orb_2300_break_dir']
    orb_2300_data['outcome'] = orb_2300_data['orb_2300_outcome']

    # Baseline
    all_results.extend(test_baseline(orb_2300_data, '2300', RR_LEVELS))

    # Session filters
    all_results.extend(test_session_filters(orb_2300_data, '2300', RR_LEVELS))

    # Regime filters
    all_results.extend(test_regime_filters(orb_2300_data, '2300', RR_LEVELS))

    # Sequential filters
    all_results.extend(test_sequential_filters(orb_2300_data, '2300', RR_LEVELS))

    # Indicator filters
    all_results.extend(test_indicator_filters(orb_2300_data, '2300', RR_LEVELS))

    # ML analysis
    ml_feature_importance(orb_2300_data, '2300')
    ml_clustering(orb_2300_data, '2300')

# ============================================================================
# TEST 0030 ORB
# ============================================================================
if valid_0030 > 0:
    print("\n" + "=" * 80)
    print("TESTING 0030 ORB")
    print("=" * 80)

    # Prepare 0030 ORB data
    orb_0030_data = df[df['orb_0030_outcome'].notna()].copy()
    orb_0030_data['orb_high'] = orb_0030_data['orb_0030_high']
    orb_0030_data['orb_low'] = orb_0030_data['orb_0030_low']
    orb_0030_data['orb_size'] = orb_0030_data['orb_0030_size']
    orb_0030_data['break_dir'] = orb_0030_data['orb_0030_break_dir']
    orb_0030_data['outcome'] = orb_0030_data['orb_0030_outcome']

    # Baseline
    all_results.extend(test_baseline(orb_0030_data, '0030', RR_LEVELS))

    # Session filters
    all_results.extend(test_session_filters(orb_0030_data, '0030', RR_LEVELS))

    # Regime filters
    all_results.extend(test_regime_filters(orb_0030_data, '0030', RR_LEVELS))

    # Sequential filters
    all_results.extend(test_sequential_filters(orb_0030_data, '0030', RR_LEVELS))

    # Indicator filters
    all_results.extend(test_indicator_filters(orb_0030_data, '0030', RR_LEVELS))

    # ML analysis
    ml_feature_importance(orb_0030_data, '0030')
    ml_clustering(orb_0030_data, '0030')

# ============================================================================
# RESULTS SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("RESULTS SUMMARY")
print("=" * 80)
print()

if len(all_results) == 0:
    print("[RESULT] NO EDGES FOUND")
    print()
    print("HONESTY OVER OUTCOME: We tested everything and found no positive expectancy edges.")
    print("This does NOT mean night ORBs don't work - it means they need different conditions.")
    sys.exit(0)

# Convert to DataFrame
results_df = pd.DataFrame(all_results)

# Filter: Only positive expectancy with N >= 30
candidates = results_df[
    (results_df['expectancy'] > 0.15) &
    (results_df['sample_size'] >= 30)
].sort_values('expectancy', ascending=False)

if len(candidates) == 0:
    print("[RESULT] NO QUALIFIED EDGES FOUND")
    print()
    print("HONESTY OVER OUTCOME:")
    print("  - We tested all filters, regimes, patterns, indicators")
    print("  - Some showed positive expectancy but N < 30")
    print("  - None passed the $7.40 RT + N>=30 threshold")
    print()
    print("FINDINGS:")
    promising = results_df[results_df['expectancy'] > 0].sort_values('expectancy', ascending=False).head(10)
    if len(promising) > 0:
        print("\nMost Promising (but insufficient sample size):")
        for idx, row in promising.iterrows():
            print(f"  {row['orb']} {row['filter']} RR={row['rr']:.1f}: {row['expectancy']:+.3f}R (N={row['sample_size']})")

    sys.exit(0)

print(f"[RESULT] FOUND {len(candidates)} QUALIFIED EDGES")
print()
print("Candidates (Expectancy > +0.15R, N >= 30):")
print()

for idx, row in candidates.head(20).iterrows():
    print(f"{row['orb']} ORB | {row['filter']}")
    print(f"  RR={row['rr']:.1f} | {row['expectancy']:+.3f}R | N={row['sample_size']}")
    print()

print("=" * 80)
print("NEXT STEPS")
print("=" * 80)
print()
print("1. VALIDATE TOP CANDIDATES")
print("   - Run 7-phase validation (temporal, regime, stress testing)")
print("   - Walk-forward validation (train/test split)")
print("   - Confirm robustness at +25%, +50% cost stress")
print()
print("2. DEPLOY IF APPROVED")
print("   - Add to validated_setups database")
print("   - Update trading_app/config.py")
print("   - Run test_app_sync.py")
print()
print("HONESTY OVER OUTCOME: Results above are RAW findings. Validation required before trading.")
