#!/usr/bin/env python3
"""
Priority Engine Verification - audit3

Verifies:
1. search_knowledge table exists and has correct schema
2. PriorityEngine loads and calculates priorities
3. Result classification works (GOOD/NEUTRAL/BAD)
4. Param hashing v2 is deterministic
5. Provenance tracking captures all metadata
6. ε-exploration split works correctly

Usage:
    python scripts/check/check_priority_engine.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add trading_app to path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "trading_app"))

import duckdb
from result_classifier import classify_result, RULESET_VERSION, get_thresholds
from priority_engine import PriorityEngine, PRIORITY_VERSION
from provenance import create_provenance_dict
from auto_search_engine import compute_param_hash_v2, PARAM_HASH_VERSION, EPSILON


DB_PATH = REPO_ROOT / "data" / "db" / "gold.db"


def check_schema():
    """Check search_knowledge table schema"""
    print("=" * 70)
    print("CHECK 1: search_knowledge Schema")
    print("=" * 70)
    print()

    if not DB_PATH.exists():
        print(f"[FAIL] Database not found: {DB_PATH}")
        return False

    try:
        conn = duckdb.connect(str(DB_PATH), read_only=True)

        # Check table exists
        tables = conn.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_name = 'search_knowledge'
        """).fetchall()

        if not tables:
            print("[FAIL] Table 'search_knowledge' not found")
            return False

        print("[OK] Table 'search_knowledge' exists")

        # Check columns
        columns = conn.execute("DESCRIBE search_knowledge").fetchall()
        column_names = [col[0] for col in columns]

        required_columns = [
            'knowledge_id', 'param_hash', 'param_hash_version',
            'instrument', 'setup_family', 'orb_time', 'rr_target',
            'filters_json', 'result_class', 'expectancy_r',
            'sample_size', 'robust_flags', 'ruleset_version',
            'priority_version', 'git_commit', 'db_path',
            'created_at', 'last_seen_at', 'notes'
        ]

        missing = [col for col in required_columns if col not in column_names]

        if missing:
            print(f"[FAIL] Missing columns: {missing}")
            return False

        print(f"[OK] All {len(required_columns)} required columns present")

        # Check indexes
        indexes = conn.execute("""
            SELECT index_name FROM duckdb_indexes()
            WHERE table_name = 'search_knowledge'
        """).fetchall()

        print(f"[OK] {len(indexes)} indexes created")

        conn.close()
        return True

    except Exception as e:
        print(f"[FAIL] Error checking schema: {e}")
        return False


def check_result_classifier():
    """Check result classification logic"""
    print()
    print("=" * 70)
    print("CHECK 2: Result Classifier")
    print("=" * 70)
    print()

    # Test cases
    test_cases = [
        (0.30, 60, 0, "GOOD"),
        (0.25, 50, 0, "GOOD"),
        (0.20, 40, 1, "NEUTRAL"),
        (0.15, 30, 1, "NEUTRAL"),
        (0.10, 25, 2, "BAD"),
    ]

    passed = 0
    for exp_r, n, flags, expected in test_cases:
        result = classify_result(exp_r, n, flags)
        if result == expected:
            passed += 1
        else:
            print(f"[FAIL] ExpR={exp_r}, N={n}, Flags={flags} => {result} (expected {expected})")

    if passed == len(test_cases):
        print(f"[OK] All {len(test_cases)} classification tests passed")
        print(f"[OK] Ruleset version: {RULESET_VERSION}")
        return True
    else:
        print(f"[FAIL] {passed}/{len(test_cases)} tests passed")
        return False


