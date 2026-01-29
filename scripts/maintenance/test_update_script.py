#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lightweight Database Audit (No API Calls)
Quick validation of data integrity and freshness

Usage:
    python scripts/maintenance/test_update_script.py

Exit codes:
    0 = All checks pass
    1 = Issues found
"""

import sys
import io
import os
from pathlib import Path
from datetime import datetime, timedelta
import duckdb
from zoneinfo import ZoneInfo

# Fix Unicode output on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def quick_audit(db_path: str, symbol: str = 'MGC'):
    """
    Quick database audit (no API calls).

    Checks:
    1. No duplicate timestamps
    2. No OHLC violations (last 3 days)
    3. Feature freshness (lag < 3 days acceptable)
    4. Recent data completeness (last 3 days)
    """
    print("="*60)
    print("QUICK DATABASE AUDIT (No API Calls)")
    print("="*60)

    conn = None
    all_pass = True

    try:
        conn = duckdb.connect(db_path, read_only=True)

        # 1. Check for duplicates
        print("\n1. Duplicate Check:")
        dupes = conn.execute("""
            SELECT COUNT(*) FROM (
                SELECT ts_utc, COUNT(*) as cnt
                FROM bars_1m
                WHERE symbol = ?
                GROUP BY ts_utc
                HAVING COUNT(*) > 1
            )
        """, [symbol]).fetchone()[0]

        if dupes > 0:
            print(f"   ❌ FAIL: {dupes} duplicate timestamps")
            all_pass = False
        else:
            print("   ✅ PASS: No duplicates")

        # 2. Check OHLC violations (last 3 days)
        print("\n2. Price Sanity Check:")
        tz_brisbane = ZoneInfo("Australia/Brisbane")
        cutoff = datetime.now(tz_brisbane).date() - timedelta(days=3)

        violations = conn.execute("""
            SELECT COUNT(*) FROM bars_1m
            WHERE symbol = ?
            AND DATE_TRUNC('day', ts_utc AT TIME ZONE 'Australia/Brisbane') >= ?
            AND (
                high < GREATEST(open, close)
                OR low > LEAST(open, close)
                OR high < low
            )
        """, [symbol, cutoff]).fetchone()[0]

        if violations > 0:
            print(f"   ❌ FAIL: {violations} OHLC violations")
            all_pass = False
        else:
            print("   ✅ PASS: No OHLC violations")

        # 3. Check feature freshness
        print("\n3. Feature Freshness Check:")
        latest_bar_ts = conn.execute("""
            SELECT MAX(ts_utc) FROM bars_1m WHERE symbol = ?
        """, [symbol]).fetchone()[0]

        latest_feat_date = conn.execute("""
            SELECT MAX(date_local) FROM daily_features WHERE instrument = ?
        """, [symbol]).fetchone()[0]

        bar_date = latest_bar_ts.astimezone(tz_brisbane).date()
        lag_days = (bar_date - latest_feat_date).days if latest_feat_date else 999

        if lag_days <= 3:
            print(f"   ✅ PASS: Feature lag = {lag_days} days")
            print(f"      Latest bars: {bar_date}")
            print(f"      Latest features: {latest_feat_date}")
        else:
            print(f"   ⚠️  WARNING: Feature lag = {lag_days} days (consider rebuilding)")
            print(f"      Latest bars: {bar_date}")
            print(f"      Latest features: {latest_feat_date}")
            # Don't fail on feature lag (may be schema issue)

        # 4. Check recent data completeness
        print("\n4. Data Completeness Check:")
        cutoff_3d = datetime.now(tz_brisbane).date() - timedelta(days=3)

        daily_counts = conn.execute("""
            SELECT
                DATE_TRUNC('day', ts_utc AT TIME ZONE 'Australia/Brisbane') as day,
                COUNT(*) as bars
            FROM bars_1m
            WHERE symbol = ?
            AND DATE_TRUNC('day', ts_utc AT TIME ZONE 'Australia/Brisbane') >= ?
            GROUP BY day
            ORDER BY day DESC
        """, [symbol, cutoff_3d]).fetchall()

        issues = []
        for day, bars in daily_counts:
            if bars < 100 and day.weekday() < 5:  # Weekday with low bars
                issues.append(f"{day}: {bars} bars (low)")

        if issues:
            print(f"   ⚠️  WARNING: {len(issues)} days with low bar counts")
            for issue in issues:
                print(f"      - {issue}")
        else:
            print(f"   ✅ PASS: All {len(daily_counts)} recent days OK")

        # Summary
        bar_count = conn.execute("""
            SELECT COUNT(*) FROM bars_1m WHERE symbol = ?
        """, [symbol]).fetchone()[0]

        feat_count = conn.execute("""
            SELECT COUNT(*) FROM daily_features WHERE instrument = ?
        """, [symbol]).fetchone()[0]

        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"Database: {db_path}")
        print(f"Symbol: {symbol}")
        print(f"Total bars: {bar_count:,}")
        print(f"Total daily_features: {feat_count:,}")
        print(f"Latest bars: {bar_date}")
        print(f"Latest features: {latest_feat_date}")
        print("="*60)

    finally:
        if conn:
            conn.close()

    return all_pass


def main():
    """Main execution flow."""
    try:
        # Change to project root
        project_root = Path(__file__).parent.parent.parent
        os.chdir(project_root)

        db_path = "data/db/gold.db"
        symbol = "MGC"

        if not Path(db_path).exists():
            print(f"ERROR: Database not found: {db_path}", file=sys.stderr)
            return 1

        if quick_audit(db_path, symbol):
            print("\n✅ ALL QUICK CHECKS PASSED")
            return 0
        else:
            print("\n❌ ISSUES FOUND - Run full integrity check:")
            print("   python scripts/maintenance/verify_system_integrity.py")
            return 1

    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
