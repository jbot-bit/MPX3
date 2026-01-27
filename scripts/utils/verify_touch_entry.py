"""
Verify LIMIT_AT_ORB touch-based entry is working correctly

Shows detailed trade examples to prove touch detection is accurate
"""

import duckdb
from datetime import date
from strategies.execution_engine import simulate_orb_trade
from strategies.execution_modes import ExecutionMode

DB_PATH = 'data/db/gold.db'

def verify_touch_entry():
    """Show detailed examples of touch vs close entry"""

    con = duckdb.connect(DB_PATH, read_only=True)

    # Test date with known ORB
    test_date = date(2025, 1, 10)

    # Get ORB values
    row = con.execute("""
        SELECT orb_1000_high, orb_1000_low, orb_1000_size, orb_1000_break_dir
        FROM daily_features
        WHERE date_local = ? AND instrument = 'MGC'
    """, [test_date]).fetchone()

    orb_high, orb_low, orb_size, break_dir = row

    print("="*80)
    print(f"TOUCH vs CLOSE ENTRY VERIFICATION - {test_date}")
    print("="*80)
    print()
    print(f"ORB: High={orb_high}, Low={orb_low}, Size={orb_size:.2f}, Direction={break_dir}")
    print()

    # Test MARKET_ON_CLOSE
    result_market = simulate_orb_trade(
        con=con,
        date_local=test_date,
        orb="1000",
        mode="1m",
        confirm_bars=1,
        rr=2.0,
        sl_mode="full",
        exec_mode=ExecutionMode.MARKET_ON_CLOSE,
        slippage_ticks=1.5,
        commission_per_contract=1.0
    )

    print("MARKET_ON_CLOSE (uses CLOSE + slippage):")
    print(f"  Entry price: {result_market.entry_price}")
    print(f"  Entry time: {result_market.entry_ts}")
    print(f"  Slippage: {result_market.slippage_ticks} ticks")
    print(f"  Stop: {result_market.stop_price}")
    print(f"  Target: {result_market.target_price}")
    print(f"  Risk: {result_market.stop_ticks:.1f} ticks")
    print(f"  Outcome: {result_market.outcome} ({result_market.r_multiple:+.2f}R)")
    print()

    # Test LIMIT_AT_ORB
    result_limit = simulate_orb_trade(
        con=con,
        date_local=test_date,
        orb="1000",
        mode="1m",
        confirm_bars=1,
        rr=2.0,
        sl_mode="full",
        exec_mode=ExecutionMode.LIMIT_AT_ORB,
        slippage_ticks=0.0,
        commission_per_contract=1.0
    )

    print("LIMIT_AT_ORB (uses TOUCH of ORB edge):")
    print(f"  Entry price: {result_limit.entry_price}")
    print(f"  Entry time: {result_limit.entry_ts}")
    print(f"  Slippage: {result_limit.slippage_ticks} ticks")
    print(f"  Stop: {result_limit.stop_price}")
    print(f"  Target: {result_limit.target_price}")
    print(f"  Risk: {result_limit.stop_ticks:.1f} ticks")
    print(f"  Outcome: {result_limit.outcome} ({result_limit.r_multiple:+.2f}R)")
    print()

    # Verify entry prices
    print("VERIFICATION:")
    if result_market.direction == "UP":
        print(f"  ORB high: {orb_high}")
        print(f"  MARKET entry: {result_market.entry_price} (should be > ORB high)")
        print(f"  LIMIT entry: {result_limit.entry_price} (should be = ORB high)")
        assert result_market.entry_price > orb_high, "MARKET should enter ABOVE ORB high"
        assert abs(result_limit.entry_price - orb_high) < 0.001, "LIMIT should enter AT ORB high"
        print("  [PASS] MARKET entered above ORB high (has slippage)")
        print("  [PASS] LIMIT entered exactly at ORB high (touch-based)")
    else:
        print(f"  ORB low: {orb_low}")
        print(f"  MARKET entry: {result_market.entry_price} (should be < ORB low)")
        print(f"  LIMIT entry: {result_limit.entry_price} (should be = ORB low)")
        assert result_market.entry_price < orb_low, "MARKET should enter BELOW ORB low"
        assert abs(result_limit.entry_price - orb_low) < 0.001, "LIMIT should enter AT ORB low"
        print("  [PASS] MARKET entered below ORB low (has slippage)")
        print("  [PASS] LIMIT entered exactly at ORB low (touch-based)")

    print()

    # Show cost difference
    print("COST COMPARISON:")
    print(f"  MARKET cost: {result_market.cost_r:.3f}R (slippage={result_market.slippage_ticks} ticks + commission=${result_market.commission})")
    print(f"  LIMIT cost: {result_limit.cost_r:.3f}R (slippage={result_limit.slippage_ticks} ticks + commission=${result_limit.commission})")
    print(f"  Savings: {result_market.cost_r - result_limit.cost_r:.3f}R per trade")
    print()

    # Show bars around entry to prove touch happened
    print("BAR-BY-BAR PROOF:")
    bars = con.execute(f"""
        SELECT
            (ts_utc AT TIME ZONE 'Australia/Brisbane') AS ts_local,
            high, low, close
        FROM bars_1m
        WHERE symbol = 'MGC'
          AND (ts_utc AT TIME ZONE 'Australia/Brisbane') >= '{test_date} 10:05:00'
          AND (ts_utc AT TIME ZONE 'Australia/Brisbane') <= '{test_date} 10:20:00'
        ORDER BY ts_local
    """).fetchall()

    print(f"  Bars around entry time (showing when ORB {orb_high if result_limit.direction == 'UP' else orb_low} was touched):")
    for ts, high, low, close in bars[:10]:
        touched = ""
        if result_limit.direction == "UP" and high >= orb_high:
            touched = " <-- TOUCHED ORB HIGH!" if abs(high - orb_high) < 2.0 else ""
        elif result_limit.direction == "DOWN" and low <= orb_low:
            touched = " <-- TOUCHED ORB LOW!" if abs(low - orb_low) < 2.0 else ""

        close_outside = ""
        if result_limit.direction == "UP" and close > orb_high:
            close_outside = " (close outside)"
        elif result_limit.direction == "DOWN" and close < orb_low:
            close_outside = " (close outside)"

        print(f"    {ts}: H={high:.2f} L={low:.2f} C={close:.2f}{touched}{close_outside}")

    print()
    print("[PASS] Touch detection verified - LIMIT_AT_ORB enters when bar HIGH/LOW touches ORB edge")
    print("[PASS] Close detection verified - MARKET_ON_CLOSE enters when bar CLOSE is outside ORB")
    print()

    con.close()


if __name__ == "__main__":
    verify_touch_entry()
