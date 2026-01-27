"""
Basic test of execution modes refactoring.

Tests that the refactored execution engine:
1. Imports correctly
2. Has all 3 execution modes available
3. Dataclass has new fields
4. Function signature updated

This is a SYNTAX test only - doesn't run actual trades yet.
"""

print("="*80)
print("TESTING EXECUTION MODES REFACTORING - SYNTAX CHECK")
print("="*80)
print()

# Test 1: Import execution modes
print("[TEST 1] Import execution modes...")
try:
    from strategies.execution_modes import ExecutionMode
    print(f"  [OK] ExecutionMode enum imported")
    print(f"  Available modes: {[m.value for m in ExecutionMode]}")
    print()
except Exception as e:
    print(f"  [FAIL] Could not import: {e}")
    exit(1)

# Test 2: Import execution engine
print("[TEST 2] Import execution engine...")
try:
    from strategies.execution_engine import simulate_orb_trade, TradeResult
    print(f"  [OK] simulate_orb_trade imported")
    print()
except Exception as e:
    print(f"  [FAIL] Could not import: {e}")
    exit(1)

# Test 3: Check TradeResult has new fields
print("[TEST 3] Check TradeResult dataclass...")
try:
    required_fields = [
        'slippage_ticks',
        'commission',
        'cost_r',
        'fill_ts'
    ]

    from dataclasses import fields
    field_names = [f.name for f in fields(TradeResult)]

    for field in required_fields:
        if field in field_names:
            print(f"  [OK] {field} exists")
        else:
            print(f"  [FAIL] {field} MISSING")
            exit(1)

    print()
except Exception as e:
    print(f"  [FAIL] Could not check fields: {e}")
    exit(1)

# Test 4: Check function signature
print("[TEST 4] Check function signature...")
try:
    import inspect
    sig = inspect.signature(simulate_orb_trade)
    params = list(sig.parameters.keys())

    required_params = ['exec_mode', 'slippage_ticks', 'commission_per_contract']

    for param in required_params:
        if param in params:
            print(f"  [OK] {param} parameter exists")
        else:
            print(f"  [FAIL] {param} parameter MISSING")
            exit(1)

    # Check default value for exec_mode
    default_mode = sig.parameters['exec_mode'].default
    if default_mode == ExecutionMode.MARKET_ON_CLOSE:
        print(f"  [OK] exec_mode defaults to MARKET_ON_CLOSE")
    else:
        print(f"  [WARN] exec_mode defaults to {default_mode} (expected MARKET_ON_CLOSE)")

    print()
except Exception as e:
    print(f"  [FAIL] Could not check signature: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("="*80)
print("ALL SYNTAX TESTS PASSED")
print("="*80)
print()
print("Next steps:")
print("  1. Complete refactoring of execution_engine.py")
print("  2. Update all TradeResult returns to include new fields")
print("  3. Replace entry logic with execution mode calls")
print("  4. Test with real data")
print()
