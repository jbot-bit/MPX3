"""
Populate Validated Trades - Per-Strategy B-Entry Results
==========================================================

Populates validated_trades table with strategy-specific tradeable results.

ARCHITECTURE:
- daily_features = STRUCTURAL metrics (ORB-anchored, market structure)
- validated_trades = TRADEABLE metrics (entry-anchored, per-strategy results)

KEY FEATURES:
- One row per (date_local, setup_id) combination
- RR from validated_setups (not hardcoded)
- Supports multiple RR values per ORB time (e.g., 1000 ORB: RR=1.5/2.0/2.5/3.0)
- Uses shared loader (CHECK.TXT Req #6)

Usage:
    python populate_validated_trades.py               # All dates, all strategies
    python populate_validated_trades.py 2025-01-10    # Single date, all strategies
"""

import duckdb
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, 'C:/Users/sydne/OneDrive/Desktop/MPX3')
from pipeline.cost_model import COST_MODELS, calculate_realized_rr
from pipeline.load_validated_setups import load_validated_setups

TZ_LOCAL = ZoneInfo("Australia/Brisbane")
TZ_UTC = ZoneInfo("UTC")

DB_PATH = "data/db/gold.db"
SYMBOL = "MGC"

# Cost model
MGC_COSTS = COST_MODELS['MGC']
MGC_POINT_VALUE = MGC_COSTS['point_value']
MGC_FRICTION = MGC_COSTS['total_friction']


def _dt_local(d: date, hh: int, mm: int) -> datetime:
    return datetime(d.year, d.month, d.day, hh, mm, tzinfo=TZ_LOCAL)


def _fetch_1m_bars(conn, start_local: datetime, end_local: datetime):
    """Fetch 1-minute bars for a time window."""
    start_utc = start_local.astimezone(TZ_UTC)
    end_utc = end_local.astimezone(TZ_UTC)

    rows = conn.execute(
        """
        SELECT ts_utc, open, high, low, close
        FROM bars_1m
        WHERE symbol = ?
          AND ts_utc >= ? AND ts_utc < ?
        ORDER BY ts_utc
        """,
        [SYMBOL, start_utc, end_utc],
    ).fetchall()

    return rows


