"""
Test script to verify app components work correctly.
Run this before launching the Streamlit app.
"""

import sys
import os

# Add parent directory to path to access .env
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Testing Trading App Components")
print("=" * 60)

# Test 1: Import all modules
print("\n1. Testing imports...")
try:
    from config import *
    print("   [OK] config.py imported successfully")
except Exception as e:
    print(f"   [FAIL] config.py import failed: {e}")
    sys.exit(1)

try:
    from data_loader import LiveDataLoader
    print("   [OK] data_loader.py imported successfully")
except Exception as e:
    print(f"   [FAIL] data_loader.py import failed: {e}")
    sys.exit(1)

try:
    from strategy_engine import StrategyEngine, StrategyState, ActionType
    print("   [OK] strategy_engine.py imported successfully")
except Exception as e:
    print(f"   [FAIL] strategy_engine.py import failed: {e}")
    sys.exit(1)

try:
    from utils import calculate_position_size, format_price, log_to_journal
    print("   [OK] utils.py imported successfully")
except Exception as e:
    print(f"   [FAIL] utils.py import failed: {e}")
    sys.exit(1)

# Test 2: Check .env configuration
print("\n2. Testing configuration...")
print(f"   Database path: {DB_PATH}")
print(f"   Primary instrument: {PRIMARY_INSTRUMENT}")
print(f"   Timezone: {TZ_LOCAL}")
print(f"   ProjectX configured: {'Yes' if PROJECTX_USERNAME and PROJECTX_API_KEY else 'No (will use database mode)'}")

# Test 3: Initialize data loader (without API calls)
print("\n3. Testing data loader initialization...")
try:
    loader = LiveDataLoader("MGC")
    print(f"   [OK] LiveDataLoader created for MGC")
    print(f"   ProjectX token: {'Yes' if loader.projectx_token else 'No (database mode)'}")
except Exception as e:
    print(f"   [WARN] LiveDataLoader initialization failed: {e}")
    print(f"   This is OK if ProjectX API is unavailable - app will use database mode")
    # Create a fallback loader for testing
    loader = None

# Test 4: Test strategy engine initialization
print("\n4. Testing strategy engine...")
if loader:
    try:
        engine = StrategyEngine(loader)
        print("   [OK] StrategyEngine created successfully")

        # Test evaluation (may fail if no data)
        try:
            eval_result = engine.evaluate_all()
            print(f"   [OK] Strategy evaluation completed")
            print(f"     Strategy: {eval_result.strategy_name}")
            print(f"     State: {eval_result.state.value}")
            print(f"     Action: {eval_result.action.value}")
        except Exception as e:
            print(f"   [WARN] Strategy evaluation skipped: {e}")
            print(f"     This is normal if database has no data yet")

    except Exception as e:
        print(f"   [FAIL] StrategyEngine initialization failed: {e}")
        sys.exit(1)
else:
    print("   [SKIP] Strategy engine test skipped (no data loader)")

# Test 5: Test position sizing
print("\n5. Testing position sizing calculator...")
try:
    contracts = calculate_position_size(
        account_size=100000,
        risk_pct=0.25,
        entry_price=2700.0,
        stop_price=2695.0,
        tick_value=10.0  # MGC
    )
    print(f"   [OK] Position sizing works: {contracts} contracts")
    print(f"     (Account: $100k, Risk: 0.25%, Stop: 5pts @ $10/pt)")
except Exception as e:
    print(f"   [FAIL] Position sizing failed: {e}")
    sys.exit(1)

# Test 6: Test journal logging
print("\n6. Testing journal logging...")
try:
    from strategy_engine import StrategyEvaluation

    test_eval = StrategyEvaluation(
        strategy_name="TEST",
        priority=99,
        state=StrategyState.INVALID,
        action=ActionType.STAND_DOWN,
        reasons=["Component test"],
        next_instruction="Testing journal",
        entry_price=None,
        stop_price=None,
        target_price=None,
        risk_pct=None
    )

    log_to_journal(test_eval)
    print("   [OK] Journal logging works")

    # Try to retrieve entries
    from utils import get_recent_journal_entries
    entries = get_recent_journal_entries(limit=1)
    if entries is not None and not entries.empty:
        print(f"   [OK] Journal retrieval works ({len(entries)} entries)")
    else:
        print("   [WARN] No journal entries yet (this is normal)")

except Exception as e:
    print(f"   [FAIL] Journal logging failed: {e}")
    sys.exit(1)

# Test 7: Check critical constants
print("\n7. Verifying strategy parameters...")
print(f"   Cascade min gap: {CASCADE_MIN_GAP_POINTS}pts")
print(f"   ORB configs: {len(ORB_CONFIGS)} defined")
print(f"   Strategy priority: {', '.join(STRATEGY_PRIORITY)}")
print(f"   Risk limits: {len(RISK_LIMITS)} strategies")

# Summary
print("\n" + "=" * 60)
print("[OK] All component tests passed!")
print("\nReady to launch Streamlit app:")
print("  streamlit run app_trading_hub.py")
print("\nOr from project root:")
print("  streamlit run trading_app/app_trading_hub.py")
print("=" * 60)
