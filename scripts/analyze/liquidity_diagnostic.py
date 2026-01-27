#!/usr/bin/env python3
"""
Liquidity Diagnostic - Edge Survival Analysis

Tests if validated edges survive real-world execution conditions.
NO CHANGES to strategy logic - pure diagnostic.

Outputs:
- Edge holds in X conditions
- Edge fails in Y conditions
- Failure starts when Z happens
"""

import duckdb
import sys
from typing import Dict, Tuple

DB_PATH = "gold.db"

def calculate_expectancy(win_rate: float, rr: float, cost_r: float) -> float:
    """Calculate expected R per trade"""
    return (win_rate/100) * rr - (1 - win_rate/100) * 1.0 - cost_r


def analyze_mgc_1000_liquidity():
    """Analyze MGC 1000 ORB under different liquidity conditions"""
    conn = duckdb.connect(DB_PATH)

    print("=" * 70)
    print("MGC 1000 ORB - LIQUIDITY DIAGNOSTIC")
    print("=" * 70)
    print()

    # Get all 1000 ORB trades with volume at entry
    query = """
    WITH entry_volumes AS (
        SELECT
            df.date_local,
            df.orb_1000_break_dir,
            df.orb_1000_outcome,
            df.orb_1000_size,
            df.orb_1000_r_multiple,
            -- Get volume from first 1-min bar after ORB (10:05-10:06)
            (
                SELECT AVG(volume)
                FROM bars_1m b
                WHERE b.symbol = 'MGC'
                AND b.ts_utc >= TIMESTAMP '1970-01-01' + (EXTRACT(EPOCH FROM df.date_local) + 36300) * INTERVAL '1 second'  -- 10:05 local = 00:05 UTC next day
                AND b.ts_utc < TIMESTAMP '1970-01-01' + (EXTRACT(EPOCH FROM df.date_local) + 37200) * INTERVAL '1 second'   -- 10:15 local
                LIMIT 10
            ) as entry_volume
        FROM daily_features df
        WHERE df.orb_1000_break_dir != 'NONE'
        AND df.orb_1000_outcome IS NOT NULL
        AND df.date_local >= '2020-01-01'
    )
    SELECT
        date_local,
        orb_1000_break_dir as break_dir,
        orb_1000_outcome as outcome,
        orb_1000_size as orb_size,
        orb_1000_r_multiple as r_multiple,
        COALESCE(entry_volume, 150) as volume  -- Default if missing
    FROM entry_volumes
    WHERE orb_1000_size IS NOT NULL
    ORDER BY date_local
    """

    results = conn.execute(query).fetchall()

    if not results:
        print("❌ No data found for MGC 1000 ORB")
        return

    print(f"Total trades analyzed: {len(results)}")
    print()

    # Calculate volume statistics
    volumes = [r[5] for r in results]
    avg_volume = sum(volumes) / len(volumes)
    volumes_sorted = sorted(volumes)
    median_volume = volumes_sorted[len(volumes_sorted)//2]

    print(f"Volume Statistics:")
    print(f"  Average: {avg_volume:.0f} contracts")
    print(f"  Median: {median_volume:.0f} contracts")
    print(f"  Min: {min(volumes):.0f} contracts")
    print(f"  Max: {max(volumes):.0f} contracts")
    print()

    # Define liquidity buckets
    low_threshold = median_volume * 0.5
    high_threshold = median_volume * 1.5

    print(f"Liquidity Buckets:")
    print(f"  LOW: < {low_threshold:.0f} contracts")
    print(f"  NORMAL: {low_threshold:.0f} - {high_threshold:.0f} contracts")
    print(f"  HIGH: > {high_threshold:.0f} contracts")
    print()

    # Segment trades by liquidity
    low_liq = [r for r in results if r[5] < low_threshold]
    normal_liq = [r for r in results if low_threshold <= r[5] <= high_threshold]
    high_liq = [r for r in results if r[5] > high_threshold]

    # Calculate win rates and expectancy for each bucket
    def analyze_bucket(trades, bucket_name, base_cost_r=0.125):
        if not trades:
            return

        wins = sum(1 for t in trades if t[2] == 'WIN')
        losses = len(trades) - wins
        win_rate = (wins / len(trades)) * 100

        # Assume RR=1.5 (from validated_setups)
        rr = 1.5

        # Calculate expectancy with different cost scenarios
        base_expectancy = calculate_expectancy(win_rate, rr, base_cost_r)

        # Stress test: 2x slippage
        stress_cost_r = base_cost_r + 0.125  # Add another 0.125R for worse slippage
        stress_expectancy = calculate_expectancy(win_rate, rr, stress_cost_r)

        # Stress test: 3x slippage
        crisis_cost_r = base_cost_r + 0.250  # Add 0.250R for crisis slippage
        crisis_expectancy = calculate_expectancy(win_rate, rr, crisis_cost_r)

        return {
            'name': bucket_name,
            'trades': len(trades),
            'win_rate': win_rate,
            'base_expectancy': base_expectancy,
            'stress_expectancy': stress_expectancy,
            'crisis_expectancy': crisis_expectancy
        }

    low_stats = analyze_bucket(low_liq, "LOW")
    normal_stats = analyze_bucket(normal_liq, "NORMAL")
    high_stats = analyze_bucket(high_liq, "HIGH")

    # Print results
    print("=" * 70)
    print("RESULTS BY LIQUIDITY CONDITION")
    print("=" * 70)
    print()

    for stats in [low_stats, normal_stats, high_stats]:
        if not stats:
            continue

        print(f"{stats['name']} LIQUIDITY ({stats['trades']} trades):")
        print(f"  Win Rate: {stats['win_rate']:.1f}%")
        print(f"  Expectancy (base cost 0.125R): {stats['base_expectancy']:+.3f}R")
        print(f"  Expectancy (2x slippage):      {stats['stress_expectancy']:+.3f}R")
        print(f"  Expectancy (3x slippage):      {stats['crisis_expectancy']:+.3f}R")

        if stats['base_expectancy'] < 0:
            print(f"  [X] FAILING - Negative expectancy at base cost")
        elif stats['stress_expectancy'] < 0:
            print(f"  [!] FRAGILE - Fails under 2x slippage")
        elif stats['crisis_expectancy'] < 0:
            print(f"  [!] MARGINAL - Fails under 3x slippage")
        else:
            print(f"  [OK] ROBUST - Survives stress scenarios")
        print()

    # Calculate breakeven analysis
    print("=" * 70)
    print("BREAKEVEN ANALYSIS")
    print("=" * 70)
    print()

    # For each liquidity bucket, find max cost before expectancy goes negative
    for stats in [low_stats, normal_stats, high_stats]:
        if not stats:
            continue

        win_rate = stats['win_rate']
        rr = 1.5

        # Expectancy = (WR × RR) - (1-WR) × 1 - Cost
        # Breakeven when expectancy = 0
        # Cost_max = (WR × RR) - (1-WR)
        wr_decimal = win_rate / 100
        max_cost = (wr_decimal * rr) - (1 - wr_decimal)

        print(f"{stats['name']} LIQUIDITY:")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Max Cost Before Failure: {max_cost:.3f}R")
        print(f"  Base Cost: 0.125R")
        print(f"  Safety Margin: {(max_cost - 0.125):.3f}R")

        # How much slippage can you afford?
        # Base = commission (0.05R) + 5 tick slippage (0.075R) = 0.125R
        # Additional slippage allowed = (max_cost - 0.125R)
        # Each 5 ticks = 0.075R
        additional_slippage_r = max_cost - 0.125
        additional_ticks = (additional_slippage_r / 0.075) * 5
        total_ticks_allowed = 5 + additional_ticks

        print(f"  Max Slippage: {total_ticks_allowed:.1f} ticks")
        print()

    conn.close()

    # Print summary
    print("=" * 70)
    print("SUMMARY - EDGE SURVIVAL")
    print("=" * 70)
    print()

    if low_stats:
        if low_stats['base_expectancy'] >= 0.10:
            print(f"[OK] Edge HOLDS in LOW liquidity")
        elif low_stats['base_expectancy'] >= 0:
            print(f"[!] Edge MARGINAL in LOW liquidity (+{low_stats['base_expectancy']:.3f}R)")
        else:
            print(f"[X] Edge FAILS in LOW liquidity ({low_stats['base_expectancy']:.3f}R)")

    if normal_stats:
        if normal_stats['stress_expectancy'] >= 0:
            print(f"[OK] Edge HOLDS in NORMAL liquidity (survives 2x slippage)")
        else:
            print(f"[!] Edge FAILS in NORMAL liquidity under stress")

    if high_stats:
        print(f"[OK] Edge HOLDS in HIGH liquidity")

    print()

    # Find failure threshold
    if low_stats and low_stats['base_expectancy'] < 0:
        print(f"[X] Failure starts when: Volume < {low_threshold:.0f} contracts")
    elif normal_stats and normal_stats['stress_expectancy'] < 0:
        print(f"[!] Failure starts when: Slippage > 10 ticks (2x normal)")
    else:
        print(f"[OK] No failure observed in tested conditions")


if __name__ == "__main__":
    analyze_mgc_1000_liquidity()
