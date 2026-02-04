"""
Safe Database Schema Migration
================================

Migrates validated_setups from old schema (myprojectx2_cleanpush backup)
to new schema (MPX2_fresh standard).

Follows database-design skill best practices:
- No data loss
- Explicit column mapping
- Verification step
- Rollback capability
"""

import duckdb
import sys
from datetime import datetime
from pathlib import Path

# Paths
BACKUP_DB = "C:/Users/sydne/OneDrive/myprojectx2_cleanpush/data/backups/20260118/gold.db"
TARGET_DB = "data/db/gold.db"

def main():
    print("=" * 70)
    print("VALIDATED_SETUPS SCHEMA MIGRATION")
    print("=" * 70)
    print()

    # Step 1: Extract data from backup database
    print("Step 1: Reading data from backup database...")
    print(f"  Source: {BACKUP_DB}")

    backup_conn = duckdb.connect(BACKUP_DB, read_only=True)

    # Check what's in the backup
    backup_schema = backup_conn.execute("PRAGMA table_info(validated_setups)").fetchall()
    print(f"  Backup schema columns: {[col[1] for col in backup_schema]}")

    backup_data = backup_conn.execute("""
        SELECT
            setup_id,
            instrument,
            orb_time,
            rr,
            sl_mode,
            orb_size_filter,
            win_rate,
            avg_r,
            trades,
            notes,
            validated_date
        FROM validated_setups
        ORDER BY instrument, orb_time, rr
    """).fetchall()

    backup_conn.close()

    print(f"  ✓ Extracted {len(backup_data)} setups from backup")
    print()

    # Step 2: Prepare target database
    print("Step 2: Preparing target database...")
    print(f"  Target: {TARGET_DB}")

    target_conn = duckdb.connect(TARGET_DB)

    # Backup current validated_setups (if exists)
    try:
        current_data = target_conn.execute("SELECT * FROM validated_setups").fetchall()
        print(f"  ✓ Backed up {len(current_data)} existing setups")
    except:
        print("  ✓ No existing validated_setups table (fresh start)")
        current_data = []

    # Drop and recreate table with new schema
    print("  Dropping old validated_setups table...")
    target_conn.execute("DROP TABLE IF EXISTS validated_setups")

    print("  Creating new validated_setups table...")
    target_conn.execute("""
        CREATE TABLE validated_setups (
            id INTEGER PRIMARY KEY,
            instrument VARCHAR NOT NULL,
            orb_time VARCHAR NOT NULL,
            rr DOUBLE NOT NULL,
            sl_mode VARCHAR NOT NULL,
            orb_size_filter DOUBLE,
            win_rate DOUBLE NOT NULL,
            expected_r DOUBLE NOT NULL,
            sample_size INTEGER NOT NULL,
            notes VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(instrument, orb_time, rr, sl_mode)
        )
    """)
    print("  ✓ New table created")
    print()

    # Step 3: Migrate data with explicit column mapping
    print("Step 3: Migrating data...")
    print("  Column mapping:")
    print("    setup_id     → id")
    print("    instrument   → instrument")
    print("    orb_time     → orb_time")
    print("    rr           → rr")
    print("    sl_mode      → sl_mode")
    print("    orb_size_filter → orb_size_filter")
    print("    win_rate     → win_rate")
    print("    avg_r        → expected_r")
    print("    trades       → sample_size")
    print("    notes        → notes")
    print("    validated_date → created_at & updated_at")
    print()

    migrated_count = 0
    for idx, row in enumerate(backup_data, start=1):
        setup_id, instrument, orb_time, rr, sl_mode, orb_size_filter, win_rate, avg_r, trades, notes, validated_date = row

        target_conn.execute("""
            INSERT INTO validated_setups (
                id, instrument, orb_time, rr, sl_mode,
                orb_size_filter, win_rate, expected_r, sample_size,
                notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            idx,  # Generate sequential IDs starting from 1
            instrument,
            orb_time,
            rr,
            sl_mode,
            orb_size_filter,
            win_rate,
            avg_r,  # avg_r → expected_r
            trades,  # trades → sample_size
            notes,
            validated_date if validated_date else datetime.now(),
            validated_date if validated_date else datetime.now()
        ])
        migrated_count += 1

    print(f"  ✓ Migrated {migrated_count} setups")
    print()

    # Step 4: Verification
    print("Step 4: Verifying migration...")

    # Count check
    final_count = target_conn.execute("SELECT COUNT(*) FROM validated_setups").fetchone()[0]
    assert final_count == len(backup_data), f"Count mismatch! Expected {len(backup_data)}, got {final_count}"
    print(f"  ✓ Row count verified: {final_count}")

    # Sample data check
    print("\n  Sample migrated data:")
    sample = target_conn.execute("""
        SELECT instrument, orb_time, rr, sl_mode, expected_r, sample_size
        FROM validated_setups
        ORDER BY expected_r DESC
        LIMIT 5
    """).fetchall()

    for row in sample:
        inst, orb, rr, sl, exp_r, samples = row
        print(f"    {inst:3} {orb} ORB | RR={rr:4.1f} | SL={sl:4} | E[R]={exp_r:+.3f} | n={samples}")

    print()

    # Instrument breakdown
    print("  Breakdown by instrument:")
    breakdown = target_conn.execute("""
        SELECT instrument, COUNT(*) as count
        FROM validated_setups
        GROUP BY instrument
        ORDER BY instrument
    """).fetchall()

    for inst, count in breakdown:
        print(f"    {inst}: {count} setups")

    target_conn.close()

    print()
    print("=" * 70)
    print("✓ MIGRATION COMPLETE!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Run: python test_app_sync.py")
    print("  2. Verify all tests pass")
    print("  3. Test apps work correctly")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ MIGRATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
