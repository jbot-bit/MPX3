"""
HONEST LIMIT COMPARISON

Compares MARKET vs LIMIT_RETRACE (same trigger logic).

LIMIT_RETRACE:
- Waits for CLOSE confirmation (same as MARKET)
- THEN places limit at ORB edge
- Fills if price retraces

This is apples-to-apples: Same trigger, different fill price.
"""

import duckdb
from datetime import date
from strategies.execution_engine import simulate_orb_trade
from strategies.execution_modes import ExecutionMode

DB_PATH = 'data/db/gold.db'


def honest_comparison(orb_time: str, rr: float, sl_mode: str = "full"):
    """Fair comparison using LIMIT_RETRACE (same trigger as MARKET)"""

    print("="*80)
    print(f"HONEST COMPARISON: {orb_time} ORB RR={rr} SL={sl_mode}")
    print("="*80)
    print()
    print("Methodology:")
    print("  - MARKET: Close-based trigger, entry at close + 1.5 ticks slippage")
    print("  - LIMIT_RETRACE: SAME close-based trigger, entry at ORB edge if retrace")
    print("  - Same trigger = apples-to-apples comparison")
    print("  - Difference is ONLY fill price and slippage")
    print()

    con = duckdb.connect(DB_PATH, read_only=True)

    # Get trading days
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

    # Test both modes
    market_results = []
    limit_results = []

    for day in days:
        # MARKET
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

        # LIMIT_RETRACE (same trigger!)
        r_limit = simulate_orb_trade(
            con=con,
            date_local=day,
            orb=orb_time,
            mode="1m",
            confirm_bars=1,
            rr=rr,
            sl_mode=sl_mode,
            exec_mode=ExecutionMode.LIMIT_RETRACE,
            slippage_ticks=0.0,
            commission_per_contract=1.0
        )
        limit_results.append(r_limit)

    con.close()

    # Calculate stats
    def calc_stats(results, name):
        total = len(results)
        filled = [r for r in results if r.outcome in ('WIN', 'LOSS')]
        fill_rate = len(filled) / total * 100

        r_per_opp = []
        for r in results:
            if r.outcome in ('WIN', 'LOSS'):
                r_per_opp.append(r.r_multiple - r.cost_r)
            else:
                r_per_opp.append(0.0)

        avg_r = sum(r_per_opp) / len(r_per_opp)
        total_r = sum(r_per_opp)

        if filled:
            wins = sum(1 for t in filled if t.outcome == 'WIN')
            win_rate = wins / len(filled) * 100
        else:
            win_rate = 0.0

        return {
            'opportunities': total,
            'fills': len(filled),
            'fill_rate': fill_rate,
            'win_rate': win_rate,
            'avg_r_per_opp': avg_r,
            'total_r': total_r
        }

    market_stats = calc_stats(market_results, "MARKET")
    limit_stats = calc_stats(limit_results, "LIMIT_RETRACE")

    # Display
    print("RESULTS:")
    print()
    print(f"{'Metric':<30} {'MARKET':>15} {'LIMIT_RETRACE':>18} {'Diff':>12}")
    print("-" * 80)
    print(f"{'Total Opportunities':<30} {market_stats['opportunities']:>15,} {limit_stats['opportunities']:>18,} {'-':>12}")
    print(f"{'Fills':<30} {market_stats['fills']:>15,} {limit_stats['fills']:>18,} {limit_stats['fills'] - market_stats['fills']:>+12,}")
    print(f"{'Fill Rate':<30} {market_stats['fill_rate']:>14.1f}% {limit_stats['fill_rate']:>17.1f}% {limit_stats['fill_rate'] - market_stats['fill_rate']:>+11.1f}%")
    print(f"{'Win Rate (of fills)':<30} {market_stats['win_rate']:>14.1f}% {limit_stats['win_rate']:>17.1f}% {limit_stats['win_rate'] - market_stats['win_rate']:>+11.1f}%")
    print()
    print(f"{'Avg R per OPPORTUNITY':<30} {market_stats['avg_r_per_opp']:>+14.3f}R {limit_stats['avg_r_per_opp']:>+17.3f}R {limit_stats['avg_r_per_opp'] - market_stats['avg_r_per_opp']:>+11.3f}R")
    print(f"{'Total R':<30} {market_stats['total_r']:>+14.1f}R {limit_stats['total_r']:>+17.1f}R {limit_stats['total_r'] - market_stats['total_r']:>+11.1f}R")
    print()
    print(f"{'Expected R/year (250 days)':<30} {market_stats['avg_r_per_opp'] * 250:>+14.1f}R {limit_stats['avg_r_per_opp'] * 250:>+17.1f}R {(limit_stats['avg_r_per_opp'] - market_stats['avg_r_per_opp']) * 250:>+11.1f}R")
    print()

    # Verdict
    print("="*80)
    print("VERDICT (HONEST):")
    print("="*80)
    print()

    if limit_stats['avg_r_per_opp'] > market_stats['avg_r_per_opp']:
        improvement = limit_stats['avg_r_per_opp'] - market_stats['avg_r_per_opp']
        print(f"[PASS] LIMIT_RETRACE BEATS MARKET by {improvement:+.3f}R per opportunity")
        print()
        print("Why LIMIT_RETRACE wins:")
        print("  - Same trigger logic (close confirmation)")
        print("  - Better fill price (at ORB edge if retrace occurs)")
        print("  - No slippage (limit order)")
        print(f"  - Misses {market_stats['fill_rate'] - limit_stats['fill_rate']:.1f}% of fills BUT still more profitable")
    else:
        degradation = market_stats['avg_r_per_opp'] - limit_stats['avg_r_per_opp']
        print(f"[FAIL] MARKET BEATS LIMIT_RETRACE by {degradation:+.3f}R per opportunity")
        print()
        print("Why MARKET wins:")
        print("  - Better fill rate (guaranteed fills)")
        print("  - LIMIT_RETRACE misses too many trades that don't retrace")

    print()


if __name__ == "__main__":
    import sys
    orb_time = sys.argv[1] if len(sys.argv) > 1 else "1000"
    rr = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0

    honest_comparison(orb_time, rr, "full")
