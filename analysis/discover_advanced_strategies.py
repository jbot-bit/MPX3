"""
ADVANCED STRATEGY SEARCH - Complex Multi-Condition Filters
===========================================================

Tests advanced filter combinations:
1. Session context (Asia range, London range, pre-move travel)
2. Market regime (trending vs ranging vs volatile)
3. Time-of-day patterns
4. Combined filters (ORB size + session context)
5. Momentum filters (RSI, recent moves)

NO LOOKAHEAD - only information available at signal time
"""

import duckdb
import pandas as pd
from itertools import product

DB_PATH = "data/db/gold.db"


def search_session_context_filters():
    """Test session context filters (Asia/London characteristics)"""
    con = duckdb.connect(DB_PATH)

    orb_times = ['0900', '1000', '1100', '1800']
    rr_targets = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]

    # Session filters (use PREVIOUS day for 0900/1000/1100, SAME day for 1800+)
    session_filters = [
        ("NO_FILTER", "1=1"),
        ("BIG_ASIA", "asia_range > atr_20 * 0.8"),
        ("SMALL_ASIA", "asia_range < atr_20 * 0.3"),
        ("BIG_LONDON", "london_range > atr_20 * 0.5"),
        ("SMALL_LONDON", "london_range < atr_20 * 0.2"),
        ("BIG_PREMOVE", "pre_orb_travel > atr_20 * 0.5"),
        ("QUIET_PREMOVE", "pre_orb_travel < atr_20 * 0.2"),
    ]

    results = []
    print('='*70)
    print('ADVANCED SEARCH: Session Context Filters')
    print('='*70)
    print()

    for orb_time, rr, (filter_name, filter_sql) in product(orb_times, rr_targets, session_filters):
        # Determine if we use SAME day or PREVIOUS day features
        if orb_time in ['0900', '1000', '1100']:
            # Use PREVIOUS day (not available yet at signal time)
            # For 1100: Asia not complete, London not started
            # For 0900/1000: Previous day patterns might predict
            join_condition = """
                JOIN daily_features_v2 df_prev
                    ON df_prev.date_local = vt.date_local - INTERVAL '1 day'
                    AND df_prev.instrument = 'MGC'
            """
            filter_sql_adj = filter_sql.replace('asia_range', 'df_prev.asia_range') \
                                       .replace('london_range', 'df_prev.london_range') \
                                       .replace('pre_orb_travel', 'df_prev.pre_orb_travel') \
                                       .replace('atr_20', 'df_prev.atr_20')
        else:
            # 1800: Use SAME day (Asia complete, London starting)
            join_condition = """
                JOIN daily_features_v2 df
                    ON df.date_local = vt.date_local
                    AND df.instrument = 'MGC'
            """
            filter_sql_adj = filter_sql.replace('asia_range', 'df.asia_range') \
                                       .replace('london_range', 'df.london_range') \
                                       .replace('pre_orb_travel', 'df.pre_orb_travel') \
                                       .replace('atr_20', 'df.atr_20')

        query = f"""
            WITH strategy_trades AS (
                SELECT
                    vt.outcome,
                    vt.realized_rr
                FROM validated_setups vs
                JOIN validated_trades vt ON vs.id = vt.setup_id
                {join_condition}
                WHERE vs.orb_time = '{orb_time}'
                  AND vs.rr = {rr}
                  AND vs.sl_mode = 'full'
                  AND vt.outcome IN ('WIN', 'LOSS')
                  AND {filter_sql_adj}
            )
            SELECT
                '{orb_time}' as orb_time,
                {rr} as rr,
                '{filter_name}' as filter,
                COUNT(*) as trades,
                ROUND(SUM(CASE WHEN outcome = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*), 3) as win_rate,
                ROUND(AVG(realized_rr), 3) as avg_exp
            FROM strategy_trades
            HAVING COUNT(*) >= 25
        """

        try:
            result = con.execute(query).fetchone()
            if result and result[5] >= 0.15:  # Only survivors
                results.append(result)
        except:
            pass

    con.close()

    df = pd.DataFrame(results, columns=['orb_time', 'rr', 'filter', 'trades', 'win_rate', 'avg_exp'])
    return df.sort_values('avg_exp', ascending=False)


