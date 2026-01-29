"""
HONEST FILTER TESTING - NO LOOKAHEAD BIAS
==========================================

Tests if 1100/1800 filters work using ONLY information available at signal time.

For 1100 ORB (11:00):
- Use PREVIOUS day Asia/London patterns (known at 11:00)
- Use current ORB size (known at 11:05)
- Use historical ATR (known always)

For 1800 ORB (18:00):
- Use SAME day Asia (complete at 17:00, before 18:00 ORB)
- Use PREVIOUS day London (current London not complete yet)
- Use current ORB size (known at 18:05)
"""

import duckdb
import sys
from datetime import date

DB_PATH = "data/db/gold.db"

def test_1100_with_honest_filters():
    """Test 1100 ORB with NO LOOKAHEAD"""
    con = duckdb.connect(DB_PATH)

    print('='*70)
    print('TEST 1: 1100 ORB + SMALL ORB SIZE (<15% ATR)')
    print('NO LOOKAHEAD - ORB size known at 11:05, ATR from previous data')
    print('-'*70)

    result = con.execute("""
        SELECT
            COUNT(*) as trades,
            ROUND(SUM(CASE WHEN vt.outcome = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*), 3) as win_rate,
            ROUND(AVG(vt.realized_rr), 3) as avg_exp,
            ROUND(MIN(vt.realized_rr), 3) as min_exp,
            ROUND(MAX(vt.realized_rr), 3) as max_exp
        FROM validated_setups vs
        JOIN validated_trades vt ON vs.id = vt.setup_id
        JOIN daily_features_v2 df ON vt.date_local = df.date_local AND df.instrument = 'MGC'
        WHERE vs.orb_time = '1100'
          AND vt.outcome IN ('WIN', 'LOSS')
          AND (df.orb_1100_size / df.atr_20) < 0.15
    """).df()

    print(result.to_string(index=False))
    print()

    if result['avg_exp'].values[0] >= 0.05:
        print(f'RESULT: VIABLE FILTER (+{result["avg_exp"].values[0]:.3f}R, n={result["trades"].values[0]})')
    else:
        print(f'RESULT: FAILS (+{result["avg_exp"].values[0]:.3f}R < +0.05R threshold)')
    print()

    print('='*70)
    print('TEST 2: 1100 ORB + PREVIOUS DAY A2_EXPANDED')
    print('NO LOOKAHEAD - Previous Asia data known at 11:00')
    print('-'*70)

    result2 = con.execute("""
        SELECT
            COUNT(*) as trades,
            ROUND(SUM(CASE WHEN vt.outcome = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*), 3) as win_rate,
            ROUND(AVG(vt.realized_rr), 3) as avg_exp
        FROM validated_setups vs
        JOIN validated_trades vt ON vs.id = vt.setup_id
        JOIN daily_features_v2 df_prev
            ON df_prev.date_local = vt.date_local - INTERVAL '1 day'
            AND df_prev.instrument = 'MGC'
        WHERE vs.orb_time = '1100'
          AND vt.outcome IN ('WIN', 'LOSS')
          AND df_prev.asia_type_code = 'A2_EXPANDED'
    """).df()

    print(result2.to_string(index=False))
    print()

    if result2['avg_exp'].values[0] >= 0.05:
        print(f'RESULT: VIABLE FILTER (+{result2["avg_exp"].values[0]:.3f}R, n={result2["trades"].values[0]})')
    else:
        print(f'RESULT: FAILS (+{result2["avg_exp"].values[0]:.3f}R < +0.05R threshold)')
    print()

    print('='*70)
    print('TEST 3: 1100 ORB + PREVIOUS DAY L2_SWEEP_LOW')
    print('NO LOOKAHEAD - Previous London data known at 11:00')
    print('-'*70)

    result3 = con.execute("""
        SELECT
            COUNT(*) as trades,
            ROUND(SUM(CASE WHEN vt.outcome = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*), 3) as win_rate,
            ROUND(AVG(vt.realized_rr), 3) as avg_exp
        FROM validated_setups vs
        JOIN validated_trades vt ON vs.id = vt.setup_id
        JOIN daily_features_v2 df_prev
            ON df_prev.date_local = vt.date_local - INTERVAL '1 day'
            AND df_prev.instrument = 'MGC'
        WHERE vs.orb_time = '1100'
          AND vt.outcome IN ('WIN', 'LOSS')
          AND df_prev.london_type_code = 'L2_SWEEP_LOW'
    """).df()

    print(result3.to_string(index=False))
    print()

    if result3['avg_exp'].values[0] >= 0.05:
        print(f'RESULT: VIABLE FILTER (+{result3["avg_exp"].values[0]:.3f}R, n={result3["trades"].values[0]})')
    else:
        print(f'RESULT: FAILS (+{result3["avg_exp"].values[0]:.3f}R < +0.05R threshold)')
    print()

    con.close()