def calculate_tradeable_for_strategy(conn, trade_date: date, setup_id: int, orb_time: str,
                                      orb_high: float, orb_low: float, scan_end_local: datetime,
                                      rr: float, sl_mode: str):
    """
    Calculate tradeable metrics for a single strategy using B-entry model.

    B-ENTRY MODEL:
    - Signal: First 1m CLOSE outside ORB
    - Entry: NEXT 1m OPEN after signal close
    - Stop: ORB edge (full) or midpoint (half)
    - Risk: |entry - stop| (entry-anchored)
    - Target: entry +/- RR * risk
    - Outcome: WIN/LOSS/OPEN/NO_TRADE
    """
    if orb_high is None or orb_low is None:
        return None  # No ORB formed

    # Fetch bars from ORB end to scan end
    orb_hh, orb_mm = int(orb_time[:2]), int(orb_time[2:])
    orb_end_local = _dt_local(trade_date, orb_hh, orb_mm) + timedelta(minutes=5)
    bars = _fetch_1m_bars(conn, orb_end_local, scan_end_local)

    if not bars:
        return None  # No bars available

    # Convert to list of tuples (keep ts_utc as datetime for comparison)
    bars = [(ts_utc, float(o), float(h), float(l), float(c)) for ts_utc, o, h, l, c in bars]

    # STEP 1: Detect break direction
    break_dir = None
    signal_bar_index = None

    for i, bar in enumerate(bars):
        ts_utc, bar_open, bar_high, bar_low, bar_close = bar

        if bar_close > orb_high:
            break_dir = "UP"
            signal_bar_index = i
            break
        elif bar_close < orb_low:
            break_dir = "DOWN"
            signal_bar_index = i
            break

    if break_dir is None:
        # No break detected
        return {
            "setup_id": setup_id,
            "instrument": SYMBOL,
            "orb_time": orb_time,
            "entry_price": None,
            "stop_price": None,
            "target_price": None,
            "exit_price": None,
            "risk_points": None,
            "target_points": None,
            "risk_dollars": None,
            "outcome": "NO_TRADE",
            "realized_rr": None,
            "mae": None,
            "mfe": None
        }

    # STEP 2: Calculate entry price (B-entry model: NEXT 1m OPEN)
    if signal_bar_index + 1 >= len(bars):
        # No entry bar available (signal at last bar)
        return {
            "setup_id": setup_id,
            "instrument": SYMBOL,
            "orb_time": orb_time,
            "entry_price": None,
            "stop_price": None,
            "target_price": None,
            "exit_price": None,
            "risk_points": None,
            "target_points": None,
            "risk_dollars": None,
            "outcome": "NO_TRADE",
            "realized_rr": None,
            "mae": None,
            "mfe": None
        }

    entry_bar = bars[signal_bar_index + 1]
    entry_ts, entry_bar_open, entry_bar_high, entry_bar_low, entry_bar_close = entry_bar

    # B-ENTRY: Entry at NEXT 1m OPEN
    entry_price = float(entry_bar_open)

    # STEP 3: Calculate stop based on mode
    orb_mid = (orb_high + orb_low) / 2.0
    if sl_mode == "full":
        stop_price = orb_low if break_dir == "UP" else orb_high
    else:  # half
        stop_price = orb_mid

    # STEP 4: Calculate entry-anchored risk
    risk_points = abs(entry_price - stop_price)

    if risk_points == 0:
        # Zero risk - invalid setup
        return {
            "setup_id": setup_id,
            "instrument": SYMBOL,
            "orb_time": orb_time,
            "entry_price": entry_price,
            "stop_price": stop_price,
            "target_price": None,
            "exit_price": None,
            "risk_points": 0.0,
            "target_points": None,
            "risk_dollars": None,
            "outcome": "NO_TRADE",
            "realized_rr": None,
            "mae": None,
            "mfe": None
        }

    # STEP 5: Calculate target using strategy-specific RR
    target_points = rr * risk_points
    if break_dir == "UP":
        target_price = entry_price + target_points
    else:
        target_price = entry_price - target_points

    # STEP 6: Calculate risk in dollars (with friction)
    risk_dollars = (risk_points * MGC_POINT_VALUE) + MGC_FRICTION

    # STEP 7: Scan remaining bars for outcome
    outcome = "OPEN"
    exit_price = None
    mae = 0.0
    mfe = 0.0

    for bar in bars[signal_bar_index + 2:]:  # Start after entry bar
        ts_utc, bar_open, bar_high, bar_low, bar_close = bar

        # Calculate excursion (in R)
        if break_dir == "UP":
            adverse_excursion = (entry_price - bar_low) / risk_points  # Drawdown
            favorable_excursion = (bar_high - entry_price) / risk_points  # Profit
        else:
            adverse_excursion = (bar_high - entry_price) / risk_points  # Drawdown
            favorable_excursion = (entry_price - bar_low) / risk_points  # Profit

        mae = min(mae, -adverse_excursion)  # Most negative
        mfe = max(mfe, favorable_excursion)  # Most positive

        # Check for stop or target hit
        if break_dir == "UP":
            if bar_low <= stop_price:
                outcome = "LOSS"
                exit_price = stop_price
                break
            elif bar_high >= target_price:
                outcome = "WIN"
                exit_price = target_price
                break
        else:
            if bar_high >= stop_price:
                outcome = "LOSS"
                exit_price = stop_price
                break
            elif bar_low <= target_price:
                outcome = "WIN"
                exit_price = target_price
                break

    # STEP 8: Calculate realized RR
    if outcome == "WIN":
        # WIN: Full reward achieved (target hit)
        realized_reward_dollars = (target_points * MGC_POINT_VALUE) - MGC_FRICTION
        realized_risk_dollars = (risk_points * MGC_POINT_VALUE) + MGC_FRICTION
        realized_rr = realized_reward_dollars / realized_risk_dollars if realized_risk_dollars > 0 else 0.0
    elif outcome == "LOSS":
        # LOSS: Full risk taken (stop hit)
        realized_rr = -1.0  # Lose 1R (by definition)
    else:
        realized_rr = None  # OPEN outcome

    return {
        "setup_id": setup_id,
        "instrument": SYMBOL,
        "orb_time": orb_time,
        "entry_price": entry_price,
        "stop_price": stop_price,
        "target_price": target_price,
        "exit_price": exit_price,
        "risk_points": risk_points,
        "target_points": target_points,
        "risk_dollars": risk_dollars,
        "outcome": outcome,
        "realized_rr": realized_rr,
        "mae": mae,
        "mfe": mfe
    }


