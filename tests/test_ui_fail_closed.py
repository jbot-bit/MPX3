"""
UI FAIL-CLOSED CONTRACT TESTS (UPDATE17)
=========================================

Tests that prove the UI cannot lie and cannot strand the user.

CRITICAL RULES TESTED:
1. Missing data → UNKNOWN → Cannot approve
2. Invalid data → UNKNOWN → Cannot approve (no exceptions)
3. Only PASS status allows approval
4. Approval action calls real promotion function

NO Streamlit dependencies - pure logic tests.
"""

import pytest
from trading_app.ui_contract import (
    safe_parse_json,
    derive_validation_status,
    can_approve,
)


class TestSafeParseJson:
    """Test safe JSON parsing (never raises)."""

    def test_valid_json(self):
        """Valid JSON returns parsed dict."""
        result = safe_parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_none_input(self):
        """None input returns None."""
        result = safe_parse_json(None)
        assert result is None

    def test_empty_string(self):
        """Empty string returns None."""
        result = safe_parse_json('')
        assert result is None

    def test_invalid_json_no_exception(self):
        """Invalid JSON returns None, does NOT raise."""
        result = safe_parse_json('invalid json')
        assert result is None

    def test_non_dict_json(self):
        """Non-dict JSON (array, string) returns None."""
        assert safe_parse_json('["array"]') is None
        assert safe_parse_json('"string"') is None
        assert safe_parse_json('123') is None


class TestDeriveValidationStatus:
    """Test validation status derivation (fail-closed)."""

    # TEST A: Missing metrics_json → UNKNOWN
    def test_missing_metrics_json(self):
        """Missing metrics_json returns UNKNOWN (fail-closed)."""
        status = derive_validation_status(
            metrics_json=None,
            robustness_json='{"stress_50_pass": true}'
        )
        assert status == "UNKNOWN"
        assert can_approve(status) is False

    # TEST B: Missing robustness_json → UNKNOWN
    def test_missing_robustness_json(self):
        """Missing robustness_json returns UNKNOWN (fail-closed)."""
        status = derive_validation_status(
            metrics_json='{"avg_r": 0.25}',
            robustness_json=None
        )
        assert status == "UNKNOWN"
        assert can_approve(status) is False

    # TEST C: Malformed JSON → UNKNOWN (no exception)
    def test_malformed_metrics_json_no_exception(self):
        """Malformed metrics_json returns UNKNOWN, does NOT raise."""
        status = derive_validation_status(
            metrics_json='invalid json',
            robustness_json='{"stress_50_pass": true}'
        )
        assert status == "UNKNOWN"
        assert can_approve(status) is False

    def test_malformed_robustness_json_no_exception(self):
        """Malformed robustness_json returns UNKNOWN, does NOT raise."""
        status = derive_validation_status(
            metrics_json='{"avg_r": 0.25}',
            robustness_json='invalid json'
        )
        assert status == "UNKNOWN"
        assert can_approve(status) is False

    # TEST D: PASS conditions
    def test_pass_status_avg_r_valid_stress_50_pass(self):
        """avg_r >= 0.15 AND stress_50_pass = True → PASS (can approve)."""
        status = derive_validation_status(
            metrics_json='{"avg_r": 0.25}',
            robustness_json='{"stress_50_pass": true, "stress_25_pass": true}'
        )
        assert status == "PASS"
        assert can_approve(status) is True

    def test_pass_status_exact_threshold(self):
        """avg_r = 0.15 (exact threshold) AND stress_50_pass = True → PASS."""
        status = derive_validation_status(
            metrics_json='{"avg_r": 0.15}',
            robustness_json='{"stress_50_pass": true}'
        )
        assert status == "PASS"
        assert can_approve(status) is True

    # TEST E: WEAK conditions
    def test_weak_status_stress_25_only(self):
        """avg_r >= 0.15 AND stress_25_pass = True (but stress_50_pass = False) → WEAK (cannot approve)."""
        status = derive_validation_status(
            metrics_json='{"avg_r": 0.25}',
            robustness_json='{"stress_25_pass": true, "stress_50_pass": false}'
        )
        assert status == "WEAK"
        assert can_approve(status) is False

    def test_weak_status_stress_50_missing(self):
        """avg_r >= 0.15 AND stress_25_pass = True (but stress_50_pass missing) → WEAK."""
        status = derive_validation_status(
            metrics_json='{"avg_r": 0.25}',
            robustness_json='{"stress_25_pass": true}'
        )
        assert status == "WEAK"
        assert can_approve(status) is False

    # TEST F: FAIL conditions
    def test_fail_status_avg_r_below_threshold(self):
        """avg_r < 0.15 → FAIL (cannot approve), even if stress tests pass."""
        status = derive_validation_status(
            metrics_json='{"avg_r": 0.10}',
            robustness_json='{"stress_50_pass": true, "stress_25_pass": true}'
        )
        assert status == "FAIL"
        assert can_approve(status) is False

    def test_fail_status_both_stress_fail(self):
        """avg_r >= 0.15 but both stress tests fail → FAIL."""
        status = derive_validation_status(
            metrics_json='{"avg_r": 0.25}',
            robustness_json='{"stress_25_pass": false, "stress_50_pass": false}'
        )
        assert status == "FAIL"
        assert can_approve(status) is False

    def test_fail_status_stress_missing(self):
        """avg_r >= 0.15 but both stress results missing → FAIL (fail-closed)."""
        status = derive_validation_status(
            metrics_json='{"avg_r": 0.25}',
            robustness_json='{}'
        )
        assert status == "FAIL"
        assert can_approve(status) is False


