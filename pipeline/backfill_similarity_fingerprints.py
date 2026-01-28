"""
Backfill similarity_fingerprint column for existing edges in edge_registry

This is a one-time migration to add semantic similarity support to existing edges.
"""

import duckdb
import sys
import os
from pathlib import Path

# Add paths
repo_root = Path(__file__).parent.parent
trading_app_dir = repo_root / "trading_app"
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(trading_app_dir))

# Force local database
os.environ['FORCE_LOCAL_DB'] = '1'

from cloud_mode import get_database_path
from edge_utils import generate_similarity_fingerprint
import json

def backfill_fingerprints():
    """Backfill similarity fingerprints for all edges"""

    db_path = get_database_path()
    conn = duckdb.connect(db_path)

    print(f"Connected to: {db_path}")

    # Get all edges
    edges = conn.execute("""
        SELECT edge_id, instrument, orb_time, direction,
               trigger_definition, filters_applied, rr, sl_mode
        FROM edge_registry
        WHERE similarity_fingerprint IS NULL
    """).fetchall()

    if not edges:
        print("[OK] All edges already have fingerprints!")
        conn.close()
        return

    print(f"[INFO] Found {len(edges)} edge(s) without fingerprints")

    updated = 0
    for edge in edges:
        edge_id, instrument, orb_time, direction, trigger, filters_json, rr, sl_mode = edge

        # Parse filters
        filters_applied = {}
        if filters_json:
            if isinstance(filters_json, str):
                filters_applied = json.loads(filters_json)
            else:
                filters_applied = filters_json

        # Generate fingerprint
        fingerprint = generate_similarity_fingerprint(
            instrument=instrument,
            orb_time=orb_time,
            direction=direction,
            trigger_definition=trigger,
            filters_applied=filters_applied,
            rr=rr,
            sl_mode=sl_mode
        )

        # Update database
        conn.execute("""
            UPDATE edge_registry
            SET similarity_fingerprint = ?
            WHERE edge_id = ?
        """, [fingerprint, edge_id])

        updated += 1
        print(f"  {updated}/{len(edges)} - {edge_id[:16]}... -> {fingerprint[:50]}...")

    conn.close()

    print(f"\n[OK] Backfilled {updated} edge(s) successfully!")

if __name__ == "__main__":
    backfill_fingerprints()
