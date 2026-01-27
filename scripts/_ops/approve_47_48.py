#!/usr/bin/env python3
"""
Approve candidates 47-48 in edge_candidates table
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trading_app.cloud_mode import get_database_connection

def main():
    conn = get_database_connection(read_only=False)

    print("="*80)
    print("APPROVE CANDIDATES 47-48")
    print("="*80)
    print()

    # Check current status
    print("BEFORE:")
    query_before = """
        SELECT candidate_id, status, approved_at, approved_by
        FROM edge_candidates
        WHERE candidate_id IN (47, 48)
        ORDER BY candidate_id
    """

    results = conn.execute(query_before).fetchall()
    for row in results:
        print(f"  Candidate {row[0]}: status={row[1]}, approved_at={row[2]}, approved_by={row[3]}")

    print()

    # Update status
    print("Updating status to APPROVED...")
    update_query = """
        UPDATE edge_candidates
        SET status = 'APPROVED',
            approved_at = CURRENT_TIMESTAMP,
            approved_by = 'claude_verify'
        WHERE candidate_id IN (47, 48)
    """

    conn.execute(update_query)
    conn.commit()

    print("OK Updated")
    print()

    # Check after
    print("AFTER:")
    results_after = conn.execute(query_before).fetchall()
    for row in results_after:
        print(f"  Candidate {row[0]}: status={row[1]}, approved_at={row[2]}, approved_by={row[3]}")

    print()
    print("="*80)
    print("APPROVAL COMPLETE")
    print("="*80)

    conn.close()

if __name__ == "__main__":
    main()
