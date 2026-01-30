"""
UI CONTRACT - FAIL-CLOSED VALIDATION LOGIC (UPDATE17)
=======================================================

Pure functions for UI validation status derivation.
NO Streamlit dependencies - can be tested independently.

CRITICAL RULES:
1. Status is UI-derived only, NEVER written to DB
2. Missing/invalid data → UNKNOWN (fail-closed)
3. Only PASS status allows approval

This module would have prevented:
- Mock validation data bug (would return UNKNOWN on missing data)
- Fake PASS states (approval requires real metrics)
"""

import json
from typing import Optional


def safe_parse_json(s: Optional[str]) -> Optional[dict]:
    """
    Safely parse JSON string without raising exceptions.

    Args:
        s: JSON string or None

    Returns:
        Parsed dict if valid JSON, None otherwise

    Examples:
        >>> safe_parse_json('{"key": "value"}')
        {'key': 'value'}
        >>> safe_parse_json(None)
        None
        >>> safe_parse_json('')
        None
        >>> safe_parse_json('invalid json')
        None
    """
    if not s:
        return None

    try:
        result = json.loads(s)
        if isinstance(result, dict):
            return result
        return None
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def derive_validation_status(
    metrics_json: Optional[str],
    robustness_json: Optional[str]
) -> str:
    """
    Derive validation status from metrics and robustness data.

    FAIL-CLOSED: Missing or invalid data returns UNKNOWN.

    Args:
        metrics_json: JSON string with avg_r, win_rate, etc.
        robustness_json: JSON string with stress_25_pass, stress_50_pass

    Returns:
        One of: "PASS", "WEAK", "FAIL", "UNKNOWN"

    Status Rules:
        - PASS: avg_r >= 0.15R AND stress_50_pass = True
        - WEAK: avg_r >= 0.15R AND stress_25_pass = True (but stress_50_pass = False)
        - FAIL: avg_r < 0.15R OR both stress tests fail
        - UNKNOWN: Missing or invalid data (FAIL-CLOSED)

    Examples:
        >>> derive_validation_status('{"avg_r": 0.25}', '{"stress_50_pass": true}')
        'PASS'
        >>> derive_validation_status('{"avg_r": 0.25}', '{"stress_25_pass": true}')
        'WEAK'
        >>> derive_validation_status('{"avg_r": 0.10}', '{"stress_50_pass": true}')
        'FAIL'
        >>> derive_validation_status(None, '{"stress_50_pass": true}')
        'UNKNOWN'
    """
    # Parse metrics
    metrics = safe_parse_json(metrics_json)
    if metrics is None:
        return "UNKNOWN"

    # Extract avg_r
    avg_r = metrics.get('avg_r')
    if avg_r is None or not isinstance(avg_r, (int, float)):
        return "UNKNOWN"

    # Check minimum expectancy threshold
    if avg_r < 0.15:
        return "FAIL"

    # Parse robustness (fail-closed if missing)
    robustness = safe_parse_json(robustness_json)
    if robustness is None:
        return "UNKNOWN"

    # Check stress test results
    stress_50_pass = robustness.get('stress_50_pass')
    stress_25_pass = robustness.get('stress_25_pass')

    # PASS: Survives +50% stress
    if stress_50_pass is True:
        return "PASS"

    # WEAK: Survives +25% stress only
    if stress_25_pass is True:
        return "WEAK"

    # FAIL: Both stress tests fail or missing
    return "FAIL"


def can_approve(status: str) -> bool:
    """
    Check if a candidate can be approved based on status.

    CRITICAL: Only PASS status allows approval.

    Args:
        status: Validation status (PASS/WEAK/FAIL/UNKNOWN)

    Returns:
        True only if status == "PASS", False otherwise

    Examples:
        >>> can_approve("PASS")
        True
        >>> can_approve("WEAK")
        False
        >>> can_approve("FAIL")
        False
        >>> can_approve("UNKNOWN")
        False
    """
    return status == "PASS"
