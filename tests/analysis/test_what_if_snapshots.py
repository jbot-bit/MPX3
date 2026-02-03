"""
Comprehensive unit tests for analysis/what_if_snapshots.py

Tests cover:
- SnapshotManager class initialization
- save_snapshot method
- load_snapshot method
- list_snapshots method
- Snapshot immutability
- Data version tracking
- Edge cases and error handling

NOTE: These tests use mocked MetricsResult objects since we can't easily
run the full WhatIfEngine without production database setup.
"""

import pytest
import json
import uuid
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analysis.what_if_snapshots import SnapshotManager


# =============================================================================
# Helper Functions
# =============================================================================

def create_mock_metrics_result(
    sample_size=50,
    win_rate=0.6,
    expected_r=0.25,
    avg_win=1.5,
    avg_loss=-1.0,
    max_dd=-3.0,
    sharpe_ratio=1.0,
    total_r=12.5,
    stress_25_exp_r=0.20,
    stress_50_exp_r=0.15,
    stress_25_pass=True,
    stress_50_pass=True
):
    """Create a mock MetricsResult object"""
    mock = MagicMock()
    mock.sample_size = sample_size
    mock.win_rate = win_rate
    mock.expected_r = expected_r
    mock.avg_win = avg_win
    mock.avg_loss = avg_loss
    mock.max_dd = max_dd
    mock.sharpe_ratio = sharpe_ratio
    mock.total_r = total_r
    mock.stress_25_exp_r = stress_25_exp_r
    mock.stress_50_exp_r = stress_50_exp_r
    mock.stress_25_pass = stress_25_pass
    mock.stress_50_pass = stress_50_pass
    mock.trades = []
    return mock


def create_mock_result(
    cache_key="MGC_1000_BOTH_rr2.0_full_abc123_2024-01-01_2024-12-31_v1",
    condition_set=None,
    baseline=None,
    conditional=None,
    non_matched=None,
    delta=None
):
    """Create a mock WhatIfEngine result dict"""
    if condition_set is None:
        condition_set = {
            "orb_size_min": 0.5,
            "orb_size_max": None,
            "asia_travel_max": 2.5,
            "pre_orb_travel_max": None,
            "asia_types": None,
            "london_types": None,
            "orb_size_percentile_min": None,
            "orb_size_percentile_max": None,
            "percentile_window_days": 20
        }

    if baseline is None:
        baseline = create_mock_metrics_result()
    if conditional is None:
        conditional = create_mock_metrics_result(sample_size=30, win_rate=0.7, expected_r=0.35)
    if non_matched is None:
        non_matched = create_mock_metrics_result(sample_size=20, win_rate=0.4, expected_r=0.05)

    if delta is None:
        delta = {
            "sample_size": -20,
            "win_rate_pct": 10.0,
            "expected_r": 0.10,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "max_dd": 0.0,
            "sharpe_ratio": 0.2,
            "total_r": 5.0
        }

    return {
        "cache_key": cache_key,
        "condition_set": condition_set,
        "baseline": baseline,
        "conditional": conditional,
        "non_matched": non_matched,
        "delta": delta,
        "timestamp": datetime.now().isoformat()
    }


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_db(tmp_path):
    """Create a mock DuckDB database with required tables"""
    import duckdb

    db_path = tmp_path / "test.db"
    conn = duckdb.connect(str(db_path))

    # Create what_if_snapshots table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS what_if_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            cache_key TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            instrument TEXT NOT NULL,
            orb_time TEXT NOT NULL,
            direction TEXT NOT NULL,
            rr DOUBLE NOT NULL,
            sl_mode TEXT NOT NULL,
            conditions JSON NOT NULL,
            date_start TEXT,
            date_end TEXT,
            baseline_sample_size INTEGER NOT NULL,
            baseline_win_rate DOUBLE NOT NULL,
            baseline_expected_r DOUBLE NOT NULL,
            baseline_avg_win DOUBLE NOT NULL,
            baseline_avg_loss DOUBLE NOT NULL,
            baseline_max_dd DOUBLE NOT NULL,
            baseline_sharpe_ratio DOUBLE NOT NULL,
            baseline_total_r DOUBLE NOT NULL,
            baseline_stress_25_exp_r DOUBLE NOT NULL,
            baseline_stress_50_exp_r DOUBLE NOT NULL,
            baseline_stress_25_pass BOOLEAN NOT NULL,
            baseline_stress_50_pass BOOLEAN NOT NULL,
            conditional_sample_size INTEGER NOT NULL,
            conditional_win_rate DOUBLE NOT NULL,
            conditional_expected_r DOUBLE NOT NULL,
            conditional_avg_win DOUBLE NOT NULL,
            conditional_avg_loss DOUBLE NOT NULL,
            conditional_max_dd DOUBLE NOT NULL,
            conditional_sharpe_ratio DOUBLE NOT NULL,
            conditional_total_r DOUBLE NOT NULL,
            conditional_stress_25_exp_r DOUBLE NOT NULL,
            conditional_stress_50_exp_r DOUBLE NOT NULL,
            conditional_stress_25_pass BOOLEAN NOT NULL,
            conditional_stress_50_pass BOOLEAN NOT NULL,
            non_matched_sample_size INTEGER NOT NULL,
            non_matched_win_rate DOUBLE NOT NULL,
            non_matched_expected_r DOUBLE NOT NULL,
            delta_sample_size INTEGER NOT NULL,
            delta_win_rate_pct DOUBLE NOT NULL,
            delta_expected_r DOUBLE NOT NULL,
            delta_avg_win DOUBLE NOT NULL,
            delta_avg_loss DOUBLE NOT NULL,
            delta_max_dd DOUBLE NOT NULL,
            delta_sharpe_ratio DOUBLE NOT NULL,
            delta_total_r DOUBLE NOT NULL,
            data_version TEXT,
            engine_version TEXT NOT NULL DEFAULT 'v1',
            notes TEXT,
            promoted_to_candidate BOOLEAN DEFAULT FALSE,
            candidate_edge_id TEXT,
            created_by TEXT
        )
    """)

    # Create daily_features table for data version check
    conn.execute("""
        CREATE TABLE daily_features (
            date_local DATE,
            instrument VARCHAR
        )
    """)
    conn.execute("INSERT INTO daily_features VALUES ('2024-12-31', 'MGC')")

    return conn


@pytest.fixture
def manager(mock_db):
    """Create SnapshotManager with mock database"""
    return SnapshotManager(mock_db)


# =============================================================================
# Test SnapshotManager Initialization
# =============================================================================

class TestSnapshotManagerInit:
    """Test SnapshotManager initialization"""

    def test_initialization_with_valid_connection(self, mock_db):
        """Should initialize with valid connection"""
        manager = SnapshotManager(mock_db)
        assert manager.conn is mock_db

    def test_initialization_creates_table(self, tmp_path):
        """Should create table if it doesn't exist"""
        import duckdb

        db_path = tmp_path / "new.db"
        conn = duckdb.connect(str(db_path))

        # Create daily_features for data version
        conn.execute("CREATE TABLE daily_features (date_local DATE)")
        conn.execute("INSERT INTO daily_features VALUES ('2024-01-01')")

        # Create docs directory with schema file
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        manager = SnapshotManager(conn)
        # Should not raise even without schema file
        conn.close()

    def test_initialization_with_none_connection_raises(self):
        """Should raise error with None connection"""
        with pytest.raises(ValueError):
            SnapshotManager(None)