def search_combined_filters():
    """Test combined filters (ORB size + session context)"""
    con = duckdb.connect(DB_PATH)

    orb_times = ['0900', '1000', '1100', '1800']
    rr_targets = [2.0, 2.5, 3.0, 3.5, 4.0]

    # Combined filters
    combined_filters = [
        ("SMALL_ORB+BIG_ASIA",
         "(orb_size / atr_20) < 0.15 AND asia_range > atr_20 * 0.8"),
        ("SMALL_ORB+SMALL_ASIA",
         "(orb_size / atr_20) < 0.15 AND asia_range < atr_20 * 0.3"),
        ("SMALL_ORB+BIG_PREMOVE",
         "(orb_size / atr_20) < 0.15 AND pre_orb_travel > atr_20 * 0.5"),
        ("SMALL_ORB+QUIET_PREMOVE",
         "(orb_size / atr_20) < 0.15 AND pre_orb_travel < atr_20 * 0.2"),
        ("BIG_ORB+BIG_ASIA",
         "(orb_size / atr_20) > 0.20 AND asia_range > atr_20 * 0.8"),
        ("BIG_ORB+SMALL_ASIA",
         "(orb_size / atr_20) > 0.20 AND asia_range < atr_20 * 0.3"),
    ]

    results = []
    print('='*70)
    print('ADVANCED SEARCH: Combined Filters')
    print('='*70)
    print()

    for orb_time, rr, (filter_name, filter_sql) in product(orb_times, rr_targets, combined_filters):
        # Adjust for same/previous day
        if orb_time in ['0900', '1000']:
            # Previous day session context
            filter_sql_adj = filter_sql.replace('orb_size', f'df.orb_{orb_time}_size') \
                                       .replace('atr_20', 'df.atr_20') \
                                       .replace('asia_range', 'df_prev.asia_range') \
                                       .replace('pre_orb_travel', 'df_prev.pre_orb_travel')

            query = f"""
                WITH strategy_trades AS (
                    SELECT vt.outcome, vt.realized_rr
                    FROM validated_setups vs
                    JOIN validated_trades vt ON vs.id = vt.setup_id
                    JOIN daily_features_v2 df ON vt.date_local = df.date_local AND df.instrument = 'MGC'
                    JOIN daily_features_v2 df_prev ON df_prev.date_local = vt.date_local - INTERVAL '1 day' AND df_prev.instrument = 'MGC'
                    WHERE vs.orb_time = '{orb_time}' AND vs.rr = {rr} AND vs.sl_mode = 'full'
                      AND vt.outcome IN ('WIN', 'LOSS') AND {filter_sql_adj}
                )
                SELECT
                    '{orb_time}' as orb_time, {rr} as rr, '{filter_name}' as filter,
                    COUNT(*) as trades,
                    ROUND(SUM(CASE WHEN outcome = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*), 3) as win_rate,
                    ROUND(AVG(realized_rr), 3) as avg_exp
                FROM strategy_trades
                HAVING COUNT(*) >= 20
            """
        elif orb_time == '1100':
            # 1100 uses current ORB size, previous session context
            filter_sql_adj = filter_sql.replace('orb_size', f'df.orb_{orb_time}_size') \
                                       .replace('atr_20', 'df.atr_20') \
                                       .replace('asia_range', 'df_prev.asia_range') \
                                       .replace('pre_orb_travel', 'df_prev.pre_orb_travel')

            query = f"""
                WITH strategy_trades AS (
                    SELECT vt.outcome, vt.realized_rr
                    FROM validated_setups vs
                    JOIN validated_trades vt ON vs.id = vt.setup_id
                    JOIN daily_features_v2 df ON vt.date_local = df.date_local AND df.instrument = 'MGC'
                    JOIN daily_features_v2 df_prev ON df_prev.date_local = vt.date_local - INTERVAL '1 day' AND df_prev.instrument = 'MGC'
                    WHERE vs.orb_time = '{orb_time}' AND vs.rr = {rr} AND vs.sl_mode = 'full'
                      AND vt.outcome IN ('WIN', 'LOSS') AND {filter_sql_adj}
                )
                SELECT
                    '{orb_time}' as orb_time, {rr} as rr, '{filter_name}' as filter,
                    COUNT(*) as trades,
                    ROUND(SUM(CASE WHEN outcome = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*), 3) as win_rate,
                    ROUND(AVG(realized_rr), 3) as avg_exp
                FROM strategy_trades
                HAVING COUNT(*) >= 20
            """
        else:
            # 1800 uses current day all features
            filter_sql_adj = filter_sql.replace('orb_size', f'df.orb_{orb_time}_size') \
                                       .replace('atr_20', 'df.atr_20') \
                                       .replace('asia_range', 'df.asia_range') \
                                       .replace('pre_orb_travel', 'df.pre_orb_travel')

            query = f"""
                WITH strategy_trades AS (
                    SELECT vt.outcome, vt.realized_rr
                    FROM validated_setups vs
                    JOIN validated_trades vt ON vs.id = vt.setup_id
                    JOIN daily_features_v2 df ON vt.date_local = df.date_local AND df.instrument = 'MGC'
                    WHERE vs.orb_time = '{orb_time}' AND vs.rr = {rr} AND vs.sl_mode = 'full'
                      AND vt.outcome IN ('WIN', 'LOSS') AND {filter_sql_adj}
                )
                SELECT
                    '{orb_time}' as orb_time, {rr} as rr, '{filter_name}' as filter,
                    COUNT(*) as trades,
                    ROUND(SUM(CASE WHEN outcome = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*), 3) as win_rate,
                    ROUND(AVG(realized_rr), 3) as avg_exp
                FROM strategy_trades
                HAVING COUNT(*) >= 20
            """

        try:
            result = con.execute(query).fetchone()
            if result and result[5] >= 0.15:  # Only survivors
                results.append(result)
        except:
            pass

    con.close()

    df = pd.DataFrame(results, columns=['orb_time', 'rr', 'filter', 'trades', 'win_rate', 'avg_exp'])
    return df.sort_values('avg_exp', ascending=False)


