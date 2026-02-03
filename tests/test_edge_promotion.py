"""
Test edge candidate promotion workflow.

Tests the complete lifecycle:
- Create candidate (DRAFT)
- Approve candidate (APPROVED)
- Promote candidate (→ validated_setups)

CRITICAL TESTS:
- Promotion MUST fail if required fields missing (fail-closed)
- NO hardcoded placeholder values allowed
- promoted_validated_setup_id gets set correctly

Run:
    pytest tests/test_edge_promotion.py -v

DEPRECATION NOTE (2026-01-21):
These tests target deprecated local-only workflow. Edge promotion now uses
cloud MotherDuck database via get_database_connection(). Tests are skipped
when cloud mode is active due to schema mismatch between test expectations
and actual MotherDuck schema (missing promoted_validated_setup_id column).

Tests need refactor to work with cloud-mode or use FORCE_LOCAL_DB=1.
"""

import pytest
import sys
import os
from pathlib import Path
from datetime import datetime

# Skip all tests in this module if in cloud mode
# These tests mock local database but functions use cloud-aware connections
# Schema mismatch: tests expect promoted_validated_setup_id column not in cloud schema
CLOUD_MODE = os.getenv("CLOUD_MODE", "0").lower() in ["1", "true", "yes"]
FORCE_LOCAL = os.getenv("FORCE_LOCAL_DB", "0").lower() in ["1", "true", "yes"]

pytestmark = pytest.mark.skipif(
    CLOUD_MODE or not FORCE_LOCAL,
    reason="Edge promotion tests target deprecated local-only workflow. "
           "Functions now use cloud MotherDuck via get_database_connection(). "
           "Schema mismatch: test expects promoted_validated_setup_id column not in cloud schema. "
           "Run with FORCE_LOCAL_DB=1 to test local-only mode."
)

# Add trading_app to path
sys.path.insert(0, str(Path(__file__).parent.parent / "trading_app"))

from edge_pipeline import (
    create_edge_candidate,
    promote_candidate_to_validated_setups,
    get_candidate_status,
    extract_candidate_manifest
)
from edge_candidate_utils import approve_edge_candidate


def _set_robustness_json(conn, candidate_id: int, robustness: dict) -> None:
    """
    Helper to set robustness_json on a candidate.

    Simulates what research_runner would do after running stress tests.
    Required by promotion gates (fail-closed) per audit3.txt, CLAUDE.md.

    Args:
        conn: Database connection
        candidate_id: ID of candidate to update
        robustness: Dict with stress test results, must include:
            - stress_50_pass: bool (required for promotion)
            - stress_50_exp_r: float (for logging)
    """
    import json
    conn.execute("""
        UPDATE edge_candidates
        SET robustness_json = ?::JSON
        WHERE candidate_id = ?
    """, [json.dumps(robustness), candidate_id])
    conn.commit()


@pytest.fixture
def test_db(tmp_path):
    """
    Create a temporary test database with edge_candidates and validated_setups tables.

    Uses tmp_path fixture to create a real file-based DB (not :memory:)
    to avoid DuckDB connection isolation issues.
    """
    import duckdb

    db_path = tmp_path / "test_edge.db"
    conn = duckdb.connect(str(db_path))

    # Create edge_candidates table (matching real schema)
    conn.execute("""
        CREATE TABLE edge_candidates (
            candidate_id INTEGER PRIMARY KEY,
            created_at_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            instrument TEXT NOT NULL,
            name TEXT NOT NULL,
            hypothesis_text TEXT NOT NULL,
            feature_spec_json JSON,
            filter_spec_json JSON NOT NULL,
            test_window_start DATE,
            test_window_end DATE,
            metrics_json JSON,
            robustness_json JSON,
            slippage_assumptions_json JSON,
            status TEXT NOT NULL DEFAULT 'DRAFT',
            notes TEXT,
            code_version TEXT,
            data_version TEXT,
            test_config_json JSON,
            approved_at TIMESTAMP,
            approved_by TEXT,
            promoted_validated_setup_id VARCHAR,
            promoted_by TEXT,
            promoted_at TIMESTAMP
        )
    """)

    # Create validated_setups table (must match edge_pipeline.py INSERT schema)
    conn.execute("""
        CREATE TABLE validated_setups (
            setup_id VARCHAR PRIMARY KEY,
            instrument TEXT NOT NULL,
            orb_time TEXT NOT NULL,
            rr DOUBLE NOT NULL,
            sl_mode TEXT NOT NULL,
            close_confirmations INTEGER DEFAULT 1,
            buffer_ticks DOUBLE DEFAULT 0.0,
            orb_size_filter DOUBLE,
            atr_filter DOUBLE,
            min_gap_filter DOUBLE,
            trades INTEGER NOT NULL,
            win_rate DOUBLE NOT NULL,
            avg_r DOUBLE NOT NULL,
            annual_trades INTEGER NOT NULL,
            tier TEXT NOT NULL,
            notes TEXT,
            validated_date DATE,
            data_source TEXT
        )
    """)

    conn.commit()
    conn.close()

    return db_path