def populate_date(conn, trade_date: date, strategies: list):
    """
    Populate validated_trades for a single date, all strategies.
    """
    # Fetch ORB data from daily_features (STRUCTURAL metrics)
    row = conn.execute(
        """
        SELECT orb_0900_high, orb_0900_low,
               orb_1000_high, orb_1000_low,
               orb_1100_high, orb_1100_low,
               orb_1800_high, orb_1800_low,
               orb_2300_high, orb_2300_low,
               orb_0030_high, orb_0030_low
        FROM daily_features
        WHERE date_local = ? AND instrument = ?
        """,
        [trade_date, SYMBOL],
    ).fetchone()

    if not row:
        print(f"  [SKIP] {trade_date}: No daily_features row")
        return

    # Map ORB times to high/low values
    orb_data = {
        '0900': (row[0], row[1]),
        '1000': (row[2], row[3]),
        '1100': (row[4], row[5]),
        '1800': (row[6], row[7]),
        '2300': (row[8], row[9]),
        '0030': (row[10], row[11])
    }

    # Scan end times per ORB (local time)
    scan_end_times = {
        '0900': (18, 0),   # 09:00 ORB scans until 18:00
        '1000': (18, 0),   # 10:00 ORB scans until 18:00
        '1100': (18, 0),   # 11:00 ORB scans until 18:00
        '1800': (23, 0),   # 18:00 ORB scans until 23:00
        '2300': (2, 0),    # 23:00 ORB scans until 02:00 next day
        '0030': (9, 0)     # 00:30 ORB scans until 09:00 same day
    }

    # Process each strategy
    trades_inserted = 0
    for strategy in strategies:
        setup_id = strategy['id']
        orb_time = strategy['orb_time']
        rr = strategy['rr']
        sl_mode = strategy['sl_mode']

        # Get ORB high/low for this ORB time
        orb_high, orb_low = orb_data.get(orb_time, (None, None))

        if orb_high is None or orb_low is None:
            # No ORB formed for this time
            continue

        # Calculate scan end time
        scan_hh, scan_mm = scan_end_times[orb_time]
        if scan_hh < 9:  # Next day (for 2300/0030 ORBs)
            scan_end_local = _dt_local(trade_date + timedelta(days=1), scan_hh, scan_mm)
        else:
            scan_end_local = _dt_local(trade_date, scan_hh, scan_mm)

        # Calculate tradeable metrics
        result = calculate_tradeable_for_strategy(
            conn, trade_date, setup_id, orb_time, orb_high, orb_low,
            scan_end_local, rr, sl_mode
        )

        if result is None:
            continue

        # Insert into validated_trades (UPSERT)
        conn.execute(
            """
            INSERT OR REPLACE INTO validated_trades
            (date_local, setup_id, instrument, orb_time, entry_price, stop_price, target_price,
             exit_price, risk_points, target_points, risk_dollars, outcome, realized_rr, mae, mfe)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                trade_date, result['setup_id'], result['instrument'], result['orb_time'],
                result['entry_price'], result['stop_price'], result['target_price'], result['exit_price'],
                result['risk_points'], result['target_points'], result['risk_dollars'],
                result['outcome'], result['realized_rr'], result['mae'], result['mfe']
            ]
        )
        trades_inserted += 1

    if trades_inserted > 0:
        print(f"  [OK] {trade_date}: {trades_inserted} trades inserted")


def main():
    conn = duckdb.connect(DB_PATH)

    # Load ALL strategies from validated_setups (not just first per ORB)
    print("\n" + "=" * 80)
    print("LOADING STRATEGIES FROM VALIDATED_SETUPS")
    print("=" * 80)
    strategies = load_validated_setups(conn, instrument='MGC')
    print(f"\n[INFO] Loaded {len(strategies)} strategies (IDs: {[s['id'] for s in strategies]})")
    print()

    # Determine date range
    if len(sys.argv) > 1:
        # Single date mode
        single_date = date.fromisoformat(sys.argv[1])
        dates = [single_date]
        print(f"[INFO] Processing single date: {single_date}")
    else:
        # All dates mode
        rows = conn.execute(
            """
            SELECT DISTINCT date_local
            FROM daily_features
            WHERE instrument = ?
            ORDER BY date_local
            """,
            [SYMBOL],
        ).fetchall()
        dates = [row[0] for row in rows]
        print(f"[INFO] Processing all dates: {len(dates)} dates")

    print()
    print("=" * 80)
    print("POPULATING VALIDATED_TRADES")
    print("=" * 80)

    for trade_date in dates:
        populate_date(conn, trade_date, strategies)

    conn.close()

    print()
    print("=" * 80)
    print("POPULATION COMPLETE")
    print("=" * 80)
    print()

    # Show summary
    conn = duckdb.connect(DB_PATH)
    summary = conn.execute("""
        SELECT
            vs.id as setup_id,
            vs.orb_time,
            vs.rr,
            COUNT(vt.date_local) as trade_count,
            SUM(CASE WHEN vt.outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN vt.outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
            SUM(CASE WHEN vt.outcome = 'OPEN' THEN 1 ELSE 0 END) as open_count
        FROM validated_setups vs
        LEFT JOIN validated_trades vt ON vs.id = vt.setup_id
        WHERE vs.instrument = 'MGC'
        GROUP BY vs.id, vs.orb_time, vs.rr
        ORDER BY vs.orb_time, vs.rr
    """).fetchall()

    print("SUMMARY BY STRATEGY:")
    print("-" * 80)
    print(f"{'Setup ID':<10} {'ORB':<6} {'RR':<6} {'Trades':<8} {'Wins':<6} {'Losses':<8} {'Open':<6}")
    print("-" * 80)
    for row in summary:
        setup_id, orb_time, rr, trade_count, wins, losses, open_count = row
        print(f"{setup_id:<10} {orb_time:<6} {rr:<6.1f} {trade_count:<8} {wins:<6} {losses:<8} {open_count:<6}")
    print("-" * 80)

    conn.close()


if __name__ == "__main__":
    main()
