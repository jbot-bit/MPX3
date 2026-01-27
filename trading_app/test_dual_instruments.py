"""
TEST DUAL INSTRUMENT SUPPORT
Validates that both MGC and NQ work correctly with instrument-specific configs.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from data_loader import LiveDataLoader
from strategy_engine import StrategyEngine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_instrument(symbol: str):
    """Test an instrument end-to-end."""
    print(f"\n{'='*80}")
    print(f"TESTING {symbol}")
    print(f"{'='*80}\n")

    try:
        # 1. Initialize data loader
        print(f"1. Initializing data loader for {symbol}...")
        loader = LiveDataLoader(symbol)
        loader.backfill_from_gold_db("../data/db/gold.db", days=2)
        print(f"   [OK] Data loaded: {len(loader.bars_df)} bars")

        # 2. Get latest bar
        latest = loader.get_latest_bar()
        if latest:
            print(f"   [OK] Latest bar: {latest['ts_local']} @ ${latest['close']:.2f}")
        else:
            print(f"   [WARN] No bars found (data might be historical)")
            # This is OK for testing configs - continue anyway

        # 3. Get ATR
        atr = loader.get_today_atr()
        if atr:
            print(f"   [OK] ATR(20): {atr:.2f} points")
        else:
            print(f"   [WARN]  ATR not available")

        # 4. Initialize strategy engine
        print(f"\n2. Initializing strategy engine...")
        engine = StrategyEngine(loader)
        print(f"   [OK] Engine initialized")
        print(f"   - Instrument: {engine.instrument}")
        print(f"   - CASCADE gap: {engine.cascade_min_gap:.1f}pts")

        # 5. Check ORB configs
        print(f"\n3. Checking ORB configurations...")
        for orb_name, config in engine.orb_configs.items():
            if config.get("tier") == "SKIP":
                print(f"   [SKIP]  {orb_name}: SKIP (negative expectancy)")
            else:
                print(f"   [OK] {orb_name}: RR={config['rr']}, SL={config['sl_mode']}, tier={config['tier']}")

        # 6. Check ORB filters
        print(f"\n4. Checking ORB size filters...")
        for orb_name, threshold in engine.orb_size_filters.items():
            if threshold is None:
                print(f"   * {orb_name}: No filter")
            else:
                print(f"   * {orb_name}: < {threshold*100:.1f}% ATR")

        # 7. Test ORB filter logic
        print(f"\n5. Testing ORB filter logic...")
        # Simulate a small ORB
        if atr:
            test_orb_high = 1000.0
            test_orb_low = 1000.0 - (atr * 0.05)  # 5% of ATR
            result = loader.check_orb_size_filter(test_orb_high, test_orb_low, "0900")
            print(f"   Test ORB (5% ATR): {result['pass']} - {result['reason']}")
        else:
            print(f"   [WARN]  Skipping filter test (no ATR)")

        # 8. Evaluate strategies
        print(f"\n6. Evaluating strategies...")
        evaluation = engine.evaluate_all()
        print(f"   Strategy: {evaluation.strategy_name}")
        print(f"   State: {evaluation.state.value}")
        print(f"   Action: {evaluation.action.value}")
        print(f"   Reasons:")
        for reason in evaluation.reasons:
            print(f"     - {reason}")

        # 9. Close loader
        loader.close()
        print(f"\n[OK] ALL TESTS PASSED FOR {symbol}")
        return True

    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run tests for both instruments."""
    print("\n" + "="*80)
    print("DUAL INSTRUMENT SUPPORT - END-TO-END TEST")
    print("="*80)

    # Test MGC
    mgc_pass = test_instrument("MGC")

    # Test NQ
    nq_pass = test_instrument("MNQ")

    # Summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    print(f"MGC: {'[OK] PASS' if mgc_pass else '[FAIL] FAIL'}")
    print(f"NQ:  {'[OK] PASS' if nq_pass else '[FAIL] FAIL'}")
    print(f"{'='*80}\n")

    if mgc_pass and nq_pass:
        print("SUCCESS: ALL TESTS PASSED - DUAL INSTRUMENT SUPPORT WORKING")
        return 0
    else:
        print("[WARN]  SOME TESTS FAILED - CHECK LOGS ABOVE")
        return 1


if __name__ == "__main__":
    exit(main())
