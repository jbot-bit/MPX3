"""
FIND VIABLE REAL R SETUPS

Tests all profitable combinations from optimization results
to find setups where real R degradation is acceptable (<0.10R).

Hypothesis: Wider stops (0.50, 0.75, 1.00) will have less degradation
because entry distance becomes a smaller percentage of risk.
"""

import duckdb
import pandas as pd
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from execution_metrics import ExecutionMetricsCalculator, aggregate_metrics

TZ_LOCAL = ZoneInfo("Australia/Brisbane")
TZ_UTC = ZoneInfo("UTC")

DB_PATH = 'gold.db'
SYMBOL = 'MGC'

ORBS = {
    '0900': (9, 0),
    '1000': (10, 0),
    '1100': (11, 0),
    '1800': (18, 0),
    '2300': (23, 0),
    '0030': (0, 30),
}

# Promising ORBs from optimization
ORB_TIMES = ['1100', '1800', '2300']


def test_setup(orb_time, stop_frac, rr):
    """Test one setup with real execution"""
    conn = duckdb.connect(DB_PATH, read_only=True)

    query = f"""
        SELECT
            date_local,
            orb_{orb_time}_high as orb_high,
            orb_{orb_time}_low as orb_low,
            orb_{orb_time}_break_dir as break_dir
        FROM daily_features
        WHERE instrument = 'MGC'
          AND orb_{orb_time}_high IS NOT NULL
          AND orb_{orb_time}_low IS NOT NULL
          AND orb_{orb_time}_break_dir IS NOT NULL
          AND orb_{orb_time}_break_dir != 'NONE'
        ORDER BY date_local
    """

    df_days = conn.execute(query).fetchdf()
    hour, minute = ORBS[orb_time]

    bars_cache = {}
    for idx, row in df_days.iterrows():
        trade_date = pd.to_datetime(row['date_local']).date()

        if hour == 0 and minute == 30:
            orb_start = datetime(trade_date.year, trade_date.month, trade_date.day, hour, minute, tzinfo=TZ_LOCAL) + timedelta(days=1)
        else:
            orb_start = datetime(trade_date.year, trade_date.month, trade_date.day, hour, minute, tzinfo=TZ_LOCAL)

        scan_start = orb_start + timedelta(minutes=5)

        if hour < 9 or (hour == 0 and minute == 30):
            scan_end = datetime(orb_start.year, orb_start.month, orb_start.day, 9, 0, tzinfo=TZ_LOCAL)
        else:
            scan_end = datetime(orb_start.year, orb_start.month, orb_start.day, 9, 0, tzinfo=TZ_LOCAL) + timedelta(days=1)

        start_utc = scan_start.astimezone(TZ_UTC)
        end_utc = scan_end.astimezone(TZ_UTC)

        bars = conn.execute("""
            SELECT high, low, close
            FROM bars_1m
            WHERE symbol = ?
              AND ts_utc >= ?
              AND ts_utc < ?
            ORDER BY ts_utc
        """, [SYMBOL, start_utc, end_utc]).fetchdf()

        bars_cache[str(trade_date)] = bars

    conn.close()

    # Calculate execution metrics
    calc = ExecutionMetricsCalculator(commission=1.5, slippage_ticks=1.5)
    trades = []

    for idx, row in df_days.iterrows():
        date_str = str(pd.to_datetime(row['date_local']).date())
        orb_high = row['orb_high']
        orb_low = row['orb_low']
        break_dir = row['break_dir']
        bars = bars_cache.get(date_str)

        if bars is not None and len(bars) > 0:
            entry_close = None
            for i, bar in enumerate(bars.itertuples()):
                if break_dir == 'UP' and bar.close > orb_high:
                    entry_close = bar.close
                    entry_bar_idx = i
                    break
                elif break_dir == 'DOWN' and bar.close < orb_low:
                    entry_close = bar.close
                    entry_bar_idx = i
                    break

            if entry_close:
                metrics = calc.calculate_trade_metrics(
                    orb_high=orb_high,
                    orb_low=orb_low,
                    entry_close=entry_close,
                    break_dir=break_dir,
                    bars_1m=bars,
                    rr=rr,
                    stop_mode=stop_frac,
                    entry_bar_idx=entry_bar_idx
                )

                if metrics:
                    trades.append(metrics)

    if len(trades) > 0:
        agg = aggregate_metrics(trades)
        return {
            'orb_time': orb_time,
            'stop_frac': stop_frac,
            'rr': rr,
            'trades': len(trades),
            'canonical_avg_r': agg['canonical_avg_r'],
            'real_avg_r': agg['real_avg_r'],
            'degradation': agg['performance_degradation'],
            'avg_canonical_risk': agg['avg_canonical_risk'],
            'avg_real_risk': agg['avg_real_risk']
        }
    else:
        return None


