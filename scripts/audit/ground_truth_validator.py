"""
GROUND TRUTH VALIDATOR
======================

Phase 1 of Assumption Audit: Manually verify trades end-to-end

This script:
1. Picks 10 random trades from validated_trades
2. Loads raw 1m bars for each trade date
3. Manually recalculates EVERYTHING step-by-step:
   - ORB window (5 bars)
   - ORB high/low
   - Break detection (first close outside range)
   - Entry price (next 1m open after break)
   - Stop price (ORB edge)
   - Target price (entry +/- RR × risk)
   - Exit price (when target or stop hit)
   - Realized RR (after costs)
4. Compares manual calculations to database values
5. Reports ANY discrepancies (if ANY found: STOP EVERYTHING)

CRITICAL: This is the FOUNDATION. If this fails, all results are suspect.
"""

import duckdb
import sys
from datetime import datetime, timedelta
import pytz

sys.path.insert(0, 'C:/Users/sydne/OneDrive/Desktop/MPX3')

from pipeline.cost_model import get_cost_model, get_instrument_specs

DB_PATH = 'data/db/gold.db'
TZ_LOCAL = pytz.timezone('Australia/Brisbane')
TZ_UTC = pytz.UTC

# Get MGC specs
MGC_SPECS = get_instrument_specs('MGC')
MGC_COST = get_cost_model('MGC')
MGC_POINT_VALUE = MGC_SPECS['point_value']
MGC_FRICTION_RT = MGC_COST['total_friction']


