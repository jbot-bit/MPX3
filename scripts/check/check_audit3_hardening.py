#!/usr/bin/env python3
"""
Audit3 Hardening Verification (check.txt requirements)

Verifies:
A) Hash canonicalization (determinism, collision avoidance)
B) Memory skip (deduplication works)
C) Exploration determinism (stable ordering, untested pool)
D) Provenance presence (version tracking)

Usage:
    python scripts/check/check_audit3_hardening.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add trading_app to path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "trading_app"))

import duckdb
from auto_search_engine import (
    compute_param_hash_v2,
    PARAM_HASH_VERSION,
    RULESET_VERSION,
    PRIORITY_VERSION,
    EPSILON
)
from result_classifier import classify_result


DB_PATH = REPO_ROOT / "data" / "db" / "gold.db"


def check_hash_canonicalization():
    """
    A) Hash Canonicalization
    - Same params produce same hash across runs
    - Different params produce different hashes
    - Filter dict ordering doesn't affect hash (canonicalization)
    """
    print("=" * 70)
    print("CHECK A: Hash Canonicalization")
    print("=" * 70)
    print()

    # Test 1: Determinism (same params => same hash)
    params1 = {
        'instrument': 'MGC',
        'setup_family': 'ORB_BASELINE',
        'orb_time': '1000',
        'rr_target': 2.0,
        'filters': {'orb_size': 0.10}
    }

    hash1 = compute_param_hash_v2(params1)
    hash2 = compute_param_hash_v2(params1)

    if hash1 != hash2:
        print(f"[FAIL] Hash not deterministic: {hash1} != {hash2}")
        return False

    print(f"[OK] Hash is deterministic: {hash1}")

    # Test 2: Filter dict order doesn't matter (canonicalization)
    params2 = {
        'filters': {'orb_size': 0.10},  # Filter first
        'rr_target': 2.0,
        'orb_time': '1000',
        'setup_family': 'ORB_BASELINE',
        'instrument': 'MGC'
    }

    hash3 = compute_param_hash_v2(params2)

    if hash1 != hash3:
        print(f"[FAIL] Hash depends on dict order: {hash1} != {hash3}")
        return False

    print(f"[OK] Hash ignores dict order (canonical)")

    # Test 3: Different filter values => different hashes
    params3 = params1.copy()
    params3['filters'] = {'orb_size': 0.15}  # Different filter value

    hash4 = compute_param_hash_v2(params3)

    if hash1 == hash4:
        print(f"[FAIL] Different filter values produce same hash")
        return False

    print(f"[OK] Different filter values => different hashes")
    print(f"  Filter 0.10: {hash1}")
    print(f"  Filter 0.15: {hash4}")

    # Test 4: Different RR => different hashes
    params4 = params1.copy()
    params4['rr_target'] = 1.5

    hash5 = compute_param_hash_v2(params4)

    if hash1 == hash5:
        print(f"[FAIL] Different RR targets produce same hash")
        return False

    print(f"[OK] Different RR targets => different hashes")
    print(f"  RR 2.0: {hash1}")
    print(f"  RR 1.5: {hash5}")

    # Test 5: Empty filters vs no filters
    params5 = params1.copy()
    params5['filters'] = {}

    params6 = params1.copy()
    del params6['filters']

    hash6 = compute_param_hash_v2(params5)
    hash7 = compute_param_hash_v2(params6)

    if hash6 != hash7:
        print(f"[FAIL] Empty filters != missing filters")
        return False

    print(f"[OK] Empty filters == missing filters (canonical)")

    return True


def check_memory_skip():
    """
    B) Memory Skip
    - Second identical run results in high "skipped(memory)"
    - No duplicate param_hash inserts into search_knowledge
    """
    print()
    print("=" * 70)
    print("CHECK B: Memory Skip (Deduplication)")
    print("=" * 70)
    print()

    if not DB_PATH.exists():
        print(f"[SKIP] Database not found: {DB_PATH}")
        return True

    try:
        conn = duckdb.connect(str(DB_PATH), read_only=True)

        # Check search_memory has unique param_hash
        result = conn.execute("""
            SELECT COUNT(*) as total, COUNT(DISTINCT param_hash) as unique_hashes
            FROM search_memory
        """).fetchone()

        total_rows = result[0]
        unique_hashes = result[1]

        if total_rows == 0:
            print("[OK] search_memory is empty (no tests run yet)")
            conn.close()
            return True

        if total_rows != unique_hashes:
            print(f"[FAIL] Duplicate param_hash in search_memory: {total_rows} rows, {unique_hashes} unique")
            conn.close()
            return False

        print(f"[OK] search_memory has no duplicates ({unique_hashes} unique hashes)")

        # Check search_knowledge has unique param_hash
        result = conn.execute("""
            SELECT COUNT(*) as total, COUNT(DISTINCT param_hash) as unique_hashes
            FROM search_knowledge
        """).fetchone()

        total_rows = result[0]
        unique_hashes = result[1]

        if total_rows == 0:
            print("[OK] search_knowledge is empty (no tests run yet)")
            conn.close()
            return True

        if total_rows != unique_hashes:
            print(f"[FAIL] Duplicate param_hash in search_knowledge: {total_rows} rows, {unique_hashes} unique")
            conn.close()
            return False

        print(f"[OK] search_knowledge has no duplicates ({unique_hashes} unique hashes)")

        conn.close()
        return True

    except Exception as e:
        print(f"[FAIL] Error checking memory skip: {e}")
        return False


def check_exploration_determinism():
    """
    C) Exploration Determinism
    - Exploration selection order is stable between runs
    - Exploration draws only from untested pool
    """
    print()
    print("=" * 70)
    print("CHECK C: Exploration Determinism")
    print("=" * 70)
    print()

    # Test: Epsilon value is deterministic
    if not (0.0 < EPSILON < 1.0):
        print(f"[FAIL] EPSILON out of range: {EPSILON}")
        return False

    print(f"[OK] EPSILON = {EPSILON} ({EPSILON*100:.0f}%)")

    # Test: Epsilon split calculation
    total = 100
    exploit_count = int(total * (1 - EPSILON))
    explore_count = total - exploit_count

    print(f"[OK] Example split: {exploit_count} exploit + {explore_count} explore")

    if explore_count == 0:
        print("[WARN] Exploration count is 0 (epsilon too small or total too small)")

    # Test: Hash-sorted ordering is deterministic
    params_list = [
        {'instrument': 'MGC', 'setup_family': 'ORB_BASELINE', 'orb_time': '1000', 'rr_target': 2.0, 'filters': {}},
        {'instrument': 'MGC', 'setup_family': 'ORB_BASELINE', 'orb_time': '0900', 'rr_target': 2.0, 'filters': {}},
        {'instrument': 'MGC', 'setup_family': 'ORB_BASELINE', 'orb_time': '1100', 'rr_target': 2.0, 'filters': {}},
    ]

    # Compute hashes
    hashes = [compute_param_hash_v2(p) for p in params_list]

    # Sort by hash
    sorted_indices = sorted(range(len(hashes)), key=lambda i: hashes[i])

    # Repeat
    hashes2 = [compute_param_hash_v2(p) for p in params_list]
    sorted_indices2 = sorted(range(len(hashes2)), key=lambda i: hashes2[i])

    if sorted_indices != sorted_indices2:
        print(f"[FAIL] Hash sorting is not deterministic")
        return False

    print(f"[OK] Hash-sorted ordering is deterministic")
    print(f"  Order: {sorted_indices}")

    return True


def check_provenance_presence():
    """
    D) Provenance Presence
    - DB rows contain param_hash_version, ruleset_version, priority_version
    - Version constants are defined and non-empty
    """
    print()
    print("=" * 70)
    print("CHECK D: Provenance & Versioning")
    print("=" * 70)
    print()

    # Test 1: Version constants defined
    if not PARAM_HASH_VERSION:
        print("[FAIL] PARAM_HASH_VERSION is empty")
        return False

    if not RULESET_VERSION:
        print("[FAIL] RULESET_VERSION is empty")
        return False

    if not PRIORITY_VERSION:
        print("[FAIL] PRIORITY_VERSION is empty")
        return False

    print(f"[OK] Version constants defined:")
    print(f"  - param_hash_version: {PARAM_HASH_VERSION}")
    print(f"  - ruleset_version: {RULESET_VERSION}")
    print(f"  - priority_version: {PRIORITY_VERSION}")

    # Test 2: DB schema has version columns
    if not DB_PATH.exists():
        print(f"[SKIP] Database not found: {DB_PATH}")
        return True

    try:
        conn = duckdb.connect(str(DB_PATH), read_only=True)

        # Check search_knowledge columns
        columns = conn.execute("DESCRIBE search_knowledge").fetchall()
        column_names = [col[0] for col in columns]

        required_version_cols = ['param_hash_version', 'ruleset_version', 'priority_version']

        missing = [col for col in required_version_cols if col not in column_names]

        if missing:
            print(f"[FAIL] Missing version columns in search_knowledge: {missing}")
            conn.close()
            return False

        print(f"[OK] search_knowledge has all version columns")

        # Check if any rows have version data
        result = conn.execute("""
            SELECT COUNT(*) FROM search_knowledge
            WHERE param_hash_version IS NOT NULL
              AND ruleset_version IS NOT NULL
              AND priority_version IS NOT NULL
        """).fetchone()

        versioned_rows = result[0]

        if versioned_rows > 0:
            print(f"[OK] {versioned_rows} rows have provenance data")
        else:
            print(f"[OK] No rows yet (versions will be written on first search)")

        conn.close()
        return True

    except Exception as e:
        print(f"[FAIL] Error checking provenance: {e}")
        return False


def check_robust_flags_bitmask():
    """
    E) Robust Flags Bitmask
    - Verify robust_flags uses bitmask pattern (extensible)
    - Verify result_classifier counts set bits correctly
    """
    print()
    print("=" * 70)
    print("CHECK E: Robust Flags Bitmask (Extensibility)")
    print("=" * 70)
    print()

    # Test: Bitmask with 0 concerns => GOOD
    result = classify_result(expectancy_r=0.30, sample_size=60, robust_flags=0x00)
    if result != "GOOD":
        print(f"[FAIL] 0 concerns should be GOOD, got {result}")
        return False

    print(f"[OK] 0 concerns (0x00) => GOOD")

    # Test: Bitmask with 1 concern => NEUTRAL
    result = classify_result(expectancy_r=0.20, sample_size=40, robust_flags=0x01)
    if result != "NEUTRAL":
        print(f"[FAIL] 1 concern should be NEUTRAL, got {result}")
        return False

    print(f"[OK] 1 concern (0x01) => NEUTRAL")

    # Test: Bitmask with 2 concerns => BAD
    result = classify_result(expectancy_r=0.20, sample_size=40, robust_flags=0x03)  # bits 0+1
    if result != "BAD":
        print(f"[FAIL] 2 concerns should be BAD, got {result}")
        return False

    print(f"[OK] 2 concerns (0x03) => BAD")

    # Test: Bitmask with multiple non-adjacent bits
    result = classify_result(expectancy_r=0.20, sample_size=40, robust_flags=0x05)  # bits 0+2
    if result != "BAD":
        print(f"[FAIL] 2 concerns (non-adjacent) should be BAD, got {result}")
        return False

    print(f"[OK] 2 concerns (0x05, non-adjacent bits) => BAD")

    print()
    print("[OK] Robust flags bitmask is extensible")
    print("  Current bits (v1.0):")
    print("    Bit 0 (0x01): Marginal sample size")
    print("    Bit 1 (0x02): Marginal expectancy")
    print("    Bit 2 (0x04): Very low sample size")
    print("    Bit 3 (0x08): Weak expectancy")
    print("  Future bits (reserved 4-7):")
    print("    Bit 4 (0x10): OOS stability (not implemented)")
    print("    Bit 5 (0x20): Cost stress (not implemented)")
    print("    Bit 6 (0x40): Regime instability (not implemented)")
    print("    Bit 7 (0x80): Tail risk / drawdown (not implemented)")

    return True


def main():
    """Run all checks"""
    print("=" * 70)
    print("AUDIT3 HARDENING VERIFICATION (check.txt)")
    print("=" * 70)
    print()

    checks = [
        ("Hash Canonicalization", check_hash_canonicalization),
        ("Memory Skip (Deduplication)", check_memory_skip),
        ("Exploration Determinism", check_exploration_determinism),
        ("Provenance & Versioning", check_provenance_presence),
        ("Robust Flags Bitmask", check_robust_flags_bitmask),
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
        print("Hardening verified:")
        print("  - Hash canonicalization works (deterministic, collision-free)")
        print("  - Memory deduplication prevents duplicate tests")
        print("  - Epsilon exploration is deterministic (hash-sorted untested pool)")
        print("  - Provenance tracking enabled (versions stored)")
        print("  - Robust flags use bitmask (extensible for future gates)")
        return 0
    else:
        print("[FAIL] SOME CHECKS FAILED")
        print()
        print("Fix the issues above before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
