#!/usr/bin/env python3
"""
TEST: Cost Model Sync

Verifies execution_engine uses cost_model (no hard-coded constants).

CRITICAL: execution_engine must ONLY use cost_model.py for all cost calculations.
No hard-coded point values, commission rates, or slippage assumptions allowed.
"""

import sys
from pathlib import Path

# Add project root to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from pipeline import cost_model


def test_no_hardcoded_constants():
    """Verify execution_engine has no hard-coded cost constants."""
    print("=" * 70)
    print("TEST: No Hard-Coded Constants in execution_engine.py")
    print("=" * 70)
    print()

    # Read execution_engine.py source
    engine_path = repo_root / "strategies" / "execution_engine.py"
    with open(engine_path, 'r') as f:
        source = f.read()

    # Check for hard-coded constants (should NOT exist)
    forbidden_patterns = [
        ("10.0", "MGC point value should come from cost_model"),
        ("7.40", "Total friction should come from cost_model"),
        ("2.40", "Commission should come from cost_model"),
        ("4.00", "Slippage should come from cost_model"),
    ]

    failures = []
    for pattern, reason in forbidden_patterns:
        if pattern in source and "cost_model" not in source.split(pattern)[0][-200:]:
            failures.append(f"Found hard-coded constant {pattern}: {reason}")

    if failures:
        print("[FAIL] Hard-coded constants detected:")
        for failure in failures:
            print(f"  - {failure}")
        print()
        print("REQUIRED FIX: Import and use cost_model.py")
        return False
    else:
        print("[OK] No hard-coded constants found")
        print()
        return True


def test_cost_model_imported():
    """Verify execution_engine imports cost_model."""
    print("=" * 70)
    print("TEST: cost_model Import in execution_engine.py")
    print("=" * 70)
    print()

    engine_path = repo_root / "strategies" / "execution_engine.py"
    with open(engine_path, 'r') as f:
        source = f.read()

    if "from pipeline.cost_model import" in source or "import cost_model" in source:
        print("[OK] cost_model imported")
        print()
        return True
    else:
        print("[FAIL] cost_model NOT imported")
        print("REQUIRED FIX: Add 'from pipeline.cost_model import calculate_realized_rr'")
        print()
        return False


def test_cost_model_used():
    """Verify execution_engine calls cost_model functions."""
    print("=" * 70)
    print("TEST: cost_model Usage in execution_engine.py")
    print("=" * 70)
    print()

    engine_path = repo_root / "strategies" / "execution_engine.py"
    with open(engine_path, 'r') as f:
        source = f.read()

    if "calculate_realized_rr(" in source:
        print("[OK] cost_model.calculate_realized_rr() is called")
        print()
        return True
    else:
        print("[FAIL] cost_model.calculate_realized_rr() NOT called")
        print("REQUIRED FIX: Call cost_model.calculate_realized_rr() for all realized RR calculations")
        print()
        return False


def test_cost_model_returns_expected_values():
    """Verify cost_model returns expected values for MGC."""
    print("=" * 70)
    print("TEST: cost_model Returns Expected Values")
    print("=" * 70)
    print()

    # Test MGC specs
    specs = cost_model.INSTRUMENT_SPECS.get('MGC')
    if not specs:
        print("[FAIL] MGC specs not found in cost_model")
        return False

    expected_specs = {
        'tick_size': 0.10,
        'tick_value': 1.00,
        'point_value': 10.00,
        'status': 'PRODUCTION'
    }

    for key, expected in expected_specs.items():
        actual = specs.get(key)
        if actual != expected:
            print(f"[FAIL] MGC {key}: expected {expected}, got {actual}")
            return False

    print("[OK] MGC specs correct:")
    print(f"  Point value: ${specs['point_value']}")
    print(f"  Tick size: {specs['tick_size']}")
    print(f"  Tick value: ${specs['tick_value']}")
    print()

    # Test MGC costs
    costs = cost_model.COST_MODELS.get('MGC')
    if not costs:
        print("[FAIL] MGC costs not found in cost_model")
        return False

    expected_costs = {
        'commission_rt': 2.40,
        'slippage_rt': 4.00,
        'spread': 1.00,
        'total_friction': 7.40,
        'status': 'PRODUCTION'
    }

    for key, expected in expected_costs.items():
        actual = costs.get(key)
        if actual != expected:
            print(f"[FAIL] MGC {key}: expected {expected}, got {actual}")
            return False

    print("[OK] MGC costs correct:")
    print(f"  Commission: ${costs['commission_rt']}")
    print(f"  Slippage: ${costs['slippage_rt']}")
    print(f"  Total friction: ${costs['total_friction']}")
    print()

    # Test realized RR calculation
    try:
        result = cost_model.calculate_realized_rr(
            instrument='MGC',
            stop_distance_points=5.0,
            rr_theoretical=1.5,
            stress_level='normal'
        )

        print("[OK] calculate_realized_rr() works:")
        print(f"  Stop: 5.0 points")
        print(f"  Theoretical RR: 1.5")
        print(f"  Realized RR: {result['realized_rr']:.3f}")
        print(f"  Realized risk: ${result['realized_risk_dollars']:.2f}")
        print(f"  Realized reward: ${result['realized_reward_dollars']:.2f}")
        print()

        return True

    except Exception as e:
        print(f"[FAIL] calculate_realized_rr() failed: {e}")
        return False


def run_all_tests():
    """Run all cost model sync tests."""
    print()
    print("=" * 70)
    print("COST MODEL SYNC TESTS")
    print("=" * 70)
    print()

    tests = [
        test_no_hardcoded_constants,
        test_cost_model_imported,
        test_cost_model_used,
        test_cost_model_returns_expected_values,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"[ERROR] Test failed with exception: {e}")
            results.append(False)

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")
    print()

    if passed == total:
        print("[OK] ALL TESTS PASSED")
        print()
        print("execution_engine.py correctly uses cost_model.py for all cost calculations.")
        return True
    else:
        print("[FAIL] SOME TESTS FAILED")
        print()
        print("CRITICAL: execution_engine must use cost_model.py (no hard-coded constants).")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