@pytest.fixture
def mock_db_connection(test_db, monkeypatch):
    """Provide a writable DuckDB connection and patch get_database_connection."""
    import duckdb

    # Create a persistent connection for the test
    conn = duckdb.connect(str(test_db), read_only=False)

    # Patch get_database_connection to return the SAME connection
    # (avoids DuckDB connection conflicts with different read_only settings)
    def mock_get_connection(read_only=True):
        return conn

    # Patch at module level AND source module (cloud_mode)
    # edge_pipeline imports at module load, edge_candidate_utils imports at runtime
    import edge_pipeline
    import cloud_mode
    monkeypatch.setattr(edge_pipeline, "get_database_connection", mock_get_connection)
    monkeypatch.setattr(cloud_mode, "get_database_connection", mock_get_connection)

    try:
        yield conn
    finally:
        conn.close()


def test_create_candidate(mock_db_connection):
    """Test creating an edge candidate."""
    candidate_id = create_edge_candidate(
        name="Test 1000 ORB Tight",
        instrument="MGC",
        hypothesis_text="1000 ORB with tight filter should have high WR",
        filter_spec={
            "orb_size_filter": 0.05,
            "sl_mode": "HALF"
        },
        test_config={
            "test_window_start": "2024-01-01",
            "test_window_end": "2025-12-31",
            "walk_forward_windows": 4
        },
        metrics={
            "orb_time": "1000",
            "rr": 8.0,
            "win_rate": 33.5,
            "avg_r": 0.342,
            "annual_trades": 260,
            "tier": "S+"
        },
        slippage_assumptions={
            "slippage_ticks": 2,
            "commission_per_contract": 2.50
        },
        code_version="abc123",
        data_version="v1",
        actor="TestUser",
        db_connection=mock_db_connection
    )

    assert candidate_id == 1

    # Verify it was created
    status = get_candidate_status(candidate_id)
    assert status["status"] == "DRAFT"
    assert status["name"] == "Test 1000 ORB Tight"


def test_approve_candidate(mock_db_connection):
    """Test approving a candidate."""
    # Create candidate
    candidate_id = create_edge_candidate(
        name="Test 0900 ORB",
        instrument="MGC",
        hypothesis_text="0900 baseline",
        filter_spec={"orb_size_filter": None, "sl_mode": "FULL"},
        test_config={"test_window_start": "2024-01-01", "test_window_end": "2025-12-31"},
        metrics={
            "orb_time": "0900",
            "rr": 2.0,
            "win_rate": 63.3,
            "avg_r": 0.266,
            "annual_trades": 300,
            "tier": "S"
        },
        slippage_assumptions={"slippage_ticks": 2, "commission_per_contract": 2.50},
        code_version="abc123",
        data_version="v1",
        actor="TestUser",
        db_connection=mock_db_connection
    )

    # Approve it
    approve_edge_candidate(candidate_id, "Josh")

    # Verify approved
    status = get_candidate_status(candidate_id)
    assert status["status"] == "APPROVED"
    assert status["approved_by"] == "Josh"
    assert status["approved_at"] is not None