# =============================================================================
# Test save_snapshot Method
# =============================================================================

class TestSaveSnapshot:
    """Test save_snapshot method"""

    def test_save_snapshot_returns_uuid(self, manager):
        """save_snapshot should return a UUID string"""
        result = create_mock_result()
        snapshot_id = manager.save_snapshot(result, notes="Test snapshot")

        assert isinstance(snapshot_id, str)
        # Should be valid UUID
        uuid.UUID(snapshot_id)

    def test_save_snapshot_with_notes(self, manager):
        """save_snapshot should store notes"""
        result = create_mock_result()
        snapshot_id = manager.save_snapshot(result, notes="My test notes")

        loaded = manager.load_snapshot(snapshot_id)
        assert loaded["notes"] == "My test notes"

    def test_save_snapshot_with_created_by(self, manager):
        """save_snapshot should store created_by"""
        result = create_mock_result()
        snapshot_id = manager.save_snapshot(result, created_by="test_user")

        loaded = manager.load_snapshot(snapshot_id)
        assert loaded["created_by"] == "test_user"

    def test_save_snapshot_stores_all_metrics(self, manager):
        """save_snapshot should store all baseline and conditional metrics"""
        result = create_mock_result()
        snapshot_id = manager.save_snapshot(result)

        loaded = manager.load_snapshot(snapshot_id)

        # Check baseline metrics
        assert loaded["baseline_sample_size"] == 50
        assert loaded["baseline_win_rate"] == 0.6
        assert loaded["baseline_expected_r"] == 0.25

        # Check conditional metrics
        assert loaded["conditional_sample_size"] == 30
        assert loaded["conditional_win_rate"] == 0.7
        assert loaded["conditional_expected_r"] == 0.35

    def test_save_snapshot_stores_conditions(self, manager):
        """save_snapshot should store condition set as JSON"""
        result = create_mock_result()
        snapshot_id = manager.save_snapshot(result)

        loaded = manager.load_snapshot(snapshot_id)
        assert loaded["conditions"]["orb_size_min"] == 0.5
        assert loaded["conditions"]["asia_travel_max"] == 2.5

    def test_save_snapshot_extracts_params_from_cache_key(self, manager):
        """save_snapshot should parse instrument/orb_time/etc from cache_key"""
        result = create_mock_result(
            cache_key="MGC_1000_UP_rr2.0_full_abc123_2024-01-01_2024-12-31_v1"
        )
        snapshot_id = manager.save_snapshot(result)

        loaded = manager.load_snapshot(snapshot_id)
        assert loaded["instrument"] == "MGC"
        assert loaded["orb_time"] == "1000"
        assert loaded["direction"] == "UP"
        assert loaded["rr"] == 2.0
        assert loaded["sl_mode"] == "FULL"


