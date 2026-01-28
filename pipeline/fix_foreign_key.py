"""
Fix foreign key constraint to allow updates to edge_registry

The experiment_run foreign key needs ON UPDATE CASCADE to allow
status updates to edge_registry while experiment runs exist.
"""

import duckdb
import sys
import os
from pathlib import Path

# Force local database
os.environ['FORCE_LOCAL_DB'] = '1'

# Add paths
repo_root = Path(__file__).parent.parent
trading_app_dir = repo_root / "trading_app"
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(trading_app_dir))

from cloud_mode import get_database_path

def fix_foreign_key(db_path: str):
    """Fix foreign key constraint by recreating experiment_run table"""

    conn = duckdb.connect(db_path)

    # Check if experiment_run exists
    tables = conn.execute("SHOW TABLES").fetchdf()
    has_experiment_run = 'experiment_run' in tables['name'].tolist()
    has_backup = 'experiment_run_backup' in tables['name'].tolist()

    count = 0
    if has_experiment_run:
        count = conn.execute("SELECT COUNT(*) FROM experiment_run").fetchone()[0]
        print(f"Current experiment_run records: {count}")

        if count > 0:
            print("\nWARNING: experiment_run has data. Backing up first...")
            # Drop existing backup if exists
            if has_backup:
                conn.execute("DROP TABLE experiment_run_backup")
            # Create backup
            conn.execute("""
                CREATE TABLE experiment_run_backup AS
                SELECT * FROM experiment_run
            """)
            print("Backup created: experiment_run_backup")
    elif has_backup:
        # Table was already dropped, but backup exists
        count = conn.execute("SELECT COUNT(*) FROM experiment_run_backup").fetchone()[0]
        print(f"Found existing backup with {count} records")
    else:
        print("No existing experiment_run table or backup")

    # Drop and recreate without foreign key constraint
    # (DuckDB doesn't support CASCADE, and the constraint prevents updates)
    print("\nDropping experiment_run table...")
    conn.execute("DROP TABLE IF EXISTS experiment_run")

    print("Recreating WITHOUT foreign key constraint...")
    print("(Referential integrity enforced by application code)")
    conn.execute("""
    CREATE TABLE experiment_run (
        run_id VARCHAR PRIMARY KEY,
        edge_id VARCHAR NOT NULL,  -- References edge_registry(edge_id) - enforced by app
        run_type VARCHAR NOT NULL,  -- VALIDATION | STRESS_TEST | WALK_FORWARD | CONTROL
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        status VARCHAR NOT NULL DEFAULT 'RUNNING',  -- RUNNING | COMPLETED | FAILED

        -- Reproducibility
        data_version_hash VARCHAR,  -- Hash of data used
        generator_version VARCHAR,  -- Version of validation code
        seed INTEGER,  -- Random seed if applicable

        -- Results
        metrics JSON,  -- All test metrics as JSON
        artifacts_path VARCHAR,  -- Path to saved artifacts

        -- Links
        control_run_id VARCHAR  -- Link to control run (if applicable)
    );
    """)

    # Recreate indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_experiment_edge ON experiment_run(edge_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_experiment_started ON experiment_run(started_at DESC);")

    # Restore data if backup exists
    if count > 0:
        print("\nRestoring data from backup...")
        conn.execute("""
            INSERT INTO experiment_run
            SELECT * FROM experiment_run_backup
        """)
        restored = conn.execute("SELECT COUNT(*) FROM experiment_run").fetchone()[0]
        print(f"Restored {restored} records")

    conn.close()
    print("\n[OK] Foreign key constraint removed!")
    print("     experiment_run now allows edge_registry updates")
    print("     Referential integrity enforced by application code")

if __name__ == "__main__":
    db_path = get_database_path()
    print(f"Fixing foreign key constraint in: {db_path}\n")
    fix_foreign_key(db_path)
