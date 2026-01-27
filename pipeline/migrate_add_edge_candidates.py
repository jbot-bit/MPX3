"""
Migration: Add edge_candidates table for Research Mode

This migration adds the edge_candidates table to support the new Research Mode lane.
Research Mode can discover and test new edges using only our data, while keeping
Trade Mode (validated_setups) locked and fail-closed.

PHASE 1: Database Schema for Edge Discovery

Run:
    python pipeline/migrate_add_edge_candidates.py

Safe to re-run (idempotent).
"""

import duckdb
from pathlib import Path
from datetime import datetime
import os
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Canonical DB path (aligned with project structure)
DB_PATH = Path(__file__).parent.parent / "data" / "db" / "gold.db"


def get_db_connection():
    """Get database connection using canonical path."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}. Run backfill first.")
    return duckdb.connect(str(DB_PATH))


def table_exists(con: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    """Check if table exists in database."""
    result = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [table_name]
    ).fetchone()
    return result[0] > 0


def create_edge_candidates_table(con: duckdb.DuckDBPyConnection) -> None:
    """
    Create edge_candidates table for Research Mode.

    This table stores proposed trading edges that are:
    - Discovered through research/analysis
    - Tested using only our database
    - NOT yet approved for live trading

    Promotion to validated_setups requires passing hard gates (Phase 3).
    """

    create_table_sql = """
    CREATE TABLE edge_candidates (
        -- Primary key
        candidate_id INTEGER PRIMARY KEY,

        -- Metadata
        created_at_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        instrument VARCHAR NOT NULL,                    -- MGC, NQ, MPL, etc.
        name VARCHAR NOT NULL,                          -- Human-readable name (e.g., "1000 ORB Tight Filter")
        hypothesis_text TEXT NOT NULL,                  -- Why this edge might work

        -- Specification (how the edge is defined)
        feature_spec_json JSON,                         -- Feature definitions, ORB params, indicators
        filter_spec_json JSON NOT NULL,                 -- Entry/stop/target rules, filters, thresholds

        -- Test window
        test_window_start DATE,                         -- Backtest start date
        test_window_end DATE,                           -- Backtest end date

        -- Performance metrics (computed by research runner)
        metrics_json JSON,                              -- Win rate, avg R, total R, n, drawdown, MAE/MFE, etc.
        robustness_json JSON,                           -- Walk-forward results, regime split results
        slippage_assumptions_json JSON,                 -- Slippage assumptions used in testing

        -- Status tracking
        status VARCHAR NOT NULL DEFAULT 'DRAFT',        -- DRAFT, TESTED, APPROVED, REJECTED
        notes TEXT,                                     -- Free-form notes, rejection reasons, etc.

        -- Constraints
        CHECK (status IN ('DRAFT', 'TESTED', 'APPROVED', 'REJECTED'))
    )
    """

    con.execute(create_table_sql)
    print(f"[OK] Created table: edge_candidates")

    # Create index on status for filtering
    con.execute("CREATE INDEX idx_edge_candidates_status ON edge_candidates(status)")
    print(f"[OK] Created index: idx_edge_candidates_status")

    # Create index on instrument for filtering
    con.execute("CREATE INDEX idx_edge_candidates_instrument ON edge_candidates(instrument)")
    print(f"[OK] Created index: idx_edge_candidates_instrument")


def insert_example_candidate(con: duckdb.DuckDBPyConnection) -> None:
    """
    Insert an example edge candidate for testing/documentation.

    This shows the expected data structure and serves as a template.
    """

    example_sql = """
    INSERT INTO edge_candidates (
        candidate_id,
        instrument,
        name,
        hypothesis_text,
        feature_spec_json,
        filter_spec_json,
        test_window_start,
        test_window_end,
        metrics_json,
        robustness_json,
        slippage_assumptions_json,
        status,
        notes
    ) VALUES (
        1,
        'MGC',
        'EXAMPLE: 1000 ORB Ultra-Tight Filter',
        'Hypothesis: 1000 ORB works better with tighter filter (<0.03×ATR) during high volatility regimes',
        '{
            "orb_time": "1000",
            "orb_duration_minutes": 5,
            "sl_mode": "FULL",
            "atr_lookback": 14,
            "regime_features": ["asia_range", "london_sweep"]
        }'::JSON,
        '{
            "orb_size_filter": 0.03,
            "min_asia_range": 5.0,
            "rr_target": 2.0,
            "entry_type": "breakout_close",
            "stop_type": "opposite_orb_edge"
        }'::JSON,
        '2024-01-01'::DATE,
        '2025-12-31'::DATE,
        '{
            "win_rate": 0.0,
            "avg_r": 0.0,
            "total_r": 0.0,
            "n_trades": 0,
            "max_drawdown_r": 0.0,
            "mae_avg": 0.0,
            "mfe_avg": 0.0
        }'::JSON,
        '{
            "walk_forward_periods": 0,
            "walk_forward_avg_r": 0.0,
            "regime_split_results": {}
        }'::JSON,
        '{
            "entry_slippage_ticks": 1,
            "exit_slippage_ticks": 1,
            "commission_per_side": 0.62
        }'::JSON,
        'DRAFT',
        'Example candidate for documentation. Metrics not yet computed.'
    )
    """

    con.execute(example_sql)
    print(f"[OK] Inserted example candidate (candidate_id=1)")


def verify_table(con: duckdb.DuckDBPyConnection) -> None:
    """Verify table structure and show example query."""

    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60)

    # Count rows
    count = con.execute("SELECT COUNT(*) FROM edge_candidates").fetchone()[0]
    print(f"\nTotal candidates: {count}")

    # Show schema
    schema = con.execute("DESCRIBE edge_candidates").fetchall()
    print(f"\nTable schema (edge_candidates):")
    for col_name, col_type, null, key, default, extra in schema:
        print(f"  {col_name:30s} {col_type:20s} {null:10s}")

    # Show example row if exists
    if count > 0:
        print(f"\nExample row:")
        example = con.execute("""
            SELECT
                candidate_id,
                instrument,
                name,
                status,
                created_at_utc
            FROM edge_candidates
            LIMIT 1
        """).fetchone()

        if example:
            print(f"  candidate_id: {example[0]}")
            print(f"  instrument: {example[1]}")
            print(f"  name: {example[2]}")
            print(f"  status: {example[3]}")
            print(f"  created_at_utc: {example[4]}")


def main():
    """Run migration to add edge_candidates table."""

    print("="*60)
    print("MIGRATION: Add edge_candidates Table (Phase 1)")
    print("="*60)
    print(f"Database: {DB_PATH}")
    print(f"Timestamp: {datetime.now()}")
    print("")

    try:
        # Connect to database
        con = get_db_connection()
        print(f"[OK] Connected to database: {DB_PATH}")

        # Check if table already exists
        if table_exists(con, "edge_candidates"):
            print(f"\n[WARN] Table 'edge_candidates' already exists. Skipping creation.")
            print(f"  (This migration is idempotent - safe to re-run)")
            verify_table(con)
            return

        print(f"\n--> Creating edge_candidates table...")

        # Create table
        create_edge_candidates_table(con)

        # Insert example for documentation
        print(f"\n--> Inserting example candidate...")
        insert_example_candidate(con)

        # Commit changes
        con.commit()
        print(f"\n[OK] Migration completed successfully")

        # Verify
        verify_table(con)

        # Close connection
        con.close()

        print("\n" + "="*60)
        print("NEXT STEPS")
        print("="*60)
        print("\nVerify table with:")
        print("  python -c \"import duckdb; con = duckdb.connect('data/db/gold.db'); \\")
        print("             print(con.execute('SELECT * FROM edge_candidates').fetchall()); \\")
        print("             con.close()\"")
        print("\nOr use check_db.py:")
        print("  python pipeline/check_db.py")
        print("\n" + "="*60)

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        raise


if __name__ == "__main__":
    main()
