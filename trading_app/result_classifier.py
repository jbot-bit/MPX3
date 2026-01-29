"""
Result Classifier - Deterministic Edge Classification

Classifies parameter combinations as GOOD/NEUTRAL/BAD using fixed thresholds.
NO human labels, NO model labels - purely rules-based.

Ruleset Version: 1.0 (audit3)
"""

# Ruleset version (audit3)
RULESET_VERSION = "1.0"


def classify_result(
    expectancy_r: float,
    sample_size: int,
    robust_flags: int
) -> str:
    """
    Deterministic result classification using fixed thresholds

    Ruleset version: 1.0 (audit3)

    Classification Rules:
    ---------------------
    GOOD:
        - expectancy_r >= 0.25R (strong edge)
        - sample_size >= 50 (statistical confidence)
        - robust_flags == 0 (passes all gates)

    NEUTRAL:
        - expectancy_r >= 0.15R (viable edge)
        - sample_size >= 30 (minimum sample)
        - robust_flags with <= 1 concern (bitmask popcount)

    BAD:
        - expectancy_r < 0.15R (weak/no edge)
        - OR sample_size < 30 (insufficient data)
        - OR robust_flags with > 1 concern (bitmask popcount)

    Args:
        expectancy_r: Expected return in R-multiples (e.g., 0.25 = +0.25R)
        sample_size: Number of trades in sample
        robust_flags: Robustness bitmask (0 = clean, popcount = number of concerns)
                      Bit 0 (0x01): Marginal sample size
                      Bit 1 (0x02): Marginal expectancy
                      Bit 2 (0x04): Very low sample size
                      Bit 3 (0x08): Weak expectancy
                      (Future: Bits 4-7 for OOS stability, cost stress, regime, tail risk)

    Returns:
        "GOOD" | "NEUTRAL" | "BAD"

    Examples:
        >>> classify_result(0.30, 60, 0)  # No concerns
        'GOOD'

        >>> classify_result(0.20, 40, 0x01)  # 1 concern (marginal sample)
        'NEUTRAL'

        >>> classify_result(0.10, 25, 0x0C)  # 2 concerns (low sample + weak expectancy)
        'BAD'

        >>> classify_result(0.30, 20, 0)  # Good edge but insufficient sample
        'BAD'

        >>> classify_result(0.10, 100, 0)  # Large sample but weak edge
        'BAD'
    """
    # Count number of concerns (popcount of bitmask)
    concern_count = bin(robust_flags).count('1')

    # GOOD threshold: Strong edge, high confidence, clean
    if expectancy_r >= 0.25 and sample_size >= 50 and concern_count == 0:
        return "GOOD"

    # NEUTRAL threshold: Viable edge, minimum confidence, minor concerns
    elif expectancy_r >= 0.15 and sample_size >= 30 and concern_count <= 1:
        return "NEUTRAL"

    # BAD threshold: Weak edge, insufficient data, or multiple concerns
    else:
        return "BAD"


def get_thresholds() -> dict:
    """
    Get classification thresholds for reference

    Returns:
        Dictionary with threshold values
    """
    return {
        'ruleset_version': RULESET_VERSION,
        'GOOD': {
            'expectancy_r_min': 0.25,
            'sample_size_min': 50,
            'robust_concerns_max': 0  # Bitmask popcount
        },
        'NEUTRAL': {
            'expectancy_r_min': 0.15,
            'sample_size_min': 30,
            'robust_concerns_max': 1  # Bitmask popcount
        },
        'BAD': {
            'expectancy_r_max': 0.15,
            'sample_size_max': 30,
            'robust_concerns_min': 2  # Bitmask popcount
        },
        'robust_flags_bitmask': {
            'bit_0_marginal_sample': 0x01,
            'bit_1_marginal_expectancy': 0x02,
            'bit_2_low_sample': 0x04,
            'bit_3_weak_expectancy': 0x08,
            # Future extensibility: bits 4-7 reserved
        }
    }


if __name__ == "__main__":
    # Test classification
    print("=" * 70)
    print(f"RESULT CLASSIFIER TEST (Ruleset v{RULESET_VERSION})")
    print("=" * 70)
    print()

    test_cases = [
        # (expectancy_r, sample_size, robust_flags_bitmask, expected_class)
        (0.30, 60, 0x00, "GOOD"),  # No concerns
        (0.25, 50, 0x00, "GOOD"),  # No concerns
        (0.24, 50, 0x00, "NEUTRAL"),  # Below 0.25R threshold
        (0.20, 40, 0x01, "NEUTRAL"),  # 1 concern (marginal sample)
        (0.15, 30, 0x01, "NEUTRAL"),  # 1 concern
        (0.14, 30, 0x01, "BAD"),  # Below 0.15R threshold + 1 concern
        (0.30, 29, 0x00, "BAD"),  # Insufficient sample (will trigger bit 2)
        (0.30, 60, 0x03, "BAD"),  # 2 concerns (bits 0+1 set)
        (0.10, 25, 0x0C, "BAD"),  # 2 concerns (bits 2+3 set)
        (0.10, 100, 0x00, "BAD"),  # Weak edge despite large sample
    ]

    passed = 0
    failed = 0

    for exp_r, n, flags, expected in test_cases:
        result = classify_result(exp_r, n, flags)
        status = "[OK]" if result == expected else "[FAIL]"

        print(f"{status} ExpR={exp_r:.2f}, N={n}, Flags={flags} => {result} (expected {expected})")

        if result == expected:
            passed += 1
        else:
            failed += 1

    print()
    print(f"Passed: {passed}/{len(test_cases)}")
    print(f"Failed: {failed}/{len(test_cases)}")
    print()

    if failed == 0:
        print("[OK] All tests passed")
    else:
        print("[FAIL] Some tests failed")
