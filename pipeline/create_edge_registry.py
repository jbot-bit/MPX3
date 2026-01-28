"""
Create edge_registry table for Canonical Trading System

This is the single source of truth for all edge candidates, tests, and outcomes.
Follows canon_build.md specification.
"""

import duckdb
import sys
from pathlib import Path

# Add paths
repo_root = Path(__file__).parent.parent
trading_app_dir = repo_root / "trading_app"
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(trading_app_dir))

from cloud_mode import get_database_path

def create_edge_registry_table(db_path: str):
    """Create edge_registry table with proper schema"""

    conn = duckdb.connect(db_path)

    # Create edge_registry table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS edge_registry (
        -- Identity
        edge_id VARCHAR PRIMARY KEY,  -- Stable hash of definition (deterministic)
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        -- Status Lifecycle
        status VARCHAR NOT NULL DEFAULT 'NEVER_TESTED',  -- NEVER_TESTED | TESTED_FAILED | VALIDATED | PROMOTED | RETIRED

        -- Edge Definition (Core)
        instrument VARCHAR NOT NULL,  -- MGC, NQ, MPL
        session VARCHAR,  -- ASIA, LONDON, NY (optional)
        orb_time VARCHAR NOT NULL,  -- 0900, 1000, 1100, 1800, 2300, 0030
        direction VARCHAR NOT NULL,  -- LONG, SHORT, BOTH

        -- Strategy Details
        trigger_definition TEXT NOT NULL,  -- Human-readable trigger logic
        filters_applied JSON,  -- Normalized JSON of all filters
        rr DOUBLE,  -- Risk:Reward target
        sl_mode VARCHAR,  -- FULL, HALF

        -- Test Configuration
        test_window VARCHAR,  -- Date range or specification (e.g., "2024-01-01 to 2025-12-31")

        -- Outcomes
        failure_reason_code VARCHAR,  -- Standardized failure code
        failure_reason_text TEXT,  -- Detailed failure explanation
        pass_reason_text TEXT,  -- Why this edge passed

        -- Lineage & Tracking
        last_tested_at TIMESTAMP,
        test_count INTEGER DEFAULT 0,
        parent_edge_id VARCHAR,  -- If this is a variant of another edge

        -- Semantic Search (for future similarity checks)
        similarity_fingerprint VARCHAR,  -- Vector hash placeholder

        -- Metadata
        notes TEXT,  -- Research notes, hypothesis, inspiration
        created_by VARCHAR DEFAULT 'operator'  -- Who created this candidate
    );
    """)

    # Create indexes for performance
    conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_status ON edge_registry(status);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_instrument ON edge_registry(instrument);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_orb_time ON edge_registry(orb_time);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_created_at ON edge_registry(created_at DESC);")

    # Create experiment_run table for lineage tracking
    conn.execute("""
    CREATE TABLE IF NOT EXISTS experiment_run (
        run_id VARCHAR PRIMARY KEY,
        edge_id VARCHAR NOT NULL,
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
        control_run_id VARCHAR,  -- Link to control run (if applicable)

        FOREIGN KEY (edge_id) REFERENCES edge_registry(edge_id)
    );
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_experiment_edge ON experiment_run(edge_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_experiment_started ON experiment_run(started_at DESC);")

    conn.close()
    print("[OK] edge_registry and experiment_run tables created successfully!")

if __name__ == "__main__":
    # Force local database (avoid MotherDuck version mismatch)
    import os
    os.environ['FORCE_LOCAL_DB'] = '1'

    db_path = get_database_path()
    print(f"Creating edge_registry in: {db_path}")
    create_edge_registry_table(db_path)
    print(f"\nTables created:")
    print("  - edge_registry (candidate tracking)")
    print("  - experiment_run (lineage tracking)")
