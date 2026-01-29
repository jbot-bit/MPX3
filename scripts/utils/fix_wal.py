#!/usr/bin/env python3
"""
Fix DuckDB WAL corruption by checkpointing and closing properly
"""

import duckdb
from pathlib import Path

db_path = Path(__file__).parent.parent.parent / "data" / "db" / "gold.db"

print(f"Fixing WAL for: {db_path}")

try:
    # Connect and checkpoint
    conn = duckdb.connect(str(db_path))
    conn.execute("CHECKPOINT")
    conn.close()
    print("✅ WAL checkpointed successfully")
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nTrying recovery...")

    # Delete WAL file (DuckDB will recreate it)
    wal_path = Path(str(db_path) + ".wal")
    if wal_path.exists():
        wal_path.unlink()
        print(f"✅ Deleted corrupted WAL: {wal_path}")

        # Try connecting again
        try:
            conn = duckdb.connect(str(db_path))
            conn.execute("CHECKPOINT")
            conn.close()
            print("✅ Database recovered")
        except Exception as e2:
            print(f"❌ Recovery failed: {e2}")
    else:
        print(f"⚠️ WAL file not found: {wal_path}")
