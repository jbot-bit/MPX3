"""
FAIR EXECUTION MODE COMPARISON

Compares MARKET vs LIMIT on R PER OPPORTUNITY basis.

Key differences from previous test:
1. R per OPPORTUNITY (not R per filled trade)
   - Missed fills count as 0R
2. LIMIT requires 1-tick PENETRATION (not just touch)
   - Models queue position reality
3. Same trading days for both modes
4. Shows fill rates explicitly

This gives honest comparison: Does LIMIT beat MARKET after accounting
for missed fills and realistic fill requirements?
"""

import duckdb
import pandas as pd
from datetime import date
from strategies.execution_engine import simulate_orb_trade
from strategies.execution_modes import ExecutionMode

DB_PATH = 'data/db/gold.db'


def fair_comparison(orb_time: str, rr: float, sl_mode: str = "full"):
    """
    Fair comparison: R per opportunity (not per filled trade)
    """

    print("="*80)
    print(f"FAIR EXECUTION COMPARISON: {orb_time} ORB RR={rr} SL={sl_mode}")
    print("="*80)
    print()
    print("Methodology:")
    print("  - MARKET: Close-based entry with 1.5 ticks slippage, $1 commission")
    print("  - LIMIT: Requires 2-tick PENETRATION (CONSERVATIVE queue penalty), $1 commission")
    print("  - Missed fills count as 0R for LIMIT")
    print("  - Comparing R PER OPPORTUNITY (not R per filled trade)")
    print("  - This is VERY conservative - price must trade 2 ticks through to fill")
    print()

    con = duckdb.connect(DB_PATH, read_only=True)

    # Get all trading days with this ORB
    days = con.execute(f"""
        SELECT date_local
        FROM daily_features
        WHERE instrument = 'MGC'
          AND orb_{orb_time}_high IS NOT NULL
          AND orb_{orb_time}_low IS NOT NULL
        ORDER BY date_local DESC
        LIMIT 200
    """).fetchdf()['date_local'].tolist()

    print(f"Testing on {len(days)} trading days...")
    print()

    # Test both modes on SAME days
    market_results = []
    limit_results = []

    for day in days:
        # MARKET mode
        r_market = simulate_orb_trade(
            con=con,
            date_local=day,
            orb=orb_time,
            mode="1m",
            confirm_bars=1,
            rr=rr,
            sl_mode=sl_mode,
            exec_mode=ExecutionMode.MARKET_ON_CLOSE,
            slippage_ticks=1.5,
            commission_per_contract=1.0
        )
        market_results.append(r_market)

        # LIMIT mode
        r_limit = simulate_orb_trade(
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
        limit_results.append(r_limit)

    con.close()

    # Calculate R per OPPORTUNITY (missed fills = 0R)
    def calculate_r_per_opportunity(results):
        """Calculate R per opportunity (including 0R for no fills)"""
        total_opportunities = len(results)
        filled_trades = [r for r in results if r.outcome in ('WIN', 'LOSS')]

        # R per opportunity (missed fills = 0R)
        r_values = []
        for r in results:
            if r.outcome in ('WIN', 'LOSS'):
                # Subtract costs from R
                net_r = r.r_multiple - r.cost_r
                r_values.append(net_r)
            else:
                # Missed fill = 0R
                r_values.append(0.0)

        fill_rate = len(filled_trades) / total_opportunities * 100
        avg_r_per_opportunity = sum(r_values) / len(r_values)
        total_r = sum(r_values)

        # Stats for filled trades only
        if filled_trades:
            wins = sum(1 for t in filled_trades if t.outcome == 'WIN')
            win_rate = wins / len(filled_trades) * 100
            net_rs_filled = [t.r_multiple - t.cost_r for t in filled_trades]
            avg_r_per_filled = sum(net_rs_filled) / len(net_rs_filled)
        else:
            win_rate = 0.0
            avg_r_per_filled = 0.0

        return {
            'total_opportunities': total_opportunities,
            'fills': len(filled_trades),
            'fill_rate': fill_rate,
            'win_rate': win_rate,
            'avg_r_per_opportunity': avg_r_per_opportunity,
            'avg_r_per_filled': avg_r_per_filled,
            'total_r': total_r
        }

    market_stats = calculate_r_per_opportunity(market_results)
    limit_stats = calculate_r_per_opportunity(limit_results)

    # Display results
    print("RESULTS:")
    print()
    print(f"{'Metric':<30} {'MARKET':>15} {'LIMIT':>15} {'Diff':>12}")
    print("-" * 80)
    print(f"{'Total Opportunities':<30} {market_stats['total_opportunities']:>15,} {limit_stats['total_opportunities']:>15,} {'-':>12}")
    print(f"{'Fills':<30} {market_stats['fills']:>15,} {limit_stats['fills']:>15,} {limit_stats['fills'] - market_stats['fills']:>+12,}")
    print(f"{'Fill Rate':<30} {market_stats['fill_rate']:>14.1f}% {limit_stats['fill_rate']:>14.1f}% {limit_stats['fill_rate'] - market_stats['fill_rate']:>+11.1f}%")
    print(f"{'Win Rate (of fills)':<30} {market_stats['win_rate']:>14.1f}% {limit_stats['win_rate']:>14.1f}% {limit_stats['win_rate'] - market_stats['win_rate']:>+11.1f}%")
    print()
    print(f"{'Avg R per OPPORTUNITY':<30} {market_stats['avg_r_per_opportunity']:>+14.3f}R {limit_stats['avg_r_per_opportunity']:>+14.3f}R {limit_stats['avg_r_per_opportunity'] - market_stats['avg_r_per_opportunity']:>+11.3f}R")
    print(f"{'Avg R per FILLED trade':<30} {market_stats['avg_r_per_filled']:>+14.3f}R {limit_stats['avg_r_per_filled']:>+14.3f}R {limit_stats['avg_r_per_filled'] - market_stats['avg_r_per_filled']:>+11.3f}R")
    print(f"{'Total R':<30} {market_stats['total_r']:>+14.1f}R {limit_stats['total_r']:>+14.1f}R {limit_stats['total_r'] - market_stats['total_r']:>+11.1f}R")
    print()
    print(f"{'Expected R/year (250 days)':<30} {market_stats['avg_r_per_opportunity'] * 250:>+14.1f}R {limit_stats['avg_r_per_opportunity'] * 250:>+14.1f}R {(limit_stats['avg_r_per_opportunity'] - market_stats['avg_r_per_opportunity']) * 250:>+11.1f}R")
    print()

    # Verdict
    print("="*80)
    print("VERDICT:")
    print("="*80)
    print()

    if limit_stats['avg_r_per_opportunity'] > market_stats['avg_r_per_opportunity']:
        improvement = limit_stats['avg_r_per_opportunity'] - market_stats['avg_r_per_opportunity']
        improvement_pct = (improvement / abs(market_stats['avg_r_per_opportunity'])) * 100 if market_stats['avg_r_per_opportunity'] != 0 else float('inf')

        print(f"[PASS] LIMIT BEATS MARKET by {improvement:+.3f}R per opportunity ({improvement_pct:+.1f}%)")
        print()
        print("Why LIMIT wins:")
        print(f"  - Better entry price (at ORB edge, not close + slippage)")
        print(f"  - Lower costs (no slippage)")
        print(f"  - Smaller risk per trade")

        if limit_stats['fill_rate'] < market_stats['fill_rate']:
            missed_pct = market_stats['fill_rate'] - limit_stats['fill_rate']
            print(f"  - Misses {missed_pct:.1f}% of fills BUT still more profitable overall")
    else:
        degradation = market_stats['avg_r_per_opportunity'] - limit_stats['avg_r_per_opportunity']
        print(f"[FAIL] MARKET BEATS LIMIT by {degradation:+.3f}R per opportunity")
        print()
        print("Why MARKET wins:")
        print(f"  - Guaranteed fills ({market_stats['fill_rate']:.1f}% vs {limit_stats['fill_rate']:.1f}%)")
        print(f"  - LIMIT misses too many opportunities")

    print()


if __name__ == "__main__":
    import sys

    orb_time = sys.argv[1] if len(sys.argv) > 1 else "1000"
    rr = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    sl_mode = sys.argv[3] if len(sys.argv) > 3 else "full"

    fair_comparison(orb_time, rr, sl_mode)
