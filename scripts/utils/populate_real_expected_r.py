"""
Populate real_expected_r column in validated_setups table

Calculates real R (entry-to-stop with slippage) for each validated setup
and updates the validated_setups table.

Usage:
    python populate_real_expected_r.py
"""

import duckdb
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from execution_metrics import ExecutionMetricsCalculator, aggregate_metrics

TZ_LOCAL = ZoneInfo("Australia/Brisbane")
TZ_UTC = ZoneInfo("UTC")

DB_PATH = 'data/db/gold.db'
SYMBOL = 'MGC'

# Execution costs (consistent with analyze_execution_metrics_simple.py)
COMMISSION = 1.5  # $1.50 per trade
SLIPPAGE_TICKS = 1.5  # 1.5 ticks = 0.15 points = $1.50

ORBS = {
    '0900': (9, 0),
    '1000': (10, 0),
    '1100': (11, 0),
    '1800': (18, 0),
    '2300': (23, 0),
    '0030': (0, 30),
}


def calculate_real_expected_r(conn, instrument, orb_time, rr, sl_mode, orb_size_filter):
    """Calculate real expected R for a validated setup"""

    # Skip special strategies (CASCADE, SINGLE_LIQ, etc.)
    if orb_time not in ['0900', '1000', '1100', '1800', '2300', '0030']:
        return None, 0

    # Get all days with this ORB breaking
    query = f"""
        SELECT
            date_local,
            orb_{orb_time}_high as orb_high,
            orb_{orb_time}_low as orb_low,
            orb_{orb_time}_size as orb_size,
            orb_{orb_time}_break_dir as break_dir
        FROM daily_features
        WHERE instrument = ?
          AND orb_{orb_time}_high IS NOT NULL
          AND orb_{orb_time}_low IS NOT NULL
          AND orb_{orb_time}_break_dir IS NOT NULL
          AND orb_{orb_time}_break_dir != 'NONE'
    """

    # Apply ORB size filter if specified
    if orb_size_filter is not None and pd.notna(orb_size_filter):
        query += f" AND orb_{orb_time}_size >= {orb_size_filter}"

    query += " ORDER BY date_local"

    df_days = conn.execute(query, [instrument]).fetchdf()

    if len(df_days) == 0:
        return None, 0

    hour, minute = ORBS[orb_time]

    # Parse sl_mode to get stop fraction
    if sl_mode == 'full':
        stop_fraction = 1.0
    elif sl_mode == 'half':
        stop_fraction = 0.5
    else:
        # Parse fraction like '0.20' or '20%'
        try:
            if '%' in sl_mode:
                stop_fraction = float(sl_mode.replace('%', '')) / 100.0
            else:
                stop_fraction = float(sl_mode)
        except:
            print(f"Warning: Could not parse sl_mode '{sl_mode}', using full")
            stop_fraction = 1.0

    # Calculate metrics for each trade
    calc = ExecutionMetricsCalculator(commission=COMMISSION, slippage_ticks=SLIPPAGE_TICKS)
    trades = []

    for idx, row in df_days.iterrows():
        trade_date = pd.to_datetime(row['date_local']).date()

        # Calculate ORB start time
        if hour == 0 and minute == 30:
            orb_start = datetime(trade_date.year, trade_date.month, trade_date.day, hour, minute, tzinfo=TZ_LOCAL) + timedelta(days=1)
        else:
            orb_start = datetime(trade_date.year, trade_date.month, trade_date.day, hour, minute, tzinfo=TZ_LOCAL)

        scan_start = orb_start + timedelta(minutes=5)

        # Scan window ends at 09:00 next day
        if hour < 9 or (hour == 0 and minute == 30):
            scan_end = datetime(orb_start.year, orb_start.month, orb_start.day, 9, 0, tzinfo=TZ_LOCAL)
        else:
            scan_end = datetime(orb_start.year, orb_start.month, orb_start.day, 9, 0, tzinfo=TZ_LOCAL) + timedelta(days=1)

        start_utc = scan_start.astimezone(TZ_UTC)
        end_utc = scan_end.astimezone(TZ_UTC)

        # Get bars for entry detection and outcome simulation
        bars = conn.execute("""
            SELECT ts_utc, high, low, close
            FROM bars_1m
            WHERE symbol = ?
              AND ts_utc >= ?
              AND ts_utc < ?
            ORDER BY ts_utc
        """, [SYMBOL, start_utc, end_utc]).fetchdf()

        if len(bars) == 0:
            continue

        # Find entry bar (first close outside ORB)
        entry_close = None
        entry_idx = None
        break_dir = row['break_dir']

        for i, bar in bars.iterrows():
            if break_dir == 'UP' and bar['close'] > row['orb_high']:
                entry_close = bar['close']
                entry_idx = i
                break
            elif break_dir == 'DOWN' and bar['close'] < row['orb_low']:
                entry_close = bar['close']
                entry_idx = i
                break

        if entry_close is None:
            continue

        # Calculate metrics
        metrics = calc.calculate_trade_metrics(
            orb_high=row['orb_high'],
            orb_low=row['orb_low'],
            entry_close=entry_close,
            break_dir=break_dir,
            bars_1m=bars,
            rr=rr,
            stop_mode=stop_fraction,
            entry_bar_idx=entry_idx
        )

        if metrics:
            trades.append(metrics)

    if not trades:
        return None, 0

    # Aggregate and return real avg R
    agg = aggregate_metrics(trades)
    return agg['real_avg_r'], len(trades)


def main():
    """Populate real_expected_r for all validated setups"""

    conn = duckdb.connect(DB_PATH)

    # Get all validated setups
    setups = conn.execute("""
        SELECT id, instrument, orb_time, rr, sl_mode, orb_size_filter, expected_r
        FROM validated_setups
        ORDER BY id
    """).fetchdf()

    print("="*80)
    print("POPULATING real_expected_r FOR VALIDATED SETUPS")
    print("="*80)
    print()
    print(f"Found {len(setups)} setups to process")
    print()

    for idx, setup in setups.iterrows():
        setup_id = setup['id']
        instrument = setup['instrument']
        orb_time = setup['orb_time']
        rr = setup['rr']
        sl_mode = setup['sl_mode']
        orb_size_filter = setup['orb_size_filter']
        canonical_r = setup['expected_r']

        print(f"Processing setup #{setup_id}: {instrument} {orb_time} ORB RR={rr} SL={sl_mode}...")

        # Calculate real expected R
        real_r, trade_count = calculate_real_expected_r(
            conn, instrument, orb_time, rr, sl_mode, orb_size_filter
        )

        if real_r is not None:
            degradation = real_r - canonical_r
            print(f"  Canonical R: {canonical_r:+.3f}")
            print(f"  Real R:      {real_r:+.3f}")
            print(f"  Degradation: {degradation:+.3f} ({trade_count} trades)")

            # Update database
            conn.execute("""
                UPDATE validated_setups
                SET real_expected_r = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, [real_r, setup_id])

            print(f"  [OK] Updated database")
        else:
            print(f"  [WARN] No trades found (skipped)")

        print()

    conn.close()

    print("="*80)
    print("DONE!")
    print("="*80)
    print()
    print("Run test_app_sync.py to verify synchronization")


if __name__ == "__main__":
    main()
