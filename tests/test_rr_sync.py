"""
Regression Test: RR Synchronization
====================================

Tests that populate_tradeable_metrics.py reads RR from validated_setups
instead of hardcoded RR_DEFAULT.

CRITICAL: This test prevents Bug #1 from ever happening again.

Test Cases:
1. get_strategy_config() loads RR from validated_setups
2. RR values match database for each ORB time
3. Fail-closed: abort if RR is None/0/missing
4. Print RR EVIDENCE TABLE before processing
5. Each ORB uses its specific RR (not default)

Run this test after ANY changes to populate_tradeable_metrics.py or validated_setups.
"""

import sys
import duckdb
from io import StringIO
from contextlib import redirect_stdout

sys.path.insert(0, 'C:/Users/sydne/OneDrive/Desktop/MPX3')
from pipeline.populate_tradeable_metrics import get_strategy_config


def test_get_strategy_config_loads_from_db():
    """Test that get_strategy_config() queries validated_setups."""
    conn = duckdb.connect("data/db/gold.db")

    # Capture stdout to verify RR EVIDENCE TABLE is printed
    output = StringIO()
    with redirect_stdout(output):
        config = get_strategy_config(conn)

    printed = output.getvalue()

    # Verify table was printed
    assert "RR EVIDENCE TABLE" in printed, "Must print RR EVIDENCE TABLE"
    assert "Source: validated_setups" in printed, "Must show source"
    assert "id" in printed and "orb_time" in printed and "rr" in printed, "Must show columns"

    # Verify config returned
    assert isinstance(config, dict), "Must return dict"
    assert len(config) > 0, "Must have at least one strategy"

    conn.close()
    print("[PASS] get_strategy_config() loads from database")


def test_rr_values_match_database():
    """Test that RR values in config match validated_setups."""
    conn = duckdb.connect("data/db/gold.db")

    # Load from database
    rows = conn.execute("""
        SELECT orb_time, rr, sl_mode, orb_size_filter
        FROM validated_setups
        WHERE instrument = 'MGC'
        ORDER BY id
    """).fetchall()

    # Load from function
    output = StringIO()
    with redirect_stdout(output):
        config = get_strategy_config(conn)

    # Verify each ORB time
    db_values = {}
    for orb_time, rr, sl_mode, filter_val in rows:
        if orb_time not in db_values:
            db_values[orb_time] = {'rr': rr, 'sl_mode': sl_mode.lower() if sl_mode else 'full', 'filter': filter_val}

    for orb_time, expected in db_values.items():
        assert orb_time in config, f"ORB {orb_time} missing from config"
        assert config[orb_time]['rr'] == expected['rr'], \
            f"ORB {orb_time}: RR mismatch (config={config[orb_time]['rr']}, db={expected['rr']})"
        assert config[orb_time]['sl_mode'] == expected['sl_mode'], \
            f"ORB {orb_time}: SL mode mismatch"

    conn.close()
    print("[PASS] RR values match database")


def test_fail_closed_on_invalid_rr():
    """Test that function aborts if RR is None/0/missing."""
    conn = duckdb.connect(":memory:")

    # Create test table with invalid RR
    conn.execute("""
        CREATE TABLE validated_setups (
            id INTEGER,
            instrument VARCHAR,
            orb_time VARCHAR,
            rr DOUBLE,
            sl_mode VARCHAR,
            orb_size_filter DOUBLE
        )
    """)

    conn.execute("""
        INSERT INTO validated_setups VALUES
        (1, 'MGC', '0900', NULL, 'full', NULL)
    """)

    # Should raise RuntimeError
    try:
        output = StringIO()
        with redirect_stdout(output):
            config = get_strategy_config(conn)
        assert False, "Should have raised RuntimeError on NULL RR"
    except RuntimeError as e:
        assert "invalid RR" in str(e), "Error must mention invalid RR"
        assert "Aborting" in str(e), "Error must mention abort"

    conn.close()
    print("[PASS] Fail-closed logic works")


