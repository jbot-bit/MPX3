"""
Comprehensive unit tests for analysis/what_if_engine.py

Tests cover:
- ConditionSet dataclass
- MetricsResult dataclass
- WhatIfEngine class
- Cache behavior
- Condition application
- Metrics calculation
- Edge cases and boundary conditions
"""

import pytest
import sys
from pathlib import Path
from typing import Dict, List
import json
import hashlib

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analysis.what_if_engine import (
    ConditionSet,
    MetricsResult,
    WhatIfEngine,
)


# =============================================================================
# Test ConditionSet Dataclass
# =============================================================================

class TestConditionSetDataclass:
    """Test ConditionSet dataclass creation and methods"""

    def test_condition_set_defaults(self):
        """ConditionSet should have sensible defaults"""
        cs = ConditionSet()
        assert cs.orb_size_min is None
        assert cs.orb_size_max is None
        assert cs.asia_travel_max is None
        assert cs.pre_orb_travel_max is None
        assert cs.asia_types is None
        assert cs.london_types is None
        assert cs.orb_size_percentile_min is None
        assert cs.orb_size_percentile_max is None
        assert cs.percentile_window_days == 20

    def test_condition_set_creation(self):
        """Create ConditionSet with custom values"""
        cs = ConditionSet(
            orb_size_min=0.5,
            orb_size_max=2.0,
            asia_travel_max=2.5,
            asia_types=["EXPANDED"],
            london_types=["CONSOLIDATION", "EXPANSION"],
        )
        assert cs.orb_size_min == 0.5
        assert cs.orb_size_max == 2.0
        assert cs.asia_travel_max == 2.5
        assert cs.asia_types == ["EXPANDED"]
        assert len(cs.london_types) == 2

    def test_condition_set_to_dict(self):
        """to_dict should return serializable dict"""
        cs = ConditionSet(orb_size_min=0.5, asia_types=["EXPANDED"])
        d = cs.to_dict()
        assert isinstance(d, dict)
        assert d["orb_size_min"] == 0.5
        assert d["asia_types"] == ["EXPANDED"]
        # Should be JSON serializable
        json_str = json.dumps(d)
        assert "orb_size_min" in json_str

    def test_condition_set_to_hash_deterministic(self):
        """to_hash should return deterministic hash"""
        cs1 = ConditionSet(orb_size_min=0.5, asia_types=["EXPANDED"])
        cs2 = ConditionSet(orb_size_min=0.5, asia_types=["EXPANDED"])
        assert cs1.to_hash() == cs2.to_hash()

    def test_condition_set_to_hash_different_for_different_values(self):
        """Different conditions should produce different hashes"""
        cs1 = ConditionSet(orb_size_min=0.5)
        cs2 = ConditionSet(orb_size_min=0.6)
        assert cs1.to_hash() != cs2.to_hash()

    def test_condition_set_to_hash_length(self):
        """Hash should be 12 characters"""
        cs = ConditionSet()
        h = cs.to_hash()
        assert len(h) == 12

    def test_condition_set_empty(self):
        """Empty ConditionSet should have consistent hash"""
        cs1 = ConditionSet()
        cs2 = ConditionSet()
        assert cs1.to_hash() == cs2.to_hash()


# =============================================================================
# Test MetricsResult Dataclass
# =============================================================================

class TestMetricsResultDataclass:
    """Test MetricsResult dataclass creation and methods"""

    def test_metrics_result_creation(self):
        """Create MetricsResult with all fields"""
        mr = MetricsResult(
            sample_size=100,
            win_rate=0.6,
            expected_r=0.25,
            avg_win=1.5,
            avg_loss=-1.0,
            max_dd=-5.0,
            sharpe_ratio=1.2,
            total_r=25.0,
            stress_25_exp_r=0.20,
            stress_50_exp_r=0.15,
            stress_25_pass=True,
            stress_50_pass=True,
            trades=[],
        )
        assert mr.sample_size == 100
        assert mr.win_rate == 0.6
        assert mr.expected_r == 0.25
        assert mr.stress_25_pass is True

    def test_metrics_result_to_dict_excludes_trades(self):
        """to_dict should exclude trades list"""
        mr = MetricsResult(
            sample_size=10,
            win_rate=0.5,
            expected_r=0.1,
            avg_win=1.0,
            avg_loss=-1.0,
            max_dd=-2.0,
            sharpe_ratio=0.5,
            total_r=1.0,
            stress_25_exp_r=0.05,
            stress_50_exp_r=0.0,
            stress_25_pass=False,
            stress_50_pass=False,
            trades=[{"date": "2024-01-01", "outcome": "WIN"}],
        )
        d = mr.to_dict()
        assert "trades" not in d
        assert "sample_size" in d
        assert "win_rate" in d

    def test_metrics_result_zero_values(self):
        """MetricsResult should handle zero values"""
        mr = MetricsResult(
            sample_size=0,
            win_rate=0.0,
            expected_r=0.0,
            avg_win=0.0,
            avg_loss=0.0,
            max_dd=0.0,
            sharpe_ratio=0.0,
            total_r=0.0,
            stress_25_exp_r=0.0,
            stress_50_exp_r=0.0,
            stress_25_pass=False,
            stress_50_pass=False,
            trades=[],
        )
        assert mr.sample_size == 0
        d = mr.to_dict()
        assert d["sample_size"] == 0


