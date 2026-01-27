#!/usr/bin/env python3
"""
Import Research Candidates to Production Staging

Imports candidates from research export JSON into production edge_candidates table.

Usage:
    python trading_app/edge_import.py --input research/candidates_export.json

Workflow:
    1. research/export_to_production.py → candidates_export.json
    2. trading_app/edge_import.py → edge_candidates table (DRAFT status)
    3. Manual review in edge_candidates_ui.py
    4. Approve candidates (APPROVED status)
    5. Promote via UI button → validated_setups
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

from cloud_mode import get_database_connection


def import_candidates_from_json(input_path: str, actor: str = "EDE_Import"):
    """
    Import candidates from JSON file into production edge_candidates table.

    Args:
        input_path: Path to JSON export file
        actor: Name/identifier of person performing import

    Returns:
        Number of candidates imported
    """
    conn = get_database_connection(read_only=False)

    try:
        print("=" * 70)
        print("Import Research Candidates to Production")
        print("=" * 70)
        print()

        # Load JSON file
        input_file = Path(input_path)
        if not input_file.exists():
            print(f"[ERROR] File not found: {input_file}")
            print()
            print("Run export first:")
            print("  python research/export_to_production.py --output research/candidates_export.json")
            return 0

        with open(input_file, 'r') as f:
            candidates = json.load(f)

        print(f"Loaded {len(candidates)} candidates from {input_file}")
        print()

        if len(candidates) == 0:
            print("No candidates to import.")
            return 0

        # Get max candidate_id
        max_id_result = conn.execute(
            "SELECT COALESCE(MAX(candidate_id), 0) FROM edge_candidates"
        ).fetchone()
        next_id = max_id_result[0] + 1

        imported_count = 0
        skipped_count = 0

        for idx, candidate in enumerate(candidates):
            # Check if already imported (by research_id in notes)
            existing = conn.execute("""
                SELECT candidate_id FROM edge_candidates
                WHERE notes LIKE ?
            """, [f"%research_id:{candidate['research_id']}%"]).fetchone()

            if existing:
                print(f"  [{idx+1}] Skipping {candidate['name']} (already imported as candidate_id={existing[0]})")
                skipped_count += 1
                continue

            # Prepare JSON fields
            filter_spec_json = json.dumps(candidate["filter_spec"])
            test_config_json = json.dumps(candidate["test_config"])
            metrics_json = json.dumps(candidate["metrics"])
            slippage_json = json.dumps(candidate["slippage_assumptions"])

            # Build notes with research metadata
            notes = (
                f"Imported from EDE research system | "
                f"research_id:{candidate['research_id']} | "
                f"survival_score:{candidate.get('survival_score', 'N/A')} | "
                f"confidence:{candidate.get('confidence_level', 'N/A')} | "
                f"imported_by:{actor}"
            )

            # Insert into edge_candidates
            conn.execute("""
                INSERT INTO edge_candidates (
                    candidate_id, name, instrument, hypothesis_text,
                    filter_spec_json, test_config_json, metrics_json, slippage_assumptions_json,
                    code_version, data_version, status, notes
                ) VALUES (
                    ?, ?, ?, ?,
                    ?::JSON, ?::JSON, ?::JSON, ?::JSON,
                    ?, ?, 'DRAFT', ?
                )
            """, [
                next_id,
                candidate["name"],
                candidate["instrument"],
                candidate["hypothesis_text"],
                filter_spec_json,
                test_config_json,
                metrics_json,
                slippage_json,
                candidate["code_version"],
                candidate["data_version"],
                notes
            ])

            print(f"  [{idx+1}] Imported {candidate['name']} as candidate_id={next_id} (DRAFT)")

            next_id += 1
            imported_count += 1

        conn.commit()

        print()
        print("=" * 70)
        print(f"[OK] Import completed")
        print("=" * 70)
        print()
        print(f"Imported: {imported_count}")
        print(f"Skipped (duplicates): {skipped_count}")
        print()
        print("Next steps:")
        print("  1. Review candidates in edge_candidates_ui.py")
        print("  2. Approve candidates (sets status = APPROVED)")
        print("  3. Promote via Promote button in UI → validated_setups")
        print("  4. Run python test_app_sync.py to verify sync")
        print()

        return imported_count

    finally:
        conn.close()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Import research candidates into production edge_candidates table"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input JSON file path (from export_to_production.py)"
    )
    parser.add_argument(
        "--actor",
        default="EDE_Import",
        help="Name/identifier of person performing import (default: EDE_Import)"
    )

    args = parser.parse_args()

    import_candidates_from_json(
        input_path=args.input,
        actor=args.actor
    )


if __name__ == "__main__":
    main()
