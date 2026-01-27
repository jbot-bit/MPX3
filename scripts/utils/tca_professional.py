"""
Professional Transaction Cost Analysis (TCA)

Based on institutional framework from TCA.txt

Key Formula:
    R_net = net_pnl / (stop_distance * point_value * contracts)

Cost as R depends on:
- Position size (number of contracts)
- Stop distance (points)
- NOT a flat percentage!
"""

import pandas as pd
from pathlib import Path

# MGC specs
TICK_SIZE = 0.1
POINT_VALUE = 10  # $10 per point

# Cost components (per contract, round trip)
# Based on user data: Tradovate $0.78 RT, typical micro $1-2 RT
COMMISSION_PER_CONTRACT = 1.00  # Conservative estimate for micros
SLIPPAGE_TICKS = 1.5  # Average entry + exit slippage
SLIPPAGE_DOLLARS = SLIPPAGE_TICKS * TICK_SIZE * POINT_VALUE  # $1.50

TOTAL_COST_PER_CONTRACT = COMMISSION_PER_CONTRACT + SLIPPAGE_DOLLARS  # $2.50

def calculate_cost_as_r(contracts: int, stop_distance_points: float) -> float:
    """
    Calculate cost as fraction of R.

    Formula from TCA.txt:
        R_net = net_pnl / (stop_distance * point_value * contracts)

    Cost impact:
        cost_as_R = (total_cost) / (stop_distance * point_value * contracts)
    """
    total_cost = TOTAL_COST_PER_CONTRACT * contracts
    risk_dollars = stop_distance_points * POINT_VALUE * contracts

    if risk_dollars == 0:
        return 0

    return total_cost / risk_dollars


def estimate_stop_distance(rr: float, sl_mode: str) -> float:
    """Estimate stop distance in points based on RR and SL mode."""
    if sl_mode == 'half':
        if rr <= 2.0:
            return 0.7
        elif rr <= 3.0:
            return 0.5
        else:
            return 0.3
    else:  # full
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


