"""
Batch optimize all ORBs with LIMIT_AT_ORB execution

Finds optimal RR for each ORB time and generates SQL to update validated_setups.

CONSERVATIVE SETTINGS:
- 2-tick penetration requirement (queue penalty)
- $1 commission
- Fair comparison (R per opportunity)
"""

import duckdb
from datetime import date
from strategies.execution_engine import simulate_orb_trade
from strategies.execution_modes import ExecutionMode

DB_PATH = 'data/db/gold.db'

ORB_TIMES = ['0900', '1000', '1100', '1800', '2300', '0030']


def optimize_orb(orb_time: str, sl_mode: str = "FULL"):
    """Find optimal RR for an ORB using LIMIT execution"""

    con = duckdb.connect(DB_PATH, read_only=True)

    # Get all trading days
    days = con.execute(f"""
        SELECT date_local
        FROM daily_features
        WHERE instrument = 'MGC'
          AND orb_{orb_time}_high IS NOT NULL
          AND orb_{orb_time}_low IS NOT NULL
        ORDER BY date_local
    """).fetchdf()['date_local'].tolist()

    # Test RR values
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
                sl_mode=sl_mode.lower(),
                exec_mode=ExecutionMode.LIMIT_AT_ORB,
                slippage_ticks=0.0,
                commission_per_contract=1.0
            )
            if result.outcome in ('WIN', 'LOSS'):
                trades.append(result)

        if len(trades) < 30:  # Need reasonable sample
            continue

        wins = sum(1 for t in trades if t.outcome == 'WIN')
        win_rate = wins / len(trades)
        net_r_multiples = [t.r_multiple - t.cost_r for t in trades]
        avg_r = sum(net_r_multiples) / len(net_r_multiples)

        results.append({
            'rr': rr,
            'trades': len(trades),
            'win_rate': win_rate,
            'avg_r': avg_r
        })

    con.close()

    # Find optimal (highest avg R with >=30 trades)
    viable = [r for r in results if r['trades'] >= 30 and r['avg_r'] > 0]
    if not viable:
        return None

    optimal = max(viable, key=lambda x: x['avg_r'])
    return optimal


def main():
    """Batch optimize all ORBs and generate SQL updates"""

    print("="*80)
    print("BATCH OPTIMIZATION - LIMIT_AT_ORB EXECUTION (2-tick penetration)")
    print("="*80)
    print()

    optimized_setups = []

    for orb_time in ORB_TIMES:
        print(f"Optimizing {orb_time} ORB...")

        optimal = optimize_orb(orb_time, sl_mode="FULL")

        if optimal:
            print(f"  Optimal RR: {optimal['rr']}")
            print(f"  Trades: {optimal['trades']}")
            print(f"  Win Rate: {optimal['win_rate']*100:.1f}%")
            print(f"  Avg R: {optimal['avg_r']:+.3f}")
            print(f"  Expected R/year: {optimal['avg_r'] * 250:+.1f}R")
            print()

            optimized_setups.append({
                'orb_time': orb_time,
                'rr': optimal['rr'],
                'sl_mode': 'FULL',
                'win_rate': optimal['win_rate'],
                'expected_r': optimal['avg_r'],
                'sample_size': optimal['trades']
            })
        else:
            print(f"  No viable setup found (need >=30 trades with positive avg R)")
            print()

    # Generate SQL updates
    print("="*80)
    print("SQL UPDATES FOR validated_setups")
    print("="*80)
    print()
    print("-- LIMIT_AT_ORB optimized setups (2-tick penetration)")
    print("-- Generated:", pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'))
    print()

    for i, setup in enumerate(optimized_setups, start=100):
        print(f"""INSERT OR REPLACE INTO validated_setups (
    id, instrument, orb_time, rr, sl_mode, orb_size_filter,
    win_rate, expected_r, sample_size, notes
) VALUES (
    {i}, 'MGC', '{setup['orb_time']}', {setup['rr']}, '{setup['sl_mode']}', NULL,
    {setup['win_rate']:.4f}, {setup['expected_r']:.4f}, {setup['sample_size']},
    'LIMIT_AT_ORB execution (2-tick penetration, $1 commission)'
);""")
        print()

    # Summary table
    print("="*80)
    print("SUMMARY TABLE")
    print("="*80)
    print()
    print(f"{'ORB':<6} {'RR':>6} {'SL Mode':<8} {'Trades':>7} {'Win%':>7} {'Avg R':>10} {'R/year':>10}")
    print("-" * 80)

    for setup in optimized_setups:
        print(f"{setup['orb_time']:<6} {setup['rr']:>6.1f} {setup['sl_mode']:<8} {setup['sample_size']:>7,} "
              f"{setup['win_rate']*100:>6.1f}% {setup['expected_r']:>+9.3f}R {setup['expected_r']*250:>+9.1f}R")

    print()
    print(f"Total setups: {len(optimized_setups)}")
    print()


if __name__ == "__main__":
    import pandas as pd
    main()
