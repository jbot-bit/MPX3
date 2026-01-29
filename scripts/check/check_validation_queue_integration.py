#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check Validation Queue Integration

Verifies that validation_queue properly integrates with edge_registry.

Tests:
1. validation_queue table exists
2. Can insert test item into validation_queue
3. Can query PENDING items
4. Field mapping matches edge_registry requirements

Usage:
    python scripts/check/check_validation_queue_integration.py
"""

import sys
import os
import duckdb
import uuid
from pathlib import Path


def check_validation_queue_integration(db_path: str = "data/db/gold.db"):
    """Verify validation queue integration"""

    conn = duckdb.connect(db_path)

    print("="*80)
    print("VALIDATION QUEUE INTEGRATION CHECK")
    print("="*80)
    print(f"Database: {db_path}")
    print()

    # ========================================================================
    # Test 1: validation_queue Exists
    # ========================================================================
    print("Test 1: validation_queue Table Exists")
    print("-"*80)

    try:
        schema = conn.execute("DESCRIBE validation_queue").fetchall()
        col_names = [col[0] for col in schema]
        print(f"  [OK] validation_queue exists with {len(col_names)} columns")

        # Check required columns
        required_cols = ['queue_id', 'instrument', 'orb_time', 'rr_target', 'status', 'score_proxy', 'sample_size']
        missing = [col for col in required_cols if col not in col_names]

        if missing:
            print(f"  [FAIL] Missing columns: {missing}")
            conn.close()
            return False
        else:
            print(f"  [OK] All required columns present")

    except Exception as e:
        print(f"  [FAIL] validation_queue table check: {e}")
        conn.close()
        return False

    print()

    # ========================================================================
    # Test 2: Insert Test Item
    # ========================================================================
    print("Test 2: Insert Test Item into validation_queue")
    print("-"*80)

    try:
        test_queue_id = 999998
        conn.execute("""
            INSERT INTO validation_queue (
                queue_id, enqueued_at, source, instrument, setup_family,
                orb_time, rr_target, filters_json, score_proxy, sample_size, status, notes
            ) VALUES (
                ?, CURRENT_TIMESTAMP, 'AUTO_SEARCH', 'MGC', 'ORB_BASELINE',
                '0900', 1.5, '{}', 0.25, 50, 'PENDING', 'Test candidate'
            )
        """, [test_queue_id])

        print(f"  [OK] Test item inserted (queue_id={test_queue_id})")

    except Exception as e:
        print(f"  [FAIL] Insert test item: {e}")
        conn.close()
        return False

    print()

    # ========================================================================
    # Test 3: Query PENDING Items
    # ========================================================================
    print("Test 3: Query PENDING Items")
    print("-"*80)

    try:
        pending = conn.execute("""
            SELECT queue_id, instrument, orb_time, rr_target, score_proxy, status
            FROM validation_queue
            WHERE status = 'PENDING'
            ORDER BY enqueued_at DESC
        """).fetchall()

        if pending:
            print(f"  [OK] Found {len(pending)} PENDING item(s)")
            for item in pending[:3]:
                print(f"       {item[1]} {item[2]} RR={item[3]} ({item[4]:.3f}R) - {item[5]}")
        else:
            print(f"  [WARNING] No PENDING items (expected at least test item)")

    except Exception as e:
        print(f"  [FAIL] Query PENDING: {e}")
        conn.close()
        return False

    print()

    # ========================================================================
    # Test 4: Field Mapping to edge_registry
    # ========================================================================
    print("Test 4: Field Mapping to edge_registry")
    print("-"*80)

    try:
        # Get edge_registry schema
        edge_schema = conn.execute("DESCRIBE edge_registry").fetchall()
        edge_cols = [col[0] for col in edge_schema]

        # Check required fields exist
        required_edge_cols = ['edge_id', 'instrument', 'orb_time', 'rr', 'status', 'trigger_definition']
        missing_edge = [col for col in required_edge_cols if col not in edge_cols]

        if missing_edge:
            print(f"  [FAIL] edge_registry missing columns: {missing_edge}")
            conn.close()
            return False

        print(f"  [OK] edge_registry has all required columns")

        # Test mapping (simulate "Start Validation" button)
        test_edge_id = str(uuid.uuid4())
        trigger_def = "Test: Auto-discovered 0900 RR=1.5 (0.25R, 50N)"

        conn.execute("""
            INSERT INTO edge_registry (
                edge_id, created_at, status, instrument, orb_time,
                direction, rr, sl_mode, trigger_definition, created_by
            ) VALUES (
                ?, CURRENT_TIMESTAMP, 'IN_PROGRESS', 'MGC', '0900',
                'BOTH', 1.5, 'FULL', ?, 'AUTO_SEARCH'
            )
        """, [test_edge_id, trigger_def])

        # Verify insert
        result = conn.execute("""
            SELECT edge_id, instrument, orb_time, rr, status, created_by
            FROM edge_registry
            WHERE edge_id = ?
        """, [test_edge_id]).fetchone()

        if result and result[0] == test_edge_id:
            print(f"  [OK] Test mapping inserted successfully")
            print(f"       edge_id: {result[0][:16]}...")
            print(f"       instrument: {result[1]}, orb: {result[2]}, rr: {result[3]}")
            print(f"       status: {result[4]}, created_by: {result[5]}")
        else:
            print(f"  [FAIL] Test mapping failed")
            conn.close()
            return False

        # Clean up test data
        conn.execute("DELETE FROM edge_registry WHERE edge_id = ?", [test_edge_id])
        conn.execute("DELETE FROM validation_queue WHERE queue_id = ?", [test_queue_id])

        print(f"  [OK] Test data cleaned up")

    except Exception as e:
        print(f"  [FAIL] Field mapping test: {e}")
        conn.close()
        return False

    print()

    conn.close()

    # ========================================================================
    # Summary
    # ========================================================================
    print("="*80)
    print("SUCCESS: Validation queue integration verified!")
    print("="*80)
    print()
    print("Integration is ready. You can now:")
    print("  1. Run Auto Search (Research tab)")
    print("  2. Send candidate to Validation Queue")
    print("  3. Go to Validation tab")
    print("  4. See candidate in 'Validation Queue (Auto Search)' section")
    print("  5. Click 'Start Validation'")
    print("  6. Candidate moves to edge_registry (IN_PROGRESS)")
    print("  7. Continue validation in existing workflow")
    print()

    return True


def main():
    # Change to project root
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)

    print()
    success = check_validation_queue_integration()
    print()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
