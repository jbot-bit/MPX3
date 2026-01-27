"""
Transaction Cost Analysis (TCA) for MGC ORB Trading

Calculates realistic execution costs and re-evaluates all filter optimization results
to identify truly profitable edges after costs.
"""

import pandas as pd
import sys
from pathlib import Path

# MGC contract specifications
TICK_SIZE = 0.1  # points
POINT_VALUE = 10  # dollars per point
TICK_VALUE = TICK_SIZE * POINT_VALUE  # $1 per tick

# Cost components (adjustable based on your broker)
COMMISSION_RT = 2.50  # round trip
SLIPPAGE_TICKS = 1.5  # average slippage in ticks
SLIPPAGE_DOLLARS = SLIPPAGE_TICKS * TICK_VALUE

TOTAL_COST_DOLLARS = COMMISSION_RT + SLIPPAGE_DOLLARS  # $4.00 total

# Minimum edge thresholds
MIN_EDGE_THIN = 0.05   # Thin edge (high frequency)
MIN_EDGE_DECENT = 0.10  # Decent edge (medium frequency)
MIN_EDGE_SOLID = 0.15   # Solid edge (low frequency)


def estimate_stop_size(rr: float, sl_mode: str) -> float:
    """
    Estimate typical stop size in points based on RR and SL mode.

    This is based on typical ORB sizes (0.3-2.0 points).
    """
    if sl_mode == 'half':
        # Half stops are smaller
        if rr <= 2.0:
            return 0.7
        elif rr <= 3.0:
            return 0.5
        else:
            return 0.3
    else:  # full
        # Full stops are larger
        if rr <= 1.5:
            return 2.0
        elif rr <= 2.0:
            return 1.5
        elif rr <= 3.0:
            return 1.0
        elif rr <= 4.0:
            return 0.7
        else:
            return 0.5


def calculate_cost_r(stop_size_points: float) -> float:
    """Calculate cost as fraction of R based on stop size."""
    risk_dollars = stop_size_points * POINT_VALUE
    return TOTAL_COST_DOLLARS / risk_dollars


