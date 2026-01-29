#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create Auto Search Tables Migration

Creates 4 tables for automated edge discovery system:
- search_runs: Track each auto-search execution
- search_candidates: Promising candidates found by search
- search_memory: Deduplication hash registry (prevents repeat searches)
- validation_queue: Manual promotion queue (ingress to validation workflow)

Idempotent: Safe to re-run (uses CREATE TABLE IF NOT EXISTS)

Usage:
    python scripts/migrations/create_auto_search_tables.py
"""

import sys
import os
import duckdb
from pathlib import Path
from datetime import datetime

def create_auto_search_tables(db_path: str = "data/db/gold.db"):
    """Create auto search tables (idempotent)"""

    conn = duckdb.connect(db_path)

    print("="*80)
    print("AUTO SEARCH TABLES MIGRATION")
    print("="*80)
    print(f"Database: {db_path}")
    print()

    # ========================================================================
    # TABLE 1: search_runs
    # ========================================================================
    print("Creating search_runs table...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS search_runs (
            run_id VARCHAR PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            instrument VARCHAR NOT NULL,
            settings_json JSON,
            status VARCHAR DEFAULT 'RUNNING',
            duration_seconds DOUBLE,
            candidates_found INTEGER DEFAULT 0,
            candidates_skipped INTEGER DEFAULT 0,
            total_tested INTEGER DEFAULT 0,
            error_message VARCHAR
        )
    """)
    print("  [OK] search_runs created")

    # ========================================================================
    # TABLE 2: search_candidates
    # ========================================================================
    print("Creating search_candidates table...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS search_candidates (
            id INTEGER PRIMARY KEY,
            run_id VARCHAR NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            instrument VARCHAR NOT NULL,
            setup_family VARCHAR,
            orb_time VARCHAR NOT NULL,
            rr_target DOUBLE NOT NULL,
            filters_json JSON,
            param_hash VARCHAR NOT NULL,
            score_proxy DOUBLE,
            sample_size INTEGER,
            win_rate_proxy DOUBLE,
            expected_r_proxy DOUBLE,
            notes TEXT,
            profitable_trade_rate DOUBLE,
            target_hit_rate DOUBLE
            -- Note: FK constraint removed (DuckDB limitations)
            -- Application enforces run_id referential integrity
        )
    """)
    print("  [OK] search_candidates created")

    # ========================================================================
    # TABLE 3: search_memory
    # ========================================================================
    print("Creating search_memory table...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS search_memory (
            memory_id INTEGER PRIMARY KEY,
            param_hash VARCHAR UNIQUE NOT NULL,
            instrument VARCHAR NOT NULL,
            setup_family VARCHAR,
            filters_json JSON,
            first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            test_count INTEGER DEFAULT 1,
            best_score DOUBLE,
            notes TEXT
        )
    """)
    print("  [OK] search_memory created")

    # ========================================================================
    # TABLE 4: validation_queue
    # ========================================================================
    print("Creating validation_queue table...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS validation_queue (
            queue_id INTEGER PRIMARY KEY,
            enqueued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source VARCHAR NOT NULL,
            source_id VARCHAR,
            instrument VARCHAR NOT NULL,
            setup_family VARCHAR,
            orb_time VARCHAR NOT NULL,
            rr_target DOUBLE NOT NULL,
            filters_json JSON,
            score_proxy DOUBLE,
            sample_size INTEGER,
            status VARCHAR DEFAULT 'PENDING',
            assigned_to VARCHAR,
            notes TEXT
        )
    """)
    print("  [OK] validation_queue created")

    # ========================================================================
    # CREATE INDEXES
    # ========================================================================
    print()
    print("Creating indexes...")

    # search_runs indexes
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_search_runs_instrument
        ON search_runs(instrument)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_search_runs_status
        ON search_runs(status)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_search_runs_created
        ON search_runs(created_at)
    """)

    # search_candidates indexes
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_search_candidates_run
        ON search_candidates(run_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_search_candidates_hash
        ON search_candidates(param_hash)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_search_candidates_score
        ON search_candidates(score_proxy DESC)
    """)

    # search_memory indexes
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_search_memory_hash
        ON search_memory(param_hash)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_search_memory_instrument
        ON search_memory(instrument)
    """)

    # validation_queue indexes
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_validation_queue_status
        ON validation_queue(status)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_validation_queue_instrument
        ON validation_queue(instrument)
    """)

    print("  [OK] All indexes created")

    conn.close()

    print()
    print("="*80)
    print("MIGRATION COMPLETE")
    print("="*80)

    # ========================================================================
    # VERIFICATION
    # ========================================================================
    print()
    print("Running verification queries...")
    print()

    verify_conn = duckdb.connect(db_path, read_only=True)

    # Check tables exist
    tables = verify_conn.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]

    required_tables = ['search_runs', 'search_candidates', 'search_memory', 'validation_queue']

    for table in required_tables:
        if table in table_names:
            # Get row count
            count = verify_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            # Get column count
            schema = verify_conn.execute(f"DESCRIBE {table}").fetchall()
            col_count = len(schema)
            print(f"[OK] {table}: EXISTS ({col_count} columns, {count} rows)")
        else:
            print(f"[MISSING] {table}: MISSING")

    verify_conn.close()

    print()
    print("="*80)
    print("SUCCESS: Auto search tables ready")
    print("="*80)
    print()
    print("Next steps:")
    print("  1. Create trading_app/auto_search_engine.py")
    print("  2. Add UI panel to trading_app/app_canonical.py")
    print("  3. Test with: python scripts/check/check_auto_search_tables.py")
    print()

    return True


def main():
    # Change to project root
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)

    print()
    success = create_auto_search_tables()
    print()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