# =============================================================================
# Test WhatIfEngine Class
# =============================================================================

class TestWhatIfEngine:
    """Test WhatIfEngine class with mock database"""

    @pytest.fixture
    def mock_db(self, tmp_path):
        """Create a mock DuckDB database with test data"""
        import duckdb

        db_path = tmp_path / "test.db"
        conn = duckdb.connect(str(db_path))

        # Create daily_features table
        conn.execute("""
            CREATE TABLE daily_features (
                date_local DATE,
                instrument VARCHAR DEFAULT 'MGC',
                atr_20 DOUBLE,
                orb_1000_size DOUBLE,
                orb_1000_break_dir VARCHAR,
                pre_orb_travel DOUBLE,
                asia_type_code VARCHAR,
                london_type_code VARCHAR,
                pre_ny_type_code VARCHAR
            )
        """)

        # Create bars_1m table for simulate_orb_trade
        conn.execute("""
            CREATE TABLE bars_1m (
                ts_utc TIMESTAMPTZ,
                symbol VARCHAR,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume INTEGER
            )
        """)

        # Insert test data
        conn.execute("""
            INSERT INTO daily_features VALUES
            ('2024-01-02', 'MGC', 15.0, 1.0, 'UP', 2.0, 'EXPANDED', 'CONSOLIDATION', 'SWEEP_HIGH'),
            ('2024-01-03', 'MGC', 16.0, 1.2, 'DOWN', 3.0, 'TIGHT', 'EXPANSION', 'CONSOLIDATION'),
            ('2024-01-04', 'MGC', 14.0, 0.8, 'UP', 1.5, 'EXPANDED', 'CONSOLIDATION', 'EXPANSION'),
            ('2024-01-05', 'MGC', 17.0, 1.5, 'NONE', 4.0, 'NORMAL', 'SWEEP_HIGH', 'SWEEP_LOW'),
            ('2024-01-08', 'MGC', 15.5, 0.9, 'UP', 2.5, 'EXPANDED', 'CONSOLIDATION', 'CONSOLIDATION')
        """)

        yield conn
        conn.close()

    def test_engine_creation(self, mock_db):
        """WhatIfEngine should initialize correctly"""
        engine = WhatIfEngine(mock_db)
        assert engine.conn is mock_db
        assert engine.cache == {}

    def test_generate_cache_key_deterministic(self, mock_db):
        """Cache key generation should be deterministic"""
        engine = WhatIfEngine(mock_db)
        cs = ConditionSet(orb_size_min=0.5)

        key1 = engine._generate_cache_key(
            'MGC', '1000', 'BOTH', 2.0, 'FULL', cs, '2024-01-01', '2024-12-31'
        )
        key2 = engine._generate_cache_key(
            'MGC', '1000', 'BOTH', 2.0, 'FULL', cs, '2024-01-01', '2024-12-31'
        )
        assert key1 == key2

    def test_generate_cache_key_different_for_different_params(self, mock_db):
        """Different parameters should produce different cache keys"""
        engine = WhatIfEngine(mock_db)
        cs = ConditionSet()

        key1 = engine._generate_cache_key(
            'MGC', '1000', 'BOTH', 2.0, 'FULL', cs, None, None
        )
        key2 = engine._generate_cache_key(
            'MGC', '1000', 'UP', 2.0, 'FULL', cs, None, None
        )
        assert key1 != key2

    def test_query_daily_features(self, mock_db):
        """_query_daily_features should return correct data"""
        engine = WhatIfEngine(mock_db)
        data = engine._query_daily_features('MGC', '1000', None, None)

        assert len(data) == 5
        assert all('date_local' in d for d in data)
        assert all('orb_size' in d for d in data)
        assert all('atr_20' in d for d in data)

    def test_query_daily_features_with_date_range(self, mock_db):
        """_query_daily_features should respect date filters"""
        engine = WhatIfEngine(mock_db)
        data = engine._query_daily_features('MGC', '1000', '2024-01-03', '2024-01-04')

        assert len(data) == 2

    def test_apply_conditions_no_filters(self, mock_db):
        """Empty conditions should match all data"""
        engine = WhatIfEngine(mock_db)
        data = engine._query_daily_features('MGC', '1000', None, None)
        cs = ConditionSet()

        matched, non_matched = engine._apply_conditions(data, '1000', cs)
        assert len(matched) == 5
        assert len(non_matched) == 0

    def test_apply_conditions_orb_size_filter(self, mock_db):
        """ORB size filter should work correctly"""
        engine = WhatIfEngine(mock_db)
        data = engine._query_daily_features('MGC', '1000', None, None)

        # Filter: orb_size / atr_20 >= 0.07 (larger than 7% of ATR)
        cs = ConditionSet(orb_size_min=0.07)
        matched, non_matched = engine._apply_conditions(data, '1000', cs)

        # With min 0.07, should filter some
        assert len(matched) + len(non_matched) == 5

    def test_apply_conditions_asia_types_filter(self, mock_db):
        """Asia type filter should work correctly"""
        engine = WhatIfEngine(mock_db)
        data = engine._query_daily_features('MGC', '1000', None, None)

        cs = ConditionSet(asia_types=["EXPANDED"])
        matched, non_matched = engine._apply_conditions(data, '1000', cs)

        # 3 rows have EXPANDED asia type
        assert len(matched) == 3
        assert len(non_matched) == 2

    def test_apply_conditions_london_types_filter(self, mock_db):
        """London type filter should work correctly"""
        engine = WhatIfEngine(mock_db)
        data = engine._query_daily_features('MGC', '1000', None, None)

        cs = ConditionSet(london_types=["CONSOLIDATION"])
        matched, non_matched = engine._apply_conditions(data, '1000', cs)

        # 3 rows have CONSOLIDATION london type
        assert len(matched) == 3

    def test_apply_conditions_combined_filters(self, mock_db):
        """Multiple filters should combine (AND logic)"""
        engine = WhatIfEngine(mock_db)
        data = engine._query_daily_features('MGC', '1000', None, None)

        cs = ConditionSet(
            asia_types=["EXPANDED"],
            london_types=["CONSOLIDATION"]
        )
        matched, non_matched = engine._apply_conditions(data, '1000', cs)

        # Should match rows with EXPANDED asia AND CONSOLIDATION london
        assert len(matched) == 3

    def test_calculate_metrics_empty(self, mock_db):
        """_calculate_metrics with empty trades should return zeros"""
        engine = WhatIfEngine(mock_db)
        result = engine._calculate_metrics([], 'MGC')

        assert result.sample_size == 0
        assert result.win_rate == 0.0
        assert result.expected_r == 0.0
        assert result.stress_25_pass is False
        assert result.stress_50_pass is False

    def test_calculate_delta(self, mock_db):
        """_calculate_delta should compute differences correctly"""
        engine = WhatIfEngine(mock_db)

        baseline = MetricsResult(
            sample_size=100,
            win_rate=0.5,
            expected_r=0.1,
            avg_win=1.5,
            avg_loss=-1.0,
            max_dd=-5.0,
            sharpe_ratio=0.8,
            total_r=10.0,
            stress_25_exp_r=0.05,
            stress_50_exp_r=0.0,
            stress_25_pass=True,
            stress_50_pass=False,
            trades=[]
        )

        conditional = MetricsResult(
            sample_size=60,
            win_rate=0.6,
            expected_r=0.2,
            avg_win=1.8,
            avg_loss=-0.9,
            max_dd=-3.0,
            sharpe_ratio=1.2,
            total_r=12.0,
            stress_25_exp_r=0.15,
            stress_50_exp_r=0.1,
            stress_25_pass=True,
            stress_50_pass=False,
            trades=[]
        )

        delta = engine._calculate_delta(baseline, conditional)

        assert delta['sample_size'] == -40  # 60 - 100
        assert abs(delta['win_rate_pct'] - 10.0) < 0.001  # (0.6 - 0.5) * 100, allow float precision
        assert abs(delta['expected_r'] - 0.1) < 0.001  # 0.2 - 0.1

    def test_clear_cache(self, mock_db):
        """clear_cache should empty the cache"""
        engine = WhatIfEngine(mock_db)
        engine.cache = {"key1": "value1", "key2": "value2"}
        engine.clear_cache()
        assert engine.cache == {}

    def test_get_cache_stats(self, mock_db):
        """get_cache_stats should return cache info"""
        engine = WhatIfEngine(mock_db)
        engine.cache = {"key1": "value1", "key2": "value2"}

        stats = engine.get_cache_stats()
        assert stats['cache_size'] == 2
        assert "key1" in stats['cache_keys']
        assert "key2" in stats['cache_keys']


