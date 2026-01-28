"""
Delete daily_features_v2 table - it's redundant

The canonical table is daily_features (which has the v2 schema).
daily_features_v2 is a duplicate and causes confusion.

DELETE IT.
"""

import duckdb
import sys
import os
from pathlib import Path

# Add paths
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

# Force local database
os.environ['FORCE_LOCAL_DB'] = '1'

from trading_app.cloud_mode import get_database_path

def delete_v2_table():
    """Delete the redundant daily_features_v2 table"""

    db_path = get_database_path()
    conn = duckdb.connect(db_path)

    print(f"Connected to: {db_path}")
    print()

    # Check if table exists
    tables = conn.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]

    if 'daily_features_v2' in table_names:
        print("[INFO] Found daily_features_v2 table - DELETING")

        # Get row count before deletion
        count = conn.execute("SELECT COUNT(*) FROM daily_features_v2").fetchone()[0]
        print(f"  Rows: {count}")

        # DELETE IT
        conn.execute("DROP TABLE daily_features_v2")
        print("[OK] Table deleted successfully!")
    else:
        print("[INFO] daily_features_v2 table doesn't exist (already deleted)")

    # Check for other v2 variants
    v2_variants = [t for t in table_names if 'v2' in t and 'daily_features' in t]
    if v2_variants:
        print()
        print(f"[WARN] Found other v2 tables: {v2_variants}")
        print("       These should probably be renamed too")

    conn.close()
    print()
    print("[OK] Done!")

if __name__ == "__main__":
    delete_v2_table()
