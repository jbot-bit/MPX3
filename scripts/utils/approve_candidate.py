#!/usr/bin/env python3
"""
Approve Edge Candidate - Manual approval script

Usage:
    python approve_candidate.py <candidate_id> [approver_name]

Examples:
    python approve_candidate.py 1 Josh
    python approve_candidate.py 5
"""

import sys
from pathlib import Path

# Add trading_app to path
sys.path.insert(0, str(Path(__file__).parent / "trading_app"))

from trading_app.edge_candidate_utils import approve_edge_candidate, set_candidate_status


def main():
    """Main entry point for approval script."""

    # Parse command line arguments
    if len(sys.argv) < 2:
        print("ERROR: candidate_id required")
        print()
        print("Usage:")
        print("  python approve_candidate.py <candidate_id> [approver_name]")
        print()
        print("Examples:")
        print("  python approve_candidate.py 1 Josh")
        print("  python approve_candidate.py 5")
        sys.exit(1)

    try:
        candidate_id = int(sys.argv[1])
    except ValueError:
        print(f"ERROR: candidate_id must be an integer, got: {sys.argv[1]}")
        sys.exit(1)

    # Get approver name (default to "Josh")
    approver = sys.argv[2] if len(sys.argv) > 2 else "Josh"

    # Approve the candidate
    print(f"Approving edge candidate {candidate_id} (approver: {approver})...")

    try:
        approve_edge_candidate(candidate_id, approver)
        print(f"✓ SUCCESS: Edge candidate {candidate_id} approved by {approver}")
        print()
        print("The candidate status is now APPROVED and can be used in recommendations.")

    except ValueError as e:
        print(f"✗ ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
