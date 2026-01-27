"""
Test execution modes refactoring

Tests that execution_engine.py correctly uses execution_modes.py functions
"""

import duckdb
from datetime import date
from strategies.execution_engine import simulate_orb_trade
from strategies.execution_modes import ExecutionMode

DB_PATH = 'data/db/gold.db'

def test_basic_execution():
    """Test that execution_engine.py runs without errors"""
    con = duckdb.connect(DB_PATH, read_only=True)

    # Test MARKET_ON_CLOSE mode
    result_market = simulate_orb_trade(
        con=con,
        date_local=date(2025, 1, 10),
        orb="1000",
        mode="1m",
        confirm_bars=1,
        rr=2.0,
        sl_mode="full",
        exec_mode=ExecutionMode.MARKET_ON_CLOSE,
        slippage_ticks=1.5,
        commission_per_contract=1.0
    )

    print("MARKET_ON_CLOSE test:")
    print(f"  Outcome: {result_market.outcome}")
    print(f"  Direction: {result_market.direction}")
    print(f"  Entry price: {result_market.entry_price}")
    print(f"  Slippage: {result_market.slippage_ticks} ticks")
    print(f"  Commission: ${result_market.commission}")
    print(f"  Cost in R: {result_market.cost_r:.3f}R")
    print()

    # Test LIMIT_AT_ORB mode
    result_limit = simulate_orb_trade(
        con=con,
        date_local=date(2025, 1, 10),
        orb="1000",
        mode="1m",
        confirm_bars=1,
        rr=2.0,
        sl_mode="full",
        exec_mode=ExecutionMode.LIMIT_AT_ORB,
        slippage_ticks=0.0,  # No slippage for limit orders
        commission_per_contract=1.0
    )

    print("LIMIT_AT_ORB test:")
    print(f"  Outcome: {result_limit.outcome}")
    print(f"  Direction: {result_limit.direction}")
    print(f"  Entry price: {result_limit.entry_price}")
    print(f"  Slippage: {result_limit.slippage_ticks} ticks")
    print(f"  Commission: ${result_limit.commission}")
    print(f"  Cost in R: {result_limit.cost_r:.3f}R")
    print()

    # Test LIMIT_RETRACE mode
    result_retrace = simulate_orb_trade(
        con=con,
        date_local=date(2025, 1, 10),
        orb="1000",
        mode="1m",
        confirm_bars=1,
        rr=2.0,
        sl_mode="full",
        exec_mode=ExecutionMode.LIMIT_RETRACE,
        slippage_ticks=0.0,
        commission_per_contract=1.0
    )

    print("LIMIT_RETRACE test:")
    print(f"  Outcome: {result_retrace.outcome}")
    print(f"  Direction: {result_retrace.direction}")
    print(f"  Entry price: {result_retrace.entry_price}")
    print(f"  Slippage: {result_retrace.slippage_ticks} ticks")
    print(f"  Commission: ${result_retrace.commission}")
    print(f"  Cost in R: {result_retrace.cost_r:.3f}R")
    print()

    con.close()

    # Assertions
    assert result_market.slippage_ticks == 1.5, "MARKET mode should have slippage"
    assert result_limit.slippage_ticks == 0.0, "LIMIT_AT_ORB mode should have no slippage"
    assert result_retrace.slippage_ticks == 0.0, "LIMIT_RETRACE mode should have no slippage"

    print("✅ All tests passed!")


if __name__ == "__main__":
    test_basic_execution()