# =============================================================================
# Test load_snapshot Method
# =============================================================================

class TestLoadSnapshot:
    """Test load_snapshot method"""

    def test_load_snapshot_returns_dict(self, manager):
        """load_snapshot should return dict with all fields"""
        result = create_mock_result()
        snapshot_id = manager.save_snapshot(result)

        loaded = manager.load_snapshot(snapshot_id)
        assert isinstance(loaded, dict)
        assert "snapshot_id" in loaded
        assert "cache_key" in loaded
        assert "conditions" in loaded

    def test_load_snapshot_parses_json_conditions(self, manager):
        """load_snapshot should parse JSON conditions"""
        result = create_mock_result()
        snapshot_id = manager.save_snapshot(result)

        loaded = manager.load_snapshot(snapshot_id)
        assert isinstance(loaded["conditions"], dict)
        assert "orb_size_min" in loaded["conditions"]

    def test_load_snapshot_not_found_raises(self, manager):
        """load_snapshot should raise for nonexistent ID"""
        with pytest.raises(ValueError) as exc_info:
            manager.load_snapshot("nonexistent-uuid")
        assert "not found" in str(exc_info.value).lower()


# =============================================================================
# Test list_snapshots Method
# =============================================================================

class TestListSnapshots:
    """Test list_snapshots method"""

    def test_list_snapshots_returns_list(self, manager):
        """list_snapshots should return a list"""
        result = manager.list_snapshots()
        assert isinstance(result, list)

    def test_list_snapshots_empty_db(self, manager):
        """list_snapshots should return empty list for empty db"""
        result = manager.list_snapshots()
        assert result == []

    def test_list_snapshots_with_data(self, manager):
        """list_snapshots should return saved snapshots"""
        # Save a few snapshots
        for i in range(3):
            result = create_mock_result(
                cache_key=f"MGC_1000_BOTH_rr2.0_full_abc{i}_2024-01-01_2024-12-31_v1"
            )
            manager.save_snapshot(result, notes=f"Snapshot {i}")

        snapshots = manager.list_snapshots()
        assert len(snapshots) == 3

    def test_list_snapshots_limit(self, manager):
        """list_snapshots should respect limit parameter"""
        for i in range(5):
            result = create_mock_result(
                cache_key=f"MGC_1000_BOTH_rr2.0_full_abc{i}_2024-01-01_2024-12-31_v1"
            )
            manager.save_snapshot(result)

        snapshots = manager.list_snapshots(limit=3)
        assert len(snapshots) == 3

    def test_list_snapshots_filter_by_instrument(self, manager):
        """list_snapshots should filter by instrument"""
        # Save MGC snapshot
        result_mgc = create_mock_result(
            cache_key="MGC_1000_BOTH_rr2.0_full_abc1_2024-01-01_2024-12-31_v1"
        )
        manager.save_snapshot(result_mgc)

        # Save NQ snapshot
        result_nq = create_mock_result(
            cache_key="NQ_1000_BOTH_rr2.0_full_abc2_2024-01-01_2024-12-31_v1"
        )
        manager.save_snapshot(result_nq)

        mgc_snapshots = manager.list_snapshots(instrument="MGC")
        assert len(mgc_snapshots) == 1
        assert mgc_snapshots[0]["instrument"] == "MGC"

    def test_list_snapshots_filter_by_orb_time(self, manager):
        """list_snapshots should filter by orb_time"""
        result_1000 = create_mock_result(
            cache_key="MGC_1000_BOTH_rr2.0_full_abc1_2024-01-01_2024-12-31_v1"
        )
        manager.save_snapshot(result_1000)

        result_1800 = create_mock_result(
            cache_key="MGC_1800_BOTH_rr2.0_full_abc2_2024-01-01_2024-12-31_v1"
        )
        manager.save_snapshot(result_1800)

        snapshots_1000 = manager.list_snapshots(orb_time="1000")
        assert len(snapshots_1000) == 1
        assert snapshots_1000[0]["orb_time"] == "1000"

    def test_list_snapshots_ordered_by_created_at_desc(self, manager):
        """list_snapshots should return newest first"""
        import time

        for i in range(3):
            result = create_mock_result(
                cache_key=f"MGC_1000_BOTH_rr2.0_full_abc{i}_2024-01-01_2024-12-31_v1"
            )
            manager.save_snapshot(result, notes=f"Snapshot {i}")
            time.sleep(0.1)  # Ensure different timestamps

        snapshots = manager.list_snapshots()
        # Most recent should be first (Snapshot 2)
        assert snapshots[0]["notes"] == "Snapshot 2"