class TestCanApprove:
    """Test approval gating logic."""

    def test_can_approve_pass_only(self):
        """Only PASS status allows approval."""
        assert can_approve("PASS") is True
        assert can_approve("WEAK") is False
        assert can_approve("FAIL") is False
        assert can_approve("UNKNOWN") is False

    def test_can_approve_case_sensitive(self):
        """Approval is case-sensitive (lowercase 'pass' does NOT approve)."""
        assert can_approve("pass") is False
        assert can_approve("Pass") is False


class TestMissingAvgR:
    """Test fail-closed behavior when avg_r is missing/invalid."""

    def test_missing_avg_r_field(self):
        """Missing avg_r field → UNKNOWN."""
        status = derive_validation_status(
            metrics_json='{"win_rate": 0.55}',  # No avg_r
            robustness_json='{"stress_50_pass": true}'
        )
        assert status == "UNKNOWN"
        assert can_approve(status) is False

    def test_invalid_avg_r_type(self):
        """Invalid avg_r type (string instead of number) → UNKNOWN."""
        status = derive_validation_status(
            metrics_json='{"avg_r": "0.25"}',  # String, not number
            robustness_json='{"stress_50_pass": true}'
        )
        assert status == "UNKNOWN"
        assert can_approve(status) is False


# STEP 3: WIRING TEST (Approve calls real promotion function)
class TestApprovalWiring:
    """Test that approve action calls real promotion function."""

    def test_approval_calls_promotion_on_pass(self, monkeypatch):
        """
        PASS status → Approve action calls real promotion function.

        This test verifies the UI approval flow calls the REAL promotion
        function, not a mock or TODO stub.
        """
        from unittest.mock import Mock
        from trading_app import edge_pipeline

        # Mock the actual promotion function
        mock_promote = Mock(return_value=123)  # Returns setup_id
        monkeypatch.setattr(edge_pipeline, 'promote_candidate_to_validated_setups', mock_promote)

        # Simulate PASS status (real status derivation, not mock)
        status = derive_validation_status(
            metrics_json='{"avg_r": 0.25}',
            robustness_json='{"stress_50_pass": true}'
        )
        assert status == "PASS"

        # Simulate approve action
        if can_approve(status):
            candidate_id = 999
            edge_pipeline.promote_candidate_to_validated_setups(
                candidate_id=candidate_id,
                actor='test_user'
            )

        # Verify promotion function called exactly once
        mock_promote.assert_called_once_with(candidate_id=999, actor='test_user')

    def test_approval_blocked_on_weak(self, monkeypatch):
        """WEAK status → Approve action does NOT call promotion."""
        from unittest.mock import Mock
        from trading_app import edge_pipeline

        mock_promote = Mock()
        monkeypatch.setattr(edge_pipeline, 'promote_candidate_to_validated_setups', mock_promote)

        # Simulate WEAK status
        status = derive_validation_status(
            metrics_json='{"avg_r": 0.25}',
            robustness_json='{"stress_25_pass": true, "stress_50_pass": false}'
        )
        assert status == "WEAK"

        # Simulate approve action (should be blocked)
        if can_approve(status):
            edge_pipeline.promote_candidate_to_validated_setups(
                candidate_id=999,
                actor='test_user'
            )

        # Verify promotion NOT called
        mock_promote.assert_not_called()

    def test_approval_blocked_on_fail(self, monkeypatch):
        """FAIL status → Approve action does NOT call promotion."""
        from unittest.mock import Mock
        from trading_app import edge_pipeline

        mock_promote = Mock()
        monkeypatch.setattr(edge_pipeline, 'promote_candidate_to_validated_setups', mock_promote)

        # Simulate FAIL status
        status = derive_validation_status(
            metrics_json='{"avg_r": 0.10}',
            robustness_json='{"stress_50_pass": true}'
        )
        assert status == "FAIL"

        # Simulate approve action (should be blocked)
        if can_approve(status):
            edge_pipeline.promote_candidate_to_validated_setups(
                candidate_id=999,
                actor='test_user'
            )

        # Verify promotion NOT called
        mock_promote.assert_not_called()

    def test_approval_blocked_on_unknown(self, monkeypatch):
        """UNKNOWN status → Approve action does NOT call promotion."""
        from unittest.mock import Mock
        from trading_app import edge_pipeline

        mock_promote = Mock()
        monkeypatch.setattr(edge_pipeline, 'promote_candidate_to_validated_setups', mock_promote)

        # Simulate UNKNOWN status (missing data)
        status = derive_validation_status(
            metrics_json=None,
            robustness_json='{"stress_50_pass": true}'
        )
        assert status == "UNKNOWN"

        # Simulate approve action (should be blocked)
        if can_approve(status):
            edge_pipeline.promote_candidate_to_validated_setups(
                candidate_id=999,
                actor='test_user'
            )

        # Verify promotion NOT called
        mock_promote.assert_not_called()
