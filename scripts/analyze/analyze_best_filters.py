"""
Analyze all filter optimization results and find the best filters across all edges.
"""

import pandas as pd
import glob
from pathlib import Path

def main():
    # Load all CSV results
    result_files = glob.glob('results/*.csv')

    print("=" * 90)
    print("BEST FILTERS ACROSS ALL 41 EDGES")
    print("=" * 90)
    print()

    all_results = []

    for file in result_files:
        df = pd.read_csv(file)

        # Extract edge info from filename
        filename = Path(file).stem  # e.g., "0030_RR1.5_half"
        parts = filename.split('_')
        orb = parts[0]
        rr = parts[1].replace('RR', '')
        sl_mode = parts[2]

        # Add edge info to dataframe
        df['orb'] = orb
        df['rr'] = rr
        df['sl_mode'] = sl_mode

        all_results.append(df)

    # Combine all results
    combined = pd.concat(all_results, ignore_index=True)

    # Filter to validated filters only (not overfit)
    validated = combined[combined['is_validated'] == True].copy()

    print(f"Total filter tests: {len(combined):,}")
    print(f"Validated filters: {len(validated):,} ({len(validated)/len(combined)*100:.1f}%)")
    print()

    # Top 20 filters by test WR improvement
    print("=" * 90)
    print("TOP 20 FILTERS BY WIN RATE IMPROVEMENT (Test Set)")
    print("=" * 90)
    print()

    top_wr = validated.nlargest(20, 'test_wr_improvement')

    for i, row in enumerate(top_wr.itertuples(), 1):
        print(f"{i}. {row.orb} ORB | RR={row.rr} | {row.sl_mode.upper()}")
        print(f"   Filter: {row.filter_name}")
        print(f"   Test: {row.test_wr:.1f}% WR ({row.test_wr_improvement:+.1f}%), {row.test_avg_r:+.3f}R avg, {row.test_trades} trades")
        print(f"   Train: {row.train_wr:.1f}% WR ({row.train_wr_improvement:+.1f}%), {row.train_avg_r:+.3f}R avg, {row.train_trades} trades")
        print(f"   Confidence: {row.confidence} | Overfit score: {row.overfit_score:.1f}%")
        print()

    # Top 20 filters by test R improvement
    print("=" * 90)
    print("TOP 20 FILTERS BY EXPECTED R IMPROVEMENT (Test Set)")
    print("=" * 90)
    print()

    top_r = validated.nlargest(20, 'test_r_improvement')

    for i, row in enumerate(top_r.itertuples(), 1):
        print(f"{i}. {row.orb} ORB | RR={row.rr} | {row.sl_mode.upper()}")
        print(f"   Filter: {row.filter_name}")
        print(f"   Test: {row.test_wr:.1f}% WR, {row.test_avg_r:+.3f}R avg ({row.test_r_improvement:+.3f}R), {row.test_trades} trades")
        print(f"   Train: {row.train_wr:.1f}% WR, {row.train_avg_r:+.3f}R avg ({row.train_r_improvement:+.3f}R), {row.train_trades} trades")
        print(f"   Confidence: {row.confidence} | Overfit score: {row.overfit_score:.1f}%")
        print()

    # Summary by ORB
    print("=" * 90)
    print("BEST FILTER PER ORB (Highest Test R Improvement)")
    print("=" * 90)
    print()

    for orb in sorted(validated['orb'].unique()):
        orb_data = validated[validated['orb'] == orb]
        best = orb_data.nlargest(1, 'test_r_improvement').iloc[0]

        print(f"{orb} ORB:")
        print(f"  Best filter: {best['filter_name']}")
        print(f"  RR={best['rr']}, {best['sl_mode'].upper()}")
        print(f"  Test: {best['test_wr']:.1f}% WR, {best['test_avg_r']:+.3f}R avg ({best['test_r_improvement']:+.3f}R), {best['test_trades']} trades")
        print(f"  Confidence: {best['confidence']}")
        print()

    # Export top 50 to CSV
    top_50 = validated.nlargest(50, 'test_r_improvement')
    top_50.to_csv('results/TOP_50_FILTERS.csv', index=False)
    print("[OK] Top 50 filters exported to: results/TOP_50_FILTERS.csv")

if __name__ == '__main__':
    main()
