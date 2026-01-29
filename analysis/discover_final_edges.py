"""
FINAL EDGE SEARCH - Multi-Day Patterns, Volatility Regimes, Momentum
====================================================================

Tests patterns using ONLY available columns (no lookahead):
1. Multi-day consecutive failures → reversal
2. Volatility regime filters (high/low ATR environments)
3. Momentum exhaustion (large pre-ORB moves → fade)
4. ORB expansion patterns (tight Asia → explosive ORB)
"""

import duckdb
import pandas as pd
from itertools import product

DB_PATH = "data/db/gold.db"


def search_consecutive_failure_patterns():
    """Test if consecutive ORB failures predict reversal"""
    con = duckdb.connect(DB_PATH)

    orb_times = ['0900', '1000', '1100', '1800']
    rr_targets = [2.0, 2.5, 3.0]

    results = []
    print('='*70)
    print('MULTI-DAY PATTERN SEARCH: Consecutive Failures')
    print('='*70)
    print()

    # Pattern: Both 0900 and 1000 failed yesterday → Trade 1000 today
    for rr in rr_targets:
        query = f"""
            WITH prev_day AS (
                SELECT
                    date_local,
                    orb_0900_outcome as prev_0900,
                    orb_1000_outcome as prev_1000
                FROM daily_features_v2
                WHERE instrument = 'MGC'
            ),
            strategy_trades AS (
                SELECT
                    vt.outcome,
                    vt.realized_rr
                FROM validated_setups vs
                JOIN validated_trades vt ON vs.id = vt.setup_id
                JOIN daily_features_v2 df ON vt.date_local = df.date_local AND df.instrument = 'MGC'
                JOIN prev_day pd ON pd.date_local = vt.date_local - INTERVAL '1 day'
                WHERE vs.orb_time = '1000'
                  AND vs.rr = {rr}
                  AND vs.sl_mode = 'full'
                  AND vt.outcome IN ('WIN', 'LOSS')
                  AND pd.prev_0900 = 'LOSS'
                  AND pd.prev_1000 = 'LOSS'
            )
            SELECT
                '1000' as orb_time,
                {rr} as rr,
                'BOTH_PREV_LOSS' as filter,
                COUNT(*) as trades,
                ROUND(SUM(CASE WHEN outcome = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*), 3) as win_rate,
                ROUND(AVG(realized_rr), 3) as avg_exp
            FROM strategy_trades
            HAVING COUNT(*) >= 15
        """

        try:
            result = con.execute(query).fetchone()
            if result and result[5] >= 0.15:
                results.append(result)
                print(f"✅ FOUND: {result[0]} RR={result[1]} {result[2]} → {result[5]:+.3f}R ({result[3]} trades, {result[4]:.1%} WR)")
        except Exception as e:
            print(f"Error testing BOTH_PREV_LOSS pattern: {e}")

    # Pattern: 0900 lost → Trade 1000 (single failure)
    for rr in rr_targets:
        query = f"""
            WITH prev_day AS (
                SELECT
                    date_local,
                    orb_0900_outcome as prev_0900
                FROM daily_features_v2
                WHERE instrument = 'MGC'
            ),
            strategy_trades AS (
                SELECT
                    vt.outcome,
                    vt.realized_rr
                FROM validated_setups vs
                JOIN validated_trades vt ON vs.id = vt.setup_id
                JOIN daily_features_v2 df ON vt.date_local = df.date_local AND df.instrument = 'MGC'
                JOIN prev_day pd ON pd.date_local = vt.date_local - INTERVAL '1 day'
                WHERE vs.orb_time = '1000'
                  AND vs.rr = {rr}
                  AND vs.sl_mode = 'full'
                  AND vt.outcome IN ('WIN', 'LOSS')
                  AND pd.prev_0900 = 'LOSS'
            )
            SELECT
                '1000' as orb_time,
                {rr} as rr,
                '0900_PREV_LOSS' as filter,
                COUNT(*) as trades,
                ROUND(SUM(CASE WHEN outcome = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*), 3) as win_rate,
                ROUND(AVG(realized_rr), 3) as avg_exp
            FROM strategy_trades
            HAVING COUNT(*) >= 20
        """

        try:
            result = con.execute(query).fetchone()
            if result and result[5] >= 0.15:
                results.append(result)
                print(f"✅ FOUND: {result[0]} RR={result[1]} {result[2]} → {result[5]:+.3f}R ({result[3]} trades, {result[4]:.1%} WR)")
        except Exception as e:
            pass

    con.close()

    if results:
        df = pd.DataFrame(results, columns=['orb_time', 'rr', 'filter', 'trades', 'win_rate', 'avg_exp'])
        return df.sort_values('avg_exp', ascending=False)
    else:
        return pd.DataFrame()


