#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Drop legacy *_type columns from daily_features

CONTEXT:
- Old schema had: asia_type, london_type, ny_type (string descriptions)
- New schema uses: asia_type_code, london_type_code, pre_ny_type_code (coded values)
- Code only inserts/reads *_type_code columns
- Legacy *_type columns contain old data but are not used

DECISION:
- Canonical naming: *_type_code (already in use by build_daily_features.py)
- Drop legacy columns: asia_type, london_type, ny_type (3 columns)

SAFETY:
- Verified no code reads legacy columns (only *_type_code used)
- Backup command: cp gold.db gold.db.backup_before_type_drop

Usage:
  python scripts/migrations/drop_legacy_type_columns.py
"""

import sys
import os
import duckdb
from pathlib import Path

def drop_legacy_type_columns(db_path: str = "data/db/gold.db"):
    """Drop unused legacy *_type columns."""

    legacy_columns = ["asia_type", "london_type", "ny_type"]

    conn = duckdb.connect(db_path)

    print("="*70)
    print("DROP LEGACY TYPE COLUMNS")
    print("="*70)
    print(f"Database: {db_path}")
    print()

    # Check which columns exist
    schema = conn.execute("PRAGMA table_info('daily_features')").fetchall()
    existing_cols = {row[1] for row in schema}

    columns_to_drop = [col for col in legacy_columns if col in existing_cols]

    if not columns_to_drop:
        print("No legacy columns found - already clean!")
        conn.close()
        return True

    print(f"Found {len(columns_to_drop)} legacy columns to drop:")
    for col in columns_to_drop:
        # Check if column has data
        count = conn.execute(
            f"SELECT COUNT(*) FROM daily_features WHERE {col} IS NOT NULL"
        ).fetchone()[0]
        print(f"  - {col:20} ({count} rows with data)")
    print()

    # Confirm drop
    print("These columns are NOT used by build_daily_features.py (only *_type_code used)")
    print("Dropping legacy columns...")
    print()

    for col in columns_to_drop:
        print(f"Dropping {col}...")
        conn.execute(f"ALTER TABLE daily_features DROP COLUMN {col}")

    conn.close()

    print()
    print("="*70)
    print("SUCCESS: Legacy type columns dropped")
    print("="*70)
    print(f"Dropped: {', '.join(columns_to_drop)}")
    print(f"Kept: asia_type_code, london_type_code, pre_ny_type_code")
    print()

    return True

def main():
    # Change to project root
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)

    print()
    success = drop_legacy_type_columns()
    print()

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
