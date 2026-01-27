"""
Migration: Add reproducibility fields to edge_candidates

Adds version tracking fields to ensure edge candidates can be reproduced:
- code_version: Git commit hash or version tag when candidate was tested
- data_version: Data snapshot identifier (e.g., "2026-01-19" or hash)
- test_config_json: Full test configuration (random seeds, parameters, etc.)

This is a SAFE migration using ALTER TABLE ADD COLUMN.

Run:
    python pipeline/migrate_add_reproducibility_fields.py

Safe to re-run (idempotent).
"""

import duckdb
from pathlib import Path
from datetime import datetime
import sys

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Canonical DB path
DB_PATH = Path(__file__).parent.parent / "data" / "db" / "gold.db"


def get_db_connection():
    """Get database connection using canonical path."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}. Run backfill first.")
    return duckdb.connect(str(DB_PATH))


def column_exists(con: duckdb.DuckDBPyConnection, table_name: str, column_name: str) -> bool:
    """Check if column exists in table."""
    result = con.execute("""
        SELECT COUNT(*)
        FROM information_schema.columns
        WHERE table_name = ?
          AND column_name = ?
    """, [table_name, column_name]).fetchone()
    return result[0] > 0


def add_reproducibility_fields(con: duckdb.DuckDBPyConnection) -> None:
    """
    Add reproducibility fields to edge_candidates table.

    Fields added:
    - code_version: Git commit hash or version tag
    - data_version: Data snapshot identifier
    - test_config_json: Full test configuration
    """

    fields_added = []

    # Field 1: code_version
    if not column_exists(con, "edge_candidates", "code_version"):
        con.execute("""
            ALTER TABLE edge_candidates
            ADD COLUMN code_version VARCHAR
        """)
        print(f"[OK] Added column: code_version")
        fields_added.append("code_version")
    else:
        print(f"[SKIP] Column 'code_version' already exists")

    # Field 2: data_version
    if not column_exists(con, "edge_candidates", "data_version"):
        con.execute("""
            ALTER TABLE edge_candidates
            ADD COLUMN data_version VARCHAR
        """)
        print(f"[OK] Added column: data_version")
        fields_added.append("data_version")
    else:
        print(f"[SKIP] Column 'data_version' already exists")

    # Field 3: test_config_json
    if not column_exists(con, "edge_candidates", "test_config_json"):
        con.execute("""
            ALTER TABLE edge_candidates
            ADD COLUMN test_config_json JSON
        """)
        print(f"[OK] Added column: test_config_json")
        fields_added.append("test_config_json")
    else:
        print(f"[SKIP] Column 'test_config_json' already exists")

    return fields_added


def update_example_candidate(con: duckdb.DuckDBPyConnection) -> None:
    """
    Update example candidate with reproducibility fields.

    Sets sensible example values for documentation.
    """

    # Check if example candidate exists
    result = con.execute("SELECT COUNT(*) FROM edge_candidates WHERE candidate_id = 1").fetchone()
    if result[0] == 0:
        print(f"[SKIP] Example candidate (id=1) not found, skipping update")
        return

    # Check if fields are already populated
    result = con.execute("""
        SELECT code_version
        FROM edge_candidates
        WHERE candidate_id = 1
    """).fetchone()

    if result[0] is not None:
        print(f"[SKIP] Example candidate already has reproducibility fields populated")
        return

    # Update with example values
    con.execute("""
        UPDATE edge_candidates
        SET
            code_version = 'v1.0.0-alpha',
            data_version = '2026-01-19',
            test_config_json = '{
                "random_seed": 42,
                "walk_forward_windows": 4,
                "train_pct": 0.7,
                "regime_detection": "volatility_quartiles",
                "slippage_ticks": 1,
                "commission_per_side": 0.62
            }'::JSON
        WHERE candidate_id = 1
    """)

    print(f"[OK] Updated example candidate with reproducibility fields")


def verify_migration(con: duckdb.DuckDBPyConnection) -> None:
    """Verify migration and show updated schema."""

    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60)

    # Show schema
    schema = con.execute("DESCRIBE edge_candidates").fetchall()
    print(f"\nUpdated schema (edge_candidates):")
    print(f"{'Column':<35s} {'Type':<20s} {'Nullable':<10s}")
    print("-" * 65)
    for col_name, col_type, null, key, default, extra in schema:
        print(f"{col_name:<35s} {col_type:<20s} {null:<10s}")

    # Count columns
    total_cols = len(schema)
    print(f"\nTotal columns: {total_cols} (expected: 17)")

    # Check reproducibility fields exist
    repro_fields = ["code_version", "data_version", "test_config_json"]
    print(f"\nReproducibility fields:")
    for field in repro_fields:
        exists = any(col[0] == field for col in schema)
        status = "[OK]" if exists else "[MISSING]"
        print(f"  {status} {field}")

    # Show example candidate if exists
    result = con.execute("SELECT COUNT(*) FROM edge_candidates WHERE candidate_id = 1").fetchone()
    if result[0] > 0:
        print(f"\nExample candidate reproducibility fields:")
        example = con.execute("""
            SELECT
                code_version,
                data_version,
                test_config_json
            FROM edge_candidates
            WHERE candidate_id = 1
        """).fetchone()

        print(f"  code_version: {example[0]}")
        print(f"  data_version: {example[1]}")
        print(f"  test_config_json: {example[2][:100] if example[2] else None}...")


def main():
    """Run migration to add reproducibility fields."""

    print("="*60)
    print("MIGRATION: Add Reproducibility Fields")
    print("="*60)
    print(f"Database: {DB_PATH}")
    print(f"Timestamp: {datetime.now()}")
    print("")

    try:
        # Connect to database
        con = get_db_connection()
        print(f"[OK] Connected to database: {DB_PATH}")

        # Check if table exists
        result = con.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = 'edge_candidates'
        """).fetchone()

        if result[0] == 0:
            print(f"\n[ERROR] Table 'edge_candidates' does not exist.")
            print(f"        Run migrate_add_edge_candidates.py first.")
            return

        print(f"\n--> Adding reproducibility fields...")

        # Add columns
        fields_added = add_reproducibility_fields(con)

        if fields_added:
            print(f"\n--> Updating example candidate...")
            update_example_candidate(con)

            # Commit changes
            con.commit()
            print(f"\n[OK] Migration completed successfully")
            print(f"     Fields added: {', '.join(fields_added)}")
        else:
            print(f"\n[OK] No changes needed - all fields already exist")

        # Verify
        verify_migration(con)

        # Close connection
        con.close()

        print("\n" + "="*60)
        print("NEXT STEPS")
        print("="*60)
        print("\nVerify new columns:")
        print("  python -c \"import duckdb; \\")
        print("             con = duckdb.connect('data/db/gold.db'); \\")
        print("             schema = con.execute('DESCRIBE edge_candidates').fetchall(); \\")
        print("             [print(s[0]) for s in schema]; \\")
        print("             con.close()\"")
        print("\nCheck example candidate:")
        print("  python -c \"import duckdb; \\")
        print("             con = duckdb.connect('data/db/gold.db'); \\")
        print("             result = con.execute('SELECT code_version, data_version FROM edge_candidates WHERE candidate_id=1').fetchone(); \\")
        print("             print(f'code_version: {result[0]}, data_version: {result[1]}'); \\")
        print("             con.close()\"")
        print("\n" + "="*60)

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        raise


if __name__ == "__main__":
    main()
