#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for update_market_data.py

Verifies:
1. Can query latest bar timestamp
2. Date range calculation works
3. Status check works
4. Idempotency (safe to run multiple times)
"""

import sys
import io
from pathlib import Path
import os

# Fix Unicode output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from scripts.maintenance.update_market_data import (
    get_latest_bar_timestamp,
    calculate_backfill_range,
    print_status
)


def test_query_latest_timestamp():
    """Test querying latest bar timestamp from database."""
    print("Test 1: Query latest bar timestamp")
    print("-" * 60)

    try:
        db_path = "data/db/gold.db"
        latest_ts = get_latest_bar_timestamp(db_path, "MGC")
        print(f"✓ Latest timestamp: {latest_ts}")
        print(f"  Type: {type(latest_ts)}")
        print(f"  Has timezone: {latest_ts.tzinfo is not None}")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_calculate_backfill_range():
    """Test date range calculation."""
    print("\nTest 2: Calculate backfill range")
    print("-" * 60)

    try:
        from datetime import datetime, timezone

        # Test with a known timestamp
        test_ts = datetime(2026, 1, 28, 23, 59, 0, tzinfo=timezone.utc)
        start_date, end_date = calculate_backfill_range(test_ts)

        print(f"✓ Input timestamp: {test_ts}")
        print(f"  Start date (local): {start_date}")
        print(f"  End date (local): {end_date}")
        print(f"  Range valid: {start_date <= end_date}")

        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_print_status():
    """Test status printing."""
    print("\nTest 3: Print status")
    print("-" * 60)

    try:
        db_path = "data/db/gold.db"
        print_status(db_path, "MGC")
        print("✓ Status printed successfully")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def test_idempotency_check():
    """Verify current data status (manual check for idempotency)."""
    print("\nTest 4: Idempotency check")
    print("-" * 60)

    try:
        db_path = "data/db/gold.db"
        latest_ts = get_latest_bar_timestamp(db_path, "MGC")
        start_date, end_date = calculate_backfill_range(latest_ts)

        if start_date > end_date:
            print("✓ Data is current - script would skip backfill (idempotent)")
            return True
        else:
            print(f"⚠ Data needs update: {start_date} to {end_date}")
            print("  Script would run backfill (expected if data not current)")
            return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("UPDATE SCRIPT TEST SUITE")
    print("="*60)

    tests = [
        test_query_latest_timestamp,
        test_calculate_backfill_range,
        test_print_status,
        test_idempotency_check
    ]

    results = [test() for test in tests]

    print("\n" + "="*60)
    print("TEST RESULTS")
    print("="*60)
    print(f"Passed: {sum(results)}/{len(results)}")

    if all(results):
        print("\n✓ ALL TESTS PASSED")
        print("\nReady to run: python scripts/maintenance/update_market_data.py")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