def search_volatility_regime_filters():
    """Test if volatility regime predicts ORB success"""
    con = duckdb.connect(DB_PATH)

    orb_times = ['0900', '1000', '1100', '1800']
    rr_targets = [2.0, 2.5, 3.0]

    # Volatility regimes (ATR percentiles)
    volatility_filters = [
        ("LOW_VOL", "atr_20 < (SELECT PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY atr_20) FROM daily_features_v2 WHERE instrument = 'MGC' AND atr_20 IS NOT NULL)"),
        ("HIGH_VOL", "atr_20 > (SELECT PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY atr_20) FROM daily_features_v2 WHERE instrument = 'MGC' AND atr_20 IS NOT NULL)"),
        ("EXTREME_VOL", "atr_20 > (SELECT PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY atr_20) FROM daily_features_v2 WHERE instrument = 'MGC' AND atr_20 IS NOT NULL)"),
    ]

    results = []
    print()
    print('='*70)
    print('VOLATILITY REGIME SEARCH')
    print('='*70)
    print()

    for orb_time, rr, (filter_name, filter_sql) in product(orb_times, rr_targets, volatility_filters):
        query = f"""
            WITH strategy_trades AS (
                SELECT
                    vt.outcome,
                    vt.realized_rr
                FROM validated_setups vs
                JOIN validated_trades vt ON vs.id = vt.setup_id
                JOIN daily_features_v2 df ON vt.date_local = df.date_local AND df.instrument = 'MGC'
                WHERE vs.orb_time = '{orb_time}'
                  AND vs.rr = {rr}
                  AND vs.sl_mode = 'full'
                  AND vt.outcome IN ('WIN', 'LOSS')
                  AND {filter_sql}
            )
            SELECT
                '{orb_time}' as orb_time,
                {rr} as rr,
                '{filter_name}' as filter,
                COUNT(*) as trades,
                ROUND(SUM(CASE WHEN outcome = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*), 3) as win_rate,
                ROUND(AVG(realized_rr), 3) as avg_exp
            FROM strategy_trades
            HAVING COUNT(*) >= 20
        """

        try:
            result = con.execute(query).fetchone()
            if result and result[5] >= 0.15:
                results.append(result)
                print(f"✅ FOUND: {result[0]} RR={result[1]} {result[2]} → {result[5]:+.3f}R ({result[3]} trades, {result[4]:.1%} WR)")
        except Exception as e:
            pass

    con.close()

    if results:
        df = pd.DataFrame(results, columns=['orb_time', 'rr', 'filter', 'trades', 'win_rate', 'avg_exp'])
        return df.sort_values('avg_exp', ascending=False)
    else:
        return pd.DataFrame()


