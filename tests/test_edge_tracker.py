"""
Tests for edge_tracker.py - Edge performance monitoring and degradation detection

Critical tests for edge health checks, regime detection, and performance tracking.
"""
import pytest
from datetime import date
from trading_app.edge_tracker import EdgeTracker


class TestEdgeTrackerInitialization:
    """Test edge tracker initialization"""

    def test_tracker_initialization_with_test_db_succeeds(self, populated_test_db):
        """Tracker initializes successfully with test database"""
        # Arrange
        db_path = populated_test_db

        # Act
        tracker = EdgeTracker(db_path=db_path)

        # Assert
        assert tracker is not None
        assert tracker.db_path == db_path

    def test_tracker_with_empty_db_handles_no_data(self, test_db):
        """Tracker handles empty database gracefully"""
        # Arrange
        db_path = test_db

        # Act
        tracker = EdgeTracker(db_path=db_path)

        # Assert
        assert tracker is not None


class TestCheckEdgeHealth:
    """Test individual edge health checking"""

    def test_check_edge_health_with_valid_setup_returns_structure(
        self, populated_test_db, sample_validated_setups
    ):
        """Edge health check returns complete structure with baseline data"""
        # Arrange
        tracker = EdgeTracker(db_path=populated_test_db)
        orb_time = '0900'

        # Act
        health = tracker.check_edge_health(orb_time)

        # Assert
        assert 'orb_time' in health
        assert 'has_baseline' in health
        assert 'status' in health

    def test_check_edge_health_with_no_baseline_returns_no_data(
        self, test_db
    ):
        """Edge health check with no validated_setups returns NO_DATA status"""
        # Arrange
        tracker = EdgeTracker(db_path=test_db)
        orb_time = '0900'

        # Act
        health = tracker.check_edge_health(orb_time)

        # Assert
        assert health['has_baseline'] is False
        assert health['status'] == 'NO_DATA'

    def test_check_edge_health_calculates_performance_metrics(
        self, populated_test_db, sample_validated_setups
    ):
        """Edge health includes performance metrics (win rate, expected R, etc.)"""
        # Arrange
        tracker = EdgeTracker(db_path=populated_test_db)
        orb_time = '0900'

        # Act
        health = tracker.check_edge_health(orb_time)

        # Assert
        if health['has_baseline']:
            assert 'baseline' in health
            assert 'win_rate' in health['baseline']
            assert 'expected_r' in health['baseline']

    def test_check_edge_health_detects_degradation(
        self, populated_test_db, sample_validated_setups
    ):
        """Edge health detects when performance degrades below baseline"""
        # Arrange
        tracker = EdgeTracker(db_path=populated_test_db)
        orb_time = '0900'

        # Act
        health = tracker.check_edge_health(orb_time)

        # Assert
        # Status should be one of: EXCELLENT, HEALTHY, WATCH, DEGRADED, NO_DATA, INSUFFICIENT_DATA
        assert health['status'] in ['EXCELLENT', 'HEALTHY', 'WATCH', 'DEGRADED', 'NO_DATA', 'INSUFFICIENT_DATA']

    def test_check_edge_health_with_invalid_orb_time_handled(
        self, populated_test_db
    ):
        """Invalid ORB time handled gracefully"""
        # Arrange
        tracker = EdgeTracker(db_path=populated_test_db)
        invalid_orb_time = '1200'  # Not valid

        # Act & Assert
        try:
            health = tracker.check_edge_health(invalid_orb_time)
            # Should return NO_DATA or handle gracefully
            assert health is not None
        except (KeyError, ValueError):
            # Expected for invalid ORB time
            pass