def validate_trade_ground_truth(conn, trade):
    """
    Manually recalculate a single trade from raw 1m bars.

    Returns: (passed, discrepancies)
    """
    date_local = trade['date_local']
    setup_id = trade['setup_id']
    orb_time = trade['orb_time']
    rr = trade['rr']

    print(f"\n{'='*80}")
    print(f"VALIDATING: {date_local} | Setup {setup_id} | {orb_time} ORB RR={rr}")
    print(f"{'='*80}")

    discrepancies = []

    # Step 1: Load raw 1m bars for this date
    # Trading day: 09:00 local -> next 09:00 local (23:00 UTC prev day -> 23:00 UTC this day)
    date_obj = datetime.strptime(str(date_local), '%Y-%m-%d')

    # Trading day starts at 09:00 local (23:00 UTC previous day)
    start_local = TZ_LOCAL.localize(datetime.combine(date_obj, datetime.min.time()) + timedelta(hours=9))
    start_utc = start_local.astimezone(TZ_UTC)

    # Trading day ends at 09:00 local next day (23:00 UTC this day)
    end_local = start_local + timedelta(days=1)
    end_utc = end_local.astimezone(TZ_UTC)

    bars_query = """
        SELECT ts_utc, open, high, low, close, volume
        FROM bars_1m
        WHERE symbol = 'MGC'
          AND ts_utc >= ?
          AND ts_utc < ?
        ORDER BY ts_utc
    """

    bars = conn.execute(bars_query, [start_utc, end_utc]).fetchall()

    if not bars:
        print(f"[SKIP] No bars found for {date_local}")
        return False, ["No bars for date"]

    print(f"[OK] Loaded {len(bars)} 1m bars for trading day")

    # Step 2: Identify ORB window (5 bars starting at orb_time)
    orb_hour = int(orb_time[:2])
    orb_minute = int(orb_time[2:])

    orb_start_local = TZ_LOCAL.localize(datetime.combine(date_obj, datetime.min.time()) +
                                       timedelta(hours=orb_hour, minutes=orb_minute))
    orb_start_utc = orb_start_local.astimezone(TZ_UTC)
    orb_end_utc = orb_start_utc + timedelta(minutes=5)

    orb_bars = [b for b in bars if orb_start_utc <= b[0] < orb_end_utc]

    if len(orb_bars) != 5:
        print(f"[WARNING] Expected 5 ORB bars, got {len(orb_bars)}")

    if not orb_bars:
        print(f"[SKIP] No ORB bars found")
        return False, ["No ORB bars"]

    # Step 3: Calculate ORB high/low manually
    manual_orb_high = max(b[2] for b in orb_bars)  # high is index 2
    manual_orb_low = min(b[3] for b in orb_bars)   # low is index 3
    manual_orb_size = manual_orb_high - manual_orb_low

    print(f"\n[MANUAL] ORB High: {manual_orb_high:.1f}")
    print(f"[MANUAL] ORB Low: {manual_orb_low:.1f}")
    print(f"[MANUAL] ORB Size: {manual_orb_size:.1f} points")

    # Step 4: Detect break (first 1m close outside ORB range, AFTER ORB window)
    post_orb_bars = [b for b in bars if b[0] >= orb_end_utc]

    manual_break_dir = None
    manual_break_bar = None

    for bar in post_orb_bars:
        close_price = bar[4]  # close is index 4

        if close_price > manual_orb_high:
            manual_break_dir = 'UP'
            manual_break_bar = bar
            break
        elif close_price < manual_orb_low:
            manual_break_dir = 'DOWN'
            manual_break_bar = bar
            break

    if manual_break_bar is None:
        print(f"[MANUAL] No break detected (outcome should be NO_TRADE)")

        # Check database outcome
        if trade['outcome'] != 'NO_TRADE':
            discrepancies.append(f"Expected outcome=NO_TRADE, got {trade['outcome']}")

        return len(discrepancies) == 0, discrepancies

    print(f"[MANUAL] Break detected: {manual_break_dir} at {manual_break_bar[0]}")
    print(f"[MANUAL] Break close: {manual_break_bar[4]:.1f}")

    # Step 5: Entry price (NEXT 1m open after break bar)
    break_idx = post_orb_bars.index(manual_break_bar)

    if break_idx + 1 >= len(post_orb_bars):
        print(f"[SKIP] No bar after break for entry")
        return False, ["No entry bar after break"]

    entry_bar = post_orb_bars[break_idx + 1]
    manual_entry_price = entry_bar[1]  # open is index 1

    print(f"[MANUAL] Entry price (next open): {manual_entry_price:.1f}")

    # Step 6: Stop price (ORB edge, sl_mode='full')
    if manual_break_dir == 'UP':
        manual_stop_price = manual_orb_low  # Long trade, stop at ORB low
    else:
        manual_stop_price = manual_orb_high  # Short trade, stop at ORB high

    print(f"[MANUAL] Stop price: {manual_stop_price:.1f}")

    # Step 7: Risk and target
    manual_risk_points = abs(manual_entry_price - manual_stop_price)
    manual_target_points = rr * manual_risk_points

    if manual_break_dir == 'UP':
        manual_target_price = manual_entry_price + manual_target_points
    else:
        manual_target_price = manual_entry_price - manual_target_points

    print(f"[MANUAL] Risk: {manual_risk_points:.1f} points")
    print(f"[MANUAL] Target: {manual_target_price:.1f} (RR={rr})")

    # Step 8: Find exit (scan bars after entry for target or stop hit)
    exit_bars = post_orb_bars[break_idx + 1:]  # Start from entry bar

    manual_exit_price = None
    manual_outcome = 'OPEN'

    for bar in exit_bars:
        bar_high = bar[2]
        bar_low = bar[3]

        if manual_break_dir == 'UP':
            # Long trade
            if bar_high >= manual_target_price:
                manual_exit_price = manual_target_price
                manual_outcome = 'WIN'
                break
            elif bar_low <= manual_stop_price:
                manual_exit_price = manual_stop_price
                manual_outcome = 'LOSS'
                break
        else:
            # Short trade
            if bar_low <= manual_target_price:
                manual_exit_price = manual_target_price
                manual_outcome = 'WIN'
                break
            elif bar_high >= manual_stop_price:
                manual_exit_price = manual_stop_price
                manual_outcome = 'LOSS'
                break

    if manual_exit_price is None:
        print(f"[MANUAL] Trade still OPEN (no target/stop hit)")
        manual_outcome = 'OPEN'
    else:
        print(f"[MANUAL] Exit price: {manual_exit_price:.1f}")
        print(f"[MANUAL] Outcome: {manual_outcome}")

    # Step 9: Calculate realized RR
    if manual_outcome in ('WIN', 'LOSS'):
        if manual_break_dir == 'UP':
            pnl_points = manual_exit_price - manual_entry_price
        else:
            pnl_points = manual_entry_price - manual_exit_price

        pnl_dollars = pnl_points * MGC_POINT_VALUE
        friction_dollars = MGC_FRICTION_RT

        net_pnl_dollars = pnl_dollars - friction_dollars
        risk_dollars = manual_risk_points * MGC_POINT_VALUE + friction_dollars

        manual_realized_rr = net_pnl_dollars / risk_dollars

        print(f"[MANUAL] P&L: {pnl_points:.1f} points = ${pnl_dollars:.2f}")
        print(f"[MANUAL] Friction: ${friction_dollars:.2f}")
        print(f"[MANUAL] Net P&L: ${net_pnl_dollars:.2f}")
        print(f"[MANUAL] Risk: ${risk_dollars:.2f}")
        print(f"[MANUAL] Realized RR: {manual_realized_rr:+.3f}R")
    else:
        manual_realized_rr = None

    # Step 10: Compare to database
    print(f"\n{'='*80}")
    print(f"COMPARISON: MANUAL vs DATABASE")
    print(f"{'='*80}")

    def compare_field(name, manual, db, tolerance=0.01):
        if manual is None and db is None:
            print(f"[MATCH] {name}: Both NULL")
            return True

        if manual is None or db is None:
            print(f"[FAIL] {name}: Manual={manual}, DB={db}")
            discrepancies.append(f"{name}: Manual={manual}, DB={db}")
            return False

        if isinstance(manual, (int, float)) and isinstance(db, (int, float)):
            diff = abs(manual - db)
            if diff <= tolerance:
                print(f"[MATCH] {name}: {manual:.3f} (diff: {diff:.4f})")
                return True
            else:
                print(f"[FAIL] {name}: Manual={manual:.3f}, DB={db:.3f} (diff: {diff:.4f})")
                discrepancies.append(f"{name}: Manual={manual:.3f}, DB={db:.3f} (diff: {diff:.4f})")
                return False
        else:
            if manual == db:
                print(f"[MATCH] {name}: {manual}")
                return True
            else:
                print(f"[FAIL] {name}: Manual={manual}, DB={db}")
                discrepancies.append(f"{name}: Manual={manual}, DB={db}")
                return False

    compare_field("Entry Price", manual_entry_price, trade['entry_price'])
    compare_field("Stop Price", manual_stop_price, trade['stop_price'])
    compare_field("Target Price", manual_target_price, trade['target_price'])
    compare_field("Exit Price", manual_exit_price, trade['exit_price'])
    compare_field("Risk Points", manual_risk_points, trade['risk_points'])
    compare_field("Target Points", manual_target_points, trade['target_points'])
    compare_field("Outcome", manual_outcome, trade['outcome'])
    compare_field("Realized RR", manual_realized_rr, trade['realized_rr'], tolerance=0.001)

    passed = len(discrepancies) == 0

    if passed:
        print(f"\n[OK] PASS: All fields match!")
    else:
        print(f"\n[FAIL] FAIL: {len(discrepancies)} discrepancies found")
        for disc in discrepancies:
            print(f"  - {disc}")

    return passed, discrepancies


