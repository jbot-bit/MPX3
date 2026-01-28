"""
Populate Tradeable Metrics - B-Entry Model
===========================================

Populates tradeable columns in daily_features table using B-entry model.

This script ONLY updates tradeable columns (48 columns), leaving structural metrics unchanged.
Safe to re-run (idempotent).

Usage:
    python populate_tradeable_metrics.py               # All dates
    python populate_tradeable_metrics.py 2025-01-10    # Single date
"""

import duckdb
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, 'C:/Users/sydne/OneDrive/Desktop/MPX3')
from pipeline.cost_model import calculate_realized_rr

TZ_LOCAL = ZoneInfo("Australia/Brisbane")
TZ_UTC = ZoneInfo("UTC")

DB_PATH = "data/db/gold.db"
SYMBOL = "MGC"
SL_MODE = "full"  # Default: full = stop at opposite edge
RR_DEFAULT = 1.0  # Default RR for calculations


def _dt_local(d: date, hh: int, mm: int) -> datetime:
    return datetime(d.year, d.month, d.day, hh, mm, tzinfo=TZ_LOCAL)


def _fetch_1m_bars(conn, start_local: datetime, end_local: datetime):
    """Fetch 1-minute bars for a time window."""
    start_utc = start_local.astimezone(TZ_UTC)
    end_utc = end_local.astimezone(TZ_UTC)

    rows = conn.execute(
        """
        SELECT ts_utc, high, low, close
        FROM bars_1m
        WHERE symbol = ?
          AND ts_utc >= ? AND ts_utc < ?
        ORDER BY ts_utc
        """,
        [SYMBOL, start_utc, end_utc],
    ).fetchall()

    return rows


def calculate_tradeable_for_orb(conn, trade_date: date, orb_time: str, orb_high: float, orb_low: float,
                                 scan_end_local: datetime, rr: float = RR_DEFAULT, sl_mode: str = SL_MODE):
    """
    Calculate tradeable metrics for a single ORB using B-entry model.

    B-ENTRY MODEL:
    - Signal: First 1m CLOSE outside ORB
    - Entry: NEXT 1m OPEN after signal close
    - Stop: ORB edge (full) or midpoint (half)
    - Risk: |entry - stop| (entry-anchored)
    - Target: entry +/- RR * risk
    - Outcome: WIN/LOSS/OPEN (not NO_TRADE for open positions)
    """
    if orb_high is None or orb_low is None:
        return {
            "entry_price": None,
            "stop_price": None,
            "risk_points": None,
            "target_price": None,
            "outcome": "NO_TRADE",
            "realized_rr": None,
            "realized_risk_dollars": None,
            "realized_reward_dollars": None
        }

    # Parse ORB time
    if orb_time == "0030":
        orb_start_local = _dt_local(trade_date + timedelta(days=1), 0, 30)
    else:
        hh = int(orb_time[:2])
        mm = int(orb_time[2:])
        orb_start_local = _dt_local(trade_date, hh, mm)

    orb_end_local = orb_start_local + timedelta(minutes=5)
    orb_mid = (orb_high + orb_low) / 2.0

    # Fetch bars AFTER ORB end
    bars = _fetch_1m_bars(conn, orb_end_local, scan_end_local)

    # STEP 1: Find signal (first 1m CLOSE outside ORB)
    signal_found = False
    signal_bar_index = None
    break_dir = "NONE"

    for i, (ts_utc, h, l, c) in enumerate(bars):
        c = float(c)
        if c > orb_high:
            break_dir = "UP"
            signal_bar_index = i
            signal_found = True
            break
        if c < orb_low:
            break_dir = "DOWN"
            signal_bar_index = i
            signal_found = True
            break

    if not signal_found:
        return {
            "entry_price": None,
            "stop_price": None,
            "risk_points": None,
            "target_price": None,
            "outcome": "NO_TRADE",
            "realized_rr": None,
            "realized_risk_dollars": None,
            "realized_reward_dollars": None
        }

    # STEP 2: Entry at NEXT 1m OPEN (B-entry model)
    if signal_bar_index + 1 >= len(bars):
        return {
            "entry_price": None,
            "stop_price": None,
            "risk_points": None,
            "target_price": None,
            "outcome": "OPEN",
            "realized_rr": None,
            "realized_risk_dollars": None,
            "realized_reward_dollars": None
        }

    entry_bar = bars[signal_bar_index + 1]
    entry_ts, entry_bar_high, entry_bar_low, entry_bar_close = entry_bar

    # Entry price = OPEN of entry bar (conservative: worst fill)
    if break_dir == "UP":
        entry_price = float(entry_bar_low)
    else:
        entry_price = float(entry_bar_high)

    # STEP 3: Calculate stop
    if sl_mode == "full":
        stop_price = orb_low if break_dir == "UP" else orb_high
    else:
        stop_price = orb_mid

    # STEP 4: Calculate entry-anchored risk
    risk_points = abs(entry_price - stop_price)

    if risk_points <= 0:
        return {
            "entry_price": entry_price,
            "stop_price": stop_price,
            "risk_points": 0.0,
            "target_price": None,
            "outcome": "OPEN",
            "realized_rr": None,
            "realized_risk_dollars": None,
            "realized_reward_dollars": None
        }

    # STEP 5: Calculate target
    if break_dir == "UP":
        target_price = entry_price + (rr * risk_points)
    else:
        target_price = entry_price - (rr * risk_points)

    # STEP 6: Calculate realized RR
    try:
        realized = calculate_realized_rr(
            instrument='MGC',
            stop_distance_points=risk_points,
            rr_theoretical=rr,
            stress_level='normal'
        )
        realized_rr_win = realized['realized_rr']
        realized_risk_dollars = realized['realized_risk_dollars']
        realized_reward_dollars = realized['realized_reward_dollars']
    except Exception:
        realized_rr_win = None
        realized_risk_dollars = None
        realized_reward_dollars = None

    # STEP 7: Check outcome
    outcome = "OPEN"

    for ts_utc, h, l, c in bars[signal_bar_index + 2:]:
        h = float(h)
        l = float(l)

        if break_dir == "UP":
            hit_stop = l <= stop_price
            hit_target = h >= target_price

            if hit_stop and hit_target:
                outcome = "LOSS"
                break
            if hit_target:
                outcome = "WIN"
                break
            if hit_stop:
                outcome = "LOSS"
                break
        else:
            hit_stop = h >= stop_price
            hit_target = l <= target_price

            if hit_stop and hit_target:
                outcome = "LOSS"
                break
            if hit_target:
                outcome = "WIN"
                break
            if hit_stop:
                outcome = "LOSS"
                break

    # STEP 8: Final realized_rr
    if outcome == "WIN":
        final_realized_rr = realized_rr_win
    elif outcome == "LOSS":
        final_realized_rr = -1.0
    else:
        final_realized_rr = None

    return {
        "entry_price": entry_price,
        "stop_price": stop_price,
        "risk_points": risk_points,
        "target_price": target_price,
        "outcome": outcome,
        "realized_rr": final_realized_rr,
        "realized_risk_dollars": realized_risk_dollars,
        "realized_reward_dollars": realized_reward_dollars
    }


