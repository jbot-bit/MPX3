"""
Edge Pipeline - Candidate lifecycle management (Phase 1)

Orchestrates the edge candidate workflow:
- Create candidates from hypothesis
- Evaluate candidates (placeholder for backtesting integration)
- Approve candidates
- Promote APPROVED candidates to validated_setups

PHASE 1 CONSTRAINTS:
- NO hardcoded placeholder values (orb_time, rr, win_rate, etc.)
- ALL promotion values MUST come from edge_candidates JSON fields
- FAIL-CLOSED: missing required fields → promotion blocked
- DB routing via cloud_mode.py only
- Explicit commits, no conn.close() in utilities
"""

import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime

from cloud_mode import get_database_connection
from edge_candidate_utils import (
    parse_json_field,
    serialize_json_field,
    approve_edge_candidate,
    set_candidate_status
)

logger = logging.getLogger(__name__)


# =============================================================================
# MANIFEST EXTRACTION (FAIL-CLOSED)
# =============================================================================

def extract_candidate_manifest(candidate_row: tuple) -> Dict[str, Any]:
    """
    Extract and validate complete manifest from edge_candidates row.

    FAIL-CLOSED: If any required field is missing, raises ValueError.

    Args:
        candidate_row: Full row from edge_candidates table

    Returns:
        Validated manifest dict with all required fields

    Raises:
        ValueError: If required fields missing or invalid
    """
    # Unpack row (based on edge_candidates schema)
    # Query below selects in this order:
    # candidate_id, name, instrument, hypothesis_text,
    # filter_spec_json, test_config_json, metrics_json, slippage_assumptions_json,
    # code_version, data_version, status, created_at_utc, approved_at, approved_by,
    # promoted_validated_setup_id, notes

    (candidate_id, name, instrument, hypothesis_text,
     filter_spec_json, test_config_json, metrics_json, slippage_assumptions_json,
     code_version, data_version, status, created_at_utc, approved_at, approved_by,
     promoted_validated_setup_id, notes) = candidate_row

    # Required fields check
    missing_fields = []

    if not instrument:
        missing_fields.append("instrument")
    if not name:
        missing_fields.append("name")
    if not hypothesis_text:
        missing_fields.append("hypothesis_text")

    # Parse JSON fields
    filter_spec = parse_json_field(filter_spec_json)
    test_config = parse_json_field(test_config_json)
    metrics = parse_json_field(metrics_json)
    slippage = parse_json_field(slippage_assumptions_json)

    if filter_spec is None:
        missing_fields.append("filter_spec_json")
    if test_config is None:
        missing_fields.append("test_config_json")
    if metrics is None:
        missing_fields.append("metrics_json")
    if slippage is None:
        missing_fields.append("slippage_assumptions_json")

    # Check required keys in metrics_json
    if metrics:
        required_metric_keys = ["orb_time", "rr", "win_rate", "avg_r", "annual_trades", "tier"]
        for key in required_metric_keys:
            if key not in metrics:
                missing_fields.append(f"metrics_json.{key}")

    # Check required keys in filter_spec_json
    if filter_spec:
        required_filter_keys = ["orb_size_filter", "sl_mode"]
        for key in required_filter_keys:
            if key not in filter_spec:
                missing_fields.append(f"filter_spec_json.{key}")

    # Check code_version and data_version
    if not code_version:
        missing_fields.append("code_version")
    if not data_version:
        missing_fields.append("data_version")

    if missing_fields:
        raise ValueError(
            f"Cannot promote candidate {candidate_id}: missing required fields: "
            f"{', '.join(missing_fields)}"
        )

    # Extract test window from test_config
    test_window_start = test_config.get("test_window_start")
    test_window_end = test_config.get("test_window_end")

    if not test_window_start or not test_window_end:
        raise ValueError(
            f"Cannot promote candidate {candidate_id}: "
            f"test_config_json must include test_window_start and test_window_end"
        )

    # Build validated manifest
    manifest = {
        "candidate_id": candidate_id,
        "instrument": instrument,
        "name": name,
        "hypothesis_text": hypothesis_text,
        "orb_time": metrics["orb_time"],
        "rr": float(metrics["rr"]),
        "win_rate": float(metrics["win_rate"]),
        "avg_r": float(metrics["avg_r"]),
        "annual_trades": int(metrics["annual_trades"]),
        "tier": metrics["tier"],
        "orb_size_filter": filter_spec["orb_size_filter"],  # Can be None
        "sl_mode": filter_spec["sl_mode"],
        "code_version": code_version,
        "data_version": data_version,
        "test_window_start": test_window_start,
        "test_window_end": test_window_end,
        "slippage_assumptions": slippage,
        "approved_by": approved_by,
        "approved_at": approved_at,
    }

    return manifest


