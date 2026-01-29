"""
Test app_canonical.py startup and runtime

This script simulates the app startup process and checks for issues.
"""

import sys
import os
from pathlib import Path

# Force local database
os.environ['FORCE_LOCAL_DB'] = '1'

# Add paths
current_dir = Path(__file__).parent / "trading_app"
repo_root = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(repo_root))

def test_imports():
    """Test all imports used in app_canonical.py"""
    print("=" * 60)
    print("TEST 1: Imports")
    print("=" * 60)

    try:
        import streamlit as st
        import duckdb
        from pathlib import Path
        from datetime import datetime
        import logging

        from cloud_mode import get_database_path
        from edge_utils import (
            create_candidate,
            get_all_candidates,
            get_candidate_by_id,
            update_candidate_status,
            get_registry_stats,
            create_experiment_run,
            complete_experiment_run,
            get_experiment_runs,
            check_prior_validation,
            run_validation_stub,
            promote_to_production,
            retire_from_production,
            find_similar_edges
        )
        from drift_monitor import DriftMonitor, get_system_health_summary
        from live_scanner import LiveScanner
        from terminal_theme import TERMINAL_CSS
        from terminal_components import (
            render_terminal_header,
            render_metric_card,
            render_status_indicator,
            render_price_display,
            render_terminal_panel
        )
        from error_logger import initialize_error_log, log_error

        print("[PASS] All imports successful")
        return True
    except Exception as e:
        print(f"[FAIL] Import error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_connection():
    """Test database connection and table existence"""
    print("\n" + "=" * 60)
    print("TEST 2: Database Connection")
    print("=" * 60)

    try:
        from cloud_mode import get_database_path
        import duckdb

        db_path = get_database_path()
        print(f"Database path: {db_path}")

        if not os.path.exists(db_path):
            print(f"[WARNING] Database file not found: {db_path}")
            print("  Run: python init_app_canonical_db.py")
            return False

        conn = duckdb.connect(db_path, read_only=True)
        print("[OK] Connection successful")

        # Check tables
        required_tables = ['edge_registry', 'experiment_run', 'validated_setups', 'validated_trades']
        tables = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main'").fetchall()
        table_names = [t[0] for t in tables]

        all_present = True
        for table in required_tables:
            if table in table_names:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                print(f"[OK] {table:25s} ({count} rows)")
            else:
                print(f"[FAIL] {table:25s} MISSING")
                all_present = False

        conn.close()

        if not all_present:
            print("\n[ACTION REQUIRED] Run: python init_app_canonical_db.py")
            return False

        print("[PASS] All required tables present")
        return True
    except Exception as e:
        print(f"[FAIL] Database error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_app_state_init():
    """Test AppState class initialization"""
    print("\n" + "=" * 60)
    print("TEST 3: AppState Initialization")
    print("=" * 60)

    try:
        from cloud_mode import get_database_path
        import duckdb

        db_path = get_database_path()

        if not os.path.exists(db_path):
            print("[SKIP] Database not found, skipping AppState test")
            return True

        # Simulate AppState initialization
        db_connection = duckdb.connect(db_path)
        print("[OK] Database connection created")

        # Test basic query
        result = db_connection.execute("SELECT 1").fetchone()
        if result and result[0] == 1:
            print("[OK] Test query successful")
        else:
            print("[FAIL] Test query failed")
            return False

        db_connection.close()
        print("[PASS] AppState initialization would succeed")
        return True
    except Exception as e:
        print(f"[FAIL] AppState error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_query_validated_setups():
    """Test the main query used in Production tab"""
    print("\n" + "=" * 60)
    print("TEST 4: Production Tab Query")
    print("=" * 60)

    try:
        from cloud_mode import get_database_path
        import duckdb

        db_path = get_database_path()

        if not os.path.exists(db_path):
            print("[SKIP] Database not found, skipping query test")
            return True

        conn = duckdb.connect(db_path, read_only=True)

        # Test the main query from app_canonical.py
        query = """
        SELECT
            vs.id,
            vs.instrument,
            vs.orb_time,
            vs.rr,
            vs.sl_mode,
            vs.orb_size_filter,
            vs.win_rate,
            vs.expected_r,
            vs.real_expected_r,
            vs.sample_size,
            vs.notes,
            COUNT(vt.date_local) as trade_count,
            SUM(CASE WHEN vt.outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN vt.outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
            AVG(vt.realized_rr) as avg_realized_rr,
            SUM(CASE WHEN vt.realized_rr >= 0.15 THEN 1 ELSE 0 END) as friction_pass_count
        FROM validated_setups vs
        LEFT JOIN validated_trades vt ON vs.id = vt.setup_id
        WHERE vs.instrument = 'MGC'
        GROUP BY vs.id, vs.instrument, vs.orb_time, vs.rr, vs.sl_mode,
                 vs.orb_size_filter, vs.win_rate, vs.expected_r, vs.real_expected_r,
                 vs.sample_size, vs.notes
        ORDER BY vs.orb_time, vs.expected_r DESC
        """

        result = conn.execute(query).fetchdf()
        print(f"[OK] Query executed successfully ({len(result)} rows)")

        if len(result) == 0:
            print("[INFO] No validated_setups found for MGC (expected for empty database)")
        else:
            print(f"[INFO] Found {len(result)} validated setups")
            for _, row in result.head(3).iterrows():
                print(f"  - {row['orb_time']} RR={row['rr']:.1f} ({row['sl_mode']})")

        conn.close()
        print("[PASS] Production tab query would succeed")
        return True
    except Exception as e:
        print(f"[FAIL] Query error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_edge_utils_functions():
    """Test edge_utils functions with database"""
    print("\n" + "=" * 60)
    print("TEST 5: edge_utils Functions")
    print("=" * 60)

    try:
        from cloud_mode import get_database_path
        from edge_utils import get_all_candidates, get_registry_stats
        import duckdb

        db_path = get_database_path()

        if not os.path.exists(db_path):
            print("[SKIP] Database not found, skipping edge_utils test")
            return True

        conn = duckdb.connect(db_path, read_only=True)

        # Test get_all_candidates
        candidates = get_all_candidates(conn)
        print(f"[OK] get_all_candidates() returned {len(candidates)} candidates")

        # Test get_registry_stats
        stats = get_registry_stats(conn)
        print(f"[OK] get_registry_stats() returned {len(stats)} stats")

        conn.close()
        print("[PASS] edge_utils functions work correctly")
        return True
    except Exception as e:
        print(f"[FAIL] edge_utils error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n")
    print("=" * 60)
    print("  APP_CANONICAL.PY STARTUP TEST SUITE".center(60))
    print("=" * 60)
    print()

    tests = [
        ("Imports", test_imports),
        ("Database Connection", test_database_connection),
        ("AppState Initialization", test_app_state_init),
        ("Production Tab Query", test_query_validated_setups),
        ("edge_utils Functions", test_edge_utils_functions),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n[EXCEPTION] {test_name} raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")

    print()
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print()
        print("[SUCCESS] All tests passed!")
        print()
        print("You can now run:")
        print("  streamlit run trading_app/app_canonical.py")
        print()
        return 0
    else:
        print()
        print("[FAILED] Some tests failed")
        print()
        print("Action items:")
        for test_name, result in results:
            if not result:
                if "Database" in test_name:
                    print("  - Run: python init_app_canonical_db.py")
                    break
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