def main():
    conn = duckdb.connect(DB_PATH)

    # Get date range
    if len(sys.argv) > 1:
        start_date = date.fromisoformat(sys.argv[1])
        end_date = start_date
        print(f"Populating tradeable metrics for: {start_date}")
    else:
        rows = conn.execute("SELECT MIN(date_local), MAX(date_local) FROM daily_features WHERE instrument = 'MGC'").fetchone()
        start_date, end_date = rows[0], rows[1]
        print(f"Populating tradeable metrics for: {start_date} to {end_date}")

    print(f"SL mode: {SL_MODE}")
    print(f"RR: {RR_DEFAULT}")
    print()

    # Process each date
    current_date = start_date
    count = 0

    while current_date <= end_date:
        # Fetch structural ORB metrics (high/low) for this date
        row = conn.execute("""
            SELECT
                orb_0900_high, orb_0900_low,
                orb_1000_high, orb_1000_low,
                orb_1100_high, orb_1100_low,
                orb_1800_high, orb_1800_low,
                orb_2300_high, orb_2300_low,
                orb_0030_high, orb_0030_low
            FROM daily_features
            WHERE date_local = ? AND instrument = 'MGC'
        """, [current_date]).fetchone()

        if not row:
            current_date += timedelta(days=1)
            continue

        # Scan window: until next Asia open (09:00 next day)
        next_asia_open = _dt_local(current_date + timedelta(days=1), 9, 0)

        # Calculate tradeable metrics for each ORB
        orbs = [
            ("0900", row[0], row[1]),
            ("1000", row[2], row[3]),
            ("1100", row[4], row[5]),
            ("1800", row[6], row[7]),
            ("2300", row[8], row[9]),
            ("0030", row[10], row[11])
        ]

        results = {}
        for orb_time, orb_high, orb_low in orbs:
            result = calculate_tradeable_for_orb(conn, current_date, orb_time, orb_high, orb_low, next_asia_open, sl_mode=SL_MODE)
            results[orb_time] = result

        # Update database
        conn.execute("""
            UPDATE daily_features
            SET
                orb_0900_tradeable_entry_price = ?,
                orb_0900_tradeable_stop_price = ?,
                orb_0900_tradeable_risk_points = ?,
                orb_0900_tradeable_target_price = ?,
                orb_0900_tradeable_outcome = ?,
                orb_0900_tradeable_realized_rr = ?,
                orb_0900_tradeable_realized_risk_dollars = ?,
                orb_0900_tradeable_realized_reward_dollars = ?,

                orb_1000_tradeable_entry_price = ?,
                orb_1000_tradeable_stop_price = ?,
                orb_1000_tradeable_risk_points = ?,
                orb_1000_tradeable_target_price = ?,
                orb_1000_tradeable_outcome = ?,
                orb_1000_tradeable_realized_rr = ?,
                orb_1000_tradeable_realized_risk_dollars = ?,
                orb_1000_tradeable_realized_reward_dollars = ?,

                orb_1100_tradeable_entry_price = ?,
                orb_1100_tradeable_stop_price = ?,
                orb_1100_tradeable_risk_points = ?,
                orb_1100_tradeable_target_price = ?,
                orb_1100_tradeable_outcome = ?,
                orb_1100_tradeable_realized_rr = ?,
                orb_1100_tradeable_realized_risk_dollars = ?,
                orb_1100_tradeable_realized_reward_dollars = ?,

                orb_1800_tradeable_entry_price = ?,
                orb_1800_tradeable_stop_price = ?,
                orb_1800_tradeable_risk_points = ?,
                orb_1800_tradeable_target_price = ?,
                orb_1800_tradeable_outcome = ?,
                orb_1800_tradeable_realized_rr = ?,
                orb_1800_tradeable_realized_risk_dollars = ?,
                orb_1800_tradeable_realized_reward_dollars = ?,

                orb_2300_tradeable_entry_price = ?,
                orb_2300_tradeable_stop_price = ?,
                orb_2300_tradeable_risk_points = ?,
                orb_2300_tradeable_target_price = ?,
                orb_2300_tradeable_outcome = ?,
                orb_2300_tradeable_realized_rr = ?,
                orb_2300_tradeable_realized_risk_dollars = ?,
                orb_2300_tradeable_realized_reward_dollars = ?,

                orb_0030_tradeable_entry_price = ?,
                orb_0030_tradeable_stop_price = ?,
                orb_0030_tradeable_risk_points = ?,
                orb_0030_tradeable_target_price = ?,
                orb_0030_tradeable_outcome = ?,
                orb_0030_tradeable_realized_rr = ?,
                orb_0030_tradeable_realized_risk_dollars = ?,
                orb_0030_tradeable_realized_reward_dollars = ?
            WHERE date_local = ? AND instrument = 'MGC'
        """, [
            results["0900"].get("entry_price"), results["0900"].get("stop_price"), results["0900"].get("risk_points"), results["0900"].get("target_price"), results["0900"].get("outcome"), results["0900"].get("realized_rr"), results["0900"].get("realized_risk_dollars"), results["0900"].get("realized_reward_dollars"),
            results["1000"].get("entry_price"), results["1000"].get("stop_price"), results["1000"].get("risk_points"), results["1000"].get("target_price"), results["1000"].get("outcome"), results["1000"].get("realized_rr"), results["1000"].get("realized_risk_dollars"), results["1000"].get("realized_reward_dollars"),
            results["1100"].get("entry_price"), results["1100"].get("stop_price"), results["1100"].get("risk_points"), results["1100"].get("target_price"), results["1100"].get("outcome"), results["1100"].get("realized_rr"), results["1100"].get("realized_risk_dollars"), results["1100"].get("realized_reward_dollars"),
            results["1800"].get("entry_price"), results["1800"].get("stop_price"), results["1800"].get("risk_points"), results["1800"].get("target_price"), results["1800"].get("outcome"), results["1800"].get("realized_rr"), results["1800"].get("realized_risk_dollars"), results["1800"].get("realized_reward_dollars"),
            results["2300"].get("entry_price"), results["2300"].get("stop_price"), results["2300"].get("risk_points"), results["2300"].get("target_price"), results["2300"].get("outcome"), results["2300"].get("realized_rr"), results["2300"].get("realized_risk_dollars"), results["2300"].get("realized_reward_dollars"),
            results["0030"].get("entry_price"), results["0030"].get("stop_price"), results["0030"].get("risk_points"), results["0030"].get("target_price"), results["0030"].get("outcome"), results["0030"].get("realized_rr"), results["0030"].get("realized_risk_dollars"), results["0030"].get("realized_reward_dollars"),
            current_date
        ])

        count += 1
        if count % 10 == 0:
            print(f"Processed {count} dates...")

        current_date += timedelta(days=1)

    conn.commit()
    conn.close()

    print()
    print(f"Done! Populated tradeable metrics for {count} dates.")
    print()


if __name__ == "__main__":
    main()