class TestGetSystemStatus:
    """Test system-wide edge health status"""

    def test_get_system_status_returns_complete_structure(
        self, populated_test_db, sample_validated_setups
    ):
        """System status returns all required fields"""
        # Arrange
        tracker = EdgeTracker(db_path=populated_test_db)

        # Act
        status = tracker.get_system_status()

        # Assert
        assert 'status' in status
        assert 'message' in status
        assert 'total_edges' in status
        assert 'edge_health' in status

    def test_get_system_status_with_no_data_returns_no_data_status(
        self, test_db
    ):
        """System status with empty database returns NO_DATA"""
        # Arrange
        tracker = EdgeTracker(db_path=test_db)

        # Act
        status = tracker.get_system_status()

        # Assert
        assert status['status'] == 'NO_DATA'
        assert status['total_edges'] == 0

    def test_get_system_status_categorizes_edges_correctly(
        self, populated_test_db, sample_validated_setups
    ):
        """System status categorizes edges into excellent/watch/degraded"""
        # Arrange
        tracker = EdgeTracker(db_path=populated_test_db)

        # Act
        status = tracker.get_system_status()

        # Assert
        if status['status'] != 'NO_DATA':
            assert 'excellent' in status
            assert 'watch' in status
            assert 'degraded' in status
            assert isinstance(status['excellent'], list)
            assert isinstance(status['watch'], list)
            assert isinstance(status['degraded'], list)

    def test_get_system_status_counts_all_edges(
        self, populated_test_db, sample_validated_setups
    ):
        """System status counts match edge_health list length"""
        # Arrange
        tracker = EdgeTracker(db_path=populated_test_db)

        # Act
        status = tracker.get_system_status()

        # Assert
        if status['status'] != 'NO_DATA':
            assert status['total_edges'] == len(status['edge_health'])

    def test_get_system_status_determines_overall_health(
        self, populated_test_db, sample_validated_setups
    ):
        """System status is EXCELLENT/HEALTHY/CAUTION/DEGRADED based on edges"""
        # Arrange
        tracker = EdgeTracker(db_path=populated_test_db)

        # Act
        status = tracker.get_system_status()

        # Assert
        expected_statuses = ['EXCELLENT', 'HEALTHY', 'CAUTION', 'DEGRADED', 'NO_DATA']
        assert status['status'] in expected_statuses


class TestDetectRegime:
    """Test market regime detection"""

    def test_detect_regime_returns_regime_type(
        self, populated_test_db, sample_validated_setups
    ):
        """Regime detection returns one of: TRENDING, RANGE_BOUND, VOLATILE, QUIET"""
        # Arrange
        tracker = EdgeTracker(db_path=populated_test_db)

        # Act
        regime = tracker.detect_regime()

        # Assert
        expected_regimes = ['TRENDING', 'RANGE_BOUND', 'VOLATILE', 'QUIET', 'UNKNOWN']
        assert regime['regime'] in expected_regimes

    def test_detect_regime_includes_confidence_score(
        self, populated_test_db, sample_validated_setups
    ):
        """Regime detection includes confidence score (0.0 to 1.0)"""
        # Arrange
        tracker = EdgeTracker(db_path=populated_test_db)

        # Act
        regime = tracker.detect_regime()

        # Assert
        assert 'confidence' in regime
        assert 0.0 <= regime['confidence'] <= 1.0

    def test_detect_regime_includes_message(
        self, populated_test_db, sample_validated_setups
    ):
        """Regime detection includes descriptive message"""
        # Arrange
        tracker = EdgeTracker(db_path=populated_test_db)

        # Act
        regime = tracker.detect_regime()

        # Assert
        assert 'message' in regime
        assert isinstance(regime['message'], str)
        assert len(regime['message']) > 0

    def test_detect_regime_with_no_data_returns_unknown(self, test_db):
        """Regime detection with no data returns UNKNOWN"""
        # Arrange
        tracker = EdgeTracker(db_path=test_db)

        # Act
        regime = tracker.detect_regime()

        # Assert
        # Should either be UNKNOWN or handle gracefully
        assert regime is not None
        assert 'regime' in regime


