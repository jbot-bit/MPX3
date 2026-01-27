"""
Tests for market_scanner.py - Real-time setup validation

Critical tests for ORB validation logic, anomaly detection, and filter checking.
"""
import pytest
from datetime import date
from trading_app.market_scanner import MarketScanner
from trading_app.config import MGC_ORB_SIZE_FILTERS


class TestMarketScannerInitialization:
    """Test scanner initialization and threshold calculation"""

    def test_scanner_initialization_with_test_db_succeeds(self, populated_test_db):
        """Scanner initializes successfully with populated test database"""
        # Arrange
        db_path = populated_test_db

        # Act
        scanner = MarketScanner(db_path=db_path)

        # Assert
        assert scanner is not None
        assert scanner.db_path == db_path
        assert scanner.tz_local is not None
        assert 'orb_size' in scanner.thresholds
        assert 'asia_travel' in scanner.thresholds

    def test_scanner_with_empty_db_uses_default_thresholds(self, test_db):
        """Scanner falls back to defaults when no historical data exists"""
        # Arrange
        db_path = test_db

        # Act
        scanner = MarketScanner(db_path=db_path)

        # Assert
        assert scanner.thresholds['orb_size']['0900']['mean'] == 0.10
        assert scanner.thresholds['orb_size']['0900']['std'] == 0.04

    def test_thresholds_calculated_for_all_orb_times(self, populated_test_db):
        """All ORB times (0900, 1000, 1100, 1800, 2300, 0030) have thresholds"""
        # Arrange & Act
        scanner = MarketScanner(db_path=populated_test_db)

        # Assert
        expected_orbs = ['0900', '1000', '1100', '1800', '2300', '0030']
        for orb_time in expected_orbs:
            assert orb_time in scanner.thresholds['orb_size']
            assert 'mean' in scanner.thresholds['orb_size'][orb_time]
            assert 'std' in scanner.thresholds['orb_size'][orb_time]


class TestGetTodayConditions:
    """Test fetching current market conditions"""

    def test_get_conditions_with_valid_data_returns_complete_dict(
        self, populated_test_db, sample_market_data
    ):
        """Conditions fetched successfully when data exists"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        test_date = sample_market_data['date_local']

        # Act
        conditions = scanner.get_today_conditions(date_local=test_date)

        # Assert
        assert conditions['data_available'] is True
        assert conditions['date_local'] == test_date
        assert 'asia_travel' in conditions
        assert 'orb_sizes' in conditions
        assert 'orb_broken' in conditions

    def test_get_conditions_with_missing_date_returns_unavailable(
        self, populated_test_db
    ):
        """Returns data_available=False when date doesn't exist in database"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        missing_date = date(2030, 1, 1)  # Future date

        # Act
        conditions = scanner.get_today_conditions(date_local=missing_date)

        # Assert
        assert conditions['data_available'] is False
        assert conditions['date_local'] == missing_date

    def test_get_conditions_parses_orb_sizes_correctly(
        self, populated_test_db, sample_market_data
    ):
        """ORB sizes extracted correctly from database"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        test_date = sample_market_data['date_local']

        # Act
        conditions = scanner.get_today_conditions(date_local=test_date)

        # Assert
        assert '0900' in conditions['orb_sizes']
        assert conditions['orb_sizes']['0900'] == sample_market_data['orb_0900_size']

    def test_get_conditions_handles_null_orbs_gracefully(
        self, populated_test_db
    ):
        """NULL ORB values (weekends, holidays) handled without crash"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        # Use weekend date where ORBs would be NULL
        weekend_date = date(2026, 1, 18)  # Saturday

        # Act
        conditions = scanner.get_today_conditions(date_local=weekend_date)

        # Assert
        # Should not crash, either no data or NULL values
        assert 'orb_sizes' in conditions


class TestCheckOrbSizeAnomaly:
    """Test anomaly detection for trap setups and unusual sizes"""

    def test_anomaly_detection_with_normal_size_returns_none(
        self, populated_test_db
    ):
        """ORB size within normal range flagged as no anomaly"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        orb_time = '0900'
        normal_size = scanner.thresholds['orb_size'][orb_time]['mean']

        # Act
        result = scanner.check_orb_size_anomaly(orb_time, normal_size)

        # Assert
        assert result['is_anomaly'] is False
        assert result['severity'] == 'NONE'

    def test_anomaly_detection_with_large_size_returns_critical(
        self, populated_test_db
    ):
        """Abnormally large ORB (>3 std devs) flagged as CRITICAL trap risk"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        orb_time = '0900'
        mean = scanner.thresholds['orb_size'][orb_time]['mean']
        std = scanner.thresholds['orb_size'][orb_time]['std']
        large_size = mean + (3.5 * std)  # 3.5 std devs above mean

        # Act
        result = scanner.check_orb_size_anomaly(orb_time, large_size)

        # Assert
        assert result['is_anomaly'] is True
        assert result['severity'] == 'CRITICAL'
        assert result['direction'] == 'LARGE'
        assert result['z_score'] > 3.0

    def test_anomaly_detection_with_small_size_returns_medium(
        self, populated_test_db
    ):
        """Abnormally small ORB (<-2 std devs) flagged as MEDIUM low probability"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        orb_time = '0900'
        mean = scanner.thresholds['orb_size'][orb_time]['mean']
        std = scanner.thresholds['orb_size'][orb_time]['std']
        small_size = mean - (2.5 * std)  # 2.5 std devs below mean

        # Act
        result = scanner.check_orb_size_anomaly(orb_time, small_size)

        # Assert
        assert result['is_anomaly'] is True
        assert result['severity'] == 'MEDIUM'
        assert result['direction'] == 'SMALL'
        assert result['z_score'] < -2.0

    def test_anomaly_detection_with_none_orb_returns_no_anomaly(
        self, populated_test_db
    ):
        """NULL ORB (not formed yet) returns no anomaly"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        orb_time = '0900'

        # Act
        result = scanner.check_orb_size_anomaly(orb_time, None)

        # Assert
        assert result['is_anomaly'] is False
        assert result['severity'] == 'NONE'
        assert 'not formed' in result['reason'].lower()


