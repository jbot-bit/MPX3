"""
SUMMARIZE ALL ORB OPTIMIZATION RESULTS

Aggregates results from all 6 ORB optimizations and identifies:
1. Which ORBs are profitable (if any) without filters
2. Which ORBs are close to profitable (candidates for filter testing)
3. Optimal stop/RR for each ORB
4. Overall patterns (do tight stops work? high RR?)
"""

import json
import pandas as pd

ORBS = ['0900', '1000', '1100', '1800', '2300', '0030']

print("="*80)
print("COMPREHENSIVE SUMMARY - ALL 6 ORBs")
print("="*80)
print()

all_data = []
missing = []

for orb in ORBS:
    results_file = f'optimization_results_{orb}_canonical.json'
    try:
        with open(results_file, 'r') as f:
            results = json.load(f)

        for r in results:
            r['orb_time'] = orb
            all_data.append(r)

        print(f"{orb}: Loaded {len(results)} combinations")

    except FileNotFoundError:
        print(f"{orb}: NOT FOUND (still running?)")
        missing.append(orb)

print()

if len(all_data) == 0:
    print("ERROR: No results found. Run optimize_orb_canonical.py first")
    exit(1)

if len(missing) > 0:
    print(f"WARNING: Missing results for {', '.join(missing)}")
    print()

df = pd.DataFrame(all_data)

# Profitable setups
profitable = df[df['avg_r'] > 0.10].sort_values('avg_r', ascending=False)

print("="*80)
print("PROFITABLE SETUPS (avg R > 0.10)")
print("="*80)
print()

if len(profitable) > 0:
    print(f"Found {len(profitable)} profitable combinations:")
    print()
    print(profitable[['orb_time', 'stop_frac', 'rr', 'trades', 'wr', 'avg_r', 'total_r']].to_string(index=False))
else:
    print("NO PROFITABLE SETUPS FOUND without filters")

print()

# Near-profitable (candidates for filter testing)
near_profitable = df[(df['avg_r'] > -0.05) & (df['avg_r'] <= 0.10)].sort_values('avg_r', ascending=False)

print("="*80)
print("NEAR-PROFITABLE (-0.05 < avg R < 0.10)")
print("="*80)
print()

if len(near_profitable) > 0:
    print(f"Found {len(near_profitable)} near-profitable combinations (candidates for filter testing):")
    print()
    print(near_profitable[['orb_time', 'stop_frac', 'rr', 'trades', 'wr', 'avg_r', 'total_r']].to_string(index=False))
else:
    print("No near-profitable setups")

print()

# Best setup per ORB
print("="*80)
print("BEST SETUP PER ORB (even if unprofitable)")
print("="*80)
print()

for orb in ORBS:
    orb_data = df[df['orb_time'] == orb]
    if len(orb_data) > 0:
        best = orb_data.nlargest(1, 'avg_r').iloc[0]
        status = "PROFITABLE" if best['avg_r'] > 0.10 else "NEAR" if best['avg_r'] > -0.05 else "UNPROFITABLE"
        print(f"{orb}: Stop={best['stop_frac']:.2f}, RR={best['rr']:.1f}, "
              f"{best['trades']:.0f} trades, {best['wr']:.1f}% WR, "
              f"{best['avg_r']:+.3f} avg R [{status}]")

print()

# Overall patterns
print("="*80)
print("PATTERNS ANALYSIS")
print("="*80)
print()

print("1. Stop fraction impact (average across all ORBs and RR values):")
for stop_frac in sorted(df['stop_frac'].unique()):
    avg = df[df['stop_frac'] == stop_frac]['avg_r'].mean()
    print(f"   {stop_frac:.2f}: {avg:+.3f} avg R")

print()
print("2. RR impact (average across all ORBs and stop fractions):")
for rr in sorted(df['rr'].unique()):
    avg = df[df['rr'] == rr]['avg_r'].mean()
    print(f"   RR {rr:.1f}: {avg:+.3f} avg R")

print()
print("3. ORB time impact (average across all stop fractions and RR values):")
for orb in ORBS:
    orb_data = df[df['orb_time'] == orb]
    if len(orb_data) > 0:
        avg = orb_data['avg_r'].mean()
        print(f"   {orb}: {avg:+.3f} avg R")

print()

# Recommendations
print("="*80)
print("RECOMMENDATIONS")
print("="*80)
print()

if len(profitable) > 0:
    print("TRADEABLE SETUPS (ready to use):")
    for idx, row in profitable.head(5).iterrows():
        print(f"  {row['orb_time']} - Stop={row['stop_frac']:.2f}, RR={row['rr']:.1f}: {row['avg_r']:+.3f} avg R")
    print()

if len(near_profitable) > 0:
    print("TEST FILTERS ON (most promising):")
    for idx, row in near_profitable.head(5).iterrows():
        print(f"  {row['orb_time']} - Stop={row['stop_frac']:.2f}, RR={row['rr']:.1f}: {row['avg_r']:+.3f} avg R")
        print(f"    -> python test_filters_canonical.py {row['orb_time']} {row['stop_frac']:.2f} {row['rr']:.1f}")
    print()

if len(profitable) == 0 and len(near_profitable) == 0:
    print("ALL SETUPS UNPROFITABLE (avg R < -0.05)")
    print()
    print("Next steps:")
    print("  1. Test filters on best setups anyway (session type, ORB size, RSI)")
    print("  2. Test advanced management (breakeven SL, partial exits)")
    print("  3. Test different instruments (NQ, MPL)")

print()

# Save full summary
df.to_csv('optimization_summary_all_6_orbs_canonical.csv', index=False)
print("Saved full results to optimization_summary_all_6_orbs_canonical.csv")
print()