def analyze_with_position_size(contracts: int = 1, results_dir: str = 'results'):
    """
    Analyze all filter results with proper TCA based on position size.

    Args:
        contracts: Number of contracts per trade
        results_dir: Directory containing filter optimization results
    """

    # Load all results
    result_files = list(Path(results_dir).glob('*.csv'))
    result_files = [f for f in result_files if f.stem != 'TOP_50_FILTERS' and 'TCA' not in f.stem]

    if not result_files:
        print(f"[ERROR] No result files found in {results_dir}/")
        return

    print("=" * 90)
    print("PROFESSIONAL TRANSACTION COST ANALYSIS")
    print("=" * 90)
    print()
    print(f"Position sizing: {contracts} contract(s) per trade")
    print(f"Commission: ${COMMISSION_PER_CONTRACT:.2f} per contract")
    print(f"Slippage: {SLIPPAGE_TICKS} ticks = ${SLIPPAGE_DOLLARS:.2f} per contract")
    print(f"Total cost: ${TOTAL_COST_PER_CONTRACT:.2f} per contract")
    print(f"Total cost for {contracts} contracts: ${TOTAL_COST_PER_CONTRACT * contracts:.2f} per trade")
    print()

    all_results = []

    for file in result_files:
        df = pd.read_csv(file)
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

            df['orb'] = orb
            df['rr'] = rr
            df['sl_mode'] = sl_mode
            all_results.append(df)

    combined = pd.concat(all_results, ignore_index=True)
    validated = combined[combined['is_validated'] == True].copy()

    print(f"Total filters tested: {len(combined):,}")
    print(f"Validated filters: {len(validated):,} ({len(validated)/len(combined)*100:.1f}%)")
    print()

    # Calculate costs properly
    validated['stop_distance_est'] = validated.apply(
        lambda row: estimate_stop_distance(row['rr'], row['sl_mode']), axis=1
    )

    validated['cost_r'] = validated['stop_distance_est'].apply(
        lambda stop: calculate_cost_as_r(contracts, stop)
    )

    validated['risk_per_trade'] = validated['stop_distance_est'] * POINT_VALUE * contracts
    validated['test_r_post_cost'] = validated['test_avg_r'] - validated['cost_r']

    # Quality categorization
    def categorize_edge(r_post_cost):
        if r_post_cost < 0:
            return 'LOSING'
        elif r_post_cost < 0.05:
            return 'MARGINAL'
        elif r_post_cost < 0.10:
            return 'THIN'
        elif r_post_cost < 0.15:
            return 'DECENT'
        elif r_post_cost < 0.20:
            return 'GOOD'
        else:
            return 'EXCELLENT'

    validated['quality'] = validated['test_r_post_cost'].apply(categorize_edge)

    # Summary
    print("=" * 90)
    print("COST AS % OF RISK BY POSITION SIZE")
    print("=" * 90)
    print()

    print("Stop Distance | Risk ($) | Cost ($) | Cost as R | % of Risk")
    print("-" * 75)

    example_stops = [0.3, 0.5, 0.7, 1.0, 1.5, 2.0]
    for stop in example_stops:
        risk_dollars = stop * POINT_VALUE * contracts
        cost_dollars = TOTAL_COST_PER_CONTRACT * contracts
        cost_r = calculate_cost_as_r(contracts, stop)
        cost_pct = cost_r * 100

        print(f"  {stop:5.2f} pts   | ${risk_dollars:7.2f}  | ${cost_dollars:7.2f} | {cost_r:8.3f}R | {cost_pct:7.2f}%")

    print()

    # Edge quality distribution
    print("=" * 90)
    print("EDGE QUALITY DISTRIBUTION (POST-COST)")
    print("=" * 90)
    print()

    quality_order = ['EXCELLENT', 'GOOD', 'DECENT', 'THIN', 'MARGINAL', 'LOSING']
    for quality in quality_order:
        count = len(validated[validated['quality'] == quality])
        if count > 0:
            pct = count / len(validated) * 100
            print(f"{quality:10s}: {count:3d} edges ({pct:5.1f}%)")

    print()

    # Profitability thresholds
    print("=" * 90)
    print("PROFITABLE EDGES BY THRESHOLD")
    print("=" * 90)
    print()

    for threshold in [0.0, 0.05, 0.10, 0.15, 0.20]:
        passing = validated[validated['test_r_post_cost'] >= threshold]
        print(f"Post-cost E[R] >= {threshold:.2f}R: {len(passing):3d} edges")

    print()

    # Top edges
    profitable = validated[validated['test_r_post_cost'] > 0].copy()

    if len(profitable) > 0:
        print("=" * 90)
        print(f"TOP 10 PROFITABLE EDGES ({contracts} contract position)")
        print("=" * 90)
        print()

        top_10 = profitable.nlargest(10, 'test_r_post_cost')

        for i, row in enumerate(top_10.itertuples(), 1):
            print(f"{i}. {row.orb} ORB | RR={row.rr:.1f} | {row.sl_mode.upper()}")
            print(f"   Filter: {row.filter_name}")
            print(f"   Stop: ~{row.stop_distance_est:.1f}pts, Risk: ${row.risk_per_trade:.2f}, Cost: {row.cost_r:.3f}R ({row.cost_r*100:.1f}%)")
            print(f"   Backtest: +{row.test_avg_r:.3f}R - {row.cost_r:.3f}R = Post-cost: +{row.test_r_post_cost:.3f}R")
            print(f"   Quality: {row.quality}, {row.test_trades} trades, {row.confidence} confidence")
            print()

    # Export
    output_file = f'{results_dir}/TCA_PROFESSIONAL_{contracts}contracts.csv'
    validated_sorted = validated.sort_values('test_r_post_cost', ascending=False)
    validated_sorted.to_csv(output_file, index=False)

    print("=" * 90)
    print(f"EXPORTED TO: {output_file}")
    print("=" * 90)
    print()

    # Recommendation
    decent_edges = validated[validated['test_r_post_cost'] >= 0.10]

    print("RECOMMENDATION:")
    print(f"  Edges with E[R] >= 0.10R post-cost: {len(decent_edges)}")

    if len(decent_edges) > 0:
        print()
        print("  Trade these edges:")
        for i, row in enumerate(decent_edges.nlargest(10, 'test_r_post_cost').itertuples(), 1):
            print(f"    {i}. {row.orb} ORB RR={row.rr:.1f} {row.sl_mode} + {row.filter_name}: +{row.test_r_post_cost:.3f}R")
    else:
        print("  Consider increasing position size or finding better filters.")

    print()


if __name__ == '__main__':
    import sys

    # Allow command-line override of contract count
    contracts = 1
    if len(sys.argv) > 1:
        try:
            contracts = int(sys.argv[1])
        except:
            print(f"Usage: python tca_professional.py [contracts]")
            print(f"Using default: {contracts} contract")

    analyze_with_position_size(contracts)