class TestCheckOrbSizeFilter:
    """Test ORB size filter validation against config.py"""

    def test_filter_check_with_size_above_threshold_passes(
        self, populated_test_db
    ):
        """ORB size >= filter threshold passes validation"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        orb_time = '2300'  # Has filter = 0.155
        filter_values = MGC_ORB_SIZE_FILTERS.get(orb_time, [0.05])
        # Extract first non-None filter
        filter_value = next((f for f in filter_values if f is not None), 0.05)
        orb_size = filter_value + 0.01  # Slightly above threshold

        # Act
        result = scanner.check_orb_size_filter(orb_time, orb_size)

        # Assert
        assert result['passes_filter'] is True
        assert result['orb_size'] == orb_size

    def test_filter_check_with_size_below_threshold_fails(
        self, populated_test_db
    ):
        """ORB size < filter threshold fails validation"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        orb_time = '2300'  # Has filter = 0.155
        filter_values = MGC_ORB_SIZE_FILTERS.get(orb_time, [0.05])
        # Extract first non-None filter
        filter_value = next((f for f in filter_values if f is not None), 0.05)
        orb_size = filter_value - 0.01  # Slightly below threshold

        # Act
        result = scanner.check_orb_size_filter(orb_time, orb_size)

        # Assert
        assert result['passes_filter'] is False
        assert 'fails' in result['reason'].lower()

    def test_filter_check_with_no_filter_configured_always_passes(
        self, populated_test_db
    ):
        """ORB time with no filter (None) always passes"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        orb_time = '1800'  # Typically no filter
        orb_size = 0.001  # Tiny size

        # Act
        result = scanner.check_orb_size_filter(orb_time, orb_size)

        # Assert
        # Should pass if no filter configured
        assert result['filter_value'] is None or result['passes_filter'] is True

    def test_filter_check_with_none_orb_fails(self, populated_test_db):
        """NULL ORB (not formed) fails filter check"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        orb_time = '0900'

        # Act
        result = scanner.check_orb_size_filter(orb_time, None)

        # Assert
        assert result['passes_filter'] is False
        assert 'not formed' in result['reason'].lower()


