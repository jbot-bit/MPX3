#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add missing session columns to daily_features table

This fixes the schema mismatch causing feature build failures.

Missing columns:
- pre_asia_high, pre_asia_low, pre_asia_range
- pre_london_high, pre_london_low, pre_london_range
- pre_ny_high, pre_ny_low, pre_ny_range
- london_range, ny_range
"""

import sys
import duckdb
from pathlib import Path

def check_column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    schema = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    return any(col[1] == column_name for col in schema)

def add_missing_columns(db_path: str):
    """Add all missing session columns to daily_features."""

    # Columns to add
    missing_columns = [
        # Pre-session windows (07:00-09:00, 17:00-18:00, 23:00-00:30)
        ("pre_asia_high", "DOUBLE"),
        ("pre_asia_low", "DOUBLE"),
        ("pre_asia_range", "DOUBLE"),
        ("pre_london_high", "DOUBLE"),
        ("pre_london_low", "DOUBLE"),
        ("pre_london_range", "DOUBLE"),
        ("pre_ny_high", "DOUBLE"),
        ("pre_ny_low", "DOUBLE"),
        ("pre_ny_range", "DOUBLE"),

        # Missing range columns
        ("london_range", "DOUBLE"),
        ("ny_range", "DOUBLE"),
    ]

    conn = None
    try:
        conn = duckdb.connect(db_path)

        print("Checking daily_features schema...")
        print("="*60)

        added = []
        skipped = []

        for col_name, col_type in missing_columns:
            if check_column_exists(conn, "daily_features", col_name):
                print(f"  ✓ {col_name:30} already exists")
                skipped.append(col_name)
            else:
                print(f"  + {col_name:30} adding as {col_type}")
                conn.execute(f"ALTER TABLE daily_features ADD COLUMN {col_name} {col_type}")
                added.append(col_name)

        print("="*60)
        print(f"Added: {len(added)} columns")
        print(f"Skipped: {len(skipped)} columns (already exist)")

        if added:
            print("\nNewly added columns:")
            for col in added:
                print(f"  - {col}")

        # Verify schema
        print("\n" + "="*60)
        print("VERIFICATION")
        print("="*60)

        schema = conn.execute("PRAGMA table_info('daily_features')").fetchall()
        session_cols = [c[1] for c in schema if any(x in c[1] for x in ['asia', 'london', 'ny']) and 'orb' not in c[1]]

        print(f"Total session columns: {len(session_cols)}")
        print("\nAll session columns in database:")
        for col in sorted(session_cols):
            print(f"  - {col}")

        return True

    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False

    finally:
        if conn:
            conn.close()

def main():
    # Change to project root
    project_root = Path(__file__).parent.parent.parent
    import os
    os.chdir(project_root)

    db_path = "data/db/gold.db"

    print("="*60)
    print("ADD MISSING SESSION COLUMNS TO daily_features")
    print("="*60)
    print(f"Database: {db_path}")
    print()

    if add_missing_columns(db_path):
        print("\n✅ Schema migration complete")
        return 0
    else:
        print("\n❌ Schema migration failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
