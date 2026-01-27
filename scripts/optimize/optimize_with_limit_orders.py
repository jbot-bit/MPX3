"""
Re-optimize all ORB setups using LIMIT_AT_ORB execution mode

This will find the optimal RR values for LIMIT orders (touch-based entry at ORB edge).
Expected to be much more profitable than MARKET orders due to:
- Better entry price (at ORB edge, not close + slippage)
- No slippage costs (save $1.50/trade)
- Lower risk (smaller distance from entry to stop)

Usage:
    python optimize_with_limit_orders.py 1000
"""

import sys
import duckdb
import pandas as pd
from datetime import date
from strategies.execution_engine import simulate_orb_trade
from strategies.execution_modes import ExecutionMode

DB_PATH = 'data/db/gold.db'

def optimize_orb_limit(orb_time: str, sl_mode: str = "full"):
    """
    Optimize RR value for an ORB using LIMIT_AT_ORB execution

    Tests RR values from 1.0 to 10.0 to find optimal
    """

    print("="*80)
    print(f"OPTIMIZING {orb_time} ORB WITH LIMIT_AT_ORB EXECUTION")
    print("="*80)
    print()
    print(f"SL Mode: {sl_mode}")
    print(f"Execution: LIMIT_AT_ORB (touch-based, no slippage)")
    print(f"Slippage: 0.0 ticks")
    print(f"Commission: $1.00 per trade")
    print()

    con = duckdb.connect(DB_PATH, read_only=True)

    # Get all trading days with this ORB
    days = con.execute(f"""
        SELECT date_local
        FROM daily_features
        WHERE instrument = 'MGC'
          AND orb_{orb_time}_high IS NOT NULL
          AND orb_{orb_time}_low IS NOT NULL
        ORDER BY date_local
    """).fetchdf()['date_local'].tolist()

    print(f"Testing on {len(days)} trading days...")
    print()

    # Test RR values from 1.0 to 10.0
    rr_values = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0]

    results = []

    for rr in rr_values:
        trades = []

        for day in days:
            result = simulate_orb_trade(
                con=con,
                date_local=day,
                orb=orb_time,
                mode="1m",
                confirm_bars=1,
                rr=rr,
                sl_mode=sl_mode,
                exec_mode=ExecutionMode.LIMIT_AT_ORB,
                slippage_ticks=0.0,
                commission_per_contract=1.0
            )

            if result.outcome in ('WIN', 'LOSS'):
                trades.append(result)

        if len(trades) == 0:
            continue

        # Calculate stats
        wins = sum(1 for t in trades if t.outcome == 'WIN')
        win_rate = wins / len(trades) * 100

        # Net R (after costs)
        net_r_multiples = [t.r_multiple - t.cost_r for t in trades]
        avg_net_r = sum(net_r_multiples) / len(net_r_multiples)
        total_net_r = sum(net_r_multiples)

        # Average cost
        avg_cost_r = sum(t.cost_r for t in trades) / len(trades)

        results.append({
            'rr': rr,
            'trades': len(trades),
            'win_rate': win_rate,
            'avg_r': avg_net_r,
            'total_r': total_net_r,
            'avg_cost_r': avg_cost_r
        })

        print(f"RR={rr:4.1f}: {len(trades):3d} trades | WR={win_rate:5.1f}% | Avg R={avg_net_r:+7.3f} | Total R={total_net_r:+7.1f} | Cost={avg_cost_r:.3f}R")

    con.close()

    print()
    print("="*80)
    print("OPTIMIZATION RESULTS")
    print("="*80)
    print()

    # Find optimal RR (highest avg R with reasonable sample size)
    viable = [r for r in results if r['trades'] >= 30 and r['avg_r'] > 0]

    if not viable:
        print("[FAIL] No viable setups found (need >=30 trades and positive avg R)")
        return None

    optimal = max(viable, key=lambda x: x['avg_r'])

    print(f"OPTIMAL SETUP:")
    print(f"  RR = {optimal['rr']}")
    print(f"  Trades = {optimal['trades']}")
    print(f"  Win Rate = {optimal['win_rate']:.1f}%")
    print(f"  Avg R = {optimal['avg_r']:+.3f}")
    print(f"  Total R = {optimal['total_r']:+.1f}")
    print(f"  Expected R/year = {optimal['avg_r'] * 250:+.1f}R (250 trading days)")
    print()

    return optimal


def main():
    """Optimize all ORBs with LIMIT execution"""

    if len(sys.argv) < 2:
        print("Usage: python optimize_with_limit_orders.py <orb_time>")
        print("Example: python optimize_with_limit_orders.py 1000")
        sys.exit(1)

    orb_time = sys.argv[1]
    sl_mode = sys.argv[2] if len(sys.argv) > 2 else "full"

    optimal = optimize_orb_limit(orb_time, sl_mode)

    if optimal:
        print("RECOMMENDATION:")
        print(f"  Add to validated_setups:")
        print(f"    ORB: {orb_time}")
        print(f"    RR: {optimal['rr']}")
        print(f"    SL Mode: {sl_mode}")
        print(f"    Expected R: {optimal['avg_r']:+.3f}")
        print(f"    Execution: LIMIT_AT_ORB")
        print()


if __name__ == "__main__":
    main()