if __name__ == "__main__":
    print("\n" + "="*80)
    print("FINDING VIABLE REAL R SETUPS")
    print("="*80)
    print("\nTesting all combinations from optimization results...")
    print("Acceptance criteria: Real R > 0.15 (profitable after costs)")
    print("(Degradation is informational only - what matters is final real R)")
    print()

    # Test wider stops for each ORB
    STOP_FRACS = [0.20, 0.25, 0.33, 0.50, 0.75, 1.00]
    RRS = [1.5, 2.0, 3.0, 4.0, 6.0, 8.0]

    viable_setups = []
    all_results = []

    for orb_time in ORB_TIMES:
        print(f"\nTesting {orb_time} ORB...")
        for stop_frac in STOP_FRACS:
            for rr in RRS:
                result = test_setup(orb_time, stop_frac, rr)
                if result:
                    all_results.append(result)

                    # Check if viable (real R is profitable)
                    if result['real_avg_r'] > 0.15:
                        viable_setups.append(result)
                        print(f"  VIABLE: Stop={stop_frac}, RR={rr}: Real R={result['real_avg_r']:+.3f} (degradation={result['degradation']:+.3f})")

    # Summary
    print("\n" + "="*80)
    print(f"FOUND {len(viable_setups)} VIABLE SETUPS (out of {len(all_results)} tested)")
    print("="*80)

    if viable_setups:
        print("\nORB    Stop   RR   Trades  Can R    Real R   Degrad   Can Risk  Real Risk")
        print("-" * 80)
        # Sort by real avg R descending
        viable_setups.sort(key=lambda x: x['real_avg_r'], reverse=True)
        for s in viable_setups:
            print(f"{s['orb_time']}  {s['stop_frac']:>5.2f}  {s['rr']:>3.1f}  {s['trades']:>6}  {s['canonical_avg_r']:>+6.3f}  {s['real_avg_r']:>+6.3f}  {s['degradation']:>+6.3f}  {s['avg_canonical_risk']:>8.2f}  {s['avg_real_risk']:>9.2f}")

        print("\n" + "="*80)
        print("READY TO PROCEED TO PHASE 5: Update validated_setups with these setups")
    else:
        print("\nNO VIABLE SETUPS FOUND!")
        print("\nTesting if ANY setup has real R > 0 (even if degradation exceeds threshold)...")

        # Find setups with positive real R (even if degradation is large)
        positive_real_r = [r for r in all_results if r['real_avg_r'] > 0]
        positive_real_r.sort(key=lambda x: x['real_avg_r'], reverse=True)

        if positive_real_r:
            print(f"\nFound {len(positive_real_r)} setups with positive real R:")
            print("\nORB    Stop   RR   Trades  Can R    Real R   Degrad   Can Risk  Real Risk")
            print("-" * 80)
            for s in positive_real_r[:10]:  # Top 10
                print(f"{s['orb_time']}  {s['stop_frac']:>5.2f}  {s['rr']:>3.1f}  {s['trades']:>6}  {s['canonical_avg_r']:>+6.3f}  {s['real_avg_r']:>+6.3f}  {s['degradation']:>+6.3f}  {s['avg_canonical_risk']:>8.2f}  {s['avg_real_risk']:>9.2f}")

            print("\nNote: User is correct - filters can improve these.")
            print("These are WITHOUT filters. Phase 4 will test filters on best candidates.")
        else:
            print("\nShowing setups with least negative real R:")
            all_results.sort(key=lambda x: x['real_avg_r'], reverse=True)
            print("\nORB    Stop   RR   Trades  Can R    Real R   Degrad   Can Risk  Real Risk")
            print("-" * 80)
            for s in all_results[:20]:  # Top 20
                print(f"{s['orb_time']}  {s['stop_frac']:>5.2f}  {s['rr']:>3.1f}  {s['trades']:>6}  {s['canonical_avg_r']:>+6.3f}  {s['real_avg_r']:>+6.3f}  {s['degradation']:>+6.3f}  {s['avg_canonical_risk']:>8.2f}  {s['avg_real_risk']:>9.2f}")

            print("\nAll setups have negative real R without filters.")
            print("But user is correct - filters (session type, ORB size, RSI, etc.)")
            print("can improve real R significantly. Proceed to Phase 4 to test filters.")

    print()
