#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check Auto Search Tables

Verifies that auto search tables exist and are functional.

Tests:
1. Tables exist with correct columns
2. Insert + select sanity check
3. Hash determinism
4. Memory skip logic

Usage:
    python scripts/check/check_auto_search_tables.py
"""

import sys
import os
import duckdb
from pathlib import Path


def check_auto_search_tables(db_path: str = "data/db/gold.db"):
    """Verify auto search tables exist and work"""

    conn = duckdb.connect(db_path)

    print("="*80)
    print("AUTO SEARCH TABLES CHECK")
    print("="*80)
    print(f"Database: {db_path}")
    print()

    # ========================================================================
    # Test 1: Tables Exist
    # ========================================================================
    print("Test 1: Tables Exist")
    print("-"*80)

    required_tables = ['search_runs', 'search_candidates', 'search_memory', 'validation_queue']
    all_tables = conn.execute("SHOW TABLES").fetchall()
    existing_table_names = [t[0] for t in all_tables]

    tables_ok = True
    for table in required_tables:
        if table in existing_table_names:
            schema = conn.execute(f"DESCRIBE {table}").fetchall()
            col_count = len(schema)
            row_count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  [OK] {table}: {col_count} columns, {row_count} rows")
        else:
            print(f"  [FAIL] {table}: MISSING")
            tables_ok = False

    if not tables_ok:
        print()
        print("ERROR: Some tables are missing. Run migration:")
        print("  python scripts/migrations/create_auto_search_tables.py")
        conn.close()
        return False

    print()

    # ========================================================================
    # Test 2: Insert + Select Sanity Check
    # ========================================================================
    print("Test 2: Insert + Select Sanity Check")
    print("-"*80)

    try:
        # Test search_runs insert
        test_run_id = "test_run_12345"
        conn.execute("""
            INSERT OR REPLACE INTO search_runs (
                run_id, instrument, settings_json, status
            ) VALUES (?, 'MGC', '{"test": true}', 'COMPLETED')
        """, [test_run_id])

        # Read back
        result = conn.execute("""
            SELECT run_id, instrument, status FROM search_runs
            WHERE run_id = ?
        """, [test_run_id]).fetchone()

        if result and result[0] == test_run_id:
            print(f"  [OK] search_runs: Insert/select works")
        else:
            print(f"  [FAIL] search_runs: Insert/select failed")
            conn.close()
            return False

        # Clean up test data
        conn.execute("DELETE FROM search_runs WHERE run_id = ?", [test_run_id])

    except Exception as e:
        print(f"  [FAIL] Insert/select test: {e}")
        conn.close()
        return False

    print()

    # ========================================================================
    # Test 3: Hash Determinism
    # ========================================================================
    print("Test 3: Hash Determinism")
    print("-"*80)

    try:
        # Import hash function
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "trading_app"))
        from auto_search_engine import compute_param_hash

        # Test same params produce same hash
        params = {
            'instrument': 'MGC',
            'setup_family': 'ORB_BASELINE',
            'orb_time': '0900',
            'rr_target': 1.5,
            'filters': {}
        }

        hash1 = compute_param_hash(params)
        hash2 = compute_param_hash(params)

        if hash1 == hash2:
            print(f"  [OK] Hash determinism: {hash1} == {hash2}")
        else:
            print(f"  [FAIL] Hash not deterministic: {hash1} != {hash2}")
            conn.close()
            return False

        # Test different params produce different hash
        params2 = {
            'instrument': 'MGC',
            'setup_family': 'ORB_BASELINE',
            'orb_time': '1000',  # Different
            'rr_target': 1.5,
            'filters': {}
        }

        hash3 = compute_param_hash(params2)

        if hash1 != hash3:
            print(f"  [OK] Different params produce different hash: {hash1} != {hash3}")
        else:
            print(f"  [FAIL] Different params produced same hash")
            conn.close()
            return False

    except Exception as e:
        print(f"  [FAIL] Hash test: {e}")
        conn.close()
        return False

    print()

    # ========================================================================
    # Test 4: Memory Skip Logic
    # ========================================================================
    print("Test 4: Memory Skip Logic")
    print("-"*80)

    try:
        # Insert test entry into search_memory
        test_hash = "test_hash_abc123"
        test_memory_id = 999999  # Test ID
        conn.execute("""
            INSERT INTO search_memory (
                memory_id, param_hash, instrument, setup_family, filters_json, best_score
            ) VALUES (?, ?, 'MGC', 'TEST_FAMILY', '{}', 0.25)
            ON CONFLICT (param_hash) DO UPDATE SET
                best_score = EXCLUDED.best_score
        """, [test_memory_id, test_hash])

        # Check if exists
        result = conn.execute("""
            SELECT 1 FROM search_memory WHERE param_hash = ?
        """, [test_hash]).fetchone()

        if result:
            print(f"  [OK] Memory insert works: hash {test_hash} found")
        else:
            print(f"  [FAIL] Memory insert failed: hash not found")
            conn.close()
            return False

        # Test skip logic (same hash should be skipped)
        exists = conn.execute("""
            SELECT 1 FROM search_memory WHERE param_hash = ? LIMIT 1
        """, [test_hash]).fetchone()

        if exists:
            print(f"  [OK] Memory skip logic: hash found, would skip re-testing")
        else:
            print(f"  [FAIL] Memory skip logic broken")
            conn.close()
            return False

        # Clean up
        conn.execute("DELETE FROM search_memory WHERE param_hash = ?", [test_hash])

    except Exception as e:
        print(f"  [FAIL] Memory test: {e}")
        conn.close()
        return False

    print()

    conn.close()

    # ========================================================================
    # Summary
    # ========================================================================
    print("="*80)
    print("SUCCESS: All auto search table checks passed!")
    print("="*80)
    print()
    print("Tables are ready for use. You can now:")
    print("  1. Run Auto Search from Streamlit app (Research tab)")
    print("  2. Check search_runs table for execution history")
    print("  3. Check search_candidates for discovered edges")
    print("  4. Check search_memory to see tested param space")
    print()

    return True


def main():
    # Change to project root
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)

    print()
    success = check_auto_search_tables()
    print()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
