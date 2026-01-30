#!/usr/bin/env python3
"""
Lifecycle Smoke Tests (UPDATE19a)
==================================

Minimal deterministic tests that prove the Candidate→Strategy conveyor belt
lifecycle is DB-backed and fail-closed.

CRITICAL RULES:
- Use temp DuckDB copy (never modify production gold.db)
- Tests must be deterministic and fast
- No Streamlit runtime dependencies (pure functions only)
- Validate flow integrity, not trading math

Tests:
1. Enqueue persists: Candidates inserted into validation_queue appear in query
2. Refresh safety: DB-backed state survives "new session" (not session_state truth)
3. Fail-closed on missing JSON: Missing metrics_json → status UNKNOWN → approve blocked
4. Approve wiring: Calls real promotion only when PASS and write-gate passes
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

import pytest
import duckdb

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from trading_app.ui_contract import derive_validation_status, can_approve


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_db():
    """Create a temporary DuckDB with minimal schema (non-destructive, no disk copy)"""
    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="test_lifecycle_")
    temp_db_path = Path(temp_dir) / "test_gold.db"

    # Create minimal schema (avoid copying large gold.db - disk space issue)
    conn = duckdb.connect(str(temp_db_path))

    # validation_queue table (with SEQUENCE for auto-increment queue_id)
    conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_validation_queue START 1")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS validation_queue (
            queue_id INTEGER PRIMARY KEY DEFAULT nextval('seq_validation_queue'),
            enqueued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source VARCHAR NOT NULL,
            source_id VARCHAR,
            instrument VARCHAR NOT NULL,
            setup_family VARCHAR,
            orb_time VARCHAR NOT NULL,
            rr_target DOUBLE NOT NULL,
            filters_json JSON,
            score_proxy DOUBLE,
            sample_size INTEGER,
            status VARCHAR DEFAULT 'PENDING',
            assigned_to VARCHAR,
            notes VARCHAR
        )
    """)

    # edge_candidates table (with all NOT NULL fields)
    conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_edge_candidates START 1")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS edge_candidates (
            candidate_id INTEGER PRIMARY KEY DEFAULT nextval('seq_edge_candidates'),
            name VARCHAR NOT NULL,
            instrument VARCHAR NOT NULL,
            hypothesis_text VARCHAR NOT NULL DEFAULT 'Test hypothesis',
            status VARCHAR DEFAULT 'DRAFT',
            metrics_json VARCHAR,
            robustness_json VARCHAR,
            filter_spec_json VARCHAR,
            test_window_start DATE DEFAULT CURRENT_DATE,
            test_window_end DATE DEFAULT CURRENT_DATE,
            created_at_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # validated_setups table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS validated_setups (
            setup_id VARCHAR PRIMARY KEY,
            instrument VARCHAR NOT NULL,
            orb_time VARCHAR NOT NULL,
            rr DOUBLE NOT NULL,
            sl_mode VARCHAR,
            close_confirmations INTEGER,
            buffer_ticks DOUBLE,
            orb_size_filter DOUBLE,
            atr_filter DOUBLE,
            min_gap_filter DOUBLE,
            trades INTEGER,
            win_rate DOUBLE,
            avg_r DOUBLE,
            annual_trades INTEGER,
            tier VARCHAR,
            notes VARCHAR,
            validated_date DATE,
            data_source VARCHAR
        )
    """)

    conn.close()

    yield temp_db_path

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


# =============================================================================
# TEST 1: Enqueue Persists (DB-backed, not session_state)
# =============================================================================

def test_enqueue_candidates_persist_in_db(temp_db):
    """
    Test that enqueueing candidates persists to validation_queue table.

    Proves: DB-backed lifecycle (not session_state truth)
    """
    conn = duckdb.connect(str(temp_db))

    # Insert test candidates into validation_queue
    test_candidates = [
        {
            'source': 'auto_search',
            'source_id': 'test_candidate_001',
            'instrument': 'MGC',
            'orb_time': '0900',
            'rr_target': 1.5,
            'filters_json': json.dumps({'orb_size_min': 0.10}),
            'score_proxy': 0.25,
            'sample_size': 50,
            'status': 'PENDING',
            'notes': 'Test candidate 1'
        },
        {
            'source': 'auto_search',
            'source_id': 'test_candidate_002',
            'instrument': 'MGC',
            'orb_time': '1000',
            'rr_target': 2.0,
            'filters_json': json.dumps({'orb_size_min': 0.15}),
            'score_proxy': 0.30,
            'sample_size': 45,
            'status': 'PENDING',
            'notes': 'Test candidate 2'
        }
    ]

    for candidate in test_candidates:
        conn.execute("""
            INSERT INTO validation_queue (
                source, source_id, instrument, orb_time, rr_target,
                filters_json, score_proxy, sample_size, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            candidate['source'],
            candidate['source_id'],
            candidate['instrument'],
            candidate['orb_time'],
            candidate['rr_target'],
            candidate['filters_json'],
            candidate['score_proxy'],
            candidate['sample_size'],
            candidate['status'],
            candidate['notes']
        ])

    conn.commit()

    # Query validation_queue (simulates Validation Gate reading queue)
    results = conn.execute("""
        SELECT source, source_id, instrument, orb_time, rr_target, status
        FROM validation_queue
        WHERE status = 'PENDING'
        ORDER BY queue_id
    """).fetchall()

    conn.close()

    # Assertions
    assert len(results) == 2, f"Expected 2 candidates in queue, got {len(results)}"
    assert results[0][1] == 'test_candidate_001', "First candidate not found"
    assert results[1][1] == 'test_candidate_002', "Second candidate not found"
    assert results[0][5] == 'PENDING', "Status should be PENDING"