def analyze_filter_results(results_dir: str = 'results'):
    """Analyze all filter optimization results with TCA."""

    # Load all individual result files
    result_files = list(Path(results_dir).glob('*.csv'))
    result_files = [f for f in result_files if f.stem != 'TOP_50_FILTERS']

    if not result_files:
        print(f"[ERROR] No result files found in {results_dir}/")
        return

    print("=" * 90)
    print("TRANSACTION COST ANALYSIS - FILTER OPTIMIZATION RESULTS")
    print("=" * 90)
    print()
    print(f"Cost assumptions:")
    print(f"  Commission: ${COMMISSION_RT:.2f} round trip")
    print(f"  Slippage: {SLIPPAGE_TICKS} ticks = ${SLIPPAGE_DOLLARS:.2f}")
    print(f"  TOTAL COST: ${TOTAL_COST_DOLLARS:.2f} per trade")
    print()

    all_results = []

    for file in result_files:
        df = pd.read_csv(file)

        # Extract edge info from filename (e.g., "0900_RR1.5_full.csv")
        filename = file.stem
        parts = filename.split('_')
        if len(parts) >= 3:
            orb = parts[0]
            rr_str = parts[1].replace('RR', '')
            sl_mode = parts[2]

            try:
                rr = float(rr_str)
            except:
                continue

            # Add edge info
            df['orb'] = orb
            df['rr'] = rr
            df['sl_mode'] = sl_mode

            all_results.append(df)

    # Combine all results
    combined = pd.concat(all_results, ignore_index=True)

    # Filter to validated filters only
    validated = combined[combined['is_validated'] == True].copy()

    print(f"Total filters tested: {len(combined):,}")
    print(f"Validated filters: {len(validated):,} ({len(validated)/len(combined)*100:.1f}%)")
    print()

    # Calculate costs for each edge
    validated['stop_size_est'] = validated.apply(
        lambda row: estimate_stop_size(row['rr'], row['sl_mode']), axis=1
    )
    validated['cost_r'] = validated['stop_size_est'].apply(calculate_cost_r)
    validated['test_r_post_cost'] = validated['test_avg_r'] - validated['cost_r']
    validated['baseline_r_post_cost'] = (validated['test_avg_r'] - validated['test_r_improvement']) - validated['cost_r']

    # Categorize by quality
    def categorize_edge(r_post_cost):
        if r_post_cost < 0:
            return 'LOSING'
        elif r_post_cost < MIN_EDGE_THIN:
            return 'MARGINAL'
        elif r_post_cost < MIN_EDGE_DECENT:
            return 'THIN'
        elif r_post_cost < MIN_EDGE_SOLID:
            return 'DECENT'
        else:
            return 'SOLID'

    validated['quality'] = validated['test_r_post_cost'].apply(categorize_edge)

    # Summary by quality
    print("=" * 90)
    print("EDGE QUALITY DISTRIBUTION (POST-COST)")
    print("=" * 90)
    print()

    quality_order = ['SOLID', 'DECENT', 'THIN', 'MARGINAL', 'LOSING']
    for quality in quality_order:
        count = len(validated[validated['quality'] == quality])
        if count > 0:
            pct = count / len(validated) * 100

            if quality == 'SOLID':
                threshold_desc = f'>= {MIN_EDGE_SOLID:.2f}R'
            elif quality == 'DECENT':
                threshold_desc = f'{MIN_EDGE_DECENT:.2f}-{MIN_EDGE_SOLID:.2f}R'
            elif quality == 'THIN':
                threshold_desc = f'{MIN_EDGE_THIN:.2f}-{MIN_EDGE_DECENT:.2f}R'
            elif quality == 'MARGINAL':
                threshold_desc = f'0.00-{MIN_EDGE_THIN:.2f}R'
            else:
                threshold_desc = '< 0.00R'

            print(f"{quality:10s} ({threshold_desc:15s}): {count:3d} edges ({pct:5.1f}%)")

    print()

    # Profitable edges only
    profitable = validated[validated['test_r_post_cost'] > 0].copy()

    print("=" * 90)
    print("PROFITABLE EDGES BY THRESHOLD")
    print("=" * 90)
    print()

    for threshold in [0.0, MIN_EDGE_THIN, MIN_EDGE_DECENT, MIN_EDGE_SOLID]:
        passing = validated[validated['test_r_post_cost'] >= threshold]
        print(f"Post-cost E[R] >= {threshold:.2f}R: {len(passing):3d} edges")

    print()

    # Top edges
    print("=" * 90)
    print("TOP 10 PROFITABLE EDGES (POST-COST)")
    print("=" * 90)
    print()

    top_10 = profitable.nlargest(10, 'test_r_post_cost')

    for i, row in enumerate(top_10.itertuples(), 1):
        print(f"{i}. {row.orb} ORB | RR={row.rr:.1f} | {row.sl_mode.upper()}")
        print(f"   Filter: {row.filter_name}")
        print(f"   Stop: ~{row.stop_size_est:.1f}pts, Cost: {row.cost_r:.2f}R")
        print(f"   Backtest: +{row.test_avg_r:.3f}R - {row.cost_r:.2f}R = Post-cost: +{row.test_r_post_cost:.3f}R")
        print(f"   {row.test_trades} test trades, {row.confidence} confidence, Quality: {row.quality}")
        print()

    # Best edge per ORB
    print("=" * 90)
    print("BEST PROFITABLE EDGE PER ORB (POST-COST)")
    print("=" * 90)
    print()

    for orb in sorted(profitable['orb'].unique()):
        orb_data = profitable[profitable['orb'] == orb]
        if len(orb_data) == 0:
            continue

        best = orb_data.nlargest(1, 'test_r_post_cost').iloc[0]

        print(f"{orb} ORB:")
        print(f"  Best: {best['filter_name']}")
        print(f"  RR={best['rr']:.1f}, {best['sl_mode'].upper()}, Stop~{best['stop_size_est']:.1f}pts")
        print(f"  Post-cost: +{best['test_r_post_cost']:.3f}R (Quality: {best['quality']})")
        print(f"  {best['test_trades']} trades, {best['confidence']} confidence")
        print()

    # Cost analysis by RR
    print("=" * 90)
    print("COST ANALYSIS BY RR LEVEL")
    print("=" * 90)
    print()

    rr_analysis = validated.groupby('rr').agg({
        'stop_size_est': 'mean',
        'cost_r': 'mean',
        'test_r_post_cost': 'mean',
    }).round(3)

    rr_analysis['count'] = validated.groupby('rr').size()
    rr_analysis['profitable'] = validated.groupby('rr').apply(lambda x: (x['test_r_post_cost'] > 0).sum())

    print("RR Level | Avg Stop | Avg Cost | Avg Post-Cost E[R] | Total | Profitable")
    print("-" * 75)
    for rr in sorted(rr_analysis.index):
        row = rr_analysis.loc[rr]
        print(f"  {rr:4.1f}   | {row['stop_size_est']:7.2f}  | {row['cost_r']:7.2f} | "
              f"{row['test_r_post_cost']:+16.3f}   | {int(row['count']):5d} | {int(row['profitable']):10d}")

    print()

    # Export tradeable edges
    tradeable = validated[validated['test_r_post_cost'] >= MIN_EDGE_DECENT].copy()
    tradeable = tradeable.sort_values('test_r_post_cost', ascending=False)

    output_file = f'{results_dir}/TRADEABLE_EDGES_POST_TCA.csv'
    tradeable.to_csv(output_file, index=False)

    print("=" * 90)
    print(f"TRADEABLE EDGES (>= {MIN_EDGE_DECENT:.2f}R post-cost)")
    print("=" * 90)
    print()
    print(f"Total tradeable edges: {len(tradeable)}")
    print(f"Exported to: {output_file}")
    print()

    if len(tradeable) > 0:
        print("Summary:")
        for i, row in enumerate(tradeable.itertuples(), 1):
            print(f"  {i}. {row.orb} ORB RR={row.rr:.1f} {row.sl_mode} + {row.filter_name}: "
                  f"+{row.test_r_post_cost:.3f}R")

    print()


if __name__ == '__main__':
    analyze_filter_results()
