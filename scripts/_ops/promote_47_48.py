#!/usr/bin/env python3
"""
Promote candidates 47-48 via edge_pipeline.py
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent / "trading_app"))

from edge_pipeline import promote_candidate_to_validated_setups
from cloud_mode import get_database_connection

def main():
    print("="*80)
    print("PROMOTE CANDIDATES 47-48 VIA EDGE_PIPELINE.PY")
    print("="*80)
    print()

    # Promote candidate 47
    print("Promoting candidate 47...")
    try:
        setup_id_47 = promote_candidate_to_validated_setups(
            candidate_id=47,
            actor="claude_approve_txt"
        )
        print(f"  SUCCESS: Created setup_id={setup_id_47}")
    except Exception as e:
        print(f"  FAILED: {e}")
        sys.exit(1)

    print()

    # Promote candidate 48
    print("Promoting candidate 48...")
    try:
        setup_id_48 = promote_candidate_to_validated_setups(
            candidate_id=48,
            actor="claude_approve_txt"
        )
        print(f"  SUCCESS: Created setup_id={setup_id_48}")
    except Exception as e:
        print(f"  FAILED: {e}")
        sys.exit(1)

    print()
    print("="*80)
    print("PROMOTION COMPLETE")
    print("="*80)
    print()

    # Verify promotion
    print("Verifying promotion in validated_setups...")
    conn = get_database_connection(read_only=True)

    query = """
        SELECT setup_id, instrument, orb_time, rr, sl_mode, win_rate, avg_r, tier
        FROM validated_setups
        WHERE setup_id IN (?, ?)
        ORDER BY setup_id
    """

    results = conn.execute(query, [setup_id_47, setup_id_48]).fetchall()

    print(f"Found {len(results)} promoted setups:")
    for row in results:
        setup_id, instrument, orb_time, rr, sl_mode, win_rate, avg_r, tier = row
        print(f"  {setup_id}: {instrument} {orb_time} RR={rr} {sl_mode} (WR={win_rate:.3f}, AvgR={avg_r:.3f}, Tier={tier})")

    print()

    if len(results) != 2:
        print(f"ERROR: Expected 2 setups, found {len(results)}")
        sys.exit(1)

    print("OK Promotion verified")

    conn.close()

if __name__ == "__main__":
    main()
