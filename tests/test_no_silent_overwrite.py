"""
Test that multiple setups per ORB are not silently overwritten.

Guards against regression to dict-based single-setup architecture.
"""

import pytest
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).parent.parent / "trading_app"))

from config_generator import load_instrument_configs
from cloud_mode import get_database_connection


def test_config_count_matches_database_count():
    """
    Test that number of setups in config matches database for each ORB time.

    This catches silent overwrites where multiple DB rows collapse to one config.
    """
    # Get database counts
    conn = get_database_connection(read_only=True)

    query = """
        SELECT orb_time, COUNT(*) as count
        FROM validated_setups
        WHERE instrument = ?
          AND orb_time NOT IN ('CASCADE', 'SINGLE_LIQ')
        GROUP BY orb_time
    """

    db_counts = {}
    results = conn.execute(query, ['MGC']).fetchall()
    for orb_time, count in results:
        db_counts[orb_time] = count

    conn.close()

    # Get config counts
    mgc_configs, _ = load_instrument_configs('MGC')

    config_counts = {}
    for orb_time, config_list in mgc_configs.items():
        if config_list is None:
            continue  # SKIP ORB
        config_counts[orb_time] = len(config_list)

    # Compare
    for orb_time, db_count in db_counts.items():
        config_count = config_counts.get(orb_time, 0)

        assert config_count == db_count, \
            f"ORB {orb_time}: database has {db_count} setups but config has {config_count} (silent overwrite?)"


def test_unique_rr_sl_combinations_preserved():
    """
    Test that unique (RR, SL_MODE) combinations are not lost.

    Each unique combination in database should appear in config.
    """
    # Get database combinations
    conn = get_database_connection(read_only=True)

    query = """
        SELECT orb_time, rr, sl_mode
        FROM validated_setups
        WHERE instrument = ?
          AND orb_time NOT IN ('CASCADE', 'SINGLE_LIQ')
        ORDER BY orb_time, rr
    """

    db_combos = {}
    results = conn.execute(query, ['MGC']).fetchall()
    for orb_time, rr, sl_mode in results:
        if orb_time not in db_combos:
            db_combos[orb_time] = []
        db_combos[orb_time].append((rr, sl_mode))

    conn.close()

    # Get config combinations
    mgc_configs, _ = load_instrument_configs('MGC')

    config_combos = {}
    for orb_time, config_list in mgc_configs.items():
        if config_list is None:
            continue
        config_combos[orb_time] = [
            (c['rr'], c['sl_mode'])
            for c in config_list
        ]

    # Compare
    for orb_time, db_combo_list in db_combos.items():
        config_combo_list = config_combos.get(orb_time, [])

        # Sort for comparison
        db_sorted = sorted(db_combo_list)
        config_sorted = sorted(config_combo_list)

        assert db_sorted == config_sorted, \
            f"ORB {orb_time}: DB combos {db_sorted} != config combos {config_sorted}"


def test_mgc_1000_both_setups_present():
    """
    Specific regression test for MGC 1000 candidates 47+48.

    This is the exact scenario that triggered the architecture fix.
    """
    mgc_configs, mgc_filters = load_instrument_configs('MGC')

    assert '1000' in mgc_configs, "MGC 1000 should exist"

    config_list = mgc_configs['1000']
    filter_list = mgc_filters['1000']

    # Should have exactly 2 setups
    assert len(config_list) == 2, \
        f"MGC 1000 should have 2 setups, found {len(config_list)} (silent overwrite?)"

    assert len(filter_list) == 2, \
        f"MGC 1000 should have 2 filters, found {len(filter_list)}"

    # Verify both combinations present
    combos = [(c['rr'], c['sl_mode']) for c in config_list]

    assert (1.0, 'FULL') in combos, "Candidate 47 (RR=1.0 FULL) missing"
    assert (2.0, 'HALF') in combos, "Candidate 48 (RR=2.0 HALF) missing"


if __name__ == "__main__":
    # Run tests directly
    print("Testing no silent overwrites...")
    print()

    try:
        test_config_count_matches_database_count()
        print("[PASS] test_config_count_matches_database_count")
    except AssertionError as e:
        print(f"[FAIL] test_config_count_matches_database_count: {e}")
        sys.exit(1)

    try:
        test_unique_rr_sl_combinations_preserved()
        print("[PASS] test_unique_rr_sl_combinations_preserved")
    except AssertionError as e:
        print(f"[FAIL] test_unique_rr_sl_combinations_preserved: {e}")
        sys.exit(1)

    try:
        test_mgc_1000_both_setups_present()
        print("[PASS] test_mgc_1000_both_setups_present")
    except AssertionError as e:
        print(f"[FAIL] test_mgc_1000_both_setups_present: {e}")
        sys.exit(1)

    print()
    print("All no-overwrite tests PASSED!")
