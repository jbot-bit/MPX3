#!/usr/bin/env python3
"""
Remove old MGC 1000 RR=8.0 setup to resolve conflict with new promoted setups
Keep only the newly promoted candidates 47-48 (RR=1.0 FULL and RR=2.0 HALF)
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trading_app.cloud_mode import get_database_connection

def main():
    conn = get_database_connection(read_only=False)

    print("="*80)
    print("REMOVE OLD MGC 1000 SETUP TO RESOLVE CONFLICT")
    print("="*80)
    print()

    # Show current MGC 1000 setups
    query = """
        SELECT setup_id, instrument, orb_time, rr, sl_mode, win_rate, avg_r, tier
        FROM validated_setups
        WHERE instrument = 'MGC' AND orb_time = '1000'
        ORDER BY setup_id
    """

    results = conn.execute(query).fetchall()
    print(f"Current MGC 1000 setups ({len(results)} total):")
    print("-"*80)
    for row in results:
        setup_id, instrument, orb_time, rr, sl_mode, win_rate, avg_r, tier = row
        print(f"  {setup_id}: RR={rr} {sl_mode} WR={win_rate:.3f} AvgR={avg_r:.3f} Tier={tier}")
    print()

    # Remove the old setup
    old_setup_id = "MGC_1000_RR8.0_FULL_C1_B0.0_NOFILTER"

    print(f"Removing old setup: {old_setup_id}")
    print("Reason: System doesn't support multiple setups per ORB time")
    print("Keeping: MGC_1000_047 (RR=1.0 FULL) and MGC_1000_048 (RR=2.0 HALF)")
    print()

    delete_query = """
        DELETE FROM validated_setups
        WHERE setup_id = ?
    """

    result = conn.execute(delete_query, [old_setup_id])
    conn.commit()

    print(f"OK Removed {old_setup_id}")
    print()

    # Verify removal
    results = conn.execute(query).fetchall()
    print(f"MGC 1000 setups after removal ({len(results)} total):")
    print("-"*80)
    for row in results:
        setup_id, instrument, orb_time, rr, sl_mode, win_rate, avg_r, tier = row
        print(f"  {setup_id}: RR={rr} {sl_mode} WR={win_rate:.3f} AvgR={avg_r:.3f} Tier={tier}")
    print()

    if len(results) == 2:
        print("="*80)
        print("SUCCESS: Now have exactly 2 MGC 1000 setups (candidates 47-48)")
        print("="*80)
    else:
        print(f"ERROR: Expected 2 setups, found {len(results)}")
        conn.close()
        sys.exit(1)

    conn.close()

if __name__ == "__main__":
    main()
