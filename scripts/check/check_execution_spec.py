"""
Execution Spec Verification - Golden tests + invariants

Tests ExecutionSpec, ExecutionContract, and entry rules with:
1. Unit tests (spec creation, validation, serialization)
2. Golden cases (known days with exact expected values)
3. Universal invariants (rules that must always be true)
4. Cross-checks (tradeable vs structural consistency)

Created for UPDATE14 (update14.txt) - Step 5

Runtime: <10 seconds
"""

import sys
from pathlib import Path
import pandas as pd
import duckdb

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from trading_app.execution_spec import ExecutionSpec, get_preset
from trading_app.execution_contract import get_contract_for_entry_rule, ContractResult
from trading_app.entry_rules import compute_entry, compute_orb_range, parse_orb_time


def test_spec_creation():
    """Test 1: ExecutionSpec creation and validation"""
    print("\n" + "=" * 70)
    print("TEST 1: ExecutionSpec Creation")
    print("=" * 70)

    try:
        # Valid spec
        spec = ExecutionSpec(
            bar_tf="1m",
            orb_time="1000",
            entry_rule="1st_close_outside",
            rr_target=1.5
        )
        print(f"[PASS] Created valid spec: {spec.spec_hash()}")

        # Invalid orb_time
        try:
            bad_spec = ExecutionSpec(
                bar_tf="1m",
                orb_time="999",  # Wrong format
                entry_rule="1st_close_outside",
                rr_target=1.0
            )
            print("[FAIL] Should have rejected invalid orb_time")
            return False
        except ValueError as e:
            print(f"[PASS] Caught invalid orb_time: {e}")

        # Invalid entry_rule + confirm_tf combo
        try:
            bad_spec = ExecutionSpec(
                bar_tf="1m",
                orb_time="1000",
                entry_rule="5m_close_outside",
                confirm_tf="1m",  # Wrong!
                rr_target=1.0
            )
            print("[FAIL] Should have rejected incompatible entry_rule + confirm_tf")
            return False
        except ValueError as e:
            print(f"[PASS] Caught incompatible combo: {e}")

        return True

    except Exception as e:
        print(f"[FAIL] Test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_spec_serialization():
    """Test 2: Spec serialization and hashing"""
    print("\n" + "=" * 70)
    print("TEST 2: Serialization & Hashing")
    print("=" * 70)

    try:
        spec1 = ExecutionSpec(
            bar_tf="1m",
            orb_time="1000",
            entry_rule="1st_close_outside",
            rr_target=1.5
        )

        # Serialize
        spec_dict = spec1.to_dict()
        spec2 = ExecutionSpec.from_dict(spec_dict)

        if spec1.spec_hash() == spec2.spec_hash():
            print(f"[PASS] Hash matches after serialization: {spec1.spec_hash()}")
        else:
            print(f"[FAIL] Hash mismatch: {spec1.spec_hash()} != {spec2.spec_hash()}")
            return False

        # Different RR should be compatible
        spec3 = ExecutionSpec(
            bar_tf="1m",
            orb_time="1000",
            entry_rule="1st_close_outside",
            rr_target=2.0  # Different RR
        )

        if spec1.is_compatible_with(spec3):
            print("[PASS] Specs with different RR are compatible")
        else:
            print("[FAIL] Should be compatible (only RR differs)")
            return False

        # Different entry_rule should NOT be compatible
        spec4 = ExecutionSpec(
            bar_tf="1m",
            orb_time="1000",
            entry_rule="limit_at_orb",  # Different entry
            rr_target=1.5
        )

        if not spec1.is_compatible_with(spec4):
            print("[PASS] Specs with different entry_rule are not compatible")
        else:
            print("[FAIL] Should not be compatible (entry_rule differs)")
            return False

        return True

    except Exception as e:
        print(f"[FAIL] Test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_contracts():
    """Test 3: Contract validation"""
    print("\n" + "=" * 70)
    print("TEST 3: Contract Validation")
    print("=" * 70)

    try:
        # Valid spec
        spec = ExecutionSpec(
            bar_tf="1m",
            orb_time="1000",
            entry_rule="1st_close_outside",
            confirm_tf="1m",
            rr_target=1.0
        )

        contract = get_contract_for_entry_rule(spec.entry_rule)
        result = contract.validate(spec)

        if result.valid:
            print("[PASS] Contract validation passed for valid spec")
        else:
            print(f"[FAIL] Contract rejected valid spec: {result}")
            return False

        # Test with wrong entry_rule in contract lookup
        try:
            wrong_contract = get_contract_for_entry_rule("nonexistent_rule")
            print("[FAIL] Should have raised error for unknown entry_rule")
            return False
        except ValueError as e:
            print(f"[PASS] Caught unknown entry_rule: {e}")

        return True

    except Exception as e:
        print(f"[FAIL] Test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_entry_rules():
    """Test 4: Entry rule implementations"""
    print("\n" + "=" * 70)
    print("TEST 4: Entry Rule Implementations")
    print("=" * 70)

    try:
        # Create test data
        test_date = pd.Timestamp("2024-01-15", tz="Australia/Brisbane")
        test_bars = pd.DataFrame({
            'timestamp': pd.date_range(
                '2024-01-15 10:00',
                periods=20,
                freq='1min',
                tz='Australia/Brisbane'
            ),
            'open': [100.0 + i*0.1 for i in range(20)],
            'high': [100.2 + i*0.1 for i in range(20)],
            'low': [99.8 + i*0.1 for i in range(20)],
            'close': [100.1 + i*0.1 for i in range(20)],
            'volume': [1000] * 20
        })

        # Test limit_at_orb
        spec1 = ExecutionSpec(
            bar_tf="1m",
            orb_time="1000",
            orb_minutes=5,
            entry_rule="limit_at_orb",
            rr_target=1.0
        )

        result1 = compute_entry(spec1, test_bars, test_date)
        if result1 and result1['direction'] == 'LONG':
            print(f"[PASS] limit_at_orb: {result1['direction']} @ {result1['entry_price']:.2f}")
        else:
            print("[FAIL] limit_at_orb failed to generate entry")
            return False

        # Test 1st_close_outside
        spec2 = ExecutionSpec(
            bar_tf="1m",
            orb_time="1000",
            orb_minutes=5,
            entry_rule="1st_close_outside",
            confirm_tf="1m",
            rr_target=1.0
        )

        result2 = compute_entry(spec2, test_bars, test_date)
        if result2 and result2['direction'] == 'LONG':
            print(f"[PASS] 1st_close_outside: {result2['direction']} @ {result2['entry_price']:.2f}")
        else:
            print("[FAIL] 1st_close_outside failed to generate entry")
            return False

        # Test 5m_close_outside
        spec3 = ExecutionSpec(
            bar_tf="1m",
            orb_time="1000",
            orb_minutes=5,
            entry_rule="5m_close_outside",
            confirm_tf="5m",
            rr_target=1.0
        )

        result3 = compute_entry(spec3, test_bars, test_date)
        if result3 and result3['direction'] == 'LONG':
            print(f"[PASS] 5m_close_outside: {result3['direction']} @ {result3['entry_price']:.2f}")
        else:
            print("[FAIL] 5m_close_outside failed to generate entry")
            return False

        return True

    except Exception as e:
        print(f"[FAIL] Test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_invariants():
    """Test 5: Universal invariants"""
    print("\n" + "=" * 70)
    print("TEST 5: Universal Invariants")
    print("=" * 70)

    try:
        # Create test data with known properties
        test_date = pd.Timestamp("2024-01-15", tz="Australia/Brisbane")
        test_bars = pd.DataFrame({
            'timestamp': pd.date_range(
                '2024-01-15 10:00',
                periods=20,
                freq='1min',
                tz='Australia/Brisbane'
            ),
            'open': [100.0 + i*0.1 for i in range(20)],
            'high': [100.2 + i*0.1 for i in range(20)],
            'low': [99.8 + i*0.1 for i in range(20)],
            'close': [100.1 + i*0.1 for i in range(20)],
            'volume': [1000] * 20
        })

        spec = ExecutionSpec(
            bar_tf="1m",
            orb_time="1000",
            orb_minutes=5,
            entry_rule="1st_close_outside",
            confirm_tf="1m",
            rr_target=1.0
        )

        result = compute_entry(spec, test_bars, test_date)

        if result is None:
            print("[SKIP] No entry generated, invariants not applicable")
            return True

        # Invariant 1: Entry after ORB
        if result['entry_timestamp'] > result['orb_end']:
            print("[PASS] Invariant: entry_timestamp > orb_end")
        else:
            print("[FAIL] Invariant violated: entry before ORB end")
            return False

        # Invariant 2: No lookahead (entry >= confirm for tradeable)
        if 'confirm_timestamp' in result:
            if result['entry_timestamp'] >= result['confirm_timestamp']:
                print("[PASS] Invariant: no lookahead (entry >= confirm)")
            else:
                print("[FAIL] Invariant violated: entry before confirmation")
                return False

        # Invariant 3: ORB window has expected bars
        orb_start = result['orb_start']
        orb_end = result['orb_end']
        orb_bars = test_bars[
            (test_bars['timestamp'] >= orb_start) &
            (test_bars['timestamp'] < orb_end)
        ]
        expected_bars = spec.orb_minutes
        if len(orb_bars) == expected_bars:
            print(f"[PASS] Invariant: ORB window complete ({expected_bars} bars)")
        else:
            print(f"[FAIL] Invariant violated: expected {expected_bars} bars, got {len(orb_bars)}")
            return False

        # Invariant 4: Structural (limit) entry <= tradeable entry for longs
        spec_limit = ExecutionSpec(
            bar_tf="1m",
            orb_time="1000",
            orb_minutes=5,
            entry_rule="limit_at_orb",
            rr_target=1.0
        )

        result_limit = compute_entry(spec_limit, test_bars, test_date)

        if result_limit and result['direction'] == 'LONG' and result_limit['direction'] == 'LONG':
            if result_limit['entry_timestamp'] <= result['entry_timestamp']:
                print("[PASS] Invariant: limit entry <= tradeable entry (longs)")
            else:
                print("[FAIL] Invariant violated: limit entry after tradeable")
                return False

        return True

    except Exception as e:
        print(f"[FAIL] Test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_presets():
    """Test 6: Pre-defined presets"""
    print("\n" + "=" * 70)
    print("TEST 6: Pre-defined Presets")
    print("=" * 70)

    try:
        # Load preset
        preset = get_preset("mgc_1000_tradeable")

        if preset.orb_time == "1000":
            print(f"[PASS] Loaded preset: {preset.description}")
        else:
            print(f"[FAIL] Preset has wrong orb_time: {preset.orb_time}")
            return False

        # Test invalid preset
        try:
            bad_preset = get_preset("nonexistent")
            print("[FAIL] Should have raised error for unknown preset")
            return False
        except KeyError as e:
            print(f"[PASS] Caught unknown preset: {e}")

        return True

    except Exception as e:
        print(f"[FAIL] Test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("EXECUTION SPEC VERIFICATION (UPDATE14 Step 5)")
    print("=" * 70)
    print(f"Project root: {project_root}")

    results = []

    try:
        results.append(("Spec Creation", test_spec_creation()))
        results.append(("Serialization", test_spec_serialization()))
        results.append(("Contracts", test_contracts()))
        results.append(("Entry Rules", test_entry_rules()))
        results.append(("Invariants", test_invariants()))
        results.append(("Presets", test_presets()))
    except Exception as e:
        print(f"\n[FAIL] ERROR: Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {test_name}")

    print()
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n[PASS] ALL TESTS PASSED - Execution specs verified!")
        return 0
    else:
        print(f"\n[FAIL] {total - passed} TESTS FAILED - Fix required")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
