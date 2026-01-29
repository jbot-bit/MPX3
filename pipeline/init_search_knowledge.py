#!/usr/bin/env python3
"""
Initialize search_knowledge Table

Creates the search_knowledge table for storing versioned parameter
exploration results with deterministic classification.

Usage:
    python pipeline/init_search_knowledge.py
"""

import duckdb
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "data" / "db" / "gold.db"
SCHEMA_PATH = REPO_ROOT / "pipeline" / "schema_search_knowledge.sql"


def init_search_knowledge_table():
    """Initialize search_knowledge table"""

    print("=" * 70)
    print("INITIALIZING search_knowledge TABLE")
    print("=" * 70)
    print()
    print(f"Database: {DB_PATH}")
    print(f"Schema: {SCHEMA_PATH}")
    print()

    if not DB_PATH.exists():
        print(f"[ERROR] Database not found: {DB_PATH}")
        return 1

    if not SCHEMA_PATH.exists():
        print(f"[ERROR] Schema file not found: {SCHEMA_PATH}")
        return 1

    # Read schema
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    # Connect and execute
    try:
        conn = duckdb.connect(str(DB_PATH))

        # Check if table already exists
        existing = conn.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'search_knowledge'
        """).fetchone()[0]

        if existing > 0:
            print("[INFO] Table 'search_knowledge' already exists")

            # Show row count
            count = conn.execute("SELECT COUNT(*) FROM search_knowledge").fetchone()[0]
            print(f"[INFO] Current row count: {count}")
        else:
            # Execute schema
            conn.execute(schema_sql)
            print("[OK] Table 'search_knowledge' created successfully")

        # Verify table structure
        columns = conn.execute("DESCRIBE search_knowledge").fetchall()
        print()
        print(f"Table structure ({len(columns)} columns):")
        for col in columns:
            print(f"  - {col[0]:25} {col[1]}")

        # Verify indexes
        indexes = conn.execute("""
            SELECT index_name
            FROM duckdb_indexes()
            WHERE table_name = 'search_knowledge'
        """).fetchall()

        print()
        print(f"Indexes ({len(indexes)}):")
        for idx in indexes:
            print(f"  - {idx[0]}")

        conn.close()

        print()
        print("=" * 70)
        print("[OK] search_knowledge initialization complete")
        print("=" * 70)
        print()

        return 0

    except Exception as e:
        print(f"[ERROR] Failed to initialize table: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(init_search_knowledge_table())
