"""
Test that config_generator returns proper list structures.

Guards against regression back to single-setup-per-ORB architecture.
"""

import pytest
import sys
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).parent.parent / "trading_app"))

from config_generator import load_instrument_configs
from cloud_mode import get_database_connection


def get_active_setup_count(instrument: str, orb_time: str) -> int:
    """Get count of ACTIVE setups from database for given instrument/orb_time."""
    conn = get_database_connection(read_only=True)
    result = conn.execute("""
        SELECT COUNT(*) FROM validated_setups
        WHERE instrument = ? AND orb_time = ? AND status = 'ACTIVE'
    """, [instrument, orb_time]).fetchone()
    conn.close()
    return result[0] if result else 0


def test_config_structure_is_lists():
    """
    Test that load_instrument_configs returns Dict[str, list] not Dict[str, dict].

    This is the core architecture requirement.
    """
    mgc_configs, mgc_filters = load_instrument_configs('MGC')

    assert isinstance(mgc_configs, dict), "Configs should be a dict"
    assert isinstance(mgc_filters, dict), "Filters should be a dict"

    # Check each ORB time returns a list
    for orb_time, config_value in mgc_configs.items():
        if config_value is None:
            # SKIP ORB, allowed
            continue

        assert isinstance(config_value, list), \
            f"ORB {orb_time} config should be list, got {type(config_value)}"

        assert len(config_value) >= 1, \
            f"ORB {orb_time} should have at least 1 setup"

        # Each item in list should be a dict with 'rr' and 'sl_mode'
        for i, setup in enumerate(config_value):
            assert isinstance(setup, dict), \
                f"ORB {orb_time} setup[{i}] should be dict, got {type(setup)}"

            assert 'rr' in setup, \
                f"ORB {orb_time} setup[{i}] missing 'rr' key"

            assert 'sl_mode' in setup, \
                f"ORB {orb_time} setup[{i}] missing 'sl_mode' key"

    # Check filters structure
    for orb_time, filter_value in mgc_filters.items():
        if filter_value is None:
            # SKIP ORB, allowed
            continue

        assert isinstance(filter_value, list), \
            f"ORB {orb_time} filter should be list, got {type(filter_value)}"


def test_mgc_1000_config_matches_database():
    """
    Test that MGC 1000 config count matches ACTIVE database rows.

    Regression test for the overwrite bug - ensures no silent data loss.
    """
    mgc_configs, mgc_filters = load_instrument_configs('MGC')

    # Get expected count from database (ACTIVE only)
    expected_count = get_active_setup_count('MGC', '1000')

    if expected_count == 0:
        # No ACTIVE setups for 1000 - config may not have this key or have None
        if '1000' in mgc_configs and mgc_configs['1000'] is not None:
            pytest.fail(f"DB has 0 ACTIVE MGC 1000 setups but config has {len(mgc_configs['1000'])}")
        return  # PASS - correctly absent

    assert '1000' in mgc_configs, "MGC should have 1000 ORB (DB has ACTIVE setups)"

    config_list = mgc_configs['1000']

    assert isinstance(config_list, list), "1000 config should be list"
    assert len(config_list) == expected_count, \
        f"MGC 1000: DB has {expected_count} ACTIVE setups but config has {len(config_list)} (silent overwrite?)"

    # Verify each config has required keys
    for i, config in enumerate(config_list):
        assert 'rr' in config, f"Config {i} missing 'rr' key"
        assert 'sl_mode' in config, f"Config {i} missing 'sl_mode' key"


def test_filter_lists_match_config_lists():
    """
    Test that filter lists have same length as config lists.

    Each setup needs a corresponding filter value (or None).
    """
    mgc_configs, mgc_filters = load_instrument_configs('MGC')

    for orb_time in mgc_configs.keys():
        config_list = mgc_configs[orb_time]
        filter_list = mgc_filters.get(orb_time)

        if config_list is None:
            assert filter_list is None, \
                f"ORB {orb_time}: config is None but filter is {filter_list}"
            continue

        assert isinstance(config_list, list), \
            f"ORB {orb_time}: config should be list"

        assert isinstance(filter_list, list), \
            f"ORB {orb_time}: filter should be list"

        assert len(config_list) == len(filter_list), \
            f"ORB {orb_time}: config has {len(config_list)} setups but filter has {len(filter_list)} values"


def test_no_cascade_or_single_liq_in_configs():
    """
    Test that CASCADE and SINGLE_LIQ are excluded from ORB configs.

    These are special strategies, not time-based ORBs.
    """
    mgc_configs, mgc_filters = load_instrument_configs('MGC')

    assert 'CASCADE' not in mgc_configs, \
        "CASCADE should not be in ORB configs (special strategy)"

    assert 'SINGLE_LIQ' not in mgc_configs, \
        "SINGLE_LIQ should not be in ORB configs (special strategy)"


if __name__ == "__main__":
    # Run tests directly
    print("Testing config_generator list structure...")
    print()

    try:
        test_config_structure_is_lists()
        print("[PASS] test_config_structure_is_lists")
    except AssertionError as e:
        print(f"[FAIL] test_config_structure_is_lists: {e}")
        sys.exit(1)

    try:
        test_mgc_1000_config_matches_database()
        print("[PASS] test_mgc_1000_config_matches_database")
    except AssertionError as e:
        print(f"[FAIL] test_mgc_1000_config_matches_database: {e}")
        sys.exit(1)

    try:
        test_filter_lists_match_config_lists()
        print("[PASS] test_filter_lists_match_config_lists")
    except AssertionError as e:
        print(f"[FAIL] test_filter_lists_match_config_lists: {e}")
        sys.exit(1)

    try:
        test_no_cascade_or_single_liq_in_configs()
        print("[PASS] test_no_cascade_or_single_liq_in_configs")
    except AssertionError as e:
        print(f"[FAIL] test_no_cascade_or_single_liq_in_configs: {e}")
        sys.exit(1)

    print()
    print("All config_generator tests PASSED!")
