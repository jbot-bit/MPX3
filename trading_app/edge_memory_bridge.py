"""
Edge Memory Bridge - Connects edge discovery to trading memory

SIMPLE integration between:
- edge_candidates → learned_patterns (validated edges become learned patterns)
- edge testing → session_state (track what was tested)
- edge promotion → trade_journal (log validation decisions)

NO COMPLEXITY. Just save findings so you never lose them again.
"""

import json
from datetime import datetime, date
from typing import Dict, Optional, List
import logging

from cloud_mode import get_database_connection

logger = logging.getLogger(__name__)


def log_edge_test(
    candidate_id: int,
    instrument: str,
    orb_time: str,
    test_result: Dict,
    notes: str = ""
) -> None:
    """
    Log that you tested an edge. Simple breadcrumb trail.

    Args:
        candidate_id: Edge candidate ID from edge_candidates
        instrument: MGC, MPL, NQ
        orb_time: '0900', '1000', etc.
        test_result: Dict with win_rate, expected_r, sample_size
        notes: What you discovered
    """
    try:
        conn = get_database_connection()

        # Update session_state with what was tested today
        today = date.today()

        # Get existing notable_conditions or create new
        existing = conn.execute("""
            SELECT notable_conditions FROM session_state
            WHERE date_local = ? AND instrument = ?
        """, [today, instrument]).fetchone()

        if existing and existing[0]:
            conditions = existing[0]
        else:
            conditions = ""

        # Append test note
        test_note = f"[{datetime.now().strftime('%H:%M')}] Tested {orb_time} ORB (candidate_{candidate_id}): WR={test_result.get('win_rate', 0):.1%}, ExpR={test_result.get('expected_r', 0):.3f}, N={test_result.get('sample_size', 0)}"
        if notes:
            test_note += f" - {notes}"

        new_conditions = f"{conditions}\n{test_note}".strip()

        # Upsert session_state
        conn.execute("""
            INSERT INTO session_state (date_local, instrument, notable_conditions, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (date_local, instrument)
            DO UPDATE SET
                notable_conditions = ?,
                updated_at = CURRENT_TIMESTAMP
        """, [today, instrument, new_conditions, new_conditions])

        conn.commit()
        conn.close()

        logger.info(f"Logged edge test: candidate_{candidate_id} for {instrument} {orb_time}")

    except Exception as e:
        logger.error(f"Failed to log edge test: {e}")


def promote_to_learned_pattern(
    candidate_id: int,
    candidate_data: Dict
) -> Optional[str]:
    """
    When an edge is validated, save it as a learned pattern.

    This is your permanent memory of "what works".

    Args:
        candidate_id: Edge candidate ID
        candidate_data: Full candidate data from edge_candidates

    Returns:
        pattern_id if successful, None otherwise
    """
    try:
        conn = get_database_connection()

        # Extract key info
        instrument = candidate_data.get('instrument', 'UNKNOWN')
        name = candidate_data.get('name', f'Candidate {candidate_id}')
        hypothesis = candidate_data.get('hypothesis_text', '')

        metrics = candidate_data.get('metrics_json', {})
        if isinstance(metrics, str):
            metrics = json.loads(metrics)

        win_rate = metrics.get('win_rate', 0)
        avg_rr = metrics.get('avg_r', 0)
        total_r = metrics.get('total_r', 0)
        sample_size = metrics.get('n_trades', 0)

        filter_spec = candidate_data.get('filter_spec_json', {})
        if isinstance(filter_spec, str):
            filter_spec = json.loads(filter_spec)

        # Generate pattern_id
        orb_time = filter_spec.get('orb_time', 'UNKNOWN')
        pattern_id = f"{instrument}_{orb_time}_candidate_{candidate_id}"

        # Build description
        description = f"{name}: {hypothesis}"

        # Build condition SQL (simplified - just the key filter)
        orb_size_filter = filter_spec.get('orb_size_filter')
        if orb_size_filter:
            condition_sql = f"orb_{orb_time}_size BETWEEN {orb_size_filter * 0.5} AND {orb_size_filter * 1.5}"
        else:
            condition_sql = f"orb_{orb_time}_outcome IS NOT NULL"

        # Determine confidence
        if sample_size >= 50 and win_rate >= 0.60:
            confidence = 0.8
        elif sample_size >= 30 and win_rate >= 0.55:
            confidence = 0.6
        else:
            confidence = 0.4

        # Insert into learned_patterns
        conn.execute("""
            INSERT INTO learned_patterns (
                pattern_id, description, hypothesis, condition_sql,
                instruments, confidence, sample_size, win_rate, avg_rr, total_r,
                discovered_date, last_validated, status,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (pattern_id) DO UPDATE SET
                confidence = ?,
                sample_size = ?,
                win_rate = ?,
                avg_rr = ?,
                total_r = ?,
                last_validated = ?,
                updated_at = CURRENT_TIMESTAMP
        """, [
            pattern_id, description, hypothesis, condition_sql,
            instrument, confidence, sample_size, win_rate, avg_rr, total_r,
            date.today(), date.today(),
            confidence, sample_size, win_rate, avg_rr, total_r, date.today()
        ])

        conn.commit()
        conn.close()

        logger.info(f"Promoted candidate_{candidate_id} to learned_pattern: {pattern_id}")
        return pattern_id

    except Exception as e:
        logger.error(f"Failed to promote to learned pattern: {e}")
        return None


