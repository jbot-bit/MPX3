"""
Initialize database for app_canonical.py

Creates all required tables:
- edge_registry: Candidate edge tracking
- experiment_run: Validation lineage
- validated_setups: Production strategies
- validated_trades: Per-strategy trade results

Usage:
    python init_app_canonical_db.py
"""

import duckdb
import sys
from pathlib import Path
import os

# Force local database
os.environ['FORCE_LOCAL_DB'] = '1'

def init_database(db_path: str = "gold.db"):
    """Initialize all required tables for app_canonical.py"""

    print(f"Initializing database: {db_path}")
    print()

    conn = duckdb.connect(db_path)

    # 1. edge_registry
    print("[1/4] Creating edge_registry...")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS edge_registry (
        -- Identity
        edge_id VARCHAR PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        -- Status Lifecycle
        status VARCHAR NOT NULL DEFAULT 'NEVER_TESTED',

        -- Edge Definition
        instrument VARCHAR NOT NULL,
        session VARCHAR,
        orb_time VARCHAR NOT NULL,
        direction VARCHAR NOT NULL,

        -- Strategy Details
        trigger_definition TEXT NOT NULL,
        filters_applied JSON,
        rr DOUBLE,
        sl_mode VARCHAR,

        -- Test Configuration
        test_window VARCHAR,

        -- Outcomes
        failure_reason_code VARCHAR,
        failure_reason_text TEXT,
        pass_reason_text TEXT,

        -- Lineage
        last_tested_at TIMESTAMP,
        test_count INTEGER DEFAULT 0,
        parent_edge_id VARCHAR,

        -- Metadata
        similarity_fingerprint VARCHAR,
        notes TEXT,
        created_by VARCHAR DEFAULT 'operator'
    );
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_status ON edge_registry(status);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_instrument ON edge_registry(instrument);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_orb_time ON edge_registry(orb_time);")
    print("  OK")

    # 2. experiment_run (note: NOT edge_experiments)
    print("[2/4] Creating experiment_run...")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS experiment_run (
        run_id VARCHAR PRIMARY KEY,
        edge_id VARCHAR NOT NULL,
        run_type VARCHAR NOT NULL,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        status VARCHAR NOT NULL DEFAULT 'RUNNING',

        -- Reproducibility
        data_version_hash VARCHAR,
        generator_version VARCHAR,
        seed INTEGER,

        -- Results
        metrics JSON,
        artifacts_path VARCHAR,

        -- Links
        control_run_id VARCHAR,

        FOREIGN KEY (edge_id) REFERENCES edge_registry(edge_id)
    );
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_experiment_edge ON experiment_run(edge_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_experiment_started ON experiment_run(started_at DESC);")
    print("  OK")

    # 3. validated_setups
    print("[3/4] Creating validated_setups...")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS validated_setups (
        id INTEGER PRIMARY KEY,
        instrument VARCHAR NOT NULL,
        orb_time VARCHAR NOT NULL,
        rr DOUBLE NOT NULL,
        sl_mode VARCHAR NOT NULL,
        orb_size_filter DOUBLE,
        win_rate DOUBLE NOT NULL,
        expected_r DOUBLE NOT NULL,
        real_expected_r DOUBLE,
        sample_size INTEGER NOT NULL,
        notes VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(instrument, orb_time, rr, sl_mode)
    );
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_validated_setups_instrument ON validated_setups(instrument);")
    print("  OK")

    # 4. validated_trades
    print("[4/4] Creating validated_trades...")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS validated_trades (
        date_local DATE NOT NULL,
        setup_id INTEGER NOT NULL,

        FOREIGN KEY (setup_id) REFERENCES validated_setups(id) ON DELETE RESTRICT,

        instrument VARCHAR NOT NULL,
        orb_time VARCHAR NOT NULL,

        entry_price DOUBLE,
        stop_price DOUBLE,
        target_price DOUBLE,
        exit_price DOUBLE,

        risk_points DOUBLE,
        target_points DOUBLE,
        risk_dollars DOUBLE,

        outcome VARCHAR,
        realized_rr DOUBLE,

        mae DOUBLE,
        mfe DOUBLE,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        PRIMARY KEY (date_local, setup_id),
        CHECK (outcome IN ('WIN', 'LOSS', 'OPEN', 'NO_TRADE', 'RISK_TOO_SMALL')),
        CHECK (risk_points >= 0 OR risk_points IS NULL),
        CHECK (target_points >= 0 OR target_points IS NULL)
    );
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_validated_trades_setup ON validated_trades(setup_id, date_local);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_validated_trades_date ON validated_trades(date_local);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_validated_trades_instrument ON validated_trades(instrument);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_validated_trades_orb ON validated_trades(orb_time);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_validated_trades_outcome ON validated_trades(outcome);")
    print("  OK")

    # Verify tables exist
    print()
    print("Verifying tables...")
    tables = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='main' ORDER BY table_name").fetchall()
    table_names = [t[0] for t in tables]

    required = ['edge_registry', 'experiment_run', 'validated_setups', 'validated_trades']
    for table in required:
        if table in table_names:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  [OK] {table:25s} ({count} rows)")
        else:
            print(f"  [MISSING] {table}")

    conn.close()

    print()
    print("[SUCCESS] Database initialization complete!")
    print()
    print("Tables created:")
    print("  1. edge_registry     - Candidate edge tracking")
    print("  2. experiment_run    - Validation lineage")
    print("  3. validated_setups  - Production strategies")
    print("  4. validated_trades  - Per-strategy trade results")
    print()
    print("You can now run: streamlit run trading_app/app_canonical.py")

if __name__ == "__main__":
    init_database("gold.db")