def test_no_hardcoded_rr_default():
    """Test that RR_DEFAULT constant is removed from file."""
    with open("pipeline/populate_tradeable_metrics.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Check that RR_DEFAULT is not defined as a constant
    assert "RR_DEFAULT = 1.0" not in content, \
        "CRITICAL: RR_DEFAULT = 1.0 hardcoded constant must be removed!"

    print("[PASS] No hardcoded RR_DEFAULT constant")


def test_calculate_tradeable_requires_rr_parameter():
    """Test that calculate_tradeable_for_orb() requires rr parameter."""
    with open("pipeline/populate_tradeable_metrics.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Check function signature
    assert "def calculate_tradeable_for_orb(conn, trade_date: date, orb_time: str, orb_high: float, orb_low: float," in content
    assert "scan_end_local: datetime, rr: float, sl_mode: str):" in content, \
        "calculate_tradeable_for_orb() must have rr parameter without default"

    print("[PASS] calculate_tradeable_for_orb() requires rr parameter")


def test_main_passes_strategy_rr():
    """Test that main() passes strategy-specific RR to calculate_tradeable_for_orb()."""
    with open("pipeline/populate_tradeable_metrics.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Check that main() reads from strategy_config
    assert "strategy_config = get_strategy_config(conn)" in content, \
        "main() must call get_strategy_config()"

    assert "if orb_time in strategy_config:" in content, \
        "main() must check if ORB time in strategy_config"

    assert "rr = strategy_config[orb_time]['rr']" in content, \
        "main() must read RR from strategy_config"

    assert "result = calculate_tradeable_for_orb(" in content and \
           "rr=rr, sl_mode=sl_mode" in content, \
        "main() must pass rr and sl_mode to calculate_tradeable_for_orb()"

    print("[PASS] main() passes strategy-specific RR")


def test_rr_evidence_table_format():
    """Test that RR EVIDENCE TABLE is printed in correct format."""
    conn = duckdb.connect("data/db/gold.db")

    output = StringIO()
    with redirect_stdout(output):
        config = get_strategy_config(conn)

    printed = output.getvalue()

    # Verify required columns
    assert "id" in printed, "Must show id column"
    assert "orb_time" in printed, "Must show orb_time column"
    assert "rr" in printed, "Must show rr column"
    assert "sl_mode" in printed, "Must show sl_mode column"
    assert "filter" in printed, "Must show filter column"
    assert "source" in printed, "Must show source column"

    # Verify actual data is shown
    assert "validated_setups" in printed, "Must show source = validated_setups"

    # Verify summary stats
    assert "Total strategies:" in printed, "Must show total count"
    assert "Unique ORB times:" in printed, "Must show unique ORB count"

    conn.close()
    print("[PASS] RR EVIDENCE TABLE format correct")


def main():
    print("\n" + "="*80)
    print("RR SYNCHRONIZATION REGRESSION TEST")
    print("="*80)
    print("\nThis test ensures populate_tradeable_metrics.py reads RR from validated_setups")
    print("instead of hardcoded RR_DEFAULT.\n")

    tests = [
        test_no_hardcoded_rr_default,
        test_get_strategy_config_loads_from_db,
        test_rr_values_match_database,
        test_fail_closed_on_invalid_rr,
        test_calculate_tradeable_requires_rr_parameter,
        test_main_passes_strategy_rr,
        test_rr_evidence_table_format,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: Unexpected error: {e}")
            failed += 1

    print("\n" + "="*80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*80 + "\n")

    if failed > 0:
        print("[FAILED] TESTS FAILED - DO NOT USE populate_tradeable_metrics.py")
        print("Fix the issues above before running the script.\n")
        sys.exit(1)
    else:
        print("[SUCCESS] ALL TESTS PASSED - populate_tradeable_metrics.py is safe to use")
        print("RR values will be read from validated_setups (not hardcoded).\n")


if __name__ == "__main__":
    main()
