"""
End-to-End Tests for What-If Analyzer System

Tests the complete lifecycle:
1. What-If analysis → Snapshot save → Load → Re-evaluate (determinism)
2. Snapshot promotion → Edge registry candidate creation
3. Live gate enforcement → Condition blocking
4. Full lifecycle: Discovery → Condition → Snapshot → Validation → Production

Usage:
    python tests/test_what_if_end_to_end.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import duckdb
from datetime import date
from analysis.what_if_engine import WhatIfEngine, ConditionSet
from analysis.what_if_snapshots import SnapshotManager
from trading_app.live_scanner import LiveScanner


def test_deterministic_evaluation(conn):
    """Test 1: What-If analysis determinism (same inputs = same outputs)"""
    print("\n=== Test 1: Deterministic Evaluation ===")

    engine = WhatIfEngine(conn)

    # Run analysis twice with identical inputs
    conditions = {
        'orb_size_min': 0.5,
        'asia_travel_max': 2.5
    }

    result1 = engine.analyze_conditions(
        instrument='MGC',
        orb_time='1000',
        direction='BOTH',
        rr=2.0,
        sl_mode='FULL',
        conditions=conditions,
        date_start='2024-01-01',
        date_end='2025-12-31',
        use_cache=False  # Force fresh calculation
    )

    result2 = engine.analyze_conditions(
        instrument='MGC',
        orb_time='1000',
        direction='BOTH',
        rr=2.0,
        sl_mode='FULL',
        conditions=conditions,
        date_start='2024-01-01',
        date_end='2025-12-31',
        use_cache=False  # Force fresh calculation
    )

    # Verify identical results
    exp_r_1 = result1['conditional'].expected_r
    exp_r_2 = result2['conditional'].expected_r
    diff = abs(exp_r_1 - exp_r_2)

    print(f"  Run 1 ExpR: {exp_r_1:.6f}R")
    print(f"  Run 2 ExpR: {exp_r_2:.6f}R")
    print(f"  Difference: {diff:.9f}R")

    if diff < 0.000001:
        print("  [PASS] PASS: Deterministic evaluation verified")
        return True
    else:
        print(f"  [FAIL] FAIL: Non-deterministic results (diff={diff})")
        return False


def test_snapshot_roundtrip(conn):
    """Test 2: Snapshot save → load → re-evaluate (exact reproduction)"""
    print("\n=== Test 2: Snapshot Roundtrip ===")

    engine = WhatIfEngine(conn)
    manager = SnapshotManager(conn)

    # Run analysis
    result = engine.analyze_conditions(
        instrument='MGC',
        orb_time='1000',
        direction='BOTH',
        rr=2.0,
        sl_mode='FULL',
        conditions={'orb_size_min': 0.5, 'asia_travel_max': 2.5},
        date_start='2024-01-01',
        date_end='2025-12-31'
    )

    original_exp_r = result['conditional'].expected_r
    print(f"  Original ExpR: {original_exp_r:.9f}R")

    # Save snapshot
    snapshot_id = manager.save_snapshot(
        result=result,
        notes="E2E test snapshot",
        created_by="test_what_if_end_to_end.py"
    )
    print(f"  Saved snapshot: {snapshot_id}")

    # Load snapshot
    loaded = manager.load_snapshot(snapshot_id)
    loaded_exp_r = loaded['conditional_expected_r']
    print(f"  Loaded ExpR: {loaded_exp_r:.9f}R")

    # Re-evaluate
    re_eval = manager.re_evaluate_snapshot(snapshot_id, engine)
    re_eval_exp_r = re_eval['conditional'].expected_r
    print(f"  Re-eval ExpR: {re_eval_exp_r:.9f}R")

    # Verify exact match
    diff_original_loaded = abs(original_exp_r - loaded_exp_r)
    diff_original_re_eval = abs(original_exp_r - re_eval_exp_r)

    print(f"  Original vs Loaded: {diff_original_loaded:.12f}R")
    print(f"  Original vs Re-eval: {diff_original_re_eval:.12f}R")

    if diff_original_loaded < 0.000001 and diff_original_re_eval < 0.000001:
        print("  [PASS] PASS: Exact snapshot reproduction verified")
        return True, snapshot_id
    else:
        print("  [FAIL] FAIL: Snapshot reproduction mismatch")
        return False, snapshot_id


def test_snapshot_promotion(conn, snapshot_id):
    """Test 3: Snapshot promotion → edge_registry candidate creation"""
    print("\n=== Test 3: Snapshot Promotion ===")

    manager = SnapshotManager(conn)

    # Promote snapshot to candidate
    edge_id = manager.promote_snapshot_to_candidate(
        snapshot_id=snapshot_id,
        trigger_definition="ORB breakout with What-If conditions",
        notes="E2E test promotion"
    )

    print(f"  Created edge_id: {edge_id}")

    # Verify edge exists in edge_registry
    row = conn.execute("""
        SELECT edge_id, instrument, orb_time, direction, rr, sl_mode,
               status, filters_applied, trigger_definition
        FROM edge_registry
        WHERE edge_id = ?
    """, [edge_id]).fetchone()

    if row:
        print(f"  [PASS] Edge exists in registry")
        print(f"     Instrument: {row[1]}")
        print(f"     ORB: {row[2]}")
        print(f"     Direction: {row[3]}")
        print(f"     RR: {row[4]}")
        print(f"     Status: {row[6]}")

        # Verify snapshot is marked as promoted
        snap_row = conn.execute("""
            SELECT promoted_to_candidate, candidate_edge_id
            FROM what_if_snapshots
            WHERE snapshot_id = ?
        """, [snapshot_id]).fetchone()

        if snap_row and snap_row[0] and snap_row[1] == edge_id:
            print(f"  [PASS] PASS: Snapshot promotion successful")
            return True, edge_id
        else:
            print(f"  [FAIL] FAIL: Snapshot promotion flag not set")
            return False, edge_id
    else:
        print(f"  [FAIL] FAIL: Edge not found in registry")
        return False, None


def test_live_gate_enforcement(conn, edge_id):
    """Test 4: Live gate enforcement (conditions block trades)"""
    print("\n=== Test 4: Live Gate Enforcement ===")

    scanner = LiveScanner(conn)

    # Load promoted conditions
    conditions = scanner._load_promoted_conditions(edge_id)

    if conditions:
        print(f"  [PASS] Conditions loaded: {conditions}")

        # Test condition evaluation with mock market state
        market_state = {
            'orb_data': {
                '1000': {
                    'size': 5.0,
                    'size_norm': 0.4,  # Below 0.5 threshold
                    'break_dir': 'UP',
                    'atr': 12.5
                }
            }
        }

        passes, reason = scanner._evaluate_conditions(conditions, market_state, '1000')

        print(f"  Condition check: {'PASS' if passes else 'FAIL'}")
        print(f"  Reason: {reason}")

        if not passes and "0.40 < 0.50" in reason:
            print("  [PASS] PASS: Live gate correctly blocks trade (ORB too small)")
            return True
        elif passes:
            print("  [FAIL] FAIL: Gate should have blocked trade")
            return False
        else:
            print("  [FAIL] FAIL: Unexpected gate behavior")
            return False
    else:
        print(f"  [FAIL] FAIL: Conditions not found for edge {edge_id}")
        return False


def test_full_lifecycle(conn):
    """Test 5: Full lifecycle flow"""
    print("\n=== Test 5: Full Lifecycle Flow ===")

    print("  Step 1: Discovery (What-If analysis)")
    engine = WhatIfEngine(conn)
    result = engine.analyze_conditions(
        instrument='MGC',
        orb_time='1000',
        direction='BOTH',
        rr=2.0,
        sl_mode='FULL',
        conditions={'orb_size_min': 0.6},  # Different condition
        date_start='2024-01-01',
        date_end='2025-12-31'
    )
    print(f"     Baseline: {result['baseline'].sample_size} trades, {result['baseline'].expected_r:.3f}R")
    print(f"     Conditional: {result['conditional'].sample_size} trades, {result['conditional'].expected_r:.3f}R")
    print(f"     Delta: {result['delta']['expected_r']:+.3f}R")

    print("  Step 2: Snapshot (save results)")
    manager = SnapshotManager(conn)
    snapshot_id = manager.save_snapshot(
        result=result,
        notes="Full lifecycle test",
        created_by="test_what_if_end_to_end.py"
    )
    print(f"     Snapshot ID: {snapshot_id}")

    print("  Step 3: Promotion (create candidate)")
    edge_id = manager.promote_snapshot_to_candidate(
        snapshot_id=snapshot_id,
        trigger_definition="ORB breakout (lifecycle test)",
        notes="Full lifecycle candidate"
    )
    print(f"     Edge ID: {edge_id}")

    print("  Step 4: Validation (check edge exists)")
    edge_row = conn.execute("""
        SELECT status FROM edge_registry WHERE edge_id = ?
    """, [edge_id]).fetchone()

    if edge_row and edge_row[0] == 'NEVER_TESTED':
        print(f"     Status: {edge_row[0]} [PASS]")
    else:
        print(f"     Status verification failed (expected NEVER_TESTED, got {edge_row[0] if edge_row else 'None'}) [FAIL]")
        return False

    print("  Step 5: Production readiness (live gate check)")
    scanner = LiveScanner(conn)
    conditions = scanner._load_promoted_conditions(edge_id)

    if conditions and 'orb_size_min' in conditions:
        print(f"     Live gate ready: min ORB size = {conditions['orb_size_min']} ATR [PASS]")
        print("  [PASS] PASS: Full lifecycle complete")
        return True
    else:
        print(f"     Live gate not configured [FAIL]")
        return False


def run_all_tests():
    """Run all end-to-end tests"""
    print("=" * 60)
    print("What-If Analyzer - End-to-End Test Suite")
    print("=" * 60)

    # Connect to database
    conn = duckdb.connect('data/db/gold.db')

    results = []

    # Test 1: Deterministic evaluation
    results.append(("Deterministic Evaluation", test_deterministic_evaluation(conn)))

    # Test 2: Snapshot roundtrip
    result, snapshot_id = test_snapshot_roundtrip(conn)
    results.append(("Snapshot Roundtrip", result))

    # Test 3: Snapshot promotion
    if result:  # Only run if Test 2 passed
        result, edge_id = test_snapshot_promotion(conn, snapshot_id)
        results.append(("Snapshot Promotion", result))

        # Test 4: Live gate enforcement
        if result:  # Only run if Test 3 passed
            results.append(("Live Gate Enforcement", test_live_gate_enforcement(conn, edge_id)))
    else:
        results.append(("Snapshot Promotion", False))
        results.append(("Live Gate Enforcement", False))

    # Test 5: Full lifecycle
    results.append(("Full Lifecycle", test_full_lifecycle(conn)))

    conn.close()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, passed in results:
        status = "[PASS] PASS" if passed else "[FAIL] FAIL"
        print(f"{test_name:30s} {status}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n*** ALL TESTS PASSED!")
        print("\nWhat-If Analyzer V1 is fully operational:")
        print("- Deterministic query engine [PASS]")
        print("- Snapshot persistence with exact reproduction [PASS]")
        print("- Promotion to validation candidates [PASS]")
        print("- Live trading condition gates [PASS]")
        print("- Full lifecycle integration [PASS]")
        return True
    else:
        print(f"\n[WARN] {total - passed} test(s) failed")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
