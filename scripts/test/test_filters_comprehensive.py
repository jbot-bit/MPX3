"""
COMPREHENSIVE FILTER TESTING

After broad search identifies promising setups, test if filters make them profitable.

Takes a specific ORB + stop/RR combination and tests it with various filters:
- Session type: CONSOLIDATION, SWEEP_HIGH, SWEEP_LOW, EXPANSION
- ORB size: Large (>1.5 ATR), Small (<0.8 ATR), Medium
- RSI: >70, <30, neutral
- Combinations: CONSOLIDATION + Small ORB, etc.

Usage: python test_filters_comprehensive.py 1000 0.75 8.0
"""

import sys
import duckdb
import pandas as pd
from datetime import datetime, timedelta

DB_PATH = 'data/db/gold.db'
SYMBOL = 'MGC'

COMMISSION = 1.0
SLIPPAGE_TICKS = 5
TICK_SIZE = 0.1
POINT_VALUE = 10.0

def simulate_with_stop_and_costs(bars_1m, orb_high, orb_low, rr, stop_fraction):
    """Simulate with fractional stop and realistic costs"""
    if len(bars_1m) == 0:
        return None

    orb_size = orb_high - orb_low

    # Find entry (close outside)
    entry_idx = None
    for i in range(len(bars_1m)):
        close = float(bars_1m.iloc[i]['close'])

        if close > orb_high or close < orb_low:
            direction = 'UP' if close > orb_high else 'DOWN'
            entry = close
            entry_idx = i
            break

    if entry_idx is None:
        return None

    # Stop at fraction of ORB from entry
    risk = orb_size * stop_fraction

    if direction == 'UP':
        stop = entry - risk
    else:
        stop = entry + risk

    target = entry + (rr * risk) if direction == 'UP' else entry - (rr * risk)

    # Check outcome
    for j in range(entry_idx + 1, len(bars_1m)):
        high = float(bars_1m.iloc[j]['high'])
        low = float(bars_1m.iloc[j]['low'])

        if direction == 'UP':
            if low <= stop:
                outcome_r = -1.0
                break
            elif high >= target:
                outcome_r = rr
                break
        else:
            if high >= stop:
                outcome_r = -1.0
                break
            elif low <= target:
                outcome_r = rr
                break
    else:
        outcome_r = 0.0

    # Subtract costs
    cost_dollars = COMMISSION + SLIPPAGE_TICKS * TICK_SIZE * POINT_VALUE
    cost_r = cost_dollars / (risk * POINT_VALUE)

    return outcome_r - cost_r


