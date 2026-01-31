"""
Mark Duplicate Candidates as REJECTED (Non-Destructive)

Uses existing write path: set_candidate_status()
NO DELETES, NO SCHEMA CHANGES
"""

import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from trading_app.cloud_mode import get_database_connection
from trading_app.edge_candidate_utils import set_candidate_status
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_duplicates():
    """
    Find duplicate candidates by spec_hash in notes field

    Returns:
        List of (candidate_id, spec_hash) tuples for duplicates (keep first, mark rest)
    """
    conn = get_database_connection(read_only=True)

    # Find candidates with spec_hash in notes
    result = conn.execute("""
        SELECT
            candidate_id,
            created_at_utc,
            REGEXP_EXTRACT(notes, 'spec_hash:([a-f0-9]+)', 1) as spec_hash
        FROM edge_candidates
        WHERE notes LIKE '%spec_hash:%'
        ORDER BY spec_hash, created_at_utc
    """).fetchdf()

    conn.close()

    if result.empty:
        return []

    # Group by spec_hash, mark all but first as duplicates
    duplicates_to_mark = []

    for spec_hash in result['spec_hash'].unique():
        group = result[result['spec_hash'] == spec_hash]

        if len(group) > 1:
            # Keep first (oldest), mark rest as duplicates
            first_id = group.iloc[0]['candidate_id']
            duplicate_ids = group.iloc[1:]['candidate_id'].tolist()

            logger.info(f"spec_hash {spec_hash[:8]}... has {len(duplicate_ids)} duplicates")
            logger.info(f"  Keeping: candidate_id={first_id}")
            logger.info(f"  Marking as duplicates: {duplicate_ids}")

            for dup_id in duplicate_ids:
                duplicates_to_mark.append((dup_id, spec_hash))

    return duplicates_to_mark


def mark_duplicates(duplicates_to_mark):
    """
    Mark duplicates as REJECTED using existing write path

    Args:
        duplicates_to_mark: List of (candidate_id, spec_hash) tuples
    """
    for candidate_id, spec_hash in duplicates_to_mark:
        try:
            set_candidate_status(
                candidate_id=candidate_id,
                status='REJECTED',
                notes=f"Duplicate of spec_hash:{spec_hash[:16]}... (auto-marked)",
                actor='dedupe_script'
            )
            logger.info(f"✓ Marked candidate {candidate_id} as REJECTED (duplicate)")
        except Exception as e:
            logger.error(f"✗ Failed to mark candidate {candidate_id}: {e}")


def main():
    """Mark all duplicate candidates as REJECTED"""

    logger.info("="*60)
    logger.info("DUPLICATE MARKING SCRIPT (Non-Destructive)")
    logger.info("="*60)

    # Find duplicates
    logger.info("\n1. Finding duplicates...")
    duplicates_to_mark = find_duplicates()

    if not duplicates_to_mark:
        logger.info("✓ No duplicates found")
        return

    logger.info(f"\nFound {len(duplicates_to_mark)} duplicates to mark")

    # Confirm before marking
    response = input(f"\nMark {len(duplicates_to_mark)} duplicates as REJECTED? (yes/no): ")

    if response.lower() != 'yes':
        logger.info("Aborted by user")
        return

    # Mark duplicates (uses existing write path)
    logger.info("\n2. Marking duplicates...")
    mark_duplicates(duplicates_to_mark)

    logger.info("\n" + "="*60)
    logger.info("COMPLETE")
    logger.info("="*60)
    logger.info(f"Marked {len(duplicates_to_mark)} duplicates as REJECTED")
    logger.info("Duplicates are now hidden from default filters (status=REJECTED)")
    logger.info("Original data preserved - no deletions performed")


if __name__ == "__main__":
    main()