def test_promote_approved_candidate(mock_db_connection):
    """Test promoting an APPROVED candidate to validated_setups."""
    # Create candidate
    candidate_id = create_edge_candidate(
        name="Test 1100 ORB Safe",
        instrument="MGC",
        hypothesis_text="1100 safest MGC ORB",
        filter_spec={"orb_size_filter": 0.08, "sl_mode": "FULL"},
        test_config={"test_window_start": "2024-01-01", "test_window_end": "2025-12-31"},
        metrics={
            "orb_time": "1100",
            "rr": 2.0,
            "win_rate": 64.9,
            "avg_r": 0.299,
            "annual_trades": 280,
            "tier": "S+"
        },
        slippage_assumptions={"slippage_ticks": 2, "commission_per_contract": 2.50},
        code_version="def456",
        data_version="v1",
        actor="TestUser",
        db_connection=mock_db_connection
    )

    # Set robustness_json (required by promotion gates, simulates research_runner)
    _set_robustness_json(mock_db_connection, candidate_id, {
        "stress_50_pass": True,
        "stress_50_exp_r": 0.18,
        "stress_25_pass": True,
        "stress_25_exp_r": 0.22
    })

    # Approve it
    approve_edge_candidate(candidate_id, "Josh")

    # Promote it
    setup_id = promote_candidate_to_validated_setups(candidate_id, "Josh")

    # setup_id is now VARCHAR format: INSTRUMENT_ORBTIME_ID (e.g., "MGC_1100_001")
    assert setup_id == f"MGC_1100_{candidate_id:03d}"

    # Verify validated_setups row created
    result = mock_db_connection.execute("""
        SELECT setup_id, instrument, orb_time, rr, win_rate, avg_r, tier,
               orb_size_filter, sl_mode, annual_trades, data_source
        FROM validated_setups
        WHERE setup_id = ?
    """, [setup_id]).fetchone()

    assert result is not None
    assert result[0] == setup_id  # setup_id VARCHAR
    assert result[1] == "MGC"  # instrument
    assert result[2] == "1100"  # orb_time
    assert result[3] == 2.0  # rr
    assert result[4] == 64.9  # win_rate
    assert result[5] == 0.299  # avg_r
    assert result[6] == "S+"  # tier
    assert result[7] == 0.08  # orb_size_filter
    assert result[8] == "FULL"  # sl_mode
    assert result[9] == 280  # annual_trades
    assert result[10] == "edge_candidates"  # data_source

    # Verify edge_candidates.promoted_validated_setup_id was set
    status = get_candidate_status(candidate_id)
    assert status["promoted_validated_setup_id"] == setup_id


def test_promote_fails_if_not_approved(mock_db_connection):
    """Test that promotion fails if candidate is not APPROVED."""
    # Create candidate (status = DRAFT)
    candidate_id = create_edge_candidate(
        name="Test Draft",
        instrument="MGC",
        hypothesis_text="Test",
        filter_spec={"orb_size_filter": None, "sl_mode": "FULL"},
        test_config={"test_window_start": "2024-01-01", "test_window_end": "2025-12-31"},
        metrics={
            "orb_time": "0900",
            "rr": 2.0,
            "win_rate": 50.0,
            "avg_r": 0.0,
            "annual_trades": 100,
            "tier": "C"
        },
        slippage_assumptions={"slippage_ticks": 2, "commission_per_contract": 2.50},
        code_version="abc123",
        data_version="v1",
        actor="TestUser",
        db_connection=mock_db_connection
    )

    # Try to promote without approving
    with pytest.raises(ValueError, match="status is 'DRAFT', must be 'APPROVED'"):
        promote_candidate_to_validated_setups(candidate_id, "Josh")