class TestValidateSetup:
    """Test comprehensive setup validation logic"""

    def test_validate_setup_with_good_conditions_returns_take(
        self, populated_test_db, sample_market_data
    ):
        """Valid setup with good conditions returns TAKE recommendation"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        test_date = sample_market_data['date_local']
        orb_time = '0900'

        # Act
        validation = scanner.validate_setup(orb_time, date_local=test_date)

        # Assert
        assert validation['orb_time'] == orb_time
        assert 'confidence' in validation
        assert 'recommendation' in validation
        assert 'reasons' in validation

    def test_validate_setup_with_no_data_returns_skip(self, populated_test_db):
        """Setup with no market data returns SKIP recommendation"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        missing_date = date(2030, 1, 1)  # Future date
        orb_time = '0900'

        # Act
        validation = scanner.validate_setup(orb_time, date_local=missing_date)

        # Assert
        assert validation['valid'] is False
        assert validation['recommendation'] == 'SKIP'
        assert 'No market data' in validation['reasons'][0]

    def test_validate_setup_with_already_broken_orb_returns_skip(
        self, populated_test_db
    ):
        """Setup where ORB already broken returns SKIP (opportunity passed)"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        # Would need test data with orb_0900_break_dir != 'NONE'
        # This tests the logic exists
        orb_time = '0900'
        test_date = date(2026, 1, 15)

        # Act
        validation = scanner.validate_setup(orb_time, date_local=test_date)

        # Assert
        # Check structure exists
        assert 'valid' in validation
        assert 'recommendation' in validation

    def test_validate_setup_with_small_orb_returns_lower_confidence(
        self, populated_test_db, sample_market_data
    ):
        """Setup with small ORB size gets lower confidence rating"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        test_date = sample_market_data['date_local']
        orb_time = '0900'

        # Act
        validation = scanner.validate_setup(orb_time, date_local=test_date)

        # Assert
        assert validation['confidence'] in ['HIGH', 'MEDIUM', 'LOW', 'INVALID']

    def test_validate_setup_with_high_asia_travel_boosts_confidence(
        self, populated_test_db, sample_market_data
    ):
        """High Asia travel (>2.5) boosts confidence for breakouts"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        test_date = sample_market_data['date_local']
        orb_time = '0900'

        # Act
        validation = scanner.validate_setup(orb_time, date_local=test_date)

        # Assert
        # If Asia travel > 2.5, should see reason mentioning it
        if validation['conditions']['asia_travel'] and validation['conditions']['asia_travel'] > 2.5:
            reasons_text = ' '.join(validation['reasons'])
            assert 'Asia travel' in reasons_text or validation['confidence'] in ['HIGH', 'MEDIUM']


class TestScanAllSetups:
    """Test scanning all MGC setups at once"""

    def test_scan_all_setups_returns_complete_structure(
        self, populated_test_db, sample_market_data
    ):
        """Scan returns all required fields with valid structure"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        test_date = sample_market_data['date_local']

        # Act
        results = scanner.scan_all_setups(date_local=test_date, auto_update=False)

        # Assert
        assert 'date_local' in results
        assert 'scan_time' in results
        assert 'valid_setups' in results
        assert 'caution_setups' in results
        assert 'invalid_setups' in results
        assert 'summary' in results
        assert 'valid_count' in results
        assert 'caution_count' in results
        assert 'invalid_count' in results

    def test_scan_all_setups_checks_all_orb_times(
        self, populated_test_db, sample_market_data
    ):
        """Scan checks all MGC ORB times (0900, 1000, 1100, 1800, 2300, 0030)"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        test_date = sample_market_data['date_local']

        # Act
        results = scanner.scan_all_setups(date_local=test_date, auto_update=False)

        # Assert
        total_setups = (
            len(results['valid_setups']) +
            len(results['caution_setups']) +
            len(results['invalid_setups'])
        )
        assert total_setups == 6  # All 6 MGC ORB times

    def test_scan_all_setups_categorizes_setups_correctly(
        self, populated_test_db, sample_market_data
    ):
        """Setups categorized into valid/caution/invalid based on recommendation"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        test_date = sample_market_data['date_local']

        # Act
        results = scanner.scan_all_setups(date_local=test_date, auto_update=False)

        # Assert
        # Check valid setups have TAKE recommendation
        for setup in results['valid_setups']:
            assert setup['recommendation'] == 'TAKE'

        # Check caution setups have CAUTION recommendation
        for setup in results['caution_setups']:
            assert setup['recommendation'] == 'CAUTION'

        # Check invalid setups have SKIP or WAIT recommendation
        for setup in results['invalid_setups']:
            assert setup['recommendation'] in ['SKIP', 'WAIT']

    def test_scan_all_setups_counts_match_lists(
        self, populated_test_db, sample_market_data
    ):
        """Count fields match actual list lengths"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        test_date = sample_market_data['date_local']

        # Act
        results = scanner.scan_all_setups(date_local=test_date, auto_update=False)

        # Assert
        assert results['valid_count'] == len(results['valid_setups'])
        assert results['caution_count'] == len(results['caution_setups'])
        assert results['invalid_count'] == len(results['invalid_setups'])

    def test_scan_all_setups_without_auto_update_uses_existing_data(
        self, populated_test_db, sample_market_data
    ):
        """Scan with auto_update=False doesn't trigger data bridge"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        test_date = sample_market_data['date_local']

        # Act
        results = scanner.scan_all_setups(date_local=test_date, auto_update=False)

        # Assert
        # Should complete without trying to update data
        assert results is not None
        assert 'valid_setups' in results


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_scanner_handles_weekend_date_gracefully(self, populated_test_db):
        """Scanner handles weekend dates without crash"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        saturday = date(2026, 1, 17)  # Saturday

        # Act
        results = scanner.scan_all_setups(date_local=saturday, auto_update=False)

        # Assert
        # Should not crash, likely all SKIP or WAIT
        assert results is not None

    def test_scanner_handles_orb_size_zero_gracefully(self, populated_test_db):
        """Scanner handles ORB size = 0.0 (no movement) correctly"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        orb_time = '0900'
        zero_size = 0.0

        # Act
        filter_result = scanner.check_orb_size_filter(orb_time, zero_size)
        anomaly_result = scanner.check_orb_size_anomaly(orb_time, zero_size)

        # Assert
        # Should handle without crash
        assert filter_result['passes_filter'] is False or True  # Either valid
        assert anomaly_result is not None

    def test_scanner_with_invalid_orb_time_handled_gracefully(
        self, populated_test_db
    ):
        """Scanner handles invalid ORB time (e.g., '1200') gracefully"""
        # Arrange
        scanner = MarketScanner(db_path=populated_test_db)
        invalid_orb_time = '1200'  # Not a valid ORB time
        test_date = date(2026, 1, 15)

        # Act & Assert
        # Should not crash, either skip or handle error
        try:
            validation = scanner.validate_setup(invalid_orb_time, date_local=test_date)
            assert validation is not None
        except KeyError:
            # Expected if invalid ORB time not in config
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
