"""
Populate Validated Trades - WITH MINIMUM RISK GATE
===================================================

Implements TCA.txt "20% Friction Cap" rule:
- Rejects trades where friction > 20% of risk
- MIN_RISK_DOLLARS = $50 (recommended from text.txt)

This is NOT a bug fix - this is professional risk management.

Usage:
    python populate_validated_trades_with_filter.py               # All dates
    python populate_validated_trades_with_filter.py 2025-01-10    # Single date
"""

import duckdb
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, 'C:/Users/sydne/OneDrive/Desktop/MPX3')
from pipeline.cost_model import COST_MODELS
from pipeline.load_validated_setups import load_validated_setups

TZ_LOCAL = ZoneInfo("Australia/Brisbane")
TZ_UTC = ZoneInfo("UTC")

DB_PATH = "data/db/gold.db"
SYMBOL = "MGC"

# Cost model
MGC_COSTS = COST_MODELS['MGC']
MGC_POINT_VALUE = MGC_COSTS['point_value']
MGC_FRICTION = MGC_COSTS['total_friction']

# MINIMUM RISK GATE (TCA.txt requirement)
MIN_RISK_DOLLARS = 50.00  # $50 keeps friction below 20%
MAX_FRICTION_RATIO = 0.20  # 20% cap on friction-to-risk ratio


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

    NEW: Applies 20% Friction Cap (TCA.txt requirement)
    """
    if orb_high is None or orb_low is None:
        return None  # No ORB formed

    # Fetch bars from ORB end to scan end
    orb_hh, orb_mm = int(orb_time[:2]), int(orb_time[2:])
    orb_end_local = _dt_local(trade_date, orb_hh, orb_mm) + timedelta(minutes=5)
    bars = _fetch_1m_bars(conn, orb_end_local, scan_end_local)

    if not bars:
        return None  # No bars available

    # Convert to list of tuples
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
            "friction_ratio": None,
            "outcome": "NO_TRADE",
            "realized_rr": None,
            "mae": None,
            "mfe": None
        }

    # STEP 2: Calculate entry price (B-entry model: NEXT 1m OPEN)
    if signal_bar_index + 1 >= len(bars):
        # No entry bar available
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
            "friction_ratio": None,
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
            "friction_ratio": None,
            "outcome": "NO_TRADE",
            "realized_rr": None,
            "mae": None,
            "mfe": None
        }

    # STEP 5: Calculate risk in dollars (WITHOUT friction for gate calculation)
    risk_dollars_base = risk_points * MGC_POINT_VALUE

    # STEP 6: Calculate friction ratio (TCA.txt)
    friction_ratio = MGC_FRICTION / risk_dollars_base if risk_dollars_base > 0 else 999.0

    # STEP 7: Apply MINIMUM RISK GATE (20% Friction Cap)
    if risk_dollars_base < MIN_RISK_DOLLARS or friction_ratio > MAX_FRICTION_RATIO:
        # REJECT: Risk too small for fixed costs
        return {
            "setup_id": setup_id,
            "instrument": SYMBOL,
            "orb_time": orb_time,
            "entry_price": entry_price,
            "stop_price": stop_price,
            "target_price": None,
            "exit_price": None,
            "risk_points": risk_points,
            "target_points": None,
            "risk_dollars": risk_dollars_base,
            "friction_ratio": friction_ratio,
            "outcome": "RISK_TOO_SMALL",  # NEW outcome for filtered trades
            "realized_rr": None,
            "mae": None,
            "mfe": None
        }

    # STEP 8: Calculate target using strategy-specific RR
    target_points = rr * risk_points
    if break_dir == "UP":
        target_price = entry_price + target_points
    else:
        target_price = entry_price - target_points

    # STEP 9: Calculate risk in dollars (WITH friction for realized RR)
    risk_dollars = risk_dollars_base + MGC_FRICTION

    # STEP 10: Scan remaining bars for outcome
    outcome = "OPEN"
    exit_price = None
    mae = 0.0
    mfe = 0.0

    for bar in bars[signal_bar_index + 2:]:  # Start after entry bar
        ts_utc, bar_open, bar_high, bar_low, bar_close = bar

        # Calculate excursion (in R)
        if break_dir == "UP":
            adverse_excursion = (entry_price - bar_low) / risk_points
            favorable_excursion = (bar_high - entry_price) / risk_points
        else:
            adverse_excursion = (bar_high - entry_price) / risk_points
            favorable_excursion = (entry_price - bar_low) / risk_points

        mae = min(mae, -adverse_excursion)
        mfe = max(mfe, favorable_excursion)

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

    # STEP 11: Calculate realized RR
    if outcome == "WIN":
        realized_reward_dollars = (target_points * MGC_POINT_VALUE) - MGC_FRICTION
        realized_risk_dollars = risk_dollars
        realized_rr = realized_reward_dollars / realized_risk_dollars if realized_risk_dollars > 0 else 0.0
    elif outcome == "LOSS":
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
        "risk_dollars": risk_dollars_base,
        "friction_ratio": friction_ratio,
        "outcome": outcome,
        "realized_rr": realized_rr,
        "mae": mae,
        "mfe": mfe
    }


def populate_date(conn, trade_date: date, strategies: list):
    """
    Populate validated_trades for a single date, all strategies.
    """
    # Fetch ORB data from daily_features
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

    # Scan end times per ORB
    scan_end_times = {
        '0900': (18, 0),
        '1000': (18, 0),
        '1100': (18, 0),
        '1800': (23, 0),
        '2300': (2, 0),
        '0030': (9, 0)
    }

    trades_inserted = 0
    for strategy in strategies:
        setup_id = strategy['id']
        orb_time = strategy['orb_time']
        rr = strategy['rr']
        sl_mode = strategy['sl_mode']

        orb_high, orb_low = orb_data.get(orb_time, (None, None))

        if orb_high is None or orb_low is None:
            continue

        scan_hh, scan_mm = scan_end_times[orb_time]
        if scan_hh < 9:
            scan_end_local = _dt_local(trade_date + timedelta(days=1), scan_hh, scan_mm)
        else:
            scan_end_local = _dt_local(trade_date, scan_hh, scan_mm)

        result = calculate_tradeable_for_strategy(
            conn, trade_date, setup_id, orb_time, orb_high, orb_low,
            scan_end_local, rr, sl_mode
        )

        if result is None:
            continue

        # Check if friction_ratio column exists, if not add it
        try:
            conn.execute("SELECT friction_ratio FROM validated_trades LIMIT 1")
        except:
            # Add friction_ratio column if missing
            conn.execute("ALTER TABLE validated_trades ADD COLUMN friction_ratio DOUBLE")
            print("[INFO] Added friction_ratio column to validated_trades")

        # Insert into validated_trades
        conn.execute(
            """
            INSERT OR REPLACE INTO validated_trades
            (date_local, setup_id, instrument, orb_time, entry_price, stop_price, target_price,
             exit_price, risk_points, target_points, risk_dollars, friction_ratio, outcome, realized_rr, mae, mfe)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                trade_date, result['setup_id'], result['instrument'], result['orb_time'],
                result['entry_price'], result['stop_price'], result['target_price'], result['exit_price'],
                result['risk_points'], result['target_points'], result['risk_dollars'], result['friction_ratio'],
                result['outcome'], result['realized_rr'], result['mae'], result['mfe']
            ]
        )
        trades_inserted += 1

    if trades_inserted > 0:
        print(f"  [OK] {trade_date}: {trades_inserted} trades inserted")