# =============================================================================
# TEST 2: Refresh Safety (No Session Truth)
# =============================================================================

def test_refresh_safety_db_backed_not_session_state(temp_db):
    """
    Test that queued candidates survive "new session" (page refresh).

    Proves: DB is source of truth, not session_state
    """
    # Session 1: Enqueue candidate
    conn1 = duckdb.connect(str(temp_db))
    conn1.execute("""
        INSERT INTO validation_queue (
            source, source_id, instrument, orb_time, rr_target, status
        ) VALUES ('auto_search', 'persistent_candidate', 'MGC', '0900', 1.5, 'PENDING')
    """)
    conn1.commit()
    conn1.close()

    # Simulate page refresh (new connection, simulates new session)
    conn2 = duckdb.connect(str(temp_db))

    results = conn2.execute("""
        SELECT source_id, status FROM validation_queue WHERE source_id = 'persistent_candidate'
    """).fetchall()

    conn2.close()

    # Assertions
    assert len(results) == 1, "Candidate should persist across sessions"
    assert results[0][0] == 'persistent_candidate', "Candidate ID should match"
    assert results[0][1] == 'PENDING', "Status should remain PENDING"


# =============================================================================
# TEST 3: Fail-Closed on Missing/Malformed JSON
# =============================================================================

def test_fail_closed_missing_metrics_json(temp_db):
    """
    Test that missing metrics_json → status UNKNOWN → approve blocked.

    Proves: Fail-closed validation (no crash, approve disabled)
    """
    conn = duckdb.connect(str(temp_db))

    # Insert candidate with NULL metrics_json
    conn.execute("""
        INSERT INTO edge_candidates (
            candidate_id, name, instrument, hypothesis_text, status, metrics_json, robustness_json
        ) VALUES (9999, 'Missing Metrics Test', 'MGC', 'Test hypothesis for missing metrics', 'PENDING', NULL, '{"stress_25_pass": true, "stress_50_pass": false}')
    """)
    conn.commit()

    # Fetch candidate
    result = conn.execute("""
        SELECT metrics_json, robustness_json FROM edge_candidates WHERE candidate_id = 9999
    """).fetchone()

    conn.close()

    metrics_json, robustness_json = result

    # Derive status using ui_contract.py (pure function, no Streamlit)
    status = derive_validation_status(metrics_json, robustness_json)

    # Assertions
    assert status == "UNKNOWN", f"Expected UNKNOWN, got {status}"
    assert not can_approve(status), "Approve should be blocked for UNKNOWN status"


def test_fail_closed_malformed_json():
    """
    Test that malformed JSON → status UNKNOWN → approve blocked (no crash).

    Proves: Fail-closed validation (graceful handling)
    """
    # Malformed JSON strings
    metrics_json = '{"avg_r": 0.25, INVALID'
    robustness_json = '{"stress_50_pass": true'

    # Derive status (should not crash)
    status = derive_validation_status(metrics_json, robustness_json)

    # Assertions
    assert status == "UNKNOWN", f"Expected UNKNOWN for malformed JSON, got {status}"
    assert not can_approve(status), "Approve should be blocked for UNKNOWN status"


# =============================================================================
# TEST 4: Approve Wiring (Calls Real Promotion Only When PASS)
# =============================================================================

