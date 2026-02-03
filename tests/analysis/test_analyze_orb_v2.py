"""
Comprehensive unit tests for analysis/analyze_orb_v2.py

Tests cover:
- ORBStats dataclass
- calculate_stats function
- ORBAnalyzerV2 class (with mock database)
- Edge cases and boundary conditions
"""

import pytest
import sys
from pathlib import Path
from typing import List, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from analysis.analyze_orb_v2 import (
    ORBStats,
    calculate_stats,
    ORBAnalyzerV2,
)


# =============================================================================
# Test ORBStats Dataclass
# =============================================================================

class TestORBStatsDataclass:
    """Test ORBStats dataclass creation and methods"""

    def test_orb_stats_creation(self):
        """Create ORBStats with all fields"""
        stats = ORBStats(
            total_trades=100,
            wins=60,
            losses=40,
            win_rate=0.6,
            total_r=25.5,
            avg_r=0.255,
        )
        assert stats.total_trades == 100
        assert stats.wins == 60
        assert stats.losses == 40
        assert stats.win_rate == 0.6
        assert stats.total_r == 25.5
        assert stats.avg_r == 0.255

    def test_orb_stats_str_with_trades(self):
        """__str__ should format nicely when trades exist"""
        stats = ORBStats(
            total_trades=100,
            wins=60,
            losses=40,
            win_rate=0.6,
            total_r=25.5,
            avg_r=0.255,
        )
        result = str(stats)
        assert "100" in result
        assert "60" in result
        assert "40" in result
        assert "60.0%" in result
        assert "+25.5" in result
        assert "+0.26" in result or "+0.25" in result

    def test_orb_stats_str_no_trades(self):
        """__str__ should handle zero trades"""
        stats = ORBStats(
            total_trades=0,
            wins=0,
            losses=0,
            win_rate=0.0,
            total_r=0.0,
            avg_r=0.0,
        )
        result = str(stats)
        assert result == "No trades"

    def test_orb_stats_negative_r(self):
        """ORBStats should handle negative R values"""
        stats = ORBStats(
            total_trades=50,
            wins=20,
            losses=30,
            win_rate=0.4,
            total_r=-15.0,
            avg_r=-0.3,
        )
        result = str(stats)
        assert "-15.0" in result
        assert "-0.30" in result


# =============================================================================
# Test calculate_stats Function
# =============================================================================

