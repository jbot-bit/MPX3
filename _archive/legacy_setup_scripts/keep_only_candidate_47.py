#!/usr/bin/env python3
"""
Keep only candidate 47 (RR=1.0 FULL, WR=52.9%) for MGC 1000 ORB
Remove candidate 48 to have exactly ONE setup per ORB time
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trading_app.cloud_mode import get_database_connection

def main():
    conn = get_database_connection(read_only=False)

    print("="*80)
    print("KEEP ONLY CANDIDATE 47 FOR MGC 1000 ORB")
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

    # Remove candidate 48
    print("Decision: Keep candidate 47 (RR=1.0 FULL, WR=52.9% - HIGHER WIN RATE)")
    print("         Remove candidate 48 (RR=2.0 HALF, WR=35.4%)")
    print("Reason: System requires exactly ONE setup per ORB time")
    print()

    delete_query = """
        DELETE FROM validated_setups
        WHERE setup_id = ?
    """

    result = conn.execute(delete_query, ["MGC_1000_048"])
    conn.commit()

    print("OK Removed MGC_1000_048")
    print()

    # Verify removal
    results = conn.execute(query).fetchall()
    print(f"MGC 1000 setups after removal ({len(results)} total):")
    print("-"*80)
    for row in results:
        setup_id, instrument, orb_time, rr, sl_mode, win_rate, avg_r, tier = row
        print(f"  {setup_id}: RR={rr} {sl_mode} WR={win_rate:.3f} AvgR={avg_r:.3f} Tier={tier}")
    print()

    if len(results) == 1:
        print("="*80)
        print("SUCCESS: Now have exactly 1 MGC 1000 setup (candidate 47)")
        print("="*80)
    else:
        print(f"ERROR: Expected 1 setup, found {len(results)}")
        conn.close()
        sys.exit(1)

    conn.close()

if __name__ == "__main__":
    main()