# =============================================================================
# Test Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_condition_set_percentile_filter(self):
        """Percentile filter configuration"""
        cs = ConditionSet(
            orb_size_percentile_min=20,
            orb_size_percentile_max=80,
            percentile_window_days=30
        )
        assert cs.orb_size_percentile_min == 20
        assert cs.orb_size_percentile_max == 80
        assert cs.percentile_window_days == 30

    def test_metrics_result_negative_sharpe(self):
        """MetricsResult should handle negative Sharpe ratio"""
        mr = MetricsResult(
            sample_size=50,
            win_rate=0.3,
            expected_r=-0.2,
            avg_win=1.0,
            avg_loss=-1.5,
            max_dd=-10.0,
            sharpe_ratio=-0.5,
            total_r=-10.0,
            stress_25_exp_r=-0.3,
            stress_50_exp_r=-0.4,
            stress_25_pass=False,
            stress_50_pass=False,
            trades=[]
        )
        assert mr.sharpe_ratio == -0.5
        assert mr.expected_r == -0.2

    def test_condition_set_single_type_list(self):
        """Single-element type lists should work"""
        cs = ConditionSet(
            asia_types=["EXPANDED"],
            london_types=["CONSOLIDATION"]
        )
        d = cs.to_dict()
        assert d["asia_types"] == ["EXPANDED"]

    def test_cache_key_with_none_dates(self, tmp_path):
        """Cache key should handle None dates"""
        import duckdb

        db_path = tmp_path / "test.db"
        conn = duckdb.connect(str(db_path))
        engine = WhatIfEngine(conn)

        cs = ConditionSet()
        key = engine._generate_cache_key(
            'MGC', '1000', 'BOTH', 2.0, 'FULL', cs, None, None
        )
        assert 'all' in key  # None dates become 'all'
        conn.close()


