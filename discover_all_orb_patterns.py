"""
ML Pattern Discovery - ALL 6 ORBs

Analyze session patterns against ALL ORB times:
- 0900, 1000, 1100 (Asia ORBs)
- 1800 (London ORB)
- 2300, 0030 (NY ORBs)

Use ML to find what ACTUALLY correlates!
"""

import duckdb
import pandas as pd
import numpy as np
from scipy import stats
from scipy.stats import pearsonr
from sklearn.ensemble import RandomForestRegressor
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = "gold.db"
INSTRUMENT = "MGC"
CUTOFF_DATE = "2026-01-12"

ORB_TIMES = ['0900', '1000', '1100', '1800', '2300', '0030']

# ============================================================================
# DATA LOADING
# ============================================================================

def load_all_orb_data():
    """Load ALL 6 ORBs with session context."""

    conn = duckdb.connect(DB_PATH, read_only=True)

    query = f"""
    SELECT
        date_local,

        -- Session ranges
        asia_range,
        london_range,
        ny_range,
        pre_asia_range,
        pre_london_range,
        pre_ny_range,

        -- Session highs/lows
        asia_high,
        asia_low,
        london_high,
        london_low,
        ny_high,
        ny_low,

        -- ALL 6 ORB outcomes
        orb_0900_outcome,
        orb_0900_r_multiple,
        orb_0900_size,

        orb_1000_outcome,
        orb_1000_r_multiple,
        orb_1000_size,

        orb_1100_outcome,
        orb_1100_r_multiple,
        orb_1100_size,

        orb_1800_outcome,
        orb_1800_r_multiple,
        orb_1800_size,

        orb_2300_outcome,
        orb_2300_r_multiple,
        orb_2300_size,

        orb_0030_outcome,
        orb_0030_r_multiple,
        orb_0030_size,

        -- ATR
        atr_20

    FROM daily_features
    WHERE instrument = '{INSTRUMENT}'
      AND date_local <= '{CUTOFF_DATE}'
      AND asia_range IS NOT NULL
      AND london_range IS NOT NULL
      AND ny_range IS NOT NULL
      AND atr_20 IS NOT NULL
    ORDER BY date_local
    """

    df = conn.execute(query).fetchdf()
    conn.close()

    # Compute derived features (same as before)
    df['prev_asia_range'] = df['asia_range'].shift(1)
    df['prev_london_range'] = df['london_range'].shift(1)
    df['prev_ny_range'] = df['ny_range'].shift(1)
    df['prev_ny_high'] = df['ny_high'].shift(1)
    df['prev_ny_low'] = df['ny_low'].shift(1)

    df['asia_london_ratio'] = df['asia_range'] / (df['london_range'] + 0.01)
    df['london_ny_ratio'] = df['london_range'] / (df['ny_range'] + 0.01)
    df['asia_range_atr'] = df['asia_range'] / df['atr_20']
    df['london_range_atr'] = df['london_range'] / df['atr_20']
    df['ny_range_atr'] = df['ny_range'] / df['atr_20']
    df['prev_asia_range_atr'] = df['prev_asia_range'] / df['atr_20']
    df['prev_london_range_atr'] = df['prev_london_range'] / df['atr_20']
    df['prev_ny_range_atr'] = df['prev_ny_range'] / df['atr_20']

    df['asia_expansion'] = df['asia_range'] - df['prev_asia_range']
    df['london_expansion'] = df['london_range'] - df['prev_london_range']
    df['ny_expansion'] = df['ny_range'] - df['prev_ny_range']

    df['asia_swept_prev_ny_high'] = (df['asia_high'] >= df['prev_ny_high']).astype(int)
    df['asia_swept_prev_ny_low'] = (df['asia_low'] <= df['prev_ny_low']).astype(int)
    df['london_broke_asia_high'] = (df['london_high'] > df['asia_high']).astype(int)
    df['london_broke_asia_low'] = (df['london_low'] < df['asia_low']).astype(int)

    df['daily_range_atr'] = (df['asia_range'] + df['london_range'] + df['ny_range']) / df['atr_20']

    return df.dropna()


# ============================================================================
# ANALYZE SINGLE ORB
# ============================================================================