def test_promote_fails_if_already_promoted(mock_db_connection):
    """Test that promotion fails if candidate was already promoted."""
    # Create and approve candidate
    candidate_id = create_edge_candidate(
        name="Test Double Promote",
        instrument="MGC",
        hypothesis_text="Test",
        filter_spec={"orb_size_filter": None, "sl_mode": "FULL"},
        test_config={"test_window_start": "2024-01-01", "test_window_end": "2025-12-31"},
        metrics={
            "orb_time": "0900",
            "rr": 2.0,
            "win_rate": 55.0,
            "avg_r": 0.20,  # Must be >= 0.15R per CLAUDE.md approval rule
            "annual_trades": 100,
            "tier": "B"
        },
        slippage_assumptions={"slippage_ticks": 2, "commission_per_contract": 2.50},
        code_version="abc123",
        data_version="v1",
        actor="TestUser",
        db_connection=mock_db_connection
    )

    # Set robustness_json (required by promotion gates, simulates research_runner)
    _set_robustness_json(mock_db_connection, candidate_id, {
        "stress_50_pass": True,
        "stress_50_exp_r": 0.16,
        "stress_25_pass": True,
        "stress_25_exp_r": 0.18
    })

    approve_edge_candidate(candidate_id, "Josh")

    # First promotion succeeds
    setup_id = promote_candidate_to_validated_setups(candidate_id, "Josh")
    assert setup_id == f"MGC_0900_{candidate_id:03d}"  # VARCHAR format: INSTRUMENT_ORBTIME_ID

    # Second promotion fails (status is now 'PROMOTED' after first promotion)
    with pytest.raises(ValueError, match="status is 'PROMOTED'"):
        promote_candidate_to_validated_setups(candidate_id, "Josh")


def test_promote_fails_if_missing_required_fields(mock_db_connection):
    """Test that promotion fails if required manifest fields are missing (FAIL-CLOSED)."""
    # Manually insert a candidate with incomplete metrics_json (missing 'rr')
    # NOTE: avg_r >= 0.15 and robustness_json required to pass earlier promotion gates
    mock_db_connection.execute("""
        INSERT INTO edge_candidates (
            candidate_id, name, instrument, hypothesis_text,
            filter_spec_json, test_config_json, metrics_json, robustness_json, slippage_assumptions_json,
            code_version, data_version, status, approved_by
        ) VALUES (
            999, 'Incomplete', 'MGC', 'Test incomplete',
            '{"orb_size_filter": null, "sl_mode": "FULL"}'::JSON,
            '{"test_window_start": "2024-01-01", "test_window_end": "2025-12-31"}'::JSON,
            '{"orb_time": "0900", "win_rate": 55.0, "avg_r": 0.20, "annual_trades": 100, "tier": "B"}'::JSON,
            '{"stress_50_pass": true, "stress_50_exp_r": 0.16}'::JSON,
            '{"slippage_ticks": 2}'::JSON,
            'abc123', 'v1', 'APPROVED', 'Josh'
        )
    """)

    # Try to promote - should fail due to missing 'rr' in metrics_json
    with pytest.raises(ValueError, match="missing required fields.*metrics_json.rr"):
        promote_candidate_to_validated_setups(999, "Josh")


