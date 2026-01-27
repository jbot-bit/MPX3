#!/usr/bin/env python3
"""
Pre-flight proof for candidates 47-48 approval/promotion
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trading_app.cloud_mode import get_database_connection

def main():
    conn = get_database_connection(read_only=True)

    print("="*80)
    print("PRE-FLIGHT PROOF: CANDIDATES 47-48")
    print("="*80)
    print()

    # Query candidates 47-48
    print("1. EDGE_CANDIDATES STATUS:")
    print("-" * 80)
    query = """
        SELECT candidate_id, status, approved_at, approved_by, name
        FROM edge_candidates
        WHERE candidate_id IN (47, 48)
        ORDER BY candidate_id
    """

    results = conn.execute(query).fetchall()

    if len(results) != 2:
        print(f"ERROR: Expected 2 candidates, found {len(results)}")
        conn.close()
        sys.exit(1)

    for row in results:
        candidate_id, status, approved_at, approved_by, name = row
        print(f"Candidate {candidate_id}: {name}")
        print(f"  Status: {status}")
        print(f"  Approved At: {approved_at}")
        print(f"  Approved By: {approved_by}")
        print()

    # Query validated_setups for matching configs
    print("2. VALIDATED_SETUPS CHECK:")
    print("-" * 80)

    # Check for 1000 ORB configs
    query_vs = """
        SELECT setup_id, instrument, orb_time, rr, sl_mode, orb_size_filter, notes
        FROM validated_setups
        WHERE instrument = 'MGC'
        AND orb_time = '1000'
        AND rr IN (1.0, 2.0)
        ORDER BY setup_id
    """

    vs_results = conn.execute(query_vs).fetchall()

    print(f"Found {len(vs_results)} existing MGC 1000 ORB setups with RR=1.0 or 2.0:")
    if len(vs_results) == 0:
        print("  (None - ready for promotion)")
    else:
        for row in vs_results:
            setup_id, instrument, orb_time, rr, sl_mode, orb_size_filter, notes = row
            print(f"  setup_id={setup_id}: {orb_time} RR={rr} {sl_mode} (filter={orb_size_filter})")
            print(f"    Notes: {notes[:100] if notes else 'N/A'}")

    print()
    print("="*80)
    print("PRE-FLIGHT COMPLETE")
    print("="*80)

    conn.close()

if __name__ == "__main__":
    main()
