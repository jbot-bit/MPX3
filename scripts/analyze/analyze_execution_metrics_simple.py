"""
EXECUTION METRICS ANALYSIS - Simplified version without unicode issues
"""

import duckdb
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from execution_metrics import ExecutionMetricsCalculator, aggregate_metrics

TZ_LOCAL = ZoneInfo("Australia/Brisbane")
TZ_UTC = ZoneInfo("UTC")

DB_PATH = 'gold.db'
SYMBOL = 'MGC'

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
    conn = duckdb.connect(DB_PATH, read_only=True)

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
            'setup': label,
            'trades': len(trades),
            'canonical_wr': agg['canonical_win_rate'],
            'canonical_avg_r': agg['canonical_avg_r'],
            'canonical_total_r': agg['canonical_total_r'],
            'real_wr': agg['real_win_rate'],
            'real_avg_r': agg['real_avg_r'],
            'real_total_r': agg['real_total_r'],
            'degradation': agg['performance_degradation'],
            'avg_canonical_risk': agg['avg_canonical_risk'],
            'avg_real_risk': agg['avg_real_risk'],
            'risk_difference': agg['avg_risk_difference'],
            'pass': abs(agg['performance_degradation']) < 0.10
        }
    else:
        return None


if __name__ == "__main__":
    print("\n" + "="*80)
    print("EXECUTION METRICS ANALYSIS - VALIDATED SETUPS (Simplified)")
    print("="*80)
    print("\nCommission: $1.50, Slippage: 1.5 ticks ($1.50), Total: $3.00\n")

    results = []
    for setup in VALIDATED_SETUPS:
        print(f"Analyzing {setup['label']}...")
        result = analyze_setup(
            orb_time=setup['orb_time'],
            stop_frac=setup['stop_frac'],
            rr=setup['rr'],
            label=setup['label']
        )
        if result:
            results.append(result)

    # Summary table
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    print("\nSetup                   Trades  Can WR  Can R    Real WR  Real R   Degrad   Status")
    print("-" * 85)
    for r in results:
        status = "PASS" if r['pass'] else "FAIL"
        print(f"{r['setup']:<23} {r['trades']:>6}  {r['canonical_wr']:>5.1f}%  {r['canonical_avg_r']:>+6.3f}  {r['real_wr']:>6.1f}%  {r['real_avg_r']:>+6.3f}  {r['degradation']:>+6.3f}  {status}")

    print("\n" + "-" * 85)
    print(f"{'ACCEPTANCE THRESHOLD:':<55} {'<0.100':>21}")
    print("="*85)

    all_pass = all(r['pass'] for r in results)
    print(f"\nVERDICT: {'ALL PASS' if all_pass else 'SOME/ALL FAIL'}")

    if not all_pass:
        print("\nCRITICAL ISSUE: Real execution degrades edge beyond acceptable limits!")
        print("Tight stops (stop_frac=0.20) create massive real R degradation.")
        print("\nWhy this happens:")
        print("- Entry close is ~0.7-0.9 points from ORB edge (on average)")
        print("- Slippage adds ~0.15 points")
        print("- Total entry distance: ~0.85-1.05 points from edge")
        print("- With stop_frac=0.20, canonical risk is ~0.9-1.0 points")
        print("- Real risk = canonical risk + entry distance = ~1.75-2.05 points")
        print("- Real risk is 2x canonical risk!")
        print("\nRecommendation: Test wider stops (0.50, 0.75, 1.00) where entry")
        print("distance becomes a smaller percentage of total risk.")

    print()