def test_no_hardcoded_placeholders_in_promotion(mock_db_connection):
    """
    Test that promotion extracts ALL values from candidate JSON fields.

    This test verifies NO hardcoded placeholder values are used.
    """
    # Create candidate with UNIQUE values to ensure they're extracted, not hardcoded
    candidate_id = create_edge_candidate(
        name="Unique Values Test",
        instrument="NQ",  # Different instrument
        hypothesis_text="Testing value extraction",
        filter_spec={"orb_size_filter": 0.123, "sl_mode": "CUSTOM"},  # Unique values
        test_config={"test_window_start": "2023-06-15", "test_window_end": "2024-08-20"},
        metrics={
            "orb_time": "1800",  # Unique ORB time
            "rr": 7.5,  # Unique RR
            "win_rate": 72.8,  # Unique WR
            "avg_r": 0.555,  # Unique avg_r
            "annual_trades": 175,  # Unique count
            "tier": "A"  # Unique tier
        },
        slippage_assumptions={"slippage_ticks": 5, "commission_per_contract": 3.75},
        code_version="unique_hash_789",
        data_version="v99",
        actor="TestUser",
        db_connection=mock_db_connection
    )

    # Set robustness_json (required by promotion gates, simulates research_runner)
    _set_robustness_json(mock_db_connection, candidate_id, {
        "stress_50_pass": True,
        "stress_50_exp_r": 0.35,
        "stress_25_pass": True,
        "stress_25_exp_r": 0.45
    })

    approve_edge_candidate(candidate_id, "Josh")
    setup_id = promote_candidate_to_validated_setups(candidate_id, "Josh")

    # Verify ALL unique values were extracted correctly
    import json

    result = mock_db_connection.execute("""
        SELECT instrument, orb_time, rr, win_rate, avg_r, annual_trades, tier,
               orb_size_filter, sl_mode, notes
        FROM validated_setups
        WHERE setup_id = ?
    """, [setup_id]).fetchone()

    # Assert EXACT unique values (proves no hardcoded placeholders)
    assert result[0] == "NQ", "instrument should be extracted from candidate"
    assert result[1] == "1800", "orb_time should be extracted from metrics_json"
    assert result[2] == 7.5, "rr should be extracted from metrics_json"
    assert result[3] == 72.8, "win_rate should be extracted from metrics_json"
    assert result[4] == 0.555, "avg_r should be extracted from metrics_json"
    assert result[5] == 175, "annual_trades should be extracted from metrics_json"
    assert result[6] == "A", "tier should be extracted from metrics_json"
    assert result[7] == 0.123, "orb_size_filter should be extracted from filter_spec_json"
    assert result[8] == "CUSTOM", "sl_mode should be extracted from filter_spec_json"

    # code_version, data_version, test_window_start, test_window_end are stored in notes JSON
    notes = json.loads(result[9]) if result[9] else {}
    assert notes["code_version"] == "unique_hash_789", "code_version should be in notes"
    assert notes["data_version"] == "v99", "data_version should be in notes"
    assert notes["test_window_start"] == "2023-06-15", "test_window_start should be in notes"
    assert notes["test_window_end"] == "2024-08-20", "test_window_end should be in notes"


def test_extract_manifest_validates_all_fields(mock_db_connection):
    """Test that extract_candidate_manifest validates all required fields."""
    # Create a valid candidate
    mock_db_connection.execute("""
        INSERT INTO edge_candidates (
            candidate_id, name, instrument, hypothesis_text,
            filter_spec_json, test_config_json, metrics_json, slippage_assumptions_json,
            code_version, data_version, status, approved_by
        ) VALUES (
            100, 'Valid', 'MGC', 'Test',
            '{"orb_size_filter": 0.05, "sl_mode": "FULL"}'::JSON,
            '{"test_window_start": "2024-01-01", "test_window_end": "2025-12-31"}'::JSON,
            '{"orb_time": "1000", "rr": 8.0, "win_rate": 33.5, "avg_r": 0.342, "annual_trades": 260, "tier": "S+"}'::JSON,
            '{"slippage_ticks": 2}'::JSON,
            'abc123', 'v1', 'APPROVED', 'Josh'
        )
    """)

    # Fetch the row (must match the SELECT order in promote_candidate_to_validated_setups)
    row = mock_db_connection.execute("""
        SELECT
            candidate_id, name, instrument, hypothesis_text,
            filter_spec_json, test_config_json, metrics_json, slippage_assumptions_json,
            code_version, data_version, status, created_at_utc, approved_at, approved_by,
            promoted_validated_setup_id, notes, robustness_json
        FROM edge_candidates
        WHERE candidate_id = 100
    """).fetchone()

    # Extract manifest - should succeed
    manifest = extract_candidate_manifest(row)

    assert manifest["candidate_id"] == 100
    assert manifest["orb_time"] == "1000"
    assert manifest["rr"] == 8.0
    assert manifest["win_rate"] == 33.5
    assert manifest["avg_r"] == 0.342
    assert manifest["annual_trades"] == 260
    assert manifest["tier"] == "S+"