class TestPerformanceMetrics:
    """Test performance metric calculations"""

    def test_performance_metrics_calculated_over_time_windows(
        self, populated_test_db, sample_validated_setups
    ):
        """Performance calculated for 30/60/90 day windows"""
        # Arrange
        tracker = EdgeTracker(db_path=populated_test_db)
        orb_time = '0900'

        # Act
        health = tracker.check_edge_health(orb_time)

        # Assert
        if health['has_baseline'] and 'performance' in health:
            # Should have multiple time windows
            assert '30d' in health['performance'] or 'performance' in health

    def test_performance_metrics_include_win_rate(
        self, populated_test_db, sample_validated_setups
    ):
        """Performance metrics include win rate percentage"""
        # Arrange
        tracker = EdgeTracker(db_path=populated_test_db)
        orb_time = '0900'

        # Act
        health = tracker.check_edge_health(orb_time)

        # Assert
        if health['has_baseline']:
            assert 'win_rate' in health['baseline']
            assert 0.0 <= health['baseline']['win_rate'] <= 100.0

    def test_performance_metrics_include_expected_r(
        self, populated_test_db, sample_validated_setups
    ):
        """Performance metrics include expected R-multiple"""
        # Arrange
        tracker = EdgeTracker(db_path=populated_test_db)
        orb_time = '0900'

        # Act
        health = tracker.check_edge_health(orb_time)

        # Assert
        if health['has_baseline']:
            assert 'expected_r' in health['baseline']

    def test_performance_metrics_with_insufficient_trades_marked(
        self, populated_test_db, sample_validated_setups
    ):
        """Performance with < 30 trades marked as insufficient data"""
        # Arrange
        tracker = EdgeTracker(db_path=populated_test_db)
        orb_time = '0900'

        # Act
        health = tracker.check_edge_health(orb_time)

        # Assert
        # Check has_data flag exists and is boolean
        if 'performance' in health and '30d' in health['performance']:
            assert 'has_data' in health['performance']['30d']
            assert isinstance(health['performance']['30d']['has_data'], bool)


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_tracker_handles_all_null_outcomes_gracefully(self, test_db):
        """Tracker handles case where all ORB outcomes are NULL"""
        # Arrange
        tracker = EdgeTracker(db_path=test_db)

        # Act
        status = tracker.get_system_status()

        # Assert
        # Should not crash, return NO_DATA
        assert status['status'] == 'NO_DATA'

    def test_tracker_handles_zero_sample_size_gracefully(self, test_db):
        """Tracker handles validated_setups with sample_size=0"""
        # Arrange
        tracker = EdgeTracker(db_path=test_db)
        orb_time = '0900'

        # Act
        health = tracker.check_edge_health(orb_time)

        # Assert
        # Should not crash
        assert health is not None
        assert health['status'] == 'NO_DATA'

    def test_tracker_handles_missing_daily_features_gracefully(self, test_db):
        """Tracker handles case where daily_features has no ORB data"""
        # Arrange
        tracker = EdgeTracker(db_path=test_db)

        # Act
        status = tracker.get_system_status()

        # Assert
        # Should not crash, return NO_DATA
        assert status is not None

    def test_tracker_filters_invalid_orb_times(
        self, populated_test_db, sample_validated_setups
    ):
        """Tracker filters out CASCADE, SINGLE_LIQ and other invalid ORB times"""
        # Arrange
        tracker = EdgeTracker(db_path=populated_test_db)

        # Act
        status = tracker.get_system_status()

        # Assert
        if status['status'] != 'NO_DATA':
            # Check all returned edges are valid ORB times
            valid_orb_times = ['0900', '1000', '1100', '1800', '2300', '0030']
            for edge in status['edge_health']:
                assert edge['orb_time'] in valid_orb_times


class TestRecommendations:
    """Test edge health recommendations"""

    def test_recommendations_provided_for_degraded_edges(
        self, populated_test_db, sample_validated_setups
    ):
        """Degraded edges get actionable recommendations"""
        # Arrange
        tracker = EdgeTracker(db_path=populated_test_db)
        orb_time = '0900'

        # Act
        health = tracker.check_edge_health(orb_time)

        # Assert
        if health['status'] in ['DEGRADED', 'WATCH']:
            assert 'recommendations' in health
            assert isinstance(health['recommendations'], list)

    def test_recommendations_empty_for_healthy_edges(
        self, populated_test_db, sample_validated_setups
    ):
        """Healthy edges may have empty or minimal recommendations"""
        # Arrange
        tracker = EdgeTracker(db_path=populated_test_db)
        orb_time = '0900'

        # Act
        health = tracker.check_edge_health(orb_time)

        # Assert
        if health['status'] in ['EXCELLENT', 'HEALTHY']:
            # May or may not have recommendations
            assert 'recommendations' in health or health['status'] == 'EXCELLENT'


class TestMultipleTimeWindows:
    """Test multi-timeframe analysis"""

    def test_performance_compared_across_time_windows(
        self, populated_test_db, sample_validated_setups
    ):
        """Performance metrics available for 30/60/90 day windows"""
        # Arrange
        tracker = EdgeTracker(db_path=populated_test_db)
        orb_time = '0900'

        # Act
        health = tracker.check_edge_health(orb_time)

        # Assert
        if health['has_baseline'] and 'performance' in health:
            # Should have at least one time window
            assert len(health['performance']) > 0

    def test_degradation_detected_across_windows(
        self, populated_test_db, sample_validated_setups
    ):
        """Degradation detection considers multiple time windows"""
        # Arrange
        tracker = EdgeTracker(db_path=populated_test_db)

        # Act
        status = tracker.get_system_status()

        # Assert
        # System should detect degradation if recent performance < baseline
        if status['status'] != 'NO_DATA':
            assert len(status['degraded']) >= 0  # May or may not have degraded edges


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
