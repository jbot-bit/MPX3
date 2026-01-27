#!/usr/bin/env python3
"""
Sync validated_setups from root gold.db to data/db/gold.db

After running Phase 1-5 migration on root gold.db, this script copies
the validated MGC setups (with realized_expectancy) to the apps database.

IMPORTANT: This will REPLACE data/db/gold.db validated_setups with root gold.db data.
"""

import duckdb
import sys

ROOT_DB = "gold.db"
APP_DB = "data/db/gold.db"


def sync_validated_setups():
    """Copy validated_setups from root DB to app DB."""
    print("=" * 70)
    print("SYNC VALIDATED_SETUPS: gold.db → data/db/gold.db")
    print("=" * 70)
    print()

    # Connect to both databases
    root_con = duckdb.connect(ROOT_DB)
    app_con = duckdb.connect(APP_DB)

    # Get current counts
    root_count = root_con.execute("SELECT COUNT(*) FROM validated_setups").fetchone()[0]
    app_count = app_con.execute("SELECT COUNT(*) FROM validated_setups").fetchone()[0]

    print(f"Root DB ({ROOT_DB}): {root_count} setups")
    print(f"App DB ({APP_DB}): {app_count} setups")
    print()

    # Show what will be replaced
    print("Current MGC setups in APP DB:")
    app_mgc = app_con.execute("""
        SELECT id, orb_time, rr, sl_mode, realized_expectancy
        FROM validated_setups
        WHERE instrument = 'MGC'
        ORDER BY orb_time, rr
    """).fetchall()

    for row in app_mgc:
        setup_id, orb, rr, sl, realized = row
        realized_str = f"{realized:+.3f}R" if realized else "NULL"
        print(f"  {orb} RR={rr} {sl}: realized_expectancy={realized_str}")
    print()

    print("New MGC setups from ROOT DB:")
    root_mgc = root_con.execute("""
        SELECT id, orb_time, rr, sl_mode, realized_expectancy
        FROM validated_setups
        WHERE instrument = 'MGC'
        ORDER BY orb_time, rr
    """).fetchall()

    for row in root_mgc:
        setup_id, orb, rr, sl, realized = row
        realized_str = f"{realized:+.3f}R" if realized else "NULL"
        print(f"  {orb} RR={rr} {sl}: realized_expectancy={realized_str}")
    print()

    # Confirm
    response = input("Replace APP DB validated_setups with ROOT DB data? (yes/no): ")
    if response.lower() != "yes":
        print("Aborted.")
        return

    print()
    print("Syncing...")
    print()

    # Delete all from app DB
    app_con.execute("DELETE FROM validated_setups")
    print(f"[OK] Deleted {app_count} rows from APP DB")

    # Copy all from root DB
    root_setups = root_con.execute("SELECT * FROM validated_setups").fetchall()
    root_columns = [col[0] for col in root_con.execute("PRAGMA table_info(validated_setups)").fetchall()]

    # Build INSERT statement
    placeholders = ", ".join(["?" for _ in root_columns])
    insert_sql = f"INSERT INTO validated_setups VALUES ({placeholders})"

    for row in root_setups:
        app_con.execute(insert_sql, list(row))

    new_count = app_con.execute("SELECT COUNT(*) FROM validated_setups").fetchone()[0]
    print(f"[OK] Inserted {new_count} rows into APP DB")
    print()

    # Verify MGC setups
    synced_mgc = app_con.execute("""
        SELECT orb_time, rr, sl_mode, realized_expectancy
        FROM validated_setups
        WHERE instrument = 'MGC'
        ORDER BY orb_time, rr
    """).fetchall()

    print("Verified MGC setups in APP DB:")
    for row in synced_mgc:
        orb, rr, sl, realized = row
        realized_str = f"{realized:+.3f}R" if realized else "NULL"
        status = "SURVIVES" if realized and realized >= 0.15 else ("MARGINAL" if realized and realized >= 0.05 else "FAILS" if realized else "NO DATA")
        print(f"  {orb} RR={rr} {sl}: {realized_str} [{status}]")
    print()

    print("=" * 70)
    print("SYNC COMPLETE")
    print("=" * 70)
    print()
    print("Next step: Run test_app_sync.py to verify config.py matches")
    print()

    root_con.close()
    app_con.close()


if __name__ == "__main__":
    try:
        sync_validated_setups()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
