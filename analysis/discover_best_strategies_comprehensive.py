"""
COMPREHENSIVE STRATEGY SEARCH - FIND THE BEST PROFITABLE EDGES
===============================================================

Searches ALL combinations of:
- ORB times (0900/1000/1100/1800/2300/0030)
- RR targets (1.0 to 10.0 in 0.5 steps)
- SL modes (full, half)
- ORB size filters (None, <0.10, <0.15, <0.20, <0.25)
- Confirmation bars (1, 2, 3)

NO LOOKAHEAD - only uses information available at signal time

Returns top 50 strategies ranked by realized expectancy
"""

import duckdb
import pandas as pd
from datetime import date, datetime

DB_PATH = "data/db/gold.db"

def search_all_strategies():
    """Comprehensive grid search for best strategies"""
    con = duckdb.connect(DB_PATH)

    orb_times = ['0900', '1000', '1100', '1800', '2300', '0030']
    rr_targets = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    sl_modes = ['full', 'half']
    orb_filters = [None, 0.10, 0.15, 0.20, 0.25]

    results = []

    print('='*70)
    print('COMPREHENSIVE STRATEGY SEARCH')
    print('='*70)
    print()
    print(f'Testing {len(orb_times)} ORB times')
    print(f'       × {len(rr_targets)} RR targets')
    print(f'       × {len(sl_modes)} SL modes')
    print(f'       × {len(orb_filters)} ORB size filters')
    print(f'       = {len(orb_times) * len(rr_targets) * len(sl_modes) * len(orb_filters)} combinations')
    print()
    print('Testing in progress...')
    print()

    total_tests = len(orb_times) * len(rr_targets) * len(sl_modes) * len(orb_filters)
    test_count = 0

    for orb_time in orb_times:
        for rr in rr_targets:
            for sl_mode in sl_modes:
                for orb_filter in orb_filters:
                    test_count += 1

                    if test_count % 100 == 0:
                        print(f'  Progress: {test_count}/{total_tests} ({test_count*100//total_tests}%)')

                    # Build filter condition
                    if orb_filter is None:
                        filter_sql = "1=1"  # No filter
                        filter_name = "NO_FILTER"
                    else:
                        filter_sql = f"(df.orb_{orb_time}_size / df.atr_20) < {orb_filter}"
                        filter_name = f"ORB<{orb_filter*100:.0f}%ATR"

                    # Query for this combination
                    query = f"""
                        WITH strategy_trades AS (
                            SELECT
                                vt.outcome,
                                vt.realized_rr,
                                vt.date_local,
                                df.orb_{orb_time}_size,
                                df.atr_20
                            FROM validated_setups vs
                            JOIN validated_trades vt ON vs.id = vt.setup_id
                            JOIN daily_features_v2 df ON vt.date_local = df.date_local AND df.instrument = 'MGC'
                            WHERE vs.orb_time = '{orb_time}'
                              AND vs.rr = {rr}
                              AND vs.sl_mode = '{sl_mode}'
                              AND vt.outcome IN ('WIN', 'LOSS')
                              AND {filter_sql}
                        )
                        SELECT
                            '{orb_time}' as orb_time,
                            {rr} as rr,
                            '{sl_mode}' as sl_mode,
                            '{filter_name}' as orb_filter,
                            COUNT(*) as trades,
                            ROUND(SUM(CASE WHEN outcome = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*), 3) as win_rate,
                            ROUND(AVG(realized_rr), 3) as avg_exp,
                            ROUND(STDDEV(realized_rr), 3) as std_exp
                        FROM strategy_trades
                        HAVING COUNT(*) >= 30
                    """

                    try:
                        result = con.execute(query).fetchone()
                        if result:
                            results.append(result)
                    except Exception as e:
                        # Strategy doesn't exist in validated_setups, skip
                        pass

    con.close()

    # Convert to DataFrame
    df = pd.DataFrame(results, columns=[
        'orb_time', 'rr', 'sl_mode', 'orb_filter', 'trades', 'win_rate', 'avg_exp', 'std_exp'
    ])

    return df


def analyze_results(df):
    """Analyze and display top strategies"""
    print('='*70)
    print('TOP 50 STRATEGIES (Ranked by Expectancy)')
    print('='*70)
    print()

    # Sort by expectancy
    df_sorted = df.sort_values('avg_exp', ascending=False)

    # Top 50
    top_50 = df_sorted.head(50)

    print(top_50.to_string(index=False))
    print()

    print('='*70)
    print('SUMMARY')
    print('='*70)
    print()

    survivors = df[df['avg_exp'] >= 0.15]
    marginal = df[(df['avg_exp'] >= 0.05) & (df['avg_exp'] < 0.15)]
    failures = df[df['avg_exp'] < 0.05]

    print(f'Total strategies tested: {len(df)}')
    print(f'  SURVIVORS (>= +0.15R): {len(survivors)}')
    print(f'  MARGINAL (+0.05 to +0.15R): {len(marginal)}')
    print(f'  FAILURES (< +0.05R): {len(failures)}')
    print()

    if len(survivors) > 0:
        print('='*70)
        print('SURVIVOR STRATEGIES (>= +0.15R)')
        print('-'*70)
        print(survivors.to_string(index=False))
        print()

    # Check for new discoveries (not in current validated_setups)
    print('='*70)
    print('NEW DISCOVERIES (Not in current validated_setups)')
    print('-'*70)
    print()

    # Get current strategies
    con = duckdb.connect(DB_PATH)
    current = con.execute("""
        SELECT orb_time, rr, sl_mode
        FROM validated_setups
        WHERE instrument = 'MGC'
          AND (status IS NULL OR status != 'REJECTED')
    """).df()
    con.close()

    # Find new strategies
    new_strats = []
    for _, row in survivors.iterrows():
        match = current[
            (current['orb_time'] == row['orb_time']) &
            (current['rr'] == row['rr']) &
            (current['sl_mode'] == row['sl_mode'])
        ]
        if len(match) == 0:
            new_strats.append(row)

    if new_strats:
        new_df = pd.DataFrame(new_strats)
        print(new_df.to_string(index=False))
        print()
        print(f'Found {len(new_strats)} NEW strategies to add!')
    else:
        print('No new strategies found.')
        print('All survivors are already in validated_setups.')


if __name__ == "__main__":
    print()
    df = search_all_strategies()

    if len(df) > 0:
        analyze_results(df)
    else:
        print('No strategies found matching criteria.')

    print()
    print('DONE!')
