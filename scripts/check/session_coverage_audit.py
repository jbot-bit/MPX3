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

def audit_session_coverage(db_path: str = "data/db/gold.db"):
    """
    Audit coverage of all session window columns in daily_features.

    Returns True if all columns meet the >95% coverage threshold.
    """
    conn = duckdb.connect(db_path, read_only=True)

    # Define all session window columns to audit
    session_columns = [
        # Pre-session windows
        "pre_asia_high", "pre_asia_low", "pre_asia_range",
        "pre_london_high", "pre_london_low", "pre_london_range",
        "pre_ny_high", "pre_ny_low", "pre_ny_range",

        # Main sessions
        "asia_high", "asia_low", "asia_range",
        "london_high", "london_low", "london_range",
        "ny_high", "ny_low", "ny_range",
    ]

    # Get total row count
    total_days = conn.execute("SELECT COUNT(*) FROM daily_features WHERE instrument='MGC'").fetchone()[0]

    print("="*80)
    print("SESSION COVERAGE AUDIT")
    print("="*80)
    print(f"Total trading days: {total_days}")
    print()
    print(f"{'Column Name':<25} {'Non-Null Days':>15} {'Total Days':>12} {'Coverage %':>12} {'Status':>10}")
    print("-"*80)

    failed_columns = []

    for col in session_columns:
        # Count non-null values
        non_null_count = conn.execute(
            f"SELECT COUNT(*) FROM daily_features WHERE instrument='MGC' AND {col} IS NOT NULL"
        ).fetchone()[0]

        coverage_pct = (non_null_count / total_days * 100) if total_days > 0 else 0

        # Check if coverage meets threshold (>95% = <5% null)
        status = "PASS" if coverage_pct >= 95.0 else "FAIL"
        if status == "FAIL":
            failed_columns.append((col, coverage_pct))

        print(f"{col:<25} {non_null_count:>15} {total_days:>12} {coverage_pct:>11.2f}% {status:>10}")

    conn.close()

    print("-"*80)

    if failed_columns:
        print(f"\nFAILED: {len(failed_columns)} columns below 95% coverage threshold:")
        for col, pct in failed_columns:
            print(f"  - {col}: {pct:.2f}% (missing {100-pct:.2f}%)")
        print("\nPossible causes:")
        print("  - Missing computation in build_daily_features.py")
        print("  - Missing INSERT mapping")
        print("  - Missing bars in that time window")
        print("  - Weekend/holiday gaps (expected for some dates)")
        return False
    else:
        print(f"\nSUCCESS: All {len(session_columns)} session columns meet >95% coverage threshold")
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
