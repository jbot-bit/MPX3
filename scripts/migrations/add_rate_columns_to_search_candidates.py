#!/usr/bin/env python3
"""
Add profitable_trade_rate and target_hit_rate columns to search_candidates table

This migration adds clarified metric columns to replace the ambiguous 'win_rate_proxy'.
Both metrics are kept separate to avoid confusion.
"""

import sys
import os
from pathlib import Path
import duckdb

# Change to project root
project_root = Path(__file__).parent.parent.parent
os.chdir(project_root)

DB_PATH = "data/db/gold.db"

def migrate():
    """Add new rate columns to search_candidates"""

    print("="*70)
    print("MIGRATION: Add Rate Columns to search_candidates")
    print("="*70)
    print()

    conn = duckdb.connect(DB_PATH)

    # Check if search_candidates exists
    table_exists = conn.execute("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_name = 'search_candidates'
    """).fetchone()[0] > 0

    if not table_exists:
        print("[WARNING] search_candidates table does not exist")
        print("Run scripts/migrations/create_auto_search_tables.py first")
        conn.close()
        return 1

    print("Step 1: Check existing columns")
    columns = conn.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'search_candidates'
    """).fetchall()
    existing_cols = {col[0] for col in columns}
    print(f"  Existing columns: {len(existing_cols)}")

    # Add profitable_trade_rate if missing
    if 'profitable_trade_rate' not in existing_cols:
        print()
        print("Step 2a: Adding profitable_trade_rate column...")
        conn.execute("""
            ALTER TABLE search_candidates
            ADD COLUMN profitable_trade_rate DOUBLE
        """)
        print("  [OK] profitable_trade_rate added")
    else:
        print()
        print("Step 2a: SKIP - profitable_trade_rate already exists")

    # Add target_hit_rate if missing
    if 'target_hit_rate' not in existing_cols:
        print()
        print("Step 2b: Adding target_hit_rate column...")
        conn.execute("""
            ALTER TABLE search_candidates
            ADD COLUMN target_hit_rate DOUBLE
        """)
        print("  [OK] target_hit_rate added")
    else:
        print()
        print("Step 2b: SKIP - target_hit_rate already exists")

    # Migrate existing win_rate_proxy data if needed
    if 'win_rate_proxy' in existing_cols:
        print()
        print("Step 3: Migrate existing win_rate_proxy data...")

        # Count rows with win_rate_proxy but no new columns
        count = conn.execute("""
            SELECT COUNT(*) FROM search_candidates
            WHERE win_rate_proxy IS NOT NULL
              AND (profitable_trade_rate IS NULL OR target_hit_rate IS NULL)
        """).fetchone()[0]

        if count > 0:
            print(f"  Found {count} rows to migrate")

            # Copy win_rate_proxy to both columns (we can't distinguish which type it was)
            # Mark with a note that this is migrated data
            conn.execute("""
                UPDATE search_candidates
                SET profitable_trade_rate = win_rate_proxy,
                    target_hit_rate = win_rate_proxy,
                    notes = COALESCE(notes, '') || ' [MIGRATED: Original win_rate_proxy, type ambiguous]'
                WHERE win_rate_proxy IS NOT NULL
                  AND (profitable_trade_rate IS NULL OR target_hit_rate IS NULL)
            """)
            print(f"  [OK] Migrated {count} rows (marked as ambiguous)")
        else:
            print("  [OK] No data to migrate")

    print()
    print("Step 4: Verify final schema")
    final_cols = conn.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'search_candidates'
        ORDER BY ordinal_position
    """).fetchall()

    for col in final_cols:
        print(f"  - {col[0]}")

    print()
    print("="*70)
    print("MIGRATION COMPLETE")
    print("="*70)
    print()
    print("Next steps:")
    print("  1. Update auto_search_engine.py to use new columns")
    print("  2. Update app_canonical.py UI to display both rates")
    print("  3. Run: python scripts/check/check_auto_search_tables.py")
    print()

    conn.close()
    return 0

if __name__ == "__main__":
    sys.exit(migrate())