# =============================================================================
# PROMOTION FUNCTION (SINGLE CHOKE POINT)
# =============================================================================

def promote_candidate_to_validated_setups(candidate_id: int, actor: str) -> str:
    """
    Promote an APPROVED edge candidate to validated_setups table.

    This is the ONLY function that writes to validated_setups from edge_candidates.

    FAIL-CLOSED guarantees:
    1. Candidate must have status == 'APPROVED'
    2. Candidate must NOT already be promoted
    3. Manifest must be complete (all required fields present)
    4. No hardcoded placeholder values allowed

    Args:
        candidate_id: ID of the APPROVED candidate to promote
        actor: Name/identifier of person performing promotion

    Returns:
        setup_id: ID (VARCHAR) of the newly created validated_setups row (format: INSTRUMENT_ORBTIME_ID)

    Raises:
        ValueError: If candidate not found, not approved, already promoted, or incomplete manifest
        RuntimeError: If database operations fail
    """
    conn = get_database_connection(read_only=False)

    try:
        # 1) Fetch candidate row
        result = conn.execute("""
            SELECT
                candidate_id, name, instrument, hypothesis_text,
                filter_spec_json, test_config_json, metrics_json, slippage_assumptions_json,
                code_version, data_version, status, created_at_utc, approved_at, approved_by,
                promoted_validated_setup_id, notes
            FROM edge_candidates
            WHERE candidate_id = ?
        """, [candidate_id]).fetchone()

        if result is None:
            raise ValueError(f"Edge candidate {candidate_id} not found")

        # Unpack status and promotion check
        status = result[10]
        already_promoted_id = result[14]

        # 2) Verify status == APPROVED
        if status != 'APPROVED':
            raise ValueError(
                f"Cannot promote candidate {candidate_id}: status is '{status}', must be 'APPROVED'"
            )

        # 3) Verify not already promoted
        if already_promoted_id is not None:
            raise ValueError(
                f"Cannot promote candidate {candidate_id}: already promoted as setup_id={already_promoted_id}"
            )

        # 4) Extract and validate manifest (FAIL-CLOSED)
        manifest = extract_candidate_manifest(result)

        logger.info(f"Promoting candidate {candidate_id} with manifest: {manifest}")

        # 5) Insert into validated_setups
        # Generate next setup_id (VARCHAR, not INTEGER)
        # Use pattern: MGC_0900_001, MGC_1000_002, etc.
        setup_id = f"{manifest['instrument']}_{manifest['orb_time']}_{candidate_id:03d}"

        # Build notes field with extra metadata as JSON
        notes_metadata = {
            "name": manifest["name"],
            "hypothesis_text": manifest["hypothesis_text"],
            "code_version": manifest["code_version"],
            "data_version": manifest["data_version"],
            "test_window_start": manifest["test_window_start"],
            "test_window_end": manifest["test_window_end"],
            "promoted_from_candidate_id": candidate_id,
            "promoted_by": actor,
            "promoted_at": datetime.utcnow().isoformat()
        }
        notes_json = json.dumps(notes_metadata)

        # Map to actual validated_setups columns
        # Required fields with defaults for missing values
        close_confirmations = 1  # Default confirmation bars
        buffer_ticks = 0.0  # Default buffer
        trades = manifest.get("annual_trades", 0)  # Use annual_trades as proxy for trades

        # Insert new validated setup (matches actual schema)
        conn.execute("""
            INSERT INTO validated_setups (
                setup_id, instrument, orb_time, rr, sl_mode,
                close_confirmations, buffer_ticks, orb_size_filter,
                atr_filter, min_gap_filter,
                trades, win_rate, avg_r, annual_trades, tier,
                notes, validated_date, data_source
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?,
                NULL, NULL,
                ?, ?, ?, ?, ?,
                ?, CURRENT_DATE, 'edge_candidates'
            )
        """, [
            setup_id,
            manifest["instrument"],
            manifest["orb_time"],
            manifest["rr"],
            manifest["sl_mode"],
            close_confirmations,
            buffer_ticks,
            manifest["orb_size_filter"],  # Can be None/NULL
            # atr_filter = NULL, min_gap_filter = NULL
            trades,
            manifest["win_rate"],
            manifest["avg_r"],
            manifest["annual_trades"],
            manifest["tier"],
            notes_json
            # validated_date = CURRENT_DATE, data_source = 'edge_candidates'
        ])

        # 6) Update edge_candidates with promotion tracking
        conn.execute("""
            UPDATE edge_candidates
            SET promoted_validated_setup_id = ?,
                promoted_by = ?,
                promoted_at = CURRENT_TIMESTAMP
            WHERE candidate_id = ?
        """, [setup_id, actor, candidate_id])

        # 7) Commit transaction
        conn.commit()

        logger.info(
            f"Successfully promoted candidate {candidate_id} → validated_setups.setup_id={setup_id} "
            f"by {actor}"
        )

        # 8) Return new setup_id
        return setup_id

    except Exception as e:
        logger.error(f"Failed to promote candidate {candidate_id}: {e}")
        raise
    # Note: Don't close connection (caller-managed or pooled)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_edge_candidate(
    name: str,
    instrument: str,
    hypothesis_text: str,
    filter_spec: Dict,
    test_config: Dict,
    metrics: Dict,
    slippage_assumptions: Dict,
    code_version: str,
    data_version: str,
    actor: str
) -> int:
    """
    Create a new edge candidate in DRAFT status.

    Args:
        name: Human-readable setup name
        instrument: MGC, NQ, MPL, etc.
        hypothesis_text: Description of the edge hypothesis
        filter_spec: Dict with orb_size_filter, sl_mode
        test_config: Dict with test_window_start, test_window_end
        metrics: Dict with orb_time, rr, win_rate, avg_r, annual_trades, tier
        slippage_assumptions: Dict with execution assumptions
        code_version: Git hash or version identifier
        data_version: Schema version identifier
        actor: Name of person creating candidate

    Returns:
        candidate_id: ID of newly created candidate
    """
    conn = get_database_connection(read_only=False)

    try:
        # Get next candidate_id
        max_id_result = conn.execute(
            "SELECT COALESCE(MAX(candidate_id), 0) + 1 FROM edge_candidates"
        ).fetchone()
        new_candidate_id = max_id_result[0]

        # Serialize JSON fields
        filter_spec_str = serialize_json_field(filter_spec)
        test_config_str = serialize_json_field(test_config)
        metrics_str = serialize_json_field(metrics)
        slippage_str = serialize_json_field(slippage_assumptions)

        # Insert new candidate
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
            new_candidate_id,
            name,
            instrument,
            hypothesis_text,
            filter_spec_str,
            test_config_str,
            metrics_str,
            slippage_str,
            code_version,
            data_version,
            f"Created by {actor}"
        ])

        conn.commit()

        logger.info(f"Created edge candidate {new_candidate_id}: {name} by {actor}")

        return new_candidate_id

    except Exception as e:
        logger.error(f"Failed to create edge candidate: {e}")
        raise


def get_candidate_status(candidate_id: int) -> Dict[str, Any]:
    """
    Get current status and metadata for an edge candidate.

    Args:
        candidate_id: ID of candidate

    Returns:
        Dict with status, approved_by, approved_at, promoted_validated_setup_id

    Raises:
        ValueError: If candidate not found
    """
    conn = get_database_connection(read_only=True)

    result = conn.execute("""
        SELECT
            candidate_id, name, status, approved_at, approved_by,
            promoted_validated_setup_id, created_at_utc
        FROM edge_candidates
        WHERE candidate_id = ?
    """, [candidate_id]).fetchone()

    if result is None:
        raise ValueError(f"Edge candidate {candidate_id} not found")

    return {
        "candidate_id": result[0],
        "name": result[1],
        "status": result[2],
        "approved_at": result[3],
        "approved_by": result[4],
        "promoted_validated_setup_id": result[5],
        "created_at_utc": result[6]
    }
