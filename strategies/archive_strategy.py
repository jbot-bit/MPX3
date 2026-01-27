#!/usr/bin/env python3
"""
Automatic Strategy Archiving Script

Archives existing strategies from validated_setups to validated_setups_archive
before updating them. Maintains audit trail and version history.

Usage:
    python strategies/archive_strategy.py --setup-id 123 --reason "Updated RR target"
    python strategies/archive_strategy.py --setup-id 123 --reason "Stress test results" --new-params "RR=2.0"
"""

import argparse
import duckdb
import sys
from datetime import datetime
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent / "gold.db"


def archive_strategy(setup_id: int, reason: str, new_params: str = None):
    """
    Archive a strategy from validated_setups to validated_setups_archive.

    Args:
        setup_id: ID of setup to archive
        reason: Reason for archiving
        new_params: Optional description of new parameters
    """
    conn = duckdb.connect(str(DB_PATH))

    try:
        # Step 1: Check if setup exists
        result = conn.execute(
            "SELECT * FROM validated_setups WHERE id = ?",
            [setup_id]
        ).fetchone()

        if not result:
            print(f"❌ ERROR: Setup ID {setup_id} not found in validated_setups")
            return False

        # Extract current setup data
        cols = [desc[0] for desc in conn.execute("SELECT * FROM validated_setups LIMIT 1").description]
        setup_data = dict(zip(cols, result))

        print(f"\n📋 Found setup to archive:")
        print(f"   ID: {setup_data['id']}")
        print(f"   Instrument: {setup_data['instrument']}")
        print(f"   ORB time: {setup_data['orb_time']}")
        print(f"   RR: {setup_data['rr']}")
        print(f"   Filter: {setup_data['orb_size_filter']}")
        print(f"   Win rate: {setup_data['win_rate']}%")
        print(f"   Expected R: {setup_data['expected_r']}")
        print()

        # Step 2: Get version tag (check if already archived versions exist)
        version_count = conn.execute(
            "SELECT COUNT(*) FROM validated_setups_archive WHERE id = ?",
            [setup_id]
        ).fetchone()[0]

        version_tag = f"v1.{version_count}" if version_count > 0 else "v1.0"

        # Step 3: Archive to validated_setups_archive
        conn.execute("""
            INSERT INTO validated_setups_archive (
                id, instrument, orb_time, rr, sl_mode, orb_size_filter,
                win_rate, expected_r, sample_size, notes,
                archived_at, archived_reason, version_tag
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            setup_data['id'],
            setup_data['instrument'],
            setup_data['orb_time'],
            setup_data['rr'],
            setup_data['sl_mode'],
            setup_data['orb_size_filter'],
            setup_data['win_rate'],
            setup_data['expected_r'],
            setup_data['sample_size'],
            setup_data['notes'],
            datetime.now().isoformat(),
            reason,
            version_tag
        ])

        print(f"✅ Archived setup {setup_id} to validated_setups_archive")
        print(f"   Version: {version_tag}")
        print(f"   Reason: {reason}")
        if new_params:
            print(f"   New params: {new_params}")
        print()
        print("⚠️  NEXT STEPS:")
        print("   1. Update the strategy in validated_setups")
        print("   2. Run: python test_app_sync.py")
        print("   3. Update trading_app/config.py if needed")
        print()

        return True

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

    finally:
        conn.close()


def list_archived_versions(setup_id: int):
    """List all archived versions of a setup."""
    conn = duckdb.connect(str(DB_PATH))

    try:
        results = conn.execute("""
            SELECT version_tag, archived_at, archived_reason, rr, orb_size_filter
            FROM validated_setups_archive
            WHERE id = ?
            ORDER BY archived_at DESC
        """, [setup_id]).fetchall()

        if not results:
            print(f"No archived versions found for setup {setup_id}")
            return

        print(f"\n📚 Archived versions for setup {setup_id}:")
        for row in results:
            version, archived_at, reason, rr, filter_val = row
            print(f"\n   {version} (archived {archived_at})")
            print(f"   RR: {rr}, Filter: {filter_val}")
            print(f"   Reason: {reason}")
        print()

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Archive strategies before updating validated_setups"
    )
    parser.add_argument(
        "--setup-id",
        type=int,
        required=True,
        help="ID of setup to archive"
    )
    parser.add_argument(
        "--reason",
        type=str,
        help="Reason for archiving"
    )
    parser.add_argument(
        "--new-params",
        type=str,
        help="Description of new parameters (optional)"
    )
    parser.add_argument(
        "--list-versions",
        action="store_true",
        help="List archived versions for this setup"
    )

    args = parser.parse_args()

    if args.list_versions:
        list_archived_versions(args.setup_id)
        return

    if not args.reason:
        print("❌ ERROR: --reason is required")
        sys.exit(1)

    success = archive_strategy(args.setup_id, args.reason, args.new_params)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