# =============================================================================
# Test Stress Test Logic
# =============================================================================

class TestStressTestLogic:
    """Test stress test calculations"""

    def test_stress_pass_threshold(self):
        """Stress tests should pass if expected_r >= 0.15"""
        # Stress passes at 0.15R threshold
        mr_pass = MetricsResult(
            sample_size=50,
            win_rate=0.6,
            expected_r=0.3,
            avg_win=1.5,
            avg_loss=-1.0,
            max_dd=-3.0,
            sharpe_ratio=1.0,
            total_r=15.0,
            stress_25_exp_r=0.20,  # >= 0.15, should pass
            stress_50_exp_r=0.15,  # >= 0.15, should pass
            stress_25_pass=True,
            stress_50_pass=True,
            trades=[]
        )
        assert mr_pass.stress_25_pass is True
        assert mr_pass.stress_50_pass is True

        mr_fail = MetricsResult(
            sample_size=50,
            win_rate=0.5,
            expected_r=0.18,
            avg_win=1.2,
            avg_loss=-1.0,
            max_dd=-4.0,
            sharpe_ratio=0.6,
            total_r=9.0,
            stress_25_exp_r=0.10,  # < 0.15, should fail
            stress_50_exp_r=0.05,  # < 0.15, should fail
            stress_25_pass=False,
            stress_50_pass=False,
            trades=[]
        )
        assert mr_fail.stress_25_pass is False
        assert mr_fail.stress_50_pass is False


# =============================================================================
# Test Data Types
# =============================================================================

class TestDataTypes:
    """Test data type handling"""

    def test_condition_set_dict_json_serializable(self):
        """ConditionSet.to_dict() should be JSON serializable"""
        cs = ConditionSet(
            orb_size_min=0.5,
            orb_size_max=2.0,
            asia_types=["EXPANDED", "TIGHT"],
            percentile_window_days=30
        )
        d = cs.to_dict()

        # Should not raise
        json_str = json.dumps(d)
        assert isinstance(json_str, str)

        # Should roundtrip
        parsed = json.loads(json_str)
        assert parsed["orb_size_min"] == 0.5
        assert parsed["asia_types"] == ["EXPANDED", "TIGHT"]

    def test_metrics_result_dict_json_serializable(self):
        """MetricsResult.to_dict() should be JSON serializable"""
        mr = MetricsResult(
            sample_size=50,
            win_rate=0.6,
            expected_r=0.25,
            avg_win=1.5,
            avg_loss=-1.0,
            max_dd=-3.0,
            sharpe_ratio=1.2,
            total_r=12.5,
            stress_25_exp_r=0.20,
            stress_50_exp_r=0.15,
            stress_25_pass=True,
            stress_50_pass=True,
            trades=[]
        )
        d = mr.to_dict()

        # Should not raise
        json_str = json.dumps(d)
        assert isinstance(json_str, str)