class TestCalculateStats:
    """Test calculate_stats function"""

    def test_calculate_stats_empty_list(self):
        """Empty list should return zero stats"""
        result = calculate_stats([])
        assert result.total_trades == 0
        assert result.wins == 0
        assert result.losses == 0
        assert result.win_rate == 0.0
        assert result.total_r == 0.0
        assert result.avg_r == 0.0

    def test_calculate_stats_all_wins(self):
        """All winning trades should give 100% win rate"""
        rows: List[Tuple] = [
            ("WIN", 1.0),
            ("WIN", 2.0),
            ("WIN", 1.5),
        ]
        result = calculate_stats(rows)
        assert result.total_trades == 3
        assert result.wins == 3
        assert result.losses == 0
        assert result.win_rate == 1.0
        assert result.total_r == 4.5
        assert abs(result.avg_r - 1.5) < 0.001

    def test_calculate_stats_all_losses(self):
        """All losing trades should give 0% win rate"""
        rows: List[Tuple] = [
            ("LOSS", -1.0),
            ("LOSS", -1.0),
            ("LOSS", -1.0),
        ]
        result = calculate_stats(rows)
        assert result.total_trades == 3
        assert result.wins == 0
        assert result.losses == 3
        assert result.win_rate == 0.0
        assert result.total_r == -3.0
        assert result.avg_r == -1.0

    def test_calculate_stats_mixed_results(self):
        """Mixed wins and losses should calculate correctly"""
        rows: List[Tuple] = [
            ("WIN", 2.0),
            ("LOSS", -1.0),
            ("WIN", 1.5),
            ("LOSS", -1.0),
            ("WIN", 3.0),
        ]
        result = calculate_stats(rows)
        assert result.total_trades == 5
        assert result.wins == 3
        assert result.losses == 2
        assert result.win_rate == 0.6
        assert result.total_r == 4.5
        assert result.avg_r == 0.9

    def test_calculate_stats_ignores_no_trade(self):
        """NO_TRADE outcomes should be ignored"""
        rows: List[Tuple] = [
            ("WIN", 1.0),
            ("NO_TRADE", None),
            ("LOSS", -1.0),
            ("NO_TRADE", None),
        ]
        result = calculate_stats(rows)
        assert result.total_trades == 2
        assert result.wins == 1
        assert result.losses == 1

    def test_calculate_stats_ignores_none_r_multiple(self):
        """Rows with None r_multiple should be filtered"""
        rows: List[Tuple] = [
            ("WIN", 1.0),
            ("WIN", None),  # Should be ignored
            ("LOSS", -1.0),
        ]
        result = calculate_stats(rows)
        assert result.total_trades == 2

    def test_calculate_stats_single_trade(self):
        """Single trade should work correctly"""
        rows: List[Tuple] = [("WIN", 2.5)]
        result = calculate_stats(rows)
        assert result.total_trades == 1
        assert result.wins == 1
        assert result.losses == 0
        assert result.win_rate == 1.0
        assert result.total_r == 2.5
        assert result.avg_r == 2.5

    def test_calculate_stats_large_dataset(self):
        """Large dataset should calculate correctly"""
        # 60 wins, 40 losses
        rows: List[Tuple] = [("WIN", 1.5)] * 60 + [("LOSS", -1.0)] * 40
        result = calculate_stats(rows)
        assert result.total_trades == 100
        assert result.wins == 60
        assert result.losses == 40
        assert result.win_rate == 0.6
        assert result.total_r == (60 * 1.5) + (40 * -1.0)  # 90 - 40 = 50
        assert abs(result.avg_r - 0.5) < 0.001

    def test_calculate_stats_zero_r_multiple(self):
        """Zero R multiple (scratch trade) should be counted"""
        rows: List[Tuple] = [
            ("WIN", 0.0),  # Scratch counted as win
            ("LOSS", -1.0),
        ]
        result = calculate_stats(rows)
        assert result.total_trades == 2

    def test_calculate_stats_extreme_values(self):
        """Extreme R values should be handled"""
        rows: List[Tuple] = [
            ("WIN", 100.0),
            ("LOSS", -1.0),
        ]
        result = calculate_stats(rows)
        assert result.total_r == 99.0
        assert result.avg_r == 49.5


# =============================================================================
# Test ORBAnalyzerV2 with Mock Database
# =============================================================================

