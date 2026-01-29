#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automated Daily Market Data Update Pipeline (ProjectX API Version)
Keeps bars_1m and daily_features current using ProjectX API

Usage:
    python scripts/maintenance/update_market_data_projectx.py

Designed to run via Windows Task Scheduler daily at 18:00 Brisbane time.
Uses ProjectX API instead of Databento.

Exit codes:
    0 = Success (data updated or already current)
    1 = Failure (scheduler will retry)
"""

import sys
import io
import os
import duckdb
from pathlib import Path
from datetime import datetime, timedelta, timezone
import subprocess

# Fix Unicode output on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# PHASE 2: Honesty rule - always rebuild trailing days to catch late-arriving bars
REBUILD_TAIL_DAYS = 3


def get_latest_bar_timestamp(db_path: str, symbol: str = 'MGC'):
    """Query MAX timestamp from bars_1m to determine where data ends."""
    conn = None
    try:
        conn = duckdb.connect(db_path, read_only=True)
        result = conn.execute("""
            SELECT MAX(ts_utc) FROM bars_1m
            WHERE symbol = ?
        """, [symbol]).fetchone()

        if not result or result[0] is None:
            raise Exception(
                f"No bars found for {symbol}. "
                "Run initial backfill first:\n"
                f"  python pipeline/backfill_range.py 2020-12-20 2026-01-29"
            )

        return result[0]  # Returns datetime with timezone

    except Exception as e:
        raise Exception(f"Failed to query latest bar timestamp: {e}")
    finally:
        if conn:
            conn.close()


def get_latest_feature_date(db_path: str, instrument: str = 'MGC'):
    """Query MAX date_local from daily_features (PHASE 2)."""
    conn = None
    try:
        conn = duckdb.connect(db_path, read_only=True)
        result = conn.execute("""
            SELECT MAX(date_local) FROM daily_features WHERE instrument = ?
        """, [instrument]).fetchone()

        if not result or result[0] is None:
            return None
        return result[0]
    finally:
        if conn:
            conn.close()


def get_min_bar_date(db_path: str, symbol: str = 'MGC'):
    """Get MIN date from bars_1m if daily_features is empty."""
    conn = None
    try:
        conn = duckdb.connect(db_path, read_only=True)
        result = conn.execute("""
            SELECT MIN(DATE_TRUNC('day', ts_utc AT TIME ZONE 'Australia/Brisbane'))
            FROM bars_1m WHERE symbol = ?
        """, [symbol]).fetchone()

        if not result or result[0] is None:
            return None
        return result[0].date() if hasattr(result[0], 'date') else result[0]
    finally:
        if conn:
            conn.close()


def calculate_backfill_range(latest_ts):
    """
    Calculate incremental backfill range.

    Args:
        latest_ts: Latest timestamp in bars_1m (UTC, timezone-aware)

    Returns:
        (start_date, end_date) as local Brisbane dates for backfill script
    """
    from zoneinfo import ZoneInfo

    # Start = latest + 1 minute
    start_ts = latest_ts + timedelta(minutes=1)

    # End = now rounded down to last full minute
    now_utc = datetime.now(timezone.utc).replace(second=0, microsecond=0)

    # Convert to local dates (Brisbane) for backfill script
    tz_brisbane = ZoneInfo("Australia/Brisbane")

    start_local = start_ts.astimezone(tz_brisbane).date()
    end_local = now_utc.astimezone(tz_brisbane).date()

    return start_local, end_local


def run_backfill(start_date, end_date):
    """
    Run ProjectX backfill for specified date range.

    Note: backfill_range.py uses ProjectX API.

    Args:
        start_date: Start date (local Brisbane)
        end_date: End date (local Brisbane)

    Returns:
        True if successful, False otherwise
    """
    cmd = [
        sys.executable,  # Python interpreter
        "pipeline/backfill_range.py",
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d")
    ]

    print(f"\nRunning: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"BACKFILL FAILED:\n{result.stderr}", file=sys.stderr)
        if result.stdout:
            print(f"STDOUT:\n{result.stdout}")
        return False

    print(result.stdout)
    return True


def calculate_feature_build_range(db_path: str, symbol: str = 'MGC'):
    """
    Calculate feature build range with PHASE 2 honesty rule.

    Logic:
    - End = YESTERDAY (today is incomplete, don't build features for it)
    - Start = last_feat_date + 1 (or MIN bar date if empty)
    - Apply REBUILD_TAIL_DAYS to catch late-arriving bars
    """
    from zoneinfo import ZoneInfo

    tz_brisbane = ZoneInfo("Australia/Brisbane")
    last_feat_date = get_latest_feature_date(db_path, instrument=symbol)

    # End = YESTERDAY (today's trading day incomplete)
    today_local = datetime.now(tz_brisbane).date()
    end_date_local = today_local - timedelta(days=1)

    # Determine start
    if last_feat_date is None:
        min_bar_date = get_min_bar_date(db_path, symbol)
        if min_bar_date is None:
            return None, None
        start_date_local = min_bar_date
    else:
        start_date_local = last_feat_date + timedelta(days=1)

    # Apply REBUILD_TAIL_DAYS honesty rule
    rebuild_from = end_date_local - timedelta(days=REBUILD_TAIL_DAYS)
    if start_date_local > rebuild_from:
        start_date_local = rebuild_from

    # Clamp
    if start_date_local > end_date_local:
        return None, None

    return start_date_local, end_date_local


def run_feature_builder(start_date, end_date):
    """
    Run feature builder (PHASE 2: uses correct CLI args).
    """
    cmd = [
        sys.executable,
        "pipeline/build_daily_features.py",
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d"),
        "--sl-mode", "full"
    ]

    print(f"\nRunning: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"FEATURE BUILD FAILED:\n{result.stderr}", file=sys.stderr)
        if result.stdout:
            print(f"STDOUT:\n{result.stdout}")
        return False

    print(result.stdout)
    return True


def print_status(db_path: str, symbol: str = 'MGC'):
    """Print current data status (latest timestamps in bars_1m and daily_features)."""
    conn = None
    try:
        conn = duckdb.connect(db_path, read_only=True)

        # Latest bars_1m
        bar_ts = conn.execute("""
            SELECT MAX(ts_utc) FROM bars_1m WHERE symbol = ?
        """, [symbol]).fetchone()[0]

        # Latest daily_features
        feature_date = conn.execute("""
            SELECT MAX(date_local) FROM daily_features WHERE instrument = ?
        """, [symbol]).fetchone()[0]

        # Count of rows added today (for monitoring)
        from zoneinfo import ZoneInfo
        tz_brisbane = ZoneInfo("Australia/Brisbane")
        today_local = datetime.now(tz_brisbane).date()

        bars_added_today = conn.execute("""
            SELECT COUNT(*) FROM bars_1m
            WHERE symbol = ?
            AND DATE_TRUNC('day', ts_utc AT TIME ZONE 'Australia/Brisbane') = ?
        """, [symbol, today_local]).fetchone()[0]

        print("\n" + "="*60)
        print("UPDATE STATUS")
        print("="*60)
        print(f"Symbol: {symbol}")
        print(f"Latest bars_1m timestamp: {bar_ts}")
        print(f"Latest daily_features date: {feature_date}")
        print(f"Bars added today ({today_local}): {bars_added_today}")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\nWarning: Could not print status: {e}\n", file=sys.stderr)
    finally:
        if conn:
            conn.close()


def main():
    """Main execution flow."""
    try:
        # Change to project root
        project_root = Path(__file__).parent.parent.parent
        os.chdir(project_root)

        db_path = "data/db/gold.db"
        symbol = "MGC"

        print("="*60)
        print("AUTOMATED MARKET DATA UPDATE (ProjectX API)")
        print(f"PHASE 2: REBUILD_TAIL_DAYS={REBUILD_TAIL_DAYS}")
        print("="*60)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Working directory: {os.getcwd()}")
        print(f"Database: {db_path}")
        print(f"Symbol: {symbol}")
        print("="*60)

        # Run health check to auto-fix WAL corruption if present
        print("\nRunning database health check...")
        sys.path.insert(0, 'trading_app')
        from db_health_check import run_startup_health_check

        if not run_startup_health_check(db_path):
            print("\nERROR: Database health check failed", file=sys.stderr)
            return 1

        print("Database healthy")

        # Step 1: Get current data status
        print("\nStep 1: Querying current data status...")
        latest_ts = get_latest_bar_timestamp(db_path, symbol)
        print(f"Current data ends at: {latest_ts} UTC")

        # Step 2: Calculate what needs updating
        print("\nStep 2: Calculating update range...")
        start_date, end_date = calculate_backfill_range(latest_ts)
        print(f"Update range: {start_date} to {end_date} (Brisbane local)")

        # Skip if already current
        if start_date > end_date:
            print("\nData is already current. No update needed.")
            print_status(db_path, symbol)
            return 0

        # Step 3: Run backfill if needed
        if start_date <= end_date:
            print("\nStep 3: Running incremental backfill (ProjectX API)...")
            if not run_backfill(start_date, end_date):
                print("\nFAILURE: Backfill failed", file=sys.stderr)
                return 1

            # Re-query latest bar after backfill
            latest_ts = get_latest_bar_timestamp(db_path, symbol)
            print(f"Updated latest bars_1m: {latest_ts}")
        else:
            print("\nStep 3: Bars already current, skipping backfill")

        # Step 4: Calculate feature build range (PHASE 2)
        print("\nStep 4: Calculating feature build range...")
        feat_start, feat_end = calculate_feature_build_range(db_path, symbol)

        if feat_start is None:
            print("Features already current, no rebuild needed")
        else:
            print(f"Feature build range: {feat_start} to {feat_end}")
            if REBUILD_TAIL_DAYS > 0 and feat_start < feat_end - timedelta(days=1):
                print(f"(includes REBUILD_TAIL_DAYS={REBUILD_TAIL_DAYS} for honesty)")

            # Step 5: Run feature builder
            print("\nStep 5: Building daily features...")
            if not run_feature_builder(feat_start, feat_end):
                print("\nFAILURE: Feature build failed", file=sys.stderr)
                return 1

        # Step 6: Print status
        print("\nStep 6: Verifying update...")
        print_status(db_path, symbol)

        print("SUCCESS: Market data updated")
        return 0

    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