def analyze_orb(df, orb_time):
    """Run correlation + ML analysis for a single ORB."""

    outcome_col = f'orb_{orb_time}_outcome'
    r_col = f'orb_{orb_time}_r_multiple'
    size_col = f'orb_{orb_time}_size'

    # Filter to days with this ORB
    df_orb = df[df[outcome_col].notna()].copy()

    if len(df_orb) < 100:
        return None

    # ORB size normalized
    df_orb[f'orb_{orb_time}_size_atr'] = df_orb[size_col] / df_orb['atr_20']

    # Feature list
    features = [
        'asia_range_atr', 'london_range_atr', 'ny_range_atr',
        'prev_asia_range_atr', 'prev_london_range_atr', 'prev_ny_range_atr',
        'asia_london_ratio', 'london_ny_ratio',
        'asia_expansion', 'london_expansion', 'ny_expansion',
        'asia_swept_prev_ny_high', 'asia_swept_prev_ny_low',
        'london_broke_asia_high', 'london_broke_asia_low',
        'daily_range_atr',
        f'orb_{orb_time}_size_atr'
    ]

    # Correlation analysis
    correlations = []
    for feat in features:
        if feat in df_orb.columns:
            corr, p_val = pearsonr(df_orb[feat], df_orb[r_col])
            correlations.append({
                'feature': feat,
                'correlation': corr,
                'p_value': p_val,
                'abs_corr': abs(corr)
            })

    corr_df = pd.DataFrame(correlations).sort_values('abs_corr', ascending=False)

    # Random Forest
    X = df_orb[features].values
    y = df_orb[r_col].values

    rf = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    rf.fit(X, y)

    importances = pd.DataFrame({
        'feature': features,
        'importance': rf.feature_importances_
    }).sort_values('importance', ascending=False)

    rf_score = rf.score(X, y)

    # Winners vs Losers
    winners = df_orb[df_orb[outcome_col] == 'WIN']
    losers = df_orb[df_orb[outcome_col] == 'LOSS']

    diffs = []
    for feat in features:
        if feat in df_orb.columns:
            win_mean = winners[feat].mean()
            lose_mean = losers[feat].mean()
            t_stat, p_val = stats.ttest_ind(winners[feat], losers[feat])

            if p_val < 0.05:
                diffs.append({
                    'feature': feat,
                    'winner_mean': win_mean,
                    'loser_mean': lose_mean,
                    'delta': win_mean - lose_mean,
                    'p_value': p_val
                })

    return {
        'orb_time': orb_time,
        'n_trades': len(df_orb),
        'win_rate': (df_orb[outcome_col] == 'WIN').sum() / len(df_orb),
        'avg_r': df_orb[r_col].mean(),
        'correlations': corr_df,
        'importances': importances,
        'rf_score': rf_score,
        'significant_diffs': diffs
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("\n" + "="*80)
    print("ML PATTERN DISCOVERY - ALL 6 ORBs")
    print("="*80)
    print()

    df = load_all_orb_data()
    print(f"Loaded {len(df)} complete trading days\n")

    all_results = {}

    for orb_time in ORB_TIMES:
        print("="*80)
        print(f"ORB {orb_time}")
        print("="*80)
        print()

        result = analyze_orb(df, orb_time)

        if result is None:
            print(f"Insufficient data for {orb_time} ORB")
            print()
            continue

        all_results[orb_time] = result

        print(f"Sample: {result['n_trades']} trades, {result['win_rate']*100:.1f}% WR, {result['avg_r']:+.3f}R avg")
        print()

        # Top correlations
        print("Top 5 Correlations:")
        sig_corrs = result['correlations'][result['correlations']['p_value'] < 0.05]
        if len(sig_corrs) > 0:
            for idx, row in sig_corrs.head(5).iterrows():
                print(f"  [SIG] {row['feature']:<40} r={row['correlation']:+.4f}, p={row['p_value']:.4f}")
        else:
            for idx, row in result['correlations'].head(5).iterrows():
                print(f"        {row['feature']:<40} r={row['correlation']:+.4f}, p={row['p_value']:.4f}")
        print()

        # Top feature importances
        print("Top 5 Feature Importances (Random Forest):")
        for idx, row in result['importances'].head(5).iterrows():
            bar = '#' * int(row['importance'] * 300)
            print(f"  {row['feature']:<40} {row['importance']:.4f}  {bar}")
        print(f"  R-squared: {result['rf_score']:.4f}")
        print()

        # Significant differences
        if result['significant_diffs']:
            print(f"Significant Winner/Loser Differences ({len(result['significant_diffs'])}):")
            for diff in result['significant_diffs'][:3]:
                direction = "HIGHER" if diff['delta'] > 0 else "LOWER"
                print(f"  - Winners have {direction} {diff['feature']}: {diff['delta']:+.4f} (p={diff['p_value']:.4f})")
            print()
        else:
            print("No significant winner/loser differences")
            print()

    # ========================================================================
    # CROSS-ORB SUMMARY
    # ========================================================================

    print("\n" + "="*80)
    print("CROSS-ORB SUMMARY")
    print("="*80)
    print()

    findings = []

    for orb_time, result in all_results.items():
        sig_corrs = result['correlations'][result['correlations']['p_value'] < 0.05]
        if len(sig_corrs) > 0:
            findings.append(f"  [OK] {orb_time} ORB: {len(sig_corrs)} significant correlations found")
        if result['significant_diffs']:
            findings.append(f"  [OK] {orb_time} ORB: {len(result['significant_diffs'])} winner/loser differences")

    if findings:
        print("PATTERNS DISCOVERED:")
        for f in findings:
            print(f)
        print()
        print("[OK] SOME ORBs show session sensitivity!")
        print()
        print("Next steps:")
        print("  1. Deep-dive into ORBs with significant patterns")
        print("  2. Test as filters on those specific ORBs")
        print("  3. Validate with out-of-sample data")
    else:
        print("[X] NO SIGNIFICANT PATTERNS across any ORB")
        print()
        print("Session context does NOT predict ORB outcomes on MGC.")

    print()
    print("="*80)
    print("DISCOVERY COMPLETE")
    print("="*80)
    print()


if __name__ == '__main__':
    main()