def main():
    """CLI entry point - runs filter testing"""
    if len(sys.argv) < 4:
        print("Usage: python test_filters_comprehensive.py <orb_time> <stop_frac> <rr>")
        print("Example: python test_filters_comprehensive.py 1000 0.75 8.0")
        sys.exit(1)

    orb_time = sys.argv[1]
    stop_fraction = float(sys.argv[2])
    rr = float(sys.argv[3])

    ORBS = {
        '0900': (9, 0),
        '1000': (10, 0),
        '1100': (11, 0),
        '1800': (18, 0),
        '2300': (23, 0),
        '0030': (0, 30),
    }

    if orb_time not in ORBS:
        print(f"Invalid ORB time. Must be one of: {', '.join(ORBS.keys())}")
        sys.exit(1)

    hour, minute = ORBS[orb_time]

    print("="*80)
    print(f"TESTING FILTERS: {orb_time} ORB, Stop={stop_fraction:.2f}, RR={rr:.1f}")
    print("="*80)
    print()

    conn = duckdb.connect(DB_PATH, read_only=True)

    # Load baseline data
    baseline_query = f"""
        SELECT
            date_local,
            orb_{orb_time}_high as orb_high,
            orb_{orb_time}_low as orb_low,
            orb_{orb_time}_size as orb_size,
            london_type,
            london_atr14,
            orb_{orb_time}_rsi as rsi
        FROM daily_features
        WHERE instrument = 'MGC'
          AND orb_{orb_time}_high IS NOT NULL
          AND orb_{orb_time}_low IS NOT NULL
        ORDER BY date_local
    """

    df_all = conn.execute(baseline_query).fetchdf()
    print(f"Loaded {len(df_all)} total days")
    print()

    # Define filters
    FILTERS = {
        'NO_FILTER': lambda df: df,
        'CONSOLIDATION': lambda df: df[df['london_type'] == 'CONSOLIDATION'],
        'SWEEP_HIGH': lambda df: df[df['london_type'] == 'SWEEP_HIGH'],
        'SWEEP_LOW': lambda df: df[df['london_type'] == 'SWEEP_LOW'],
        'EXPANSION': lambda df: df[df['london_type'] == 'EXPANSION'],
        'LARGE_ORB': lambda df: df[df['orb_size'] > 1.5 * df['london_atr14']],
        'SMALL_ORB': lambda df: df[df['orb_size'] < 0.8 * df['london_atr14']],
        'MEDIUM_ORB': lambda df: df[(df['orb_size'] >= 0.8 * df['london_atr14']) &
                                     (df['orb_size'] <= 1.5 * df['london_atr14'])],
        'RSI_HIGH': lambda df: df[df['rsi'] > 70],
        'RSI_LOW': lambda df: df[df['rsi'] < 30],
        'CONSOL_SMALL': lambda df: df[(df['london_type'] == 'CONSOLIDATION') &
                                       (df['orb_size'] < 0.8 * df['london_atr14'])],
        'SWEEP_HIGH_LARGE': lambda df: df[(df['london_type'] == 'SWEEP_HIGH') &
                                           (df['orb_size'] > 1.5 * df['london_atr14'])],
    }

    print("Testing filters...")
    print()

    results = []

    for filter_name, filter_func in FILTERS.items():
        df_filtered = filter_func(df_all.copy())

        if len(df_filtered) == 0:
            print(f"{filter_name:20s}: NO DAYS MATCHED")
            continue

        # Cache bars for filtered days
        bars_cache = {}
        for idx, row in df_filtered.iterrows():
            date_local = pd.to_datetime(row['date_local']).date()

            start_dt = datetime.combine(date_local, datetime.min.time()).replace(hour=hour, minute=minute+5)
            start_time = start_dt.strftime("%Y-%m-%d %H:%M:%S")
            end_dt = datetime.combine(date_local + timedelta(days=1), datetime.min.time()).replace(hour=hour)
            end_time = end_dt.strftime("%Y-%m-%d %H:%M:%S")

            bars_query = """
                SELECT
                    (ts_utc AT TIME ZONE 'Australia/Brisbane') as ts_local,
                    open, high, low, close
                FROM bars_1m
                WHERE symbol = ?
                  AND (ts_utc AT TIME ZONE 'Australia/Brisbane') > CAST(? AS TIMESTAMP)
                  AND (ts_utc AT TIME ZONE 'Australia/Brisbane') <= CAST(? AS TIMESTAMP)
                ORDER BY ts_local
            """

            bars = conn.execute(bars_query, [SYMBOL, start_time, end_time]).fetchdf()
            bars_cache[str(date_local)] = bars

        # Test on filtered days
        trade_results = []

        for idx, row in df_filtered.iterrows():
            date_local = str(pd.to_datetime(row['date_local']).date())
            orb_high = row['orb_high']
            orb_low = row['orb_low']

            bars = bars_cache.get(date_local)

            if bars is not None and len(bars) > 0:
                r_result = simulate_with_stop_and_costs(bars, orb_high, orb_low, rr, stop_fraction)

                if r_result is not None:
                    trade_results.append(r_result)

        if len(trade_results) > 0:
            count = len(trade_results)
            total_r = sum(trade_results)
            avg_r = total_r / count
            wins = len([r for r in trade_results if r > 0])
            wr = wins / count * 100
            be_wr = 100 / (rr + 1)

            results.append({
                'filter': filter_name,
                'trades': count,
                'wr': wr,
                'be_wr': be_wr,
                'avg_r': avg_r,
                'total_r': total_r
            })

            status = f"{filter_name:20s}: {count:3d} trades, {wr:5.1f}% WR, {avg_r:+.3f} avg R, {total_r:+7.1f}R"
            if avg_r > 0.10:
                print(f"{status} *** PROFITABLE ***")
            else:
                print(status)

    conn.close()

    print()
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print()

    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('avg_r', ascending=False)

    print(df_results.to_string(index=False))
    print()

    profitable = df_results[df_results['avg_r'] > 0.10]

    if len(profitable) > 0:
        print(f"Found {len(profitable)} PROFITABLE filter combinations:")
        print()

        for idx, row in profitable.iterrows():
            print(f"  {row['filter']}: {row['avg_r']:+.3f} avg R ({row['total_r']:+.1f}R total, {row['trades']:.0f} trades)")

        print()
        print("BEST FILTER:")
        best = profitable.iloc[0]
        print(f"  Filter: {best['filter']}")
        print(f"  Trades: {best['trades']:.0f}")
        print(f"  Win rate: {best['wr']:.1f}% (need {best['be_wr']:.1f}%)")
        print(f"  Avg R: {best['avg_r']:+.3f}")
        print(f"  Total R: {best['total_r']:+.1f}")
    else:
        print("NO PROFITABLE FILTERS FOUND for this setup")
        print()
        print("Try:")
        print("  - Different stop/RR combination")
        print("  - Different ORB time")
        print("  - More complex filter combinations")

    print()


if __name__ == "__main__":
    main()