def query_similar_patterns(
    instrument: str,
    orb_time: str,
    min_confidence: float = 0.5
) -> List[Dict]:
    """
    Find similar patterns you've already discovered.

    Prevents re-testing the same thing twice.

    Args:
        instrument: MGC, MPL, NQ
        orb_time: '0900', '1000', etc.
        min_confidence: Minimum confidence threshold

    Returns:
        List of similar learned patterns
    """
    try:
        conn = get_database_connection(read_only=True)

        results = conn.execute("""
            SELECT
                pattern_id, description, hypothesis,
                confidence, sample_size, win_rate, avg_rr,
                discovered_date, last_validated, status
            FROM learned_patterns
            WHERE instruments = ?
              AND pattern_id LIKE ?
              AND confidence >= ?
              AND status = 'ACTIVE'
            ORDER BY confidence DESC, last_validated DESC
        """, [instrument, f"%{orb_time}%", min_confidence]).fetchall()

        conn.close()

        patterns = []
        for row in results:
            patterns.append({
                'pattern_id': row[0],
                'description': row[1],
                'hypothesis': row[2],
                'confidence': row[3],
                'sample_size': row[4],
                'win_rate': row[5],
                'avg_rr': row[6],
                'discovered_date': row[7],
                'last_validated': row[8],
                'status': row[9]
            })

        return patterns

    except Exception as e:
        logger.error(f"Failed to query similar patterns: {e}")
        return []


def get_testing_history(days: int = 30) -> List[Dict]:
    """
    Show what you've tested recently.

    Helps you see progress and avoid repeating work.

    Args:
        days: How many days back to look

    Returns:
        List of recent test sessions
    """
    try:
        conn = get_database_connection(read_only=True)

        cutoff = date.today().replace(day=1)  # Start of current month (simplified)

        results = conn.execute("""
            SELECT date_local, instrument, notable_conditions, updated_at
            FROM session_state
            WHERE date_local >= ?
              AND notable_conditions IS NOT NULL
              AND notable_conditions != ''
            ORDER BY date_local DESC
        """, [cutoff]).fetchall()

        conn.close()

        history = []
        for row in results:
            history.append({
                'date': row[0],
                'instrument': row[1],
                'tests': row[2],
                'updated_at': row[3]
            })

        return history

    except Exception as e:
        logger.error(f"Failed to get testing history: {e}")
        return []


def mark_pattern_degraded(pattern_id: str, reason: str) -> None:
    """
    Mark a learned pattern as degraded/obsolete.

    Edges decay over time. Track that.

    Args:
        pattern_id: Pattern to mark
        reason: Why it degraded
    """
    try:
        conn = get_database_connection()

        conn.execute("""
            UPDATE learned_patterns
            SET status = 'DEGRADED',
                hypothesis = hypothesis || ' [DEGRADED: ' || ? || ']',
                updated_at = CURRENT_TIMESTAMP
            WHERE pattern_id = ?
        """, [reason, pattern_id])

        conn.commit()
        conn.close()

        logger.info(f"Marked pattern {pattern_id} as DEGRADED: {reason}")

    except Exception as e:
        logger.error(f"Failed to mark pattern degraded: {e}")