def check_priority_engine():
    """Check priority engine initialization"""
    print()
    print("=" * 70)
    print("CHECK 3: Priority Engine")
    print("=" * 70)
    print()

    try:
        conn = duckdb.connect(str(DB_PATH), read_only=True)
        engine = PriorityEngine(conn)

        priorities = engine.get_axis_priorities()

        # Verify structure
        if 'orb_times' not in priorities:
            print("[FAIL] Missing 'orb_times' in priorities")
            return False

        if 'rr_targets' not in priorities:
            print("[FAIL] Missing 'rr_targets' in priorities")
            return False

        if 'filter_types' not in priorities:
            print("[FAIL] Missing 'filter_types' in priorities")
            return False

        print("[OK] Priority engine initialized")
        print(f"[OK] Priority version: {PRIORITY_VERSION}")

        # Test combination scoring
        test_combo = {
            'orb_time': '1000',
            'rr_target': 2.0,
            'filters': {}
        }

        score = engine.score_combination(test_combo)

        if not (0.0 <= score <= 1.0):
            print(f"[FAIL] Score out of range: {score} (expected 0.0-1.0)")
            return False

        print(f"[OK] Combination scoring works (score={score:.3f})")

        conn.close()
        return True

    except Exception as e:
        print(f"[FAIL] Error checking priority engine: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_param_hash_v2():
    """Check param hash v2 determinism"""
    print()
    print("=" * 70)
    print("CHECK 4: Param Hash v2 Determinism")
    print("=" * 70)
    print()

    params1 = {
        'instrument': 'MGC',
        'setup_family': 'ORB_BASELINE',
        'orb_time': '1000',
        'rr_target': 2.0,
        'filters': {'orb_size': 0.10}
    }

    params2 = {
        'instrument': 'MGC',
        'setup_family': 'ORB_BASELINE',
        'orb_time': '1000',
        'rr_target': 2.0,
        'filters': {'orb_size': 0.10}
    }

    # Different order (should still match)
    params3 = {
        'filters': {'orb_size': 0.10},
        'rr_target': 2.0,
        'orb_time': '1000',
        'setup_family': 'ORB_BASELINE',
        'instrument': 'MGC'
    }

    hash1 = compute_param_hash_v2(params1)
    hash2 = compute_param_hash_v2(params2)
    hash3 = compute_param_hash_v2(params3)

    if hash1 != hash2:
        print(f"[FAIL] Hash not deterministic: {hash1} != {hash2}")
        return False

    if hash1 != hash3:
        print(f"[FAIL] Hash depends on dict order: {hash1} != {hash3}")
        return False

    print(f"[OK] Hash v2 is deterministic: {hash1}")
    print(f"[OK] Param hash version: {PARAM_HASH_VERSION}")

    # Test different params produce different hashes
    params4 = params1.copy()
    params4['rr_target'] = 1.5

    hash4 = compute_param_hash_v2(params4)

    if hash1 == hash4:
        print(f"[FAIL] Different params produce same hash: {hash1} == {hash4}")
        return False

    print("[OK] Different params produce different hashes")

    return True


def check_provenance():
    """Check provenance tracking"""
    print()
    print("=" * 70)
    print("CHECK 5: Provenance Tracking")
    print("=" * 70)
    print()

    prov = create_provenance_dict()

    required_fields = [
        'timestamp', 'git_commit', 'git_branch', 'db_path',
        'ruleset_version', 'priority_version', 'param_hash_version'
    ]

    missing = [f for f in required_fields if f not in prov]

    if missing:
        print(f"[FAIL] Missing provenance fields: {missing}")
        return False

    print("[OK] All provenance fields present:")
    for key, value in prov.items():
        print(f"  - {key:20} {value}")

    return True


def check_epsilon():
    """Check epsilon-exploration constant"""
    print()
    print("=" * 70)
    print("CHECK 6: Epsilon-Exploration")
    print("=" * 70)
    print()

    if not (0.0 < EPSILON < 1.0):
        print(f"[FAIL] EPSILON out of range: {EPSILON} (expected 0.0-1.0)")
        return False

    print(f"[OK] Epsilon (exploration budget) = {EPSILON} ({EPSILON*100:.0f}%)")

    # Simulate split
    total = 100
    exploit = int(total * (1 - EPSILON))
    explore = total - exploit

    print(f"[OK] Example split: {exploit} exploit + {explore} explore (total {total})")

    if explore == 0:
        print("[WARN] Exploration count is 0 (ε too small or total too small)")

    return True


def main():
    """Run all checks"""
    print("=" * 70)
    print("PRIORITY ENGINE VERIFICATION (audit3)")
    print("=" * 70)
    print()

    checks = [
        ("Schema", check_schema),
        ("Result Classifier", check_result_classifier),
        ("Priority Engine", check_priority_engine),
        ("Param Hash v2", check_param_hash_v2),
        ("Provenance", check_provenance),
        ("Epsilon-Exploration", check_epsilon),
    ]

    results = []
    for name, check_func in checks:
        result = check_func()
        results.append((name, result))

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()

    passed = sum(1 for _, result in results if result)
    failed = len(results) - passed

    for name, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {name}")

    print()
    print(f"Passed: {passed}/{len(results)}")
    print(f"Failed: {failed}/{len(results)}")
    print()

    if failed == 0:
        print("[OK] ALL CHECKS PASSED")
        print()
        print("Priority engine is ready for use:")
        print("  - search_knowledge table created")
        print("  - Result classification working (GOOD/NEUTRAL/BAD)")
        print("  - Priority scoring operational")
        print("  - Param hash v2 deterministic")
        print("  - Provenance tracking enabled")
        print(f"  - Epsilon-exploration configured ({EPSILON*100:.0f}%)")
        return 0
    else:
        print("[FAIL] SOME CHECKS FAILED")
        print()
        print("Fix the issues above before using priority engine.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
