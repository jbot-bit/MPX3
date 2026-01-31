"""
PB (Pullback) Family Grid Generator

Generates deterministic parameter combinations for PB family strategies:
- entry_token: RETEST_ORB, MID_PULLBACK
- confirm_token: CLOSE_CONFIRM, WICK_REJECT
- stop_token: STOP_ORB_OPP, STOP_SWING
- tp_token: TP_FIXED_R_1_0, TP_FIXED_R_1_5, TP_FIXED_R_2_0

Grid size: 3 ORBs × 2 directions × 2 entry × 2 confirm × 2 stop × 3 tp = 144 candidates

Usage:
    from pb_grid_generator import generate_pb_batch

    results = generate_pb_batch(actor='user')
    print(f"Generated {results['inserted']} candidates, skipped {results['skipped']} duplicates")
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from trading_app.time_spec import ORBS
from trading_app.edge_utils import generate_strategy_name, generate_edge_id
from trading_app.edge_pipeline import create_edge_candidate
from cloud_mode import get_database_connection

logger = logging.getLogger(__name__)


# =============================================================================
# PB FAMILY TOKEN DEFINITIONS
# =============================================================================

PB_ENTRY_TOKENS = [
    'RETEST_ORB',      # Retest of ORB high/low after break
    'MID_PULLBACK'     # Pullback to ORB mid
]

PB_CONFIRM_TOKENS = [
    'CLOSE_CONFIRM',   # Bar closes back in direction after touch
    'WICK_REJECT'      # Wick rejection at level
]

PB_STOP_TOKENS = [
    'STOP_ORB_OPP',    # Stop at opposite side of ORB
    'STOP_SWING'       # Stop at last swing
]

PB_TP_TOKENS = [
    'TP_FIXED_R_1_0',  # 1.0R target
    'TP_FIXED_R_1_5',  # 1.5R target
    'TP_FIXED_R_2_0'   # 2.0R target
]

# ORB subset for PB family (daytime ORBs only)
# Filter to first 3 ORBs from canonical list (0900, 1000, 1100)
PB_ORB_TIMES = ORBS[:3] if len(ORBS) >= 3 else ORBS

PB_DIRECTIONS = ['LONG', 'SHORT']


# =============================================================================
# GRID GENERATION
# =============================================================================

def generate_pb_grid(instrument: str = 'MGC') -> List[Dict[str, Any]]:
    """
    Generate all 144 PB parameter combinations.

    Args:
        instrument: MGC, NQ, MPL (default MGC)

    Returns:
        List of 144 parameter dictionaries
    """
    combinations = []

    for orb_time in PB_ORB_TIMES:
        for direction in PB_DIRECTIONS:
            for entry_token in PB_ENTRY_TOKENS:
                for confirm_token in PB_CONFIRM_TOKENS:
                    for stop_token in PB_STOP_TOKENS:
                        for tp_token in PB_TP_TOKENS:
                            combo = {
                                'instrument': instrument,
                                'orb_time': orb_time,
                                'direction': direction,
                                'entry_token': entry_token,
                                'confirm_token': confirm_token,
                                'stop_token': stop_token,
                                'tp_token': tp_token
                            }
                            combinations.append(combo)

    logger.info(f"Generated {len(combinations)} PB parameter combinations")
    return combinations


# =============================================================================
# CANDIDATE CREATION (WITH DEDUPLICATION)
# =============================================================================

def _candidate_exists(edge_id: str, db_connection) -> bool:
    """
    Check if candidate with given edge_id already exists in edge_candidates.

    Uses spec-hash stored in notes field for deduplication.
    NO SCHEMA CHANGES - uses existing notes VARCHAR field.

    Args:
        edge_id: Deterministic hash of parameters
        db_connection: DuckDB connection

    Returns:
        True if exists, False otherwise
    """
    # Query edge_candidates for matching spec-hash in notes
    # Format: "spec_hash:{edge_id}" in notes field
    result = db_connection.execute("""
        SELECT candidate_id
        FROM edge_candidates
        WHERE notes LIKE ?
        LIMIT 1
    """, [f"%spec_hash:{edge_id}%"]).fetchone()

    return result is not None


def create_pb_candidate(combo: Dict[str, Any], actor: str, db_connection=None) -> Optional[int]:
    """
    Create a single PB candidate in edge_candidates table.

    Includes deduplication check via edge_id hash.

    Args:
        combo: Parameter combination dict
        actor: Name of person/system creating candidate
        db_connection: Optional existing DuckDB connection to reuse

    Returns:
        candidate_id if created, None if skipped (duplicate)
    """
    # Generate deterministic name
    name = generate_strategy_name(
        instrument=combo['instrument'],
        orb_time=combo['orb_time'],
        direction=combo['direction'],
        entry_rule=combo['entry_token'],
        sl_mode=combo['stop_token'],
        version=1,
        family='PB'
    )

    # Build trigger definition for edge_id hash
    trigger_definition = (
        f"PB: {combo['entry_token']} entry, "
        f"{combo['confirm_token']} confirmation, "
        f"{combo['stop_token']} stop, "
        f"{combo['tp_token']} target"
    )

    # Build filters dict for hash
    filters_applied = {
        'entry_token': combo['entry_token'],
        'confirm_token': combo['confirm_token'],
        'stop_token': combo['stop_token'],
        'tp_token': combo['tp_token']
    }

    # Extract RR from tp_token
    rr_map = {
        'TP_FIXED_R_1_0': 1.0,
        'TP_FIXED_R_1_5': 1.5,
        'TP_FIXED_R_2_0': 2.0
    }
    rr = rr_map[combo['tp_token']]

    # Generate edge_id for deduplication
    edge_id = generate_edge_id(
        instrument=combo['instrument'],
        orb_time=combo['orb_time'],
        direction=combo['direction'],
        trigger_definition=trigger_definition,
        filters_applied=filters_applied,
        rr=rr,
        sl_mode=combo['stop_token']
    )

    # Check if already exists
    if _candidate_exists(edge_id, db_connection):
        logger.info(f"Skipping duplicate: {name}")
        return None

    # Build hypothesis text
    hypothesis_text = (
        f"PB Family: {combo['entry_token']} entry, {combo['confirm_token']} confirmation, "
        f"{combo['stop_token']} stop, {combo['tp_token']} target. "
        f"Grid-generated candidate for {combo['instrument']} {combo['orb_time']} ORB."
    )

    # Append spec_hash to notes for deduplication (NO SCHEMA CHANGE - uses existing notes field)
    notes_with_hash = f"spec_hash:{edge_id}\n{hypothesis_text}"

    # Build filter_spec (store PB tokens here)
    filter_spec = {
        'entry_token': combo['entry_token'],
        'confirm_token': combo['confirm_token'],
        'stop_token': combo['stop_token'],
        'tp_token': combo['tp_token'],
        'sl_mode': combo['stop_token'],  # Map to existing field
        'orb_size_filter': None  # No size filter for base grid
    }

    # Build test_config (placeholder - will be filled during backtesting)
    test_config = {
        'test_window_start': None,
        'test_window_end': None,
        'backtest_pending': True
    }

    # Build metrics (placeholder - will be filled during backtesting)
    metrics = {
        'orb_time': combo['orb_time'],
        'rr': rr,
        'win_rate': None,
        'avg_r': None,
        'annual_trades': None,
        'tier': 'UNTESTED'
    }

    # Build slippage assumptions (standard MGC assumptions)
    slippage_assumptions = {
        'commission': 2.40,
        'spread': 2.00,
        'slippage': 4.00,
        'total_rt_cost': 8.40
    }

    # Create candidate
    try:
        candidate_id = create_edge_candidate(
            name=name,
            instrument=combo['instrument'],
            hypothesis_text=hypothesis_text,
            filter_spec=filter_spec,
            test_config=test_config,
            metrics=metrics,
            slippage_assumptions=slippage_assumptions,
            code_version='UPDATE22',
            data_version='v1',
            actor=actor,
            db_connection=db_connection,
            notes=notes_with_hash  # Include spec_hash for dedupe
        )

        logger.info(f"Created candidate {candidate_id}: {name}")
        return candidate_id

    except Exception as e:
        logger.error(f"Failed to create candidate {name}: {e}")
        return None


# =============================================================================
# BATCH GENERATION
# =============================================================================

def generate_pb_batch(
    instrument: str = 'MGC',
    actor: str = 'pb_grid_generator',
    db_connection = None  # Required for app runtime to prevent connection conflicts
) -> Dict[str, Any]:
    """
    Generate full PB grid and insert into edge_candidates.

    Args:
        instrument: MGC, NQ, MPL (default MGC)
        actor: Name of person/system generating batch
        db_connection: Optional existing DuckDB connection to reuse (prevents connection conflicts)

    Returns:
        Dict with results:
            - total: Total combinations generated
            - inserted: Number of candidates created
            - skipped: Number of duplicates skipped
            - candidate_ids: List of created candidate IDs
    """
    # Require connection in app runtime (fail-closed to prevent connection conflicts)
    if db_connection is None:
        raise ValueError(
            "db_connection is required for app runtime. "
            "Pass app_state.db_connection to prevent connection conflicts."
        )

    logger.info(f"Starting PB grid generation for {instrument}")
    start_time = datetime.now()

    # Generate grid
    combinations = generate_pb_grid(instrument=instrument)

    # Create candidates
    inserted = 0
    skipped = 0
    candidate_ids = []

    for combo in combinations:
        candidate_id = create_pb_candidate(combo, actor=actor, db_connection=db_connection)

        if candidate_id is not None:
            inserted += 1
            candidate_ids.append(candidate_id)
        else:
            skipped += 1

    elapsed = (datetime.now() - start_time).total_seconds()

    results = {
        'total': len(combinations),
        'inserted': inserted,
        'skipped': skipped,
        'candidate_ids': candidate_ids,
        'elapsed_seconds': elapsed
    }

    logger.info(
        f"PB grid generation complete: {inserted} inserted, {skipped} skipped, "
        f"{elapsed:.1f}s elapsed"
    )

    return results