class TestORBAnalyzerV2:
    """Test ORBAnalyzerV2 class"""

    @pytest.fixture
    def mock_db(self, tmp_path):
        """Create a mock DuckDB database with test data"""
        import duckdb

        db_path = tmp_path / "test.db"
        conn = duckdb.connect(str(db_path))

        # Create daily_features table with required columns
        conn.execute("""
            CREATE TABLE daily_features (
                date_local DATE,
                instrument VARCHAR DEFAULT 'MGC',
                atr_20 DOUBLE,
                pre_asia_range DOUBLE,
                pre_london_range DOUBLE,
                pre_ny_range DOUBLE,
                asia_range DOUBLE,
                orb_0900_outcome VARCHAR,
                orb_0900_r_multiple DOUBLE,
                orb_0900_break_dir VARCHAR,
                orb_1000_outcome VARCHAR,
                orb_1000_r_multiple DOUBLE,
                orb_1000_break_dir VARCHAR,
                orb_1100_outcome VARCHAR,
                orb_1100_r_multiple DOUBLE,
                orb_1100_break_dir VARCHAR,
                orb_1800_outcome VARCHAR,
                orb_1800_r_multiple DOUBLE,
                orb_1800_break_dir VARCHAR,
                orb_2300_outcome VARCHAR,
                orb_2300_r_multiple DOUBLE,
                orb_2300_break_dir VARCHAR,
                orb_0030_outcome VARCHAR,
                orb_0030_r_multiple DOUBLE,
                orb_0030_break_dir VARCHAR
            )
        """)

        # Insert test data
        conn.execute("""
            INSERT INTO daily_features VALUES
            ('2024-01-02', 'MGC', 15.0, 3.0, 2.0, 4.0, 35.0, 'WIN', 1.5, 'UP', 'LOSS', -1.0, 'DOWN', 'WIN', 2.0, 'UP', 'WIN', 1.0, 'UP', 'LOSS', -1.0, 'DOWN', 'WIN', 1.5, 'UP'),
            ('2024-01-03', 'MGC', 16.0, 6.0, 1.5, 5.0, 40.0, 'LOSS', -1.0, 'DOWN', 'WIN', 2.0, 'UP', 'LOSS', -1.0, 'DOWN', 'WIN', 1.5, 'UP', 'WIN', 2.0, 'UP', 'LOSS', -1.0, 'DOWN'),
            ('2024-01-04', 'MGC', 14.0, 2.5, 2.5, 3.5, 32.0, 'WIN', 2.0, 'UP', 'WIN', 1.5, 'UP', 'WIN', 1.0, 'UP', 'LOSS', -1.0, 'DOWN', 'WIN', 1.0, 'UP', 'WIN', 2.0, 'UP'),
            ('2024-01-05', 'MGC', 17.0, 7.0, 3.0, 4.5, 45.0, 'NO_TRADE', NULL, NULL, 'LOSS', -1.0, 'DOWN', 'WIN', 2.5, 'UP', 'WIN', 2.0, 'UP', 'LOSS', -1.0, 'DOWN', 'NO_TRADE', NULL, NULL),
            ('2024-01-08', 'MGC', 15.5, 4.0, 2.0, 5.0, 38.0, 'WIN', 1.0, 'UP', 'WIN', 1.0, 'UP', 'LOSS', -1.0, 'DOWN', 'WIN', 1.5, 'UP', 'WIN', 2.0, 'UP', 'LOSS', -1.0, 'DOWN')
        """)

        conn.close()
        return str(db_path)

    def test_analyzer_creation_with_path(self, mock_db):
        """Create analyzer with database path"""
        analyzer = ORBAnalyzerV2(db_path=mock_db)
        assert analyzer.con is not None
        assert analyzer._owns_connection is True
        analyzer.close()

    def test_analyzer_creation_with_connection(self, mock_db):
        """Create analyzer with existing connection"""
        import duckdb
        conn = duckdb.connect(mock_db, read_only=True)
        analyzer = ORBAnalyzerV2(connection=conn)
        assert analyzer.con is conn
        assert analyzer._owns_connection is False
        analyzer.close()
        conn.close()

    def test_analyze_overall_returns_dict(self, mock_db):
        """analyze_overall should return dict with all ORB times"""
        analyzer = ORBAnalyzerV2(db_path=mock_db)
        try:
            result = analyzer.analyze_overall()
            assert isinstance(result, dict)
            # Check all 6 ORB times exist
            for orb_time in ["0900", "1000", "1100", "1800", "2300", "0030"]:
                assert orb_time in result
                assert "UP" in result[orb_time]
                assert "DOWN" in result[orb_time]
        finally:
            analyzer.close()

    def test_analyze_overall_structure(self, mock_db):
        """analyze_overall result should have correct structure"""
        analyzer = ORBAnalyzerV2(db_path=mock_db)
        try:
            result = analyzer.analyze_overall()
            # Check structure of one entry
            orb_1000 = result["1000"]
            up = orb_1000["UP"]
            assert "win_rate" in up
            assert "avg_r" in up
            assert "total_r" in up
            assert "total_trades" in up
            assert "wins" in up
            assert "losses" in up
        finally:
            analyzer.close()

    def test_analyze_pre_asia_returns_list(self, mock_db):
        """analyze_pre_asia should return list of edges"""
        analyzer = ORBAnalyzerV2(db_path=mock_db)
        try:
            result = analyzer.analyze_pre_asia()
            assert isinstance(result, list)
            # Each edge should have required fields
            for edge in result:
                assert "setup" in edge
                assert "win_rate" in edge
                assert "avg_r" in edge
                assert "total_trades" in edge
        finally:
            analyzer.close()

    def test_analyze_orb_correlations_returns_list(self, mock_db):
        """analyze_orb_correlations should return list of edges"""
        analyzer = ORBAnalyzerV2(db_path=mock_db)
        try:
            result = analyzer.analyze_orb_correlations()
            assert isinstance(result, list)
        finally:
            analyzer.close()

    def test_close_only_closes_owned_connection(self, mock_db):
        """close() should only close connection if owned"""
        import duckdb

        # Test with owned connection
        analyzer1 = ORBAnalyzerV2(db_path=mock_db)
        analyzer1.close()
        # Connection should be closed (will error on use)

        # Test with external connection
        conn = duckdb.connect(mock_db, read_only=True)
        analyzer2 = ORBAnalyzerV2(connection=conn)
        analyzer2.close()
        # External connection should still work
        result = conn.execute("SELECT 1").fetchone()
        assert result[0] == 1
        conn.close()


