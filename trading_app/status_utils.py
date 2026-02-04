"""
Status Derivation Utilities - SINGLE SOURCE OF TRUTH

This module contains the CANONICAL logic for deriving strategy status
from expected_r and sample_size.

RULE: Status MUST be derived, never stored as source of truth.

See: docs/STATUS_DERIVATION_SSOT.md
"""

from typing import Optional

# =============================================================================
# APPROVAL THRESHOLDS (from CLAUDE.md / strategy-validator)
# =============================================================================

# Minimum expected R to be considered viable (at $8.40 RT friction)
MIN_EXPECTED_R = 0.15

# Minimum sample size for statistical significance
MIN_SAMPLE_SIZE = 30


# =============================================================================
# CANONICAL DERIVATION FUNCTION
# =============================================================================

def derive_status(
    expected_r: Optional[float],
    sample_size: Optional[int],
    has_data: bool = True
) -> str:
    """
    Derive strategy status from metrics.

    This is the CANONICAL derivation logic. All status checks should
    use this function rather than reading the stored status column.

    Args:
        expected_r: Expected R-multiple at $8.40 friction (can be None)
        sample_size: Number of trades in backtest (can be None)
        has_data: Whether backtest data exists

    Returns:
        str: One of 'ACTIVE', 'REJECTED', 'INVALID_NO_DATA'

    Examples:
        >>> derive_status(0.20, 50)
        'ACTIVE'
        >>> derive_status(0.10, 50)
        'REJECTED'
        >>> derive_status(0.20, 20)
        'REJECTED'
        >>> derive_status(None, None)
        'INVALID_NO_DATA'
    """
    # No data case
    if not has_data:
        return 'INVALID_NO_DATA'

    # Missing metrics
    if expected_r is None or sample_size is None:
        return 'INVALID_NO_DATA'

    # Apply thresholds
    if expected_r >= MIN_EXPECTED_R and sample_size >= MIN_SAMPLE_SIZE:
        return 'ACTIVE'
    else:
        return 'REJECTED'


def check_status_consistency(
    stored_status: Optional[str],
    expected_r: Optional[float],
    sample_size: Optional[int]
) -> tuple:
    """
    Check if stored status matches derived status.

    Args:
        stored_status: Status value from database
        expected_r: Expected R-multiple
        sample_size: Number of trades

    Returns:
        tuple: (is_consistent: bool, derived_status: str, message: str)
    """
    derived = derive_status(expected_r, sample_size)

    # RETIRED is a special case - manually set, not derived
    if stored_status == 'RETIRED':
        return (True, derived, "RETIRED status is manually managed")

    # Check consistency
    if stored_status == derived:
        return (True, derived, "Status matches derivation")

    # Mismatch
    return (
        False,
        derived,
        f"MISMATCH: stored='{stored_status}' but derived='{derived}' "
        f"(expected_r={expected_r}, sample_size={sample_size})"
    )


def get_rejection_reason(
    expected_r: Optional[float],
    sample_size: Optional[int]
) -> str:
    """
    Get human-readable reason for rejection.

    Args:
        expected_r: Expected R-multiple
        sample_size: Number of trades

    Returns:
        str: Reason for rejection
    """
    if expected_r is None or sample_size is None:
        return "Missing data (expected_r or sample_size is NULL)"

    reasons = []

    if expected_r < MIN_EXPECTED_R:
        reasons.append(f"expected_r={expected_r:.3f} < {MIN_EXPECTED_R} threshold")

    if sample_size < MIN_SAMPLE_SIZE:
        reasons.append(f"sample_size={sample_size} < {MIN_SAMPLE_SIZE} threshold")

    if not reasons:
        return "Meets all criteria (should be ACTIVE)"

    return "; ".join(reasons)
