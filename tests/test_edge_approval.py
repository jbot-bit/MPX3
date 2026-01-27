"""
Test edge candidate approval functionality.

Tests the approve_edge_candidate and set_candidate_status functions
to ensure they use write-capable database connections and update
status correctly.

Run:
    pytest tests/test_edge_approval.py -v
"""

import pytest
import tempfile
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
import duckdb

# Add trading_app to path
sys.path.insert(0, str(Path(__file__).parent.parent / "trading_app"))

from trading_app.edge_candidate_utils import approve_edge_candidate, set_candidate_status


@pytest.fixture
def test_db():
    """Create a temporary DuckDB database with edge_candidates table for testing."""
    # Create temp database file path (DuckDB will create the file)
    import os
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    # Delete the empty file created by tempfile (DuckDB needs to create its own file)
    os.unlink(db_path)

    # Create test database with edge_candidates table
    conn = duckdb.connect(db_path)

    # Create edge_candidates table (minimal schema for testing)
    conn.execute("""
        CREATE TABLE edge_candidates (
            candidate_id INTEGER PRIMARY KEY,
            created_at_utc TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            instrument VARCHAR,
            name VARCHAR,
            hypothesis_text VARCHAR,
            status VARCHAR DEFAULT 'DRAFT',
            notes VARCHAR,
            approved_at TIMESTAMP,
            approved_by VARCHAR
        )
    """)

    # Insert test candidates
    conn.execute("""
        INSERT INTO edge_candidates (candidate_id, instrument, name, hypothesis_text, status)
        VALUES
            (1, 'MGC', 'Test Strategy 1', 'Test hypothesis 1', 'DRAFT'),
            (2, 'MGC', 'Test Strategy 2', 'Test hypothesis 2', 'PENDING'),
            (3, 'MGC', 'Test Strategy 3', 'Test hypothesis 3', 'APPROVED'),
            (4, 'NQ', 'Test Strategy 4', 'Test hypothesis 4', 'DRAFT')
    """)

    # Set approved_at and approved_by for candidate 3
    conn.execute("""
        UPDATE edge_candidates
        SET approved_at = CURRENT_TIMESTAMP, approved_by = 'TestUser'
        WHERE candidate_id = 3
    """)

    conn.close()

    yield db_path

    # Cleanup
    import os
    try:
        os.unlink(db_path)
    except:
        pass


def test_approve_edge_candidate_function_exists():
    """Test that approve_edge_candidate function exists and is callable."""
    assert callable(approve_edge_candidate)


def test_set_candidate_status_function_exists():
    """Test that set_candidate_status function exists and is callable."""
    assert callable(set_candidate_status)


def test_approve_edge_candidate_uses_write_connection(test_db):
    """Test that approve_edge_candidate requests read_only=False connection."""

    # Mock get_database_connection to return our test DB
    with patch('cloud_mode.get_database_connection') as mock_get_conn:
        mock_conn = duckdb.connect(test_db)
        mock_get_conn.return_value = mock_conn

        # Approve candidate 1
        approve_edge_candidate(1, "Josh")

        # Verify get_database_connection was called with read_only=False
        mock_get_conn.assert_called_once_with(read_only=False)

    # Verify status was updated (open new connection to check)
    check_conn = duckdb.connect(test_db)
    result = check_conn.execute(
        "SELECT status, approved_by FROM edge_candidates WHERE candidate_id = 1"
    ).fetchone()

    assert result[0] == 'APPROVED'
    assert result[1] == 'Josh'

    check_conn.close()


def test_approve_candidate_updates_status(test_db):
    """Test that approving a candidate updates status, approved_at, and approved_by."""

    with patch('cloud_mode.get_database_connection') as mock_get_conn:
        mock_conn = duckdb.connect(test_db)
        mock_get_conn.return_value = mock_conn

        # Approve candidate 2 (status: PENDING)
        approve_edge_candidate(2, "Josh")

    # Check database (open new connection)
    check_conn = duckdb.connect(test_db)
    result = check_conn.execute("""
        SELECT status, approved_by, approved_at
        FROM edge_candidates
        WHERE candidate_id = 2
    """).fetchone()

    assert result[0] == 'APPROVED'
    assert result[1] == 'Josh'
    assert result[2] is not None  # approved_at should be set

    check_conn.close()


