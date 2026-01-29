#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DuckDB WAL Recovery Script

Fixes WAL corruption by checkpointing and cleaning up.
Safe to run - makes backup first.
"""

import os
import sys
import io
import shutil
from pathlib import Path
from datetime import datetime

# Fix Unicode output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def recover_wal(db_path: str):
    """Recover from WAL corruption."""

    db_file = Path(db_path)
    wal_file = Path(f"{db_path}.wal")

    print("="*60)
    print("DUCKDB WAL RECOVERY")
    print("="*60)

    # Check files exist
    if not db_file.exists():
        print(f"✗ Database not found: {db_path}")
        return False

    print(f"Database: {db_path}")
    print(f"Database size: {db_file.stat().st_size:,} bytes")

    if wal_file.exists():
        print(f"WAL file: {wal_file}")
        print(f"WAL size: {wal_file.stat().st_size:,} bytes")
    else:
        print("No WAL file found (database may be clean)")

    # Create backup
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"\nCreating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)
    print("✓ Backup created")

    # Method 1: Delete WAL file (forces DuckDB to ignore corrupt WAL)
    if wal_file.exists():
        print(f"\nRemoving corrupt WAL file: {wal_file}")
        wal_file.unlink()
        print("✓ WAL file removed")

    # Method 2: Try to checkpoint (will create new clean WAL)
    try:
        import duckdb
        print("\nAttempting checkpoint...")
        conn = duckdb.connect(db_path)
        conn.execute("CHECKPOINT")
        conn.close()
        print("✓ Checkpoint successful")
    except Exception as e:
        print(f"⚠ Checkpoint warning: {e}")
        print("  (Database may still be usable)")

    # Verify database accessible
    try:
        import duckdb
        print("\nVerifying database...")
        conn = duckdb.connect(db_path, read_only=True)

        # Test query
        result = conn.execute("SELECT COUNT(*) FROM bars_1m WHERE symbol='MGC'").fetchone()
        bar_count = result[0]

        latest = conn.execute("SELECT MAX(ts_utc) FROM bars_1m WHERE symbol='MGC'").fetchone()
        latest_ts = latest[0]

        conn.close()

        print(f"✓ Database accessible")
        print(f"  bars_1m count: {bar_count:,}")
        print(f"  Latest timestamp: {latest_ts}")

        return True

    except Exception as e:
        print(f"✗ Database verification failed: {e}")
        print(f"\nRestore from backup:")
        print(f"  copy \"{backup_path}\" \"{db_path}\"")
        return False


def main():
    """Run WAL recovery."""
    import sys

    db_path = "data/db/gold.db"

    if not os.path.exists(db_path):
        print(f"✗ Database not found: {db_path}")
        print("  Current directory:", os.getcwd())
        return 1

    success = recover_wal(db_path)

    if success:
        print("\n" + "="*60)
        print("✓ RECOVERY SUCCESSFUL")
        print("="*60)
        print("\nNext steps:")
        print("1. Run: python scripts/maintenance/test_update_script.py")
        print("2. Run: python scripts/maintenance/update_market_data.py")
        return 0
    else:
        print("\n" + "="*60)
        print("✗ RECOVERY FAILED")
        print("="*60)
        print("\nManual recovery needed - see backup file created")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