def search_momentum_exhaustion_filters():
    """Test if large pre-ORB moves predict fades"""
    con = duckdb.connect(DB_PATH)

    orb_times = ['0900', '1000', '1100']
    rr_targets = [2.0, 2.5, 3.0]

    # Momentum exhaustion patterns
    momentum_filters = [
        ("BIG_ASIA_EXPANSION", "asia_range > atr_20 * 1.0"),
        ("HUGE_ASIA_EXPANSION", "asia_range > atr_20 * 1.5"),
        ("TIGHT_ASIA", "asia_range < atr_20 * 0.5"),
    ]

    results = []
    print()
    print('='*70)
    print('MOMENTUM EXHAUSTION SEARCH')
    print('='*70)
    print()

    for orb_time, rr, (filter_name, filter_sql) in product(orb_times, rr_targets, momentum_filters):
        # Use PREVIOUS day Asia for 0900/1000, SAME day for 1100
        if orb_time in ['0900', '1000']:
            join_condition = """
                JOIN daily_features_v2 df_prev
                    ON df_prev.date_local = vt.date_local - INTERVAL '1 day'
                    AND df_prev.instrument = 'MGC'
            """
            filter_sql_adj = filter_sql.replace('asia_range', 'df_prev.asia_range') \
                                       .replace('atr_20', 'df_prev.atr_20')
        else:
            join_condition = """
                JOIN daily_features_v2 df
                    ON df.date_local = vt.date_local
                    AND df.instrument = 'MGC'
            """
            filter_sql_adj = filter_sql.replace('asia_range', 'df.asia_range') \
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
            HAVING COUNT(*) >= 20
        """

        try:
            result = con.execute(query).fetchone()
            if result and result[5] >= 0.15:
                results.append(result)
                print(f"✅ FOUND: {result[0]} RR={result[1]} {result[2]} → {result[5]:+.3f}R ({result[3]} trades, {result[4]:.1%} WR)")
        except Exception as e:
            pass

    con.close()

    if results:
        df = pd.DataFrame(results, columns=['orb_time', 'rr', 'filter', 'trades', 'win_rate', 'avg_exp'])
        return df.sort_values('avg_exp', ascending=False)
    else:
        return pd.DataFrame()


def search_expansion_compression_filters():
    """Test tight Asia → explosive ORB patterns"""
    con = duckdb.connect(DB_PATH)

    orb_times = ['0900', '1000', '1100']
    rr_targets = [2.0, 2.5, 3.0]

    # Compression → Expansion patterns
    expansion_filters = [
        ("TINY_ASIA_BIG_ORB", "asia_range < atr_20 * 0.3 AND orb_size > atr_20 * 0.15"),
        ("TIGHT_ASIA_ANY_ORB", "asia_range < atr_20 * 0.4"),
        ("BIG_ASIA_TINY_ORB", "asia_range > atr_20 * 0.8 AND orb_size < atr_20 * 0.15"),
    ]

    results = []
    print()
    print('='*70)
    print('EXPANSION/COMPRESSION SEARCH')
    print('='*70)
    print()

    for orb_time, rr, (filter_name, filter_sql) in product(orb_times, rr_targets, expansion_filters):
        # Use PREVIOUS day Asia for 0900/1000
        if orb_time in ['0900', '1000']:
            filter_sql_adj = filter_sql.replace('orb_size', f'df.orb_{orb_time}_size') \
                                       .replace('asia_range', 'df_prev.asia_range') \
                                       .replace('atr_20', 'df.atr_20')

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
                HAVING COUNT(*) >= 15
            """
        else:  # 1100
            filter_sql_adj = filter_sql.replace('orb_size', f'df.orb_{orb_time}_size') \
                                       .replace('asia_range', 'df_prev.asia_range') \
                                       .replace('atr_20', 'df.atr_20')

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
                HAVING COUNT(*) >= 15
            """

        try:
            result = con.execute(query).fetchone()
            if result and result[5] >= 0.15:
                results.append(result)
                print(f"✅ FOUND: {result[0]} RR={result[1]} {result[2]} → {result[5]:+.3f}R ({result[3]} trades, {result[4]:.1%} WR)")
        except Exception as e:
            pass

    con.close()

    if results:
        df = pd.DataFrame(results, columns=['orb_time', 'rr', 'filter', 'trades', 'win_rate', 'avg_exp'])
        return df.sort_values('avg_exp', ascending=False)
    else:
        return pd.DataFrame()


if __name__ == "__main__":
    print()
    print('='*70)
    print('FINAL EDGE SEARCH - Advanced Patterns')
    print('='*70)
    print()

    all_results = []

    # Search 1: Consecutive failures
    df1 = search_consecutive_failure_patterns()
    if not df1.empty:
        all_results.append(df1)

    # Search 2: Volatility regimes
    df2 = search_volatility_regime_filters()
    if not df2.empty:
        all_results.append(df2)

    # Search 3: Momentum exhaustion
    df3 = search_momentum_exhaustion_filters()
    if not df3.empty:
        all_results.append(df3)

    # Search 4: Expansion/compression
    df4 = search_expansion_compression_filters()
    if not df4.empty:
        all_results.append(df4)

    # Combine and display all results
    if all_results:
        combined = pd.concat(all_results, ignore_index=True)
        combined = combined.sort_values('avg_exp', ascending=False)

        print()
        print('='*70)
        print('ALL DISCOVERED EDGES (>= +0.15R)')
        print('='*70)
        print(combined.to_string(index=False))
        print()
        print(f'Total discoveries: {len(combined)}')
    else:
        print()
        print('='*70)
        print('NO NEW EDGES FOUND')
        print('='*70)
        print()
        print('All tested patterns either:')
        print('- Had insufficient sample size (< 15-20 trades)')
        print('- Failed survival threshold (< +0.15R)')
        print('- Already discovered in previous searches')

    print()
    print('='*70)
    print('FINAL EDGE SEARCH COMPLETE')
    print('='*70)
    print()
