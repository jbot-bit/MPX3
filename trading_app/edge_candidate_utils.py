"""
Utility functions for edge_candidates table.

Handles JSON field serialization/deserialization robustly.
Works with both DuckDB JSON type and string representations.
"""

import json
from typing import Any, Dict, Optional


def parse_json_field(value: Any) -> Optional[Dict]:
    """
    Parse a JSON field from DuckDB, handling both JSON and string types.

    Args:
        value: Value from DuckDB (could be JSON, string, or None)

    Returns:
        Parsed dict or None
    """
    if value is None:
        return None

    # If already a dict, return it
    if isinstance(value, dict):
        return value

    # If string, parse it
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            # If it's not valid JSON, return None
            return None

    # Unknown type, return None
    return None


def serialize_json_field(value: Optional[Dict]) -> Optional[str]:
    """
    Serialize a dict to JSON string for DuckDB storage.

    Args:
        value: Dict to serialize (or None)

    Returns:
        JSON string or None
    """
    if value is None:
        return None

    if not isinstance(value, dict):
        raise TypeError(f"Expected dict, got {type(value)}")

    return json.dumps(value)


def safe_json_cast(value: Optional[Dict]) -> str:
    """
    Create a safe JSON cast for DuckDB SQL insertion.

    Args:
        value: Dict to serialize

    Returns:
        SQL fragment with JSON casting
    """
    if value is None:
        return "NULL"

    json_str = json.dumps(value)
    # Escape single quotes for SQL
    json_str_escaped = json_str.replace("'", "''")
    return f"'{json_str_escaped}'::JSON"


# Example usage:
#
# Reading from DuckDB:
# -----------------
# result = con.execute("SELECT test_config_json FROM edge_candidates WHERE candidate_id=1").fetchone()
# test_config = parse_json_field(result[0])  # Returns dict or None
#
# if test_config:
#     random_seed = test_config.get("random_seed")
#     walk_forward = test_config.get("walk_forward_windows")
#
#
# Writing to DuckDB:
# -----------------
# test_config = {
#     "random_seed": 42,
#     "walk_forward_windows": 4,
#     "train_pct": 0.7
# }
#
# # Method 1: Using parameterized query with JSON string
# config_json_str = serialize_json_field(test_config)
# con.execute("""
#     UPDATE edge_candidates
#     SET test_config_json = ?::JSON
#     WHERE candidate_id = ?
# """, [config_json_str, candidate_id])
#
# # Method 2: Using safe_json_cast (for dynamic SQL)
# con.execute(f"""
#     UPDATE edge_candidates
#     SET test_config_json = {safe_json_cast(test_config)}
#     WHERE candidate_id = {candidate_id}
# """)


# =============================================================================
# EDGE CANDIDATE APPROVAL FUNCTIONS (Write Operations)
# =============================================================================

def approve_edge_candidate(candidate_id: int, approver: str) -> None:
    """
    Approve an edge candidate by setting status='APPROVED', approved_at, and approved_by.

    This function uses a write-capable database connection to update the edge_candidates table.

    Args:
        candidate_id: ID of the candidate to approve
        approver: Name/identifier of the person approving (e.g., "Josh")

    Raises:
        ValueError: If candidate doesn't exist, is already approved, or other validation errors
        RuntimeError: If database update fails
    """
    from cloud_mode import get_database_connection
    import logging

    logger = logging.getLogger(__name__)

    # Get write-capable connection
    conn = get_database_connection(read_only=False)

    try:
        # Check if candidate exists
        result = conn.execute(
            "SELECT candidate_id, status FROM edge_candidates WHERE candidate_id = ?",
            [candidate_id]
        ).fetchone()

        if result is None:
            raise ValueError(f"Edge candidate {candidate_id} not found")

        current_status = result[1]

        # Check if already approved
        if current_status == 'APPROVED':
            logger.warning(f"Candidate {candidate_id} is already APPROVED")
            raise ValueError(f"Candidate {candidate_id} is already APPROVED")

        # Update to APPROVED status
        conn.execute("""
            UPDATE edge_candidates
            SET
                status = 'APPROVED',
                approved_at = CURRENT_TIMESTAMP,
                approved_by = ?
            WHERE candidate_id = ?
        """, [approver, candidate_id])

        conn.commit()
        logger.info(f"Edge candidate {candidate_id} approved by {approver}")

    except Exception as e:
        logger.error(f"Failed to approve candidate {candidate_id}: {e}")
        raise
    # Note: Don't close connection - it may be managed by caller or connection pool


def set_candidate_status(
    candidate_id: int,
    status: str,
    notes: Optional[str] = None,
    actor: Optional[str] = None
) -> None:
    """
    Set the status of an edge candidate.

    Reusable status setter for DRAFT/PENDING/APPROVED/REJECTED transitions.
    For APPROVED status, sets approved_at and approved_by fields.

    Args:
        candidate_id: ID of the candidate
        status: New status (DRAFT, PENDING, APPROVED, REJECTED)
        notes: Optional notes to append to existing notes
        actor: Name/identifier of person making the change

    Raises:
        ValueError: If candidate doesn't exist or invalid status
        RuntimeError: If database update fails
    """
    from cloud_mode import get_database_connection
    import logging

    logger = logging.getLogger(__name__)

    # Validate status
    valid_statuses = ['DRAFT', 'PENDING', 'APPROVED', 'REJECTED']
    if status not in valid_statuses:
        raise ValueError(f"Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}")

    # Get write-capable connection
    conn = get_database_connection(read_only=False)

    try:
        # Check if candidate exists
        result = conn.execute(
            "SELECT candidate_id, notes FROM edge_candidates WHERE candidate_id = ?",
            [candidate_id]
        ).fetchone()

        if result is None:
            raise ValueError(f"Edge candidate {candidate_id} not found")

        existing_notes = result[1] or ""

        # Build updated notes
        if notes:
            updated_notes = f"{existing_notes}\n[{actor or 'unknown'}] {notes}".strip()
        else:
            updated_notes = existing_notes

        # Update status (and approval fields if APPROVED)
        if status == 'APPROVED':
            if not actor:
                raise ValueError("actor parameter required when setting status to APPROVED")

            conn.execute("""
                UPDATE edge_candidates
                SET
                    status = ?,
                    approved_at = CURRENT_TIMESTAMP,
                    approved_by = ?,
                    notes = ?
                WHERE candidate_id = ?
            """, [status, actor, updated_notes, candidate_id])

            logger.info(f"Edge candidate {candidate_id} status set to APPROVED by {actor}")
        else:
            # For other statuses, just update status and notes
            conn.execute("""
                UPDATE edge_candidates
                SET
                    status = ?,
                    notes = ?
                WHERE candidate_id = ?
            """, [status, updated_notes, candidate_id])

            logger.info(f"Edge candidate {candidate_id} status set to {status}" + (f" by {actor}" if actor else ""))

        conn.commit()

    except Exception as e:
        logger.error(f"Failed to set candidate {candidate_id} status to {status}: {e}")
        raise
    # Note: Don't close connection - it may be managed by caller or connection pool