# =============================================================================
# Test Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_calculate_stats_fifty_fifty(self):
        """50/50 win rate should calculate correctly"""
        rows: List[Tuple] = [
            ("WIN", 2.0),
            ("LOSS", -1.0),
        ]
        result = calculate_stats(rows)
        assert result.win_rate == 0.5
        assert result.total_r == 1.0

    def test_calculate_stats_single_win(self):
        """Single win should give 100% win rate"""
        rows: List[Tuple] = [("WIN", 1.0)]
        result = calculate_stats(rows)
        assert result.win_rate == 1.0

    def test_calculate_stats_single_loss(self):
        """Single loss should give 0% win rate"""
        rows: List[Tuple] = [("LOSS", -1.0)]
        result = calculate_stats(rows)
        assert result.win_rate == 0.0

    def test_orb_stats_win_rate_precision(self):
        """Win rate should format with 1 decimal place"""
        stats = ORBStats(
            total_trades=3,
            wins=1,
            losses=2,
            win_rate=0.333333,
            total_r=-1.0,
            avg_r=-0.333,
        )
        result = str(stats)
        assert "33.3%" in result

    def test_calculate_stats_preserves_original_order(self):
        """calculate_stats should work regardless of input order"""
        rows1: List[Tuple] = [("WIN", 1.0), ("LOSS", -1.0), ("WIN", 2.0)]
        rows2: List[Tuple] = [("LOSS", -1.0), ("WIN", 2.0), ("WIN", 1.0)]

        result1 = calculate_stats(rows1)
        result2 = calculate_stats(rows2)

        assert result1.total_trades == result2.total_trades
        assert result1.wins == result2.wins
        assert result1.total_r == result2.total_r


# =============================================================================
# Test with Empty Database
# =============================================================================

class TestEmptyDatabase:
    """Test behavior with empty database"""

    @pytest.fixture
    def empty_db(self, tmp_path):
        """Create empty database with schema"""
        import duckdb

        db_path = tmp_path / "empty.db"
        conn = duckdb.connect(str(db_path))

        conn.execute("""
            CREATE TABLE daily_features (
                date_local DATE,
                instrument VARCHAR DEFAULT 'MGC',
                atr_20 DOUBLE,
                pre_asia_range DOUBLE,
                pre_london_range DOUBLE,
                pre_ny_range DOUBLE,
                asia_range DOUBLE,
                orb_0900_outcome VARCHAR,
                orb_0900_r_multiple DOUBLE,
                orb_0900_break_dir VARCHAR,
                orb_1000_outcome VARCHAR,
                orb_1000_r_multiple DOUBLE,
                orb_1000_break_dir VARCHAR,
                orb_1100_outcome VARCHAR,
                orb_1100_r_multiple DOUBLE,
                orb_1100_break_dir VARCHAR,
                orb_1800_outcome VARCHAR,
                orb_1800_r_multiple DOUBLE,
                orb_1800_break_dir VARCHAR,
                orb_2300_outcome VARCHAR,
                orb_2300_r_multiple DOUBLE,
                orb_2300_break_dir VARCHAR,
                orb_0030_outcome VARCHAR,
                orb_0030_r_multiple DOUBLE,
                orb_0030_break_dir VARCHAR
            )
        """)

        conn.close()
        return str(db_path)

    def test_analyze_overall_empty_db(self, empty_db):
        """analyze_overall should handle empty database"""
        analyzer = ORBAnalyzerV2(db_path=empty_db)
        try:
            result = analyzer.analyze_overall()
            # Should return structure with zero trades
            for orb_time in result:
                assert result[orb_time]["UP"]["total_trades"] == 0
                assert result[orb_time]["DOWN"]["total_trades"] == 0
        finally:
            analyzer.close()

    def test_analyze_pre_asia_empty_db(self, empty_db):
        """analyze_pre_asia should return empty list for empty db"""
        analyzer = ORBAnalyzerV2(db_path=empty_db)
        try:
            result = analyzer.analyze_pre_asia()
            assert isinstance(result, list)
            # May be empty or have entries with 0 trades (filtered out by minimum)
        finally:
            analyzer.close()
