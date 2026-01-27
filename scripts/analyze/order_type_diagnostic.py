#!/usr/bin/env python3
"""
Order Type Diagnostic - Market vs Limit Orders

Tests if edge survival depends on order execution method.
Current backtest assumes MARKET orders with slippage.

This checks if using LIMIT orders would change outcomes.
"""

import duckdb
import sys

DB_PATH = "gold.db"

def calculate_expectancy(win_rate: float, rr: float, cost_r: float) -> float:
    return (win_rate/100) * rr - (1 - win_rate/100) * 1.0 - cost_r


def analyze_order_types():
    """Compare market vs limit order execution"""
    conn = duckdb.connect(DB_PATH)

    print("=" * 70)
    print("ORDER TYPE DIAGNOSTIC - MGC 1000 ORB")
    print("=" * 70)
    print()

    # Get trades with entry details
    query = """
    SELECT
        df.date_local,
        df.orb_1000_high,
        df.orb_1000_low,
        df.orb_1000_break_dir,
        df.orb_1000_outcome,
        df.orb_1000_r_multiple
    FROM daily_features df
    WHERE df.orb_1000_break_dir != 'NONE'
    AND df.orb_1000_outcome IS NOT NULL
    AND df.orb_1000_high IS NOT NULL
    AND df.date_local >= '2020-01-01'
    """

    results = conn.execute(query).fetchall()

    print(f"Total trades: {len(results)}")
    print()

    # Current backtest: MARKET order with 5-tick slippage
    # Entry = first close outside ORB + 0.5 points slippage
    # Outcome already calculated in database

    wins_market = sum(1 for r in results if r[4] == 'WIN')
    wr_market = (wins_market / len(results)) * 100

    # LIMIT order scenarios:
    # 1. LIMIT at ORB edge (TOUCH entry)
    #    - Entry = ORB boundary exactly
    #    - NO slippage, but may not fill
    #    - Conservative: assume 20% of trades don't fill (missed entry)

    # 2. LIMIT with retrace (entry at ORB edge after pullback)
    #    - Entry = ORB edge + buffer (0.2-0.5 points)
    #    - Better fills, but tighter stop
    #    - Risk increases

    print("EXECUTION SCENARIOS:")
    print("=" * 70)
    print()

    # Scenario 1: Current (MARKET with slippage)
    print("1. MARKET ORDER (Current Backtest):")
    print("   Entry: First close outside ORB + 5 ticks slippage")
    print(f"   Win Rate: {wr_market:.1f}%")
    print(f"   Expectancy: {calculate_expectancy(wr_market, 1.5, 0.125):+.3f}R")
    print(f"   Fill Rate: 100%")
    print(f"   Cost: 0.125R (commission + slippage)")
    print()

    # Scenario 2: LIMIT at ORB edge
    # Conservative assumption: Win rate SAME (entry at edge vs close)
    # But 20% trades don't fill
    effective_trades_limit = len(results) * 0.8
    wr_limit_touch = wr_market  # Same WR when filled

    print("2. LIMIT AT ORB EDGE (Touch):")
    print("   Entry: ORB boundary exactly (no slippage)")
    print(f"   Win Rate (when filled): {wr_limit_touch:.1f}%")
    print(f"   Expectancy (when filled): {calculate_expectancy(wr_limit_touch, 1.5, 0.05):+.3f}R")
    print(f"   Fill Rate: ~80% (estimated)")
    print(f"   Effective Expectancy: {calculate_expectancy(wr_limit_touch, 1.5, 0.05) * 0.8:+.3f}R")
    print(f"   Cost: 0.05R (commission only, no slippage)")
    print()

    # Scenario 3: LIMIT with retrace buffer
    # Entry at ORB edge + 0.3 points
    # Better fill rate (90%), but increased risk
    # Conservatively assume WR drops 3% due to tighter stop
    wr_limit_retrace = wr_market - 3.0

    print("3. LIMIT WITH RETRACE (ORB edge + buffer):")
    print("   Entry: ORB edge + 0.3 points (after pullback)")
    print(f"   Win Rate: {wr_limit_retrace:.1f}% (-3% due to tighter stop)")
    print(f"   Expectancy: {calculate_expectancy(wr_limit_retrace, 1.5, 0.05):+.3f}R")
    print(f"   Fill Rate: ~90%")
    print(f"   Effective Expectancy: {calculate_expectancy(wr_limit_retrace, 1.5, 0.05) * 0.9:+.3f}R")
    print(f"   Cost: 0.05R (commission only)")
    print()

    # Scenario 4: MARKET in fast markets (2x slippage)
    print("4. MARKET IN FAST MARKETS (Stress Test):")
    print("   Entry: First close outside ORB + 10 ticks slippage")
    print(f"   Win Rate: {wr_market:.1f}%")
    print(f"   Expectancy: {calculate_expectancy(wr_market, 1.5, 0.250):+.3f}R")
    print(f"   Fill Rate: 100%")
    print(f"   Cost: 0.250R (commission + 2x slippage)")
    print()

    # Scenario 5: MARKET in crisis (3x slippage)
    print("5. MARKET IN CRISIS (3x Slippage):")
    print("   Entry: First close outside ORB + 15 ticks slippage")
    print(f"   Win Rate: {wr_market:.1f}%")
    print(f"   Expectancy: {calculate_expectancy(wr_market, 1.5, 0.375):+.3f}R")
    print(f"   Fill Rate: 100%")
    print(f"   Cost: 0.375R (commission + 3x slippage)")
    print()

    # Summary
    print("=" * 70)
    print("SUMMARY - ORDER TYPE IMPACT")
    print("=" * 70)
    print()

    market_exp = calculate_expectancy(wr_market, 1.5, 0.125)
    limit_touch_exp = calculate_expectancy(wr_limit_touch, 1.5, 0.05) * 0.8
    limit_retrace_exp = calculate_expectancy(wr_limit_retrace, 1.5, 0.05) * 0.9
    market_stress_exp = calculate_expectancy(wr_market, 1.5, 0.250)

    print(f"MARKET (current):        {market_exp:+.3f}R")
    print(f"LIMIT touch:             {limit_touch_exp:+.3f}R")
    print(f"LIMIT retrace:           {limit_retrace_exp:+.3f}R")
    print(f"MARKET (2x slippage):    {market_stress_exp:+.3f}R")
    print()

    if limit_touch_exp > market_exp:
        print("[OK] LIMIT touch orders IMPROVE expectancy")
    else:
        print("[!] MARKET orders BETTER than limit touch")

    if limit_retrace_exp > market_exp:
        print("[OK] LIMIT retrace orders IMPROVE expectancy")
    else:
        print("[!] MARKET orders BETTER than limit retrace")

    print()
    print("CONCLUSION:")
    print("-" * 70)

    if market_exp > 0 and market_stress_exp > 0:
        print("[OK] Edge survives with MARKET orders (even under stress)")
    elif market_exp > 0 and market_stress_exp < 0:
        print("[!] Edge holds with MARKET in normal conditions")
        print("[X] Edge FAILS with MARKET in fast markets")
    else:
        print("[X] Edge FAILS with MARKET orders")

    conn.close()


if __name__ == "__main__":
    analyze_order_types()