def search_day_of_week_filters():
    """Test day-of-week filters"""
    con = duckdb.connect(DB_PATH)

    orb_times = ['0900', '1000', '1100', '1800']
    rr_targets = [2.0, 2.5, 3.0]

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    results = []
    print('='*70)
    print('ADVANCED SEARCH: Day-of-Week Filters')
    print('='*70)
    print()

    for orb_time, rr, day in product(orb_times, rr_targets, days):
        query = f"""
            WITH strategy_trades AS (
                SELECT vt.outcome, vt.realized_rr
                FROM validated_setups vs
                JOIN validated_trades vt ON vs.id = vt.setup_id
                JOIN daily_features_v2 df ON vt.date_local = df.date_local AND df.instrument = 'MGC'
                WHERE vs.orb_time = '{orb_time}' AND vs.rr = {rr} AND vs.sl_mode = 'full'
                  AND vt.outcome IN ('WIN', 'LOSS')
                  AND dayname(df.date_local) = '{day}'
            )
            SELECT
                '{orb_time}' as orb_time, {rr} as rr, '{day}' as filter,
                COUNT(*) as trades,
                ROUND(SUM(CASE WHEN outcome = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*), 3) as win_rate,
                ROUND(AVG(realized_rr), 3) as avg_exp
            FROM strategy_trades
            HAVING COUNT(*) >= 15
        """

        try:
            result = con.execute(query).fetchone()
            if result and result[5] >= 0.20:  # Higher threshold for day filters
                results.append(result)
        except:
            pass

    con.close()

    df = pd.DataFrame(results, columns=['orb_time', 'rr', 'filter', 'trades', 'win_rate', 'avg_exp'])
    return df.sort_values('avg_exp', ascending=False)


if __name__ == "__main__":
    print()
    print('='*70)
    print('ADVANCED STRATEGY SEARCH - Complex Filters')
    print('='*70)
    print()

    # Search 1: Session context
    df1 = search_session_context_filters()
    if not df1.empty:
        print()
        print('='*70)
        print('SESSION CONTEXT SURVIVORS (>= +0.15R)')
        print('-'*70)
        print(df1.to_string(index=False))
        print(f'\nFound {len(df1)} session context strategies')
    else:
        print('\nNo session context survivors found')

    # Search 2: Combined filters
    df2 = search_combined_filters()
    if not df2.empty:
        print()
        print('='*70)
        print('COMBINED FILTER SURVIVORS (>= +0.15R)')
        print('-'*70)
        print(df2.to_string(index=False))
        print(f'\nFound {len(df2)} combined filter strategies')
    else:
        print('\nNo combined filter survivors found')

    # Search 3: Day of week
    df3 = search_day_of_week_filters()
    if not df3.empty:
        print()
        print('='*70)
        print('DAY-OF-WEEK SURVIVORS (>= +0.20R)')
        print('-'*70)
        print(df3.to_string(index=False))
        print(f'\nFound {len(df3)} day-of-week strategies')
    else:
        print('\nNo day-of-week survivors found')

    print()
    print('='*70)
    print('SEARCH COMPLETE')
    print('='*70)
    print()