def test_1800_with_honest_filters():
    """Test 1800 ORB with NO LOOKAHEAD"""
    con = duckdb.connect(DB_PATH)

    print('='*70)
    print('TEST 4: 1800 ORB + SAME DAY A2_EXPANDED')
    print('NO LOOKAHEAD - Asia complete at 17:00, before 18:00 ORB')
    print('-'*70)

    result = con.execute("""
        SELECT
            COUNT(*) as trades,
            ROUND(SUM(CASE WHEN vt.outcome = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*), 3) as win_rate,
            ROUND(AVG(vt.realized_rr), 3) as avg_exp
        FROM validated_setups vs
        JOIN validated_trades vt ON vs.id = vt.setup_id
        JOIN daily_features_v2 df ON vt.date_local = df.date_local AND df.instrument = 'MGC'
        WHERE vs.orb_time = '1800'
          AND vt.outcome IN ('WIN', 'LOSS')
          AND df.asia_type_code = 'A2_EXPANDED'
    """).df()

    print(result.to_string(index=False))
    print()

    if result['avg_exp'].values[0] >= 0.05:
        print(f'RESULT: VIABLE FILTER (+{result["avg_exp"].values[0]:.3f}R, n={result["trades"].values[0]})')
    else:
        print(f'RESULT: FAILS (+{result["avg_exp"].values[0]:.3f}R < +0.05R threshold)')
    print()

    print('='*70)
    print('TEST 5: 1800 ORB + SMALL ORB SIZE (<15% ATR)')
    print('NO LOOKAHEAD - ORB size known at 18:05')
    print('-'*70)

    result2 = con.execute("""
        SELECT
            COUNT(*) as trades,
            ROUND(SUM(CASE WHEN vt.outcome = 'WIN' THEN 1.0 ELSE 0 END) / COUNT(*), 3) as win_rate,
            ROUND(AVG(vt.realized_rr), 3) as avg_exp
        FROM validated_setups vs
        JOIN validated_trades vt ON vs.id = vt.setup_id
        JOIN daily_features_v2 df ON vt.date_local = df.date_local AND df.instrument = 'MGC'
        WHERE vs.orb_time = '1800'
          AND vt.outcome IN ('WIN', 'LOSS')
          AND (df.orb_1800_size / df.atr_20) < 0.15
    """).df()

    print(result2.to_string(index=False))
    print()

    if result2['avg_exp'].values[0] >= 0.05:
        print(f'RESULT: VIABLE FILTER (+{result2["avg_exp"].values[0]:.3f}R, n={result2["trades"].values[0]})')
    else:
        print(f'RESULT: FAILS (+{result2["avg_exp"].values[0]:.3f}R < +0.05R threshold)')
    print()

    con.close()


def summary():
    """Summarize honest filter results"""
    print('='*70)
    print('SUMMARY: HONEST FILTERS (No Lookahead)')
    print('='*70)
    print()
    print('RUN THIS SCRIPT TO TEST FILTERS WITH NO LOOKAHEAD BIAS')
    print()
    print('Expected Results:')
    print('  - 1100 + SMALL_ORB: Should show positive expectancy')
    print('  - 1100 + PREV_A2: Will show if previous day patterns predict')
    print('  - 1100 + PREV_L2: Will show if previous day patterns predict')
    print('  - 1800 + SAME_A2: Should work (Asia complete before ORB)')
    print('  - 1800 + SMALL_ORB: Should show if size filter helps')
    print()


if __name__ == "__main__":
    print()
    print('='*70)
    print('HONEST FILTER TESTING - NO LOOKAHEAD BIAS')
    print('='*70)
    print()

    test_1100_with_honest_filters()
    test_1800_with_honest_filters()
    summary()

    print('DONE!')
    print()
