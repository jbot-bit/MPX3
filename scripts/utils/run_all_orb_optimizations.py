"""
RUN ALL ORB OPTIMIZATIONS SEQUENTIALLY

Tests all 4 ORBs (0900, 1000, 1100, 1800) one at a time to avoid CPU overload.

Saves results for each ORB to JSON, then creates a summary comparing all ORBs.
"""

import subprocess
import json
import pandas as pd

ORBS = ['0900', '1000', '1100', '1800', '2300', '0030']

print("="*80)
print("RUNNING COMPREHENSIVE ORB OPTIMIZATION - ALL 6 ORBs")
print("="*80)
print()
print("This will test 36 stop/RR combinations on each ORB (216 total)")
print("Each ORB takes ~2-3 minutes to optimize")
print("Total time: ~12-18 minutes")
print()

all_profitable = []

for orb in ORBS:
    print(f"\n{'#'*80}")
    print(f"# OPTIMIZING {orb} ORB")
    print(f"{'#'*80}\n")

    # Run optimization for this ORB
    result = subprocess.run(
        ['python', 'optimize_orb_simple.py', orb],
        capture_output=False,
        text=True
    )

    if result.returncode != 0:
        print(f"ERROR: {orb} optimization failed!")
        continue

    # Load results
    results_file = f'optimization_results_{orb}.json'
    try:
        with open(results_file, 'r') as f:
            results = json.load(f)

        # Filter profitable
        for r in results:
            if r['avg_r'] > 0.10:
                r['orb_time'] = orb
                all_profitable.append(r)

    except FileNotFoundError:
        print(f"WARNING: Results file not found for {orb}")

print("\n" + "="*80)
print("FINAL SUMMARY - ALL ORBs")
print("="*80)
print()

if len(all_profitable) > 0:
    df = pd.DataFrame(all_profitable)
    df = df.sort_values('avg_r', ascending=False)

    print(f"Found {len(df)} PROFITABLE setups across all ORBs:")
    print()
    print(df[['orb_time', 'stop_frac', 'rr', 'trades', 'wr', 'avg_r', 'total_r']].to_string(index=False))
    print()

    # Best per ORB
    print("="*80)
    print("BEST SETUP PER ORB:")
    print("="*80)
    print()

    for orb in ORBS:
        orb_data = df[df['orb_time'] == orb]
        if len(orb_data) > 0:
            best = orb_data.nlargest(1, 'avg_r').iloc[0]
            print(f"{orb}: Stop={best['stop_frac']:.2f}, RR={best['rr']:.1f}, "
                  f"{best['trades']:.0f} trades, {best['wr']:.1f}% WR, "
                  f"{best['avg_r']:+.3f} avg R, {best['total_r']:+.1f}R total")
        else:
            print(f"{orb}: NO PROFITABLE SETUPS")

    print()

    # Overall best
    best = df.nlargest(1, 'avg_r').iloc[0]
    print("="*80)
    print("OVERALL BEST SETUP:")
    print("="*80)
    print(f"  ORB: {best['orb_time']}")
    print(f"  Stop: {best['stop_frac']:.2f} x ORB")
    print(f"  RR: {best['rr']:.1f}")
    print(f"  Trades: {best['trades']:.0f}")
    print(f"  Win rate: {best['wr']:.1f}% (need {best['be_wr']:.1f}%)")
    print(f"  Avg R: {best['avg_r']:+.3f}")
    print(f"  Total R: {best['total_r']:+.1f}")
    print()

    # Save summary
    df.to_csv('optimization_summary_all_orbs.csv', index=False)
    print("Saved full summary to optimization_summary_all_orbs.csv")

else:
    print("NO PROFITABLE SETUPS FOUND across any ORB")
    print()
    print("Next steps:")
    print("  1. Add filters (session type, ORB size, RSI)")
    print("  2. Test different instruments (NQ, MPL)")
    print("  3. Consider advanced management (BE SL, partial exits)")

print()
