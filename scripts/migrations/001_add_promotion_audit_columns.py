#!/usr/bin/env python3
"""
Migration: Add promotion audit columns to edge_candidates

Run this ONCE manually:
    python scripts/migrations/001_add_promotion_audit_columns.py

DO NOT run automatically on startup.

NOTES:
- Audit trail for validated_setups is stored in notes field as JSON
- This migration only adds tracking columns to edge_candidates
"""

import sys
from pathlib import Path

# Add trading_app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "trading_app"))

from cloud_mode import get_database_connection


def main():
    """Run migration."""
    print("=" * 70)
    print("Migration: Add promotion audit columns to edge_candidates")
    print("=" * 70)
    print()

    conn = get_database_connection(read_only=False)

    try:
        print("1. Adding columns to edge_candidates...")

        # Add promoted_by column
        try:
            conn.execute("ALTER TABLE edge_candidates ADD COLUMN promoted_by VARCHAR")
            print("   [OK] Added promoted_by VARCHAR")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("   - promoted_by already exists (skipped)")
            else:
                raise

        # Add promoted_at column
        try:
            conn.execute("ALTER TABLE edge_candidates ADD COLUMN promoted_at TIMESTAMP")
            print("   [OK] Added promoted_at TIMESTAMP")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                print("   - promoted_at already exists (skipped)")
            else:
                raise

        conn.commit()
        print()
        print("=" * 70)
        print("[OK] Migration completed successfully")
        print("=" * 70)
        print()
        print("Notes:")
        print("  - promoted_by/promoted_at added to edge_candidates")
        print("  - Audit trail for validated_setups stored in notes field as JSON")
        print("  - No changes needed to validated_setups schema")
        print()
        print("Verify changes:")
        print("  python -c \"from trading_app.cloud_mode import get_database_connection; con=get_database_connection(); print(con.execute('PRAGMA table_info(edge_candidates)').fetchall()); con.close()\"")

    except Exception as e:
        print()
        print(f"[ERROR] Migration failed: {e}")
        print()
        print("Rolling back...")
        # DuckDB doesn't support nested transactions, so we can't rollback ALTER TABLE
        print("Note: ALTER TABLE operations cannot be rolled back in DuckDB.")
        print("Manual cleanup may be required if partial migration occurred.")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
