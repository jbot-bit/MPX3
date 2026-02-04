"""
EXECUTION METRICS ANALYSIS - Validated Setups Only

Analyzes real R vs canonical R for the 3 validated setups:
- 1100 ORB: Stop=0.20, RR=8.0
- 1800 ORB: Stop=0.20, RR=4.0
- 2300 ORB: Stop=0.20, RR=4.0

Verifies acceptance criteria: Real R within 0.10R of canonical
"""

import duckdb
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from execution_metrics import ExecutionMetricsCalculator, aggregate_metrics, print_metrics_report

TZ_LOCAL = ZoneInfo("Australia/Brisbane")
TZ_UTC = ZoneInfo("UTC")

DB_PATH = 'gold.db'
SYMBOL = 'MGC'

# Validated setups from VALIDATION_RESULTS_SUMMARY.md
VALIDATED_SETUPS = [
    {'orb_time': '1100', 'stop_frac': 0.20, 'rr': 8.0, 'label': '1100 ORB (BEST)'},
    {'orb_time': '1800', 'stop_frac': 0.20, 'rr': 4.0, 'label': '1800 ORB'},
    {'orb_time': '2300', 'stop_frac': 0.20, 'rr': 4.0, 'label': '2300 ORB'},
]

ORBS = {
    '0900': (9, 0),
    '1000': (10, 0),
    '1100': (11, 0),
    '1800': (18, 0),
    '2300': (23, 0),
    '0030': (0, 30),
}


def analyze_setup(orb_time, stop_frac, rr, label):
    """Analyze execution metrics for one setup"""
    print("="*80)
    print(f"{label}: Stop={stop_frac}, RR={rr}")
    print("="*80)
    print()

    conn = duckdb.connect(DB_PATH, read_only=True)

    # Get all days with this ORB
    query = f"""
        SELECT
            date_local,
            orb_{orb_time}_high as orb_high,
            orb_{orb_time}_low as orb_low,
            orb_{orb_time}_size as orb_size,
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
    total_days = len(df_days)

    print(f"Found {total_days} days with {orb_time} ORB breakouts")
    print()

    # Pre-load bars
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

    # Calculate execution metrics for all trades
    # Use $3.00 total cost to match optimization assumptions
    # Commission: $1.50, Slippage: 1.5 ticks = 0.15 points = $1.50
    calc = ExecutionMetricsCalculator(commission=1.5, slippage_ticks=1.5)
    trades = []

    for idx, row in df_days.iterrows():
        date_str = str(pd.to_datetime(row['date_local']).date())
        orb_high = row['orb_high']
        orb_low = row['orb_low']
        break_dir = row['break_dir']
        bars = bars_cache.get(date_str)

        if bars is not None and len(bars) > 0:
            # Find entry bar (first close outside ORB)
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

    # Aggregate and report
    if len(trades) > 0:
        agg = aggregate_metrics(trades)
        print_metrics_report(agg)

        # Acceptance criteria check
        degradation = agg['performance_degradation']
        print("="*80)
        print("ACCEPTANCE CRITERIA CHECK")
        print("="*80)
        print()
        print(f"Real R degradation: {degradation:+.3f}R")
        print(f"Threshold: < 0.10R")
        print()

        if abs(degradation) < 0.10:
            print("PASS: Real R within 0.10R of canonical")
            print("Setup is VALIDATED for live trading with realistic execution")
        else:
            print("WARNING: Real R degradation exceeds threshold")
            print("Review slippage assumptions or entry quality")

        print()
        return {
            'setup': label,
            'trades': len(trades),
            'canonical_avg_r': agg['canonical_avg_r'],
            'real_avg_r': agg['real_avg_r'],
            'degradation': degradation,
            'pass': abs(degradation) < 0.10
        }
    else:
        print("No trades found")
        return None


if __name__ == "__main__":
    print()
    print("="*80)
    print("EXECUTION METRICS ANALYSIS - VALIDATED SETUPS")
    print("="*80)
    print()
    print("Analyzing 3 validated setups with real execution (slippage + commission)...")
    print("Commission: $1.50 per trade")
    print("Slippage: 1.5 ticks (0.15 points = $1.50)")
    print("Total cost: $3.00 per trade (matches optimization assumptions)")
    print()

    results = []
    for setup in VALIDATED_SETUPS:
        result = analyze_setup(
            orb_time=setup['orb_time'],
            stop_frac=setup['stop_frac'],
            rr=setup['rr'],
            label=setup['label']
        )
        if result:
            results.append(result)
        print()

    # Summary
    print()
    print("="*80)
    print("SUMMARY - ALL VALIDATED SETUPS")
    print("="*80)
    print()

    if results:
        print("Setup                      Trades  Canonical R  Real R    Degradation  Status")
        print("-" * 80)
        for r in results:
            status = "PASS" if r['pass'] else "WARNING"
            print(f"{r['setup']:<25} {r['trades']:>6}  {r['canonical_avg_r']:>10.3f}  {r['real_avg_r']:>7.3f}  {r['degradation']:>10.3f}  {status}")

        print()
        all_pass = all(r['pass'] for r in results)
        if all_pass:
            print("VERDICT: ALL SETUPS PASS acceptance criteria")
            print("Ready to proceed to Phase 5 (Update validated_setups)")
        else:
            print("VERDICT: Some setups fail criteria - review before live trading")

        print()
