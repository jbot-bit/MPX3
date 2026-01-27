"""
STRESS TEST: LIMIT_RETRACE with Conservative Adverse Slippage

Tests whether LIMIT advantage is robust or artifact of optimistic fills.

CONSERVATIVE LIMIT_RETRACE:
- Same close-confirm trigger as MARKET
- Fill at ORB edge + 0.5 tick adverse slippage
- Models: Imperfect fills, queue position effects

Hypothesis:
- If LIMIT still beats MARKET → robust
- If LIMIT loses → assumption-driven artifact
"""

import duckdb
from datetime import date
from strategies.execution_engine import simulate_orb_trade
from strategies.execution_modes import ExecutionMode

DB_PATH = 'data/db/gold.db'


def stress_test(orb_time: str, rr: float, sl_mode: str = "full"):
    """Stress test LIMIT_RETRACE with adverse slippage"""

    print("="*80)
    print(f"STRESS TEST: {orb_time} ORB RR={rr} SL={sl_mode}")
    print("="*80)
    print()
    print("Testing LIMIT_RETRACE robustness with conservative assumptions:")
    print()
    print("  MARKET:")
    print("    - Trigger: Close > ORB")
    print("    - Fill: Close + 1.5 ticks slippage")
    print("    - Cost: $2.50 ($1.50 slippage + $1.00 commission)")
    print()
    print("  LIMIT_RETRACE (CONSERVATIVE):")
    print("    - Trigger: Close > ORB (SAME as MARKET)")
    print("    - Fill: ORB edge + 0.5 tick ADVERSE slippage")
    print("    - Cost: $1.50 ($0.50 slippage + $1.00 commission)")
    print("    - Models: Imperfect fills, queue effects")
    print()
    print("Metric: R per OPPORTUNITY (missed fills = 0R)")
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
        # MARKET (baseline)
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

        # LIMIT_RETRACE (conservative - with 0.5 tick adverse slippage)
        r_limit = simulate_orb_trade(
            con=con,
            date_local=day,
            orb=orb_time,
            mode="1m",
            confirm_bars=1,
            rr=rr,
            sl_mode=sl_mode,
            exec_mode=ExecutionMode.LIMIT_RETRACE,
            slippage_ticks=0.5,  # ADVERSE slippage (worse fill than ORB edge)
            commission_per_contract=1.0
        )
        limit_results.append(r_limit)

    con.close()

    # Calculate stats
    def calc_stats(results):
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

    market_stats = calc_stats(market_results)
    limit_stats = calc_stats(limit_results)

    # Display
    print("RESULTS:")
    print()
    print(f"{'Metric':<30} {'MARKET':>15} {'LIMIT (0.5 slip)':>18} {'Diff':>12}")
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
    print("STRESS TEST VERDICT:")
    print("="*80)
    print()

    diff = limit_stats['avg_r_per_opp'] - market_stats['avg_r_per_opp']

    if diff > 0:
        print(f"[PASS] LIMIT STILL WINS by {diff:+.3f}R per opportunity")
        print()
        print("Conclusion: LIMIT advantage is ROBUST")
        print("  - Survives +0.5 tick adverse slippage")
        print("  - Better fill price still outweighs imperfect fills")
        print("  - Hypothesis confirmed for this ORB")
    else:
        print(f"[FAIL] MARKET WINS by {-diff:+.3f}R per opportunity")
        print()
        print("Conclusion: LIMIT advantage was ASSUMPTION-DRIVEN")
        print("  - Dies under realistic slippage assumptions")
        print("  - Optimistic fill assumptions were driving earlier results")
        print("  - Use MARKET for this ORB")

    print()

    return {
        'orb_time': orb_time,
        'rr': rr,
        'market_r': market_stats['avg_r_per_opp'],
        'limit_r': limit_stats['avg_r_per_opp'],
        'diff': diff,
        'robust': diff > 0
    }


def main():
    """Run stress test on all critical ORBs"""

    print()
    print("CONSERVATIVE STRESS TEST - LIMIT_RETRACE with +0.5 tick adverse slippage")
    print()

    results = []

    # Test critical ORBs
    results.append(stress_test('0900', 2.0, 'full'))
    print()
    results.append(stress_test('1000', 2.0, 'full'))
    print()
    results.append(stress_test('1100', 3.0, 'full'))
    print()

    # Summary
    print("="*80)
    print("STRESS TEST SUMMARY")
    print("="*80)
    print()
    print(f"{'ORB':<6} {'RR':>6} {'MARKET R/opp':>15} {'LIMIT R/opp':>15} {'Diff':>12} {'Robust?':>10}")
    print("-" * 80)

    for r in results:
        robust = "YES" if r['robust'] else "NO"
        print(f"{r['orb_time']:<6} {r['rr']:>6.1f} {r['market_r']:>+14.3f}R {r['limit_r']:>+14.3f}R {r['diff']:>+11.3f}R {robust:>10}")

    print()
    print("FINAL RECOMMENDATION:")
    print()

    robust_orbs = [r for r in results if r['robust']]
    if robust_orbs:
        print(f"[PASS] LIMIT_RETRACE is robust on {len(robust_orbs)}/3 ORBs:")
        for r in robust_orbs:
            print(f"   - {r['orb_time']} ORB: {r['diff']:+.3f}R improvement per opportunity")
        print()
        print("Use LIMIT_RETRACE on these ORBs (conservative fills confirmed)")
    else:
        print("[FAIL] LIMIT_RETRACE not robust on any ORBs under conservative assumptions")
        print()
        print("Use MARKET everywhere (simpler, no optimistic fill assumptions)")

    print()


if __name__ == "__main__":
    main()
