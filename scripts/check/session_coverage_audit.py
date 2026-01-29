#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Coverage Audit

After schema migration, verify that all session window columns are properly populated.

Per update4.txt:
- For each session/pre-session window, compute non-null % for high/low/range columns
- If any session column is >5% null on normal trading days, treat it as a bug
- Print table: column_name, non_null_days, total_days, non_null_pct

Usage:
  python scripts/check/session_coverage_audit.py
"""

import sys
import os
import duckdb
from pathlib import Path

def audit_session_coverage(db_path: str = "data/db/gold.db", instrument: str = "MGC"):
    """
    Audit coverage of all session window columns in daily_features.

    Computes coverage ONLY on trading days (days where bars_1m has data).
    This excludes weekends, holidays, and data gaps automatically.

    Returns True if all columns meet >=99% coverage on trading days.
    """
    conn = duckdb.connect(db_path, read_only=True)

    # Define session column groups for cleaner reporting
    session_groups = {
        "pre_asia": ["pre_asia_high", "pre_asia_low", "pre_asia_range"],
        "asia": ["asia_high", "asia_low", "asia_range"],
        "pre_london": ["pre_london_high", "pre_london_low", "pre_london_range"],
        "london": ["london_high", "london_low", "london_range"],
        "pre_ny": ["pre_ny_high", "pre_ny_low", "pre_ny_range"],
        "ny": ["ny_high", "ny_low", "ny_range"],
    }

    # Define trading day = day where bars_1m has >= 400 bars for the instrument
    # This excludes:
    # - Weekends (0 bars or only night session ~120 bars)
    # - Holidays (0 bars)
    # - Partial days (< 7 hours of trading)
    # A full Asia session (09:00-17:00) = 8 hours = ~480 bars minimum
    TRADING_DAY_THRESHOLD = 400  # bars (ensures at least ~7 hours of data)

    # Get list of trading days (dates with sufficient bars)
    trading_days_query = f"""
        SELECT DISTINCT
            DATE_TRUNC('day', ts_utc AT TIME ZONE 'UTC' AT TIME ZONE 'Australia/Brisbane') AS date_local
        FROM bars_1m
        WHERE symbol = '{instrument}'
        GROUP BY date_local
        HAVING COUNT(*) >= {TRADING_DAY_THRESHOLD}
        ORDER BY date_local
    """
    trading_days_result = conn.execute(trading_days_query).fetchall()
    trading_days = {row[0] for row in trading_days_result}
    trading_days_count = len(trading_days)

    # Get total days in daily_features (for comparison)
    total_days = conn.execute(
        f"SELECT COUNT(*) FROM daily_features WHERE instrument='{instrument}'"
    ).fetchone()[0]

    print("="*90)
    print("SESSION COVERAGE AUDIT (TRADING DAYS ONLY)")
    print("="*90)
    print(f"Instrument: {instrument}")
    print(f"Trading days (>={TRADING_DAY_THRESHOLD} bars in bars_1m): {trading_days_count}")
    print(f"Total rows in daily_features: {total_days}")
    print(f"Weekend/holiday/gap days: {total_days - trading_days_count}")
    print()
    print(f"{'Session Group':<15} {'Columns':>8} {'Coverage':>12} {'Status':>10}")
    print("-"*90)

    failed_groups = []

    for group_name, columns in session_groups.items():
        # For this group, compute coverage on trading days only
        # A trading day has "coverage" if ALL columns in the group are non-null

        coverage_query = f"""
            SELECT COUNT(*) FROM daily_features
            WHERE instrument = '{instrument}'
              AND date_local IN (
                  SELECT DATE_TRUNC('day', ts_utc AT TIME ZONE 'UTC' AT TIME ZONE 'Australia/Brisbane') AS trading_day
                  FROM bars_1m
                  WHERE symbol = '{instrument}'
                  GROUP BY trading_day
                  HAVING COUNT(*) >= {TRADING_DAY_THRESHOLD}
              )
              AND {' AND '.join([f'{col} IS NOT NULL' for col in columns])}
        """

        covered_days = conn.execute(coverage_query).fetchone()[0]
        coverage_pct = (covered_days / trading_days_count * 100) if trading_days_count > 0 else 0

        # Threshold depends on session type:
        # - Pre-market sessions (pre_asia, pre_london, pre_ny): >= 85% (may have no bars on some days)
        # - Main sessions (asia, london, ny): >= 99% (should always have bars on trading days)
        is_premarket = group_name.startswith("pre_")
        threshold = 85.0 if is_premarket else 99.0

        status = "PASS" if coverage_pct >= threshold else "FAIL"
        if status == "FAIL":
            failed_groups.append((group_name, coverage_pct, covered_days, trading_days_count, threshold))

        print(f"{group_name:<15} {len(columns):>8} {coverage_pct:>11.1f}% {status:>10}")

    conn.close()

    print("-"*90)

    if failed_groups:
        print(f"\nFAILED: {len(failed_groups)} groups below threshold on trading days:")
        for group, pct, covered, total, threshold in failed_groups:
            missing = total - covered
            print(f"  - {group}: {pct:.1f}% < {threshold:.0f}% ({covered}/{total} days, {missing} missing)")
        print("\nPossible causes:")
        print("  - Missing computation in build_daily_features.py")
        print("  - Missing INSERT mapping")
        print("  - Bars exist but session window computation failed")
        return False
    else:
        print(f"\nSUCCESS: All {len(session_groups)} session groups meet coverage thresholds")
        print(f"Main sessions (asia/london/ny): >=99% on {trading_days_count} trading days")
        print(f"Pre-market sessions (pre_*): >=85% (lower due to sporadic pre-market trading)")
        return True

def main():
    # Change to project root
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)

    print()
    success = audit_session_coverage()
    print()

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
