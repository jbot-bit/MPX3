#!/usr/bin/env python3
"""
Automated Daily Market Data Update Pipeline
Keeps bars_1m and daily_features current

Usage:
    python scripts/maintenance/update_market_data.py

Designed to run via Windows Task Scheduler daily at 18:00 Brisbane time.
Queries MAX timestamp from bars_1m, backfills incrementally to now, and updates features.

Exit codes:
    0 = Success (data updated or already current)
    1 = Failure (scheduler will retry)
"""

import sys
import os
import duckdb
from pathlib import Path
from datetime import datetime, timedelta, timezone
import subprocess


def get_latest_bar_timestamp(db_path: str, symbol: str = 'MGC'):
    """Query MAX timestamp from bars_1m to determine where data ends."""
    try:
        conn = duckdb.connect(db_path, read_only=True)
        result = conn.execute("""
            SELECT MAX(ts_utc) FROM bars_1m
            WHERE symbol = ?
        """, [symbol]).fetchone()
        conn.close()

        if not result or result[0] is None:
            raise Exception(
                f"No bars found for {symbol}. "
                "Run initial backfill first:\n"
                f"  python pipeline/backfill_databento_continuous.py 2020-12-20 2026-01-29"
            )

        return result[0]  # Returns datetime with timezone

    except Exception as e:
        raise Exception(f"Failed to query latest bar timestamp: {e}")


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
    Run Databento backfill for specified date range.

    Note: backfill_databento_continuous.py automatically calls build_daily_features.py
    at the end, so no separate feature building needed.

    Args:
        start_date: Start date (local Brisbane)
        end_date: End date (local Brisbane)

    Returns:
        True if successful, False otherwise
    """
    cmd = [
        sys.executable,  # Python interpreter
        "pipeline/backfill_databento_continuous.py",
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


def print_status(db_path: str, symbol: str = 'MGC'):
    """Print current data status (latest timestamps in bars_1m and daily_features)."""
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

        conn.close()

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


def main():
    """Main execution flow."""
    try:
        # Change to project root
        project_root = Path(__file__).parent.parent.parent
        os.chdir(project_root)

        db_path = "data/db/gold.db"
        symbol = "MGC"

        print("="*60)
        print("AUTOMATED MARKET DATA UPDATE")
        print("="*60)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Working directory: {os.getcwd()}")
        print(f"Database: {db_path}")
        print(f"Symbol: {symbol}")
        print("="*60)

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
            print("\n✓ Data is already current. No update needed.")
            print_status(db_path, symbol)
            return 0

        # Step 3: Run backfill
        print("\nStep 3: Running incremental backfill...")
        if not run_backfill(start_date, end_date):
            print("\n✗ FAILURE: Backfill failed", file=sys.stderr)
            return 1  # Exit non-zero on failure

        # Step 4: Print status
        print("\nStep 4: Verifying update...")
        print_status(db_path, symbol)

        print("✓ SUCCESS: Market data updated")
        return 0

    except Exception as e:
        print(f"\n✗ ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