def main():
    conn = duckdb.connect(DB_PATH)

    print("="*80)
    print("GROUND TRUTH VALIDATOR")
    print("="*80)
    print()
    print("Phase 1 of Assumption Audit")
    print("Manually verify 10 random trades end-to-end")
    print()

    # Pick 10 random RESOLVED trades (WIN or LOSS only, skip OPEN/NO_TRADE for now)
    query = """
        SELECT
            date_local, setup_id, instrument, orb_time,
            entry_price, stop_price, target_price, exit_price,
            risk_points, target_points, risk_dollars,
            outcome, realized_rr, mae, mfe
        FROM validated_trades
        WHERE outcome IN ('WIN', 'LOSS')
          AND setup_id IN (
              SELECT id FROM validated_setups
              WHERE instrument = 'MGC' AND status = 'ACTIVE'
          )
        ORDER BY RANDOM()
        LIMIT 10
    """

    # Get RR values for each setup
    setup_rr_query = """
        SELECT id, rr FROM validated_setups
    """
    setup_rr_map = {row[0]: row[1] for row in conn.execute(setup_rr_query).fetchall()}

    trades = conn.execute(query).fetchall()

    if not trades:
        print("[ERROR] No trades found to validate")
        return

    print(f"[INFO] Selected {len(trades)} random ACTIVE strategy trades to validate")
    print()

    results = []

    for i, trade_tuple in enumerate(trades, 1):
        trade = {
            'date_local': trade_tuple[0],
            'setup_id': trade_tuple[1],
            'instrument': trade_tuple[2],
            'orb_time': trade_tuple[3],
            'entry_price': trade_tuple[4],
            'stop_price': trade_tuple[5],
            'target_price': trade_tuple[6],
            'exit_price': trade_tuple[7],
            'risk_points': trade_tuple[8],
            'target_points': trade_tuple[9],
            'risk_dollars': trade_tuple[10],
            'outcome': trade_tuple[11],
            'realized_rr': trade_tuple[12],
            'mae': trade_tuple[13],
            'mfe': trade_tuple[14],
            'rr': setup_rr_map.get(trade_tuple[1], None)
        }

        print(f"\n{'#'*80}")
        print(f"TRADE {i}/10")
        print(f"{'#'*80}")

        passed, discrepancies = validate_trade_ground_truth(conn, trade)

        results.append({
            'trade': trade,
            'passed': passed,
            'discrepancies': discrepancies
        })

    # Summary
    print(f"\n{'='*80}")
    print(f"GROUND TRUTH VALIDATION SUMMARY")
    print(f"{'='*80}")
    print()

    passed_count = sum(1 for r in results if r['passed'])
    failed_count = len(results) - passed_count

    print(f"[OK] PASSED: {passed_count}/10")
    print(f"[FAIL] FAILED: {failed_count}/10")
    print()

    if failed_count > 0:
        print("FAILURES:")
        for i, result in enumerate(results, 1):
            if not result['passed']:
                trade = result['trade']
                print(f"\n  Trade {i}: {trade['date_local']} | Setup {trade['setup_id']} | {trade['orb_time']} ORB")
                for disc in result['discrepancies']:
                    print(f"    - {disc}")
        print()
        print("[CRITICAL] CRITICAL: DISCREPANCIES FOUND")
        print("[CRITICAL] STOP ALL WORK AND FIX BEFORE PROCEEDING")
    else:
        print("[OK] ALL TRADES VALIDATED SUCCESSFULLY")
        print("[OK] Ground truth matches database - proceed to Phase 2")

    conn.close()


if __name__ == "__main__":
    main()