def test_approve_already_approved_candidate_raises_error(test_db):
    """Test that approving an already-approved candidate raises ValueError."""

    with patch('cloud_mode.get_database_connection') as mock_get_conn:
        mock_conn = duckdb.connect(test_db)
        mock_get_conn.return_value = mock_conn

        # Candidate 3 is already approved
        with pytest.raises(ValueError, match="already APPROVED"):
            approve_edge_candidate(3, "Josh")

        mock_conn.close()


def test_approve_nonexistent_candidate_raises_error(test_db):
    """Test that approving a non-existent candidate raises ValueError."""

    with patch('cloud_mode.get_database_connection') as mock_get_conn:
        mock_conn = duckdb.connect(test_db)
        mock_get_conn.return_value = mock_conn

        # Candidate 999 doesn't exist
        with pytest.raises(ValueError, match="not found"):
            approve_edge_candidate(999, "Josh")

        mock_conn.close()


def test_set_candidate_status_to_pending(test_db):
    """Test setting candidate status to PENDING."""

    with patch('cloud_mode.get_database_connection') as mock_get_conn:
        mock_conn = duckdb.connect(test_db)
        mock_get_conn.return_value = mock_conn

        # Set candidate 1 to PENDING
        set_candidate_status(1, 'PENDING', notes="Ready for review", actor="Josh")

    # Check database (open new connection)
    check_conn = duckdb.connect(test_db)
    result = check_conn.execute("""
        SELECT status, notes, approved_by
        FROM edge_candidates
        WHERE candidate_id = 1
    """).fetchone()

    assert result[0] == 'PENDING'
    assert '[Josh]' in result[1]
    assert 'Ready for review' in result[1]
    assert result[2] is None  # approved_by should still be NULL (not APPROVED yet)

    check_conn.close()


def test_set_candidate_status_to_approved(test_db):
    """Test setting candidate status to APPROVED via set_candidate_status."""

    with patch('cloud_mode.get_database_connection') as mock_get_conn:
        mock_conn = duckdb.connect(test_db)
        mock_get_conn.return_value = mock_conn

        # Set candidate 4 to APPROVED
        set_candidate_status(4, 'APPROVED', notes="Looks good", actor="Josh")

    # Check database (open new connection)
    check_conn = duckdb.connect(test_db)
    result = check_conn.execute("""
        SELECT status, approved_by, approved_at
        FROM edge_candidates
        WHERE candidate_id = 4
    """).fetchone()

    assert result[0] == 'APPROVED'
    assert result[1] == 'Josh'
    assert result[2] is not None  # approved_at should be set

    check_conn.close()


def test_set_candidate_status_invalid_status(test_db):
    """Test that invalid status raises ValueError."""

    with patch('cloud_mode.get_database_connection') as mock_get_conn:
        mock_conn = duckdb.connect(test_db)
        mock_get_conn.return_value = mock_conn

        # Invalid status
        with pytest.raises(ValueError, match="Invalid status"):
            set_candidate_status(1, 'INVALID_STATUS', actor="Josh")

        mock_conn.close()


def test_set_candidate_status_approved_requires_actor(test_db):
    """Test that setting status to APPROVED without actor raises ValueError."""

    with patch('cloud_mode.get_database_connection') as mock_get_conn:
        mock_conn = duckdb.connect(test_db)
        mock_get_conn.return_value = mock_conn

        # APPROVED status requires actor
        with pytest.raises(ValueError, match="actor parameter required"):
            set_candidate_status(1, 'APPROVED')  # No actor provided

        mock_conn.close()