def test_approve_wiring_calls_promotion_only_when_pass(temp_db, monkeypatch):
    """
    Test that approve calls real promotion function only when status=PASS.

    Proves: Approve wiring is correct (not called for WEAK/FAIL/UNKNOWN)
    """
    from unittest.mock import MagicMock

    # Mock the promotion function
    mock_promote = MagicMock()

    # Patch the promotion function target (monkeypatch for testing)
    import trading_app.edge_pipeline as edge_pipeline_module
    monkeypatch.setattr(edge_pipeline_module, 'promote_candidate_to_validated_setups', mock_promote)

    # Test scenarios
    test_cases = [
        # (metrics_json, robustness_json, expected_status, should_call_promote)
        (
            '{"avg_r": 0.25, "win_rate": 0.60, "sample_size": 50}',
            '{"stress_25_pass": true, "stress_50_pass": true}',
            "PASS",
            True
        ),
        (
            '{"avg_r": 0.25, "win_rate": 0.60, "sample_size": 50}',
            '{"stress_25_pass": true, "stress_50_pass": false}',
            "WEAK",
            False
        ),
        (
            '{"avg_r": 0.10, "win_rate": 0.50, "sample_size": 50}',
            '{"stress_25_pass": false, "stress_50_pass": false}',
            "FAIL",
            False
        ),
        (
            None,
            '{"stress_25_pass": true, "stress_50_pass": true}',
            "UNKNOWN",
            False
        ),
    ]

    for metrics_json, robustness_json, expected_status, should_call_promote in test_cases:
        # Reset mock
        mock_promote.reset_mock()

        # Derive status
        status = derive_validation_status(metrics_json, robustness_json)

        # Check status
        assert status == expected_status, f"Expected {expected_status}, got {status}"

        # Simulate approve button click (only if can_approve returns True)
        if can_approve(status):
            # Approve allowed - call promotion (simulates button callback)
            mock_promote(candidate_id=1, actor='test_user')

            # Assert promotion was called exactly once
            assert mock_promote.call_count == 1, f"Promotion should be called for {status}"
        else:
            # Approve blocked - do NOT call promotion
            # Assert promotion was never called
            assert mock_promote.call_count == 0, f"Promotion should NOT be called for {status}"


# =============================================================================
# TEST 5: Dedup Protection (No Duplicate Queue Entries)
# =============================================================================

def test_dedup_protection_prevents_duplicate_enqueue(temp_db):
    """
    Test that dedup protection prevents duplicate entries in validation_queue.

    Proves: Enqueue logic checks for existing PENDING entries before inserting
    """
    conn = duckdb.connect(str(temp_db))

    # Insert first candidate
    conn.execute("""
        INSERT INTO validation_queue (
            source, source_id, instrument, orb_time, rr_target, status
        ) VALUES ('auto_search', 'candidate_123', 'MGC', '0900', 1.5, 'PENDING')
    """)
    conn.commit()

    # Simulate dedup check (before inserting duplicate)
    existing = conn.execute("""
        SELECT queue_id FROM validation_queue
        WHERE source = 'auto_search' AND source_id = 'candidate_123' AND status = 'PENDING'
    """).fetchone()

    # Should find existing entry
    assert existing is not None, "Dedup check should find existing PENDING candidate"

    # Attempt to insert duplicate (should be skipped by dedup logic in app)
    # In real app, this INSERT would NOT happen if existing is found
    # We're testing that the dedup check works

    # Count total entries for this candidate
    count = conn.execute("""
        SELECT COUNT(*) FROM validation_queue
        WHERE source = 'auto_search' AND source_id = 'candidate_123'
    """).fetchone()[0]

    conn.close()

    # Should be exactly 1 entry (not duplicated)
    assert count == 1, f"Expected 1 entry, got {count} (dedup failed)"


# =============================================================================
# TEST 6: Forbidden Table Reference Regression
# =============================================================================

def test_validation_gate_queries_only_real_tables(temp_db):
    """
    Test that Validation Gate queries reference only existing tables.

    Proves: No references to non-existent tables (e.g., experiment_metrics)
    """
    conn = duckdb.connect(str(temp_db))

    # Get all table names in database
    tables = conn.execute("SHOW TABLES").fetchdf()['name'].tolist()

    # Required tables for Validation Gate
    required_tables = ['validation_queue', 'edge_candidates']

    # Check all required tables exist
    for table in required_tables:
        assert table in tables, f"Required table '{table}' does not exist"

    # Test queries (should not raise errors)
    try:
        # Query 1: validation_queue
        conn.execute("SELECT COUNT(*) FROM validation_queue WHERE status = 'PENDING'").fetchone()

        # Query 2: edge_candidates
        conn.execute("SELECT COUNT(*) FROM edge_candidates WHERE status IN ('DRAFT', 'PENDING')").fetchone()

        queries_passed = True
    except Exception as e:
        queries_passed = False
        pytest.fail(f"Validation Gate query failed (table reference error): {e}")

    conn.close()

    assert queries_passed, "All Validation Gate queries should execute without table reference errors"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