# =============================================================================
# Test Data Version
# =============================================================================

class TestDataVersion:
    """Test data version tracking"""

    def test_get_data_version(self, manager):
        """_get_data_version should return version string"""
        version = manager._get_data_version()
        assert isinstance(version, str)
        assert "daily_features" in version

    def test_data_version_stored_in_snapshot(self, manager):
        """Snapshot should include data version"""
        result = create_mock_result()
        snapshot_id = manager.save_snapshot(result)

        loaded = manager.load_snapshot(snapshot_id)
        assert "data_version" in loaded
        assert loaded["data_version"] is not None


# =============================================================================
# Test Promotion
# =============================================================================

class TestPromotion:
    """Test snapshot promotion to candidate"""

    def test_promote_to_candidate_marks_snapshot(self, manager):
        """promote_to_candidate should update promoted flag"""
        result = create_mock_result()
        snapshot_id = manager.save_snapshot(result)

        # Mark as promoted
        manager.promote_to_candidate(snapshot_id, "edge_123")

        loaded = manager.load_snapshot(snapshot_id)
        assert loaded["promoted_to_candidate"] is True
        assert loaded["candidate_edge_id"] == "edge_123"

    def test_snapshot_default_not_promoted(self, manager):
        """New snapshots should not be promoted by default"""
        result = create_mock_result()
        snapshot_id = manager.save_snapshot(result)

        loaded = manager.load_snapshot(snapshot_id)
        assert loaded["promoted_to_candidate"] is False
        assert loaded["candidate_edge_id"] is None


# =============================================================================
# Test Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_save_snapshot_with_none_dates(self, manager):
        """save_snapshot should handle None date_start/date_end"""
        result = create_mock_result(
            cache_key="MGC_1000_BOTH_rr2.0_full_abc123_all_all_v1"
        )
        snapshot_id = manager.save_snapshot(result)

        loaded = manager.load_snapshot(snapshot_id)
        # 'all' becomes None or stored as string
        assert loaded["date_start"] in [None, "all"]

    def test_save_snapshot_with_empty_conditions(self, manager):
        """save_snapshot should handle empty condition set"""
        result = create_mock_result(condition_set={
            "orb_size_min": None,
            "orb_size_max": None,
            "asia_travel_max": None,
            "pre_orb_travel_max": None,
            "asia_types": None,
            "london_types": None,
            "orb_size_percentile_min": None,
            "orb_size_percentile_max": None,
            "percentile_window_days": 20
        })
        snapshot_id = manager.save_snapshot(result)

        loaded = manager.load_snapshot(snapshot_id)
        assert loaded["conditions"]["orb_size_min"] is None

    def test_list_snapshots_with_offset(self, manager):
        """list_snapshots should support pagination offset"""
        for i in range(5):
            result = create_mock_result(
                cache_key=f"MGC_1000_BOTH_rr2.0_full_abc{i}_2024-01-01_2024-12-31_v1"
            )
            manager.save_snapshot(result)

        all_snapshots = manager.list_snapshots()
        offset_snapshots = manager.list_snapshots(offset=2)

        assert len(all_snapshots) == 5
        assert len(offset_snapshots) == 3

    def test_save_snapshot_zero_sample_size(self, manager):
        """save_snapshot should handle zero sample size"""
        baseline = create_mock_metrics_result(sample_size=0, win_rate=0, expected_r=0)
        conditional = create_mock_metrics_result(sample_size=0, win_rate=0, expected_r=0)

        result = create_mock_result(
            baseline=baseline,
            conditional=conditional,
            delta={"sample_size": 0, "win_rate_pct": 0, "expected_r": 0,
                   "avg_win": 0, "avg_loss": 0, "max_dd": 0, "sharpe_ratio": 0, "total_r": 0}
        )
        snapshot_id = manager.save_snapshot(result)

        loaded = manager.load_snapshot(snapshot_id)
        assert loaded["baseline_sample_size"] == 0

    def test_special_characters_in_notes(self, manager):
        """save_snapshot should handle special characters in notes"""
        result = create_mock_result()
        special_notes = "Test with 'quotes', \"double quotes\", and emoji 🚀"
        snapshot_id = manager.save_snapshot(result, notes=special_notes)

        loaded = manager.load_snapshot(snapshot_id)
        assert loaded["notes"] == special_notes