def main():
    conn = duckdb.connect(DB_PATH)

    print("\n" + "=" * 80)
    print("LOADING STRATEGIES FROM VALIDATED_SETUPS")
    print("=" * 80)
    strategies = load_validated_setups(conn, instrument='MGC')
    print(f"\n[INFO] Loaded {len(strategies)} strategies")
    print()

    print("=" * 80)
    print("TCA.txt MINIMUM RISK GATE")
    print("=" * 80)
    print(f"MIN_RISK_DOLLARS: ${MIN_RISK_DOLLARS:.2f}")
    print(f"MAX_FRICTION_RATIO: {MAX_FRICTION_RATIO:.1%}")
    print(f"MGC Friction: ${MGC_FRICTION:.2f} RT")
    print(f"At ${MIN_RISK_DOLLARS:.2f} risk: {(MGC_FRICTION/MIN_RISK_DOLLARS):.1%} friction ratio")
    print("=" * 80)
    print()

    # Determine date range
    if len(sys.argv) > 1:
        single_date = date.fromisoformat(sys.argv[1])
        dates = [single_date]
        print(f"[INFO] Processing single date: {single_date}")
    else:
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

    # Show summary with filtering statistics
    conn = duckdb.connect(DB_PATH)

    print("FILTERING STATISTICS (TCA.txt 20% Friction Cap):")
    print("-" * 80)

    filter_stats = conn.execute("""
        SELECT
            vs.id as setup_id,
            vs.orb_time,
            vs.rr,
            COUNT(*) as total_signals,
            SUM(CASE WHEN vt.outcome = 'RISK_TOO_SMALL' THEN 1 ELSE 0 END) as filtered_out,
            SUM(CASE WHEN vt.outcome NOT IN ('RISK_TOO_SMALL', 'NO_TRADE') THEN 1 ELSE 0 END) as tradeable,
            SUM(CASE WHEN vt.outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN vt.outcome = 'LOSS' THEN 1 ELSE 0 END) as losses
        FROM validated_setups vs
        LEFT JOIN validated_trades vt ON vs.id = vt.setup_id
        WHERE vs.instrument = 'MGC'
        GROUP BY vs.id, vs.orb_time, vs.rr
        ORDER BY vs.orb_time, vs.rr
    """).fetchall()

    print(f"{'Setup':<6} {'ORB':<6} {'RR':<6} {'Signals':<8} {'Filtered':<10} {'Filter%':<9} {'Tradeable':<10} {'Wins':<6} {'Losses':<8}")
    print("-" * 80)
    for row in filter_stats:
        setup_id, orb_time, rr, total, filtered, tradeable, wins, losses = row
        filter_pct = (filtered / total * 100) if total > 0 else 0
        print(f"{setup_id:<6} {orb_time:<6} {rr:<6.1f} {total:<8} {filtered:<10} {filter_pct:<9.1f} {tradeable:<10} {wins:<6} {losses:<8}")
    print("-" * 80)

    conn.close()


if __name__ == "__main__":
    main()
