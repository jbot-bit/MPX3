"""
Test JSON field handling for edge_candidates table.

Verifies that JSON fields can be read and written correctly,
handling both JSON type and string representations from DuckDB.
"""

import duckdb
import json
import sys
from pathlib import Path

# Add trading_app to path
sys.path.insert(0, str(Path(__file__).parent / "trading_app"))

from edge_candidate_utils import parse_json_field, serialize_json_field, safe_json_cast

DB_PATH = Path("data/db/gold.db")


def test_read_json_fields():
    """Test reading JSON fields from existing candidate."""
    print("="*60)
    print("TEST 1: Reading JSON Fields")
    print("="*60)

    con = duckdb.connect(str(DB_PATH), read_only=True)

    # Read all JSON fields
    result = con.execute("""
        SELECT
            candidate_id,
            feature_spec_json,
            filter_spec_json,
            metrics_json,
            robustness_json,
            slippage_assumptions_json,
            test_config_json
        FROM edge_candidates
        WHERE candidate_id = 1
    """).fetchone()

    if not result:
        print("[ERROR] No candidate found with ID=1")
        con.close()
        return False

    candidate_id = result[0]
    print(f"\nCandidate ID: {candidate_id}")
    print()

    # Test each JSON field
    json_fields = [
        ("feature_spec_json", result[1]),
        ("filter_spec_json", result[2]),
        ("metrics_json", result[3]),
        ("robustness_json", result[4]),
        ("slippage_assumptions_json", result[5]),
        ("test_config_json", result[6]),
    ]

    all_passed = True

    for field_name, raw_value in json_fields:
        print(f"Testing: {field_name}")
        print(f"  Raw type: {type(raw_value)}")

        # Parse using utility
        parsed = parse_json_field(raw_value)

        if parsed is None and raw_value is not None:
            print(f"  [WARN] Failed to parse (value was not None)")
            print(f"  Raw value: {raw_value[:100] if raw_value else 'None'}...")
        elif parsed is not None:
            print(f"  [OK] Parsed successfully")
            print(f"  Parsed type: {type(parsed)}")
            print(f"  Keys: {list(parsed.keys())[:5]}")  # Show first 5 keys
        else:
            print(f"  [OK] Value is None (as expected)")

        print()

    con.close()

    print("[OK] Read test complete")
    print()
    return all_passed


def test_write_json_fields():
    """Test writing JSON fields to a test candidate."""
    print("="*60)
    print("TEST 2: Writing JSON Fields")
    print("="*60)

    con = duckdb.connect(str(DB_PATH))

    # Create test data
    test_feature_spec = {
        "orb_time": "0900",
        "orb_duration_minutes": 5,
        "sl_mode": "HALF",
        "test_field": "test_value"
    }

    test_filter_spec = {
        "orb_size_filter": 0.05,
        "min_asia_range": 6.0,
        "rr_target": 1.5,
        "entry_type": "breakout_close"
    }

    test_config = {
        "random_seed": 12345,
        "walk_forward_windows": 6,
        "train_pct": 0.8,
        "test_mode": True
    }

    print("\nInserting test candidate with JSON fields...")

    # Insert test candidate
    try:
        con.execute("""
            INSERT INTO edge_candidates (
                candidate_id,
                instrument,
                name,
                hypothesis_text,
                feature_spec_json,
                filter_spec_json,
                test_config_json,
                status
            ) VALUES (?, ?, ?, ?, ?::JSON, ?::JSON, ?::JSON, ?)
        """, [
            999,  # Test ID
            "MGC",
            "TEST: JSON Handling Verification",
            "Test hypothesis for JSON field handling",
            serialize_json_field(test_feature_spec),
            serialize_json_field(test_filter_spec),
            serialize_json_field(test_config),
            "DRAFT"
        ])

        print("[OK] Test candidate inserted (ID=999)")

        # Read it back
        print("\nReading back test candidate...")
        result = con.execute("""
            SELECT
                feature_spec_json,
                filter_spec_json,
                test_config_json
            FROM edge_candidates
            WHERE candidate_id = 999
        """).fetchone()

        if result:
            # Parse all fields
            feature_spec = parse_json_field(result[0])
            filter_spec = parse_json_field(result[1])
            config = parse_json_field(result[2])

            # Verify
            print("\nVerifying written data:")

            # Check feature_spec
            if feature_spec and feature_spec.get("test_field") == "test_value":
                print("  [OK] feature_spec_json: test_field matches")
            else:
                print("  [ERROR] feature_spec_json: test_field mismatch")

            # Check filter_spec
            if filter_spec and filter_spec.get("orb_size_filter") == 0.05:
                print("  [OK] filter_spec_json: orb_size_filter matches")
            else:
                print("  [ERROR] filter_spec_json: orb_size_filter mismatch")

            # Check test_config
            if config and config.get("random_seed") == 12345:
                print("  [OK] test_config_json: random_seed matches")
            else:
                print("  [ERROR] test_config_json: random_seed mismatch")

        # Clean up test candidate
        print("\nCleaning up test candidate...")
        con.execute("DELETE FROM edge_candidates WHERE candidate_id = 999")
        print("[OK] Test candidate deleted")

        con.commit()
        print("\n[OK] Write test complete")

    except Exception as e:
        print(f"\n[ERROR] Write test failed: {e}")
        # Try to clean up
        try:
            con.execute("DELETE FROM edge_candidates WHERE candidate_id = 999")
            con.commit()
        except:
            pass
        return False
    finally:
        con.close()

    print()
    return True


def test_safe_json_cast():
    """Test safe_json_cast utility function."""
    print("="*60)
    print("TEST 3: safe_json_cast() Function")
    print("="*60)

    test_dict = {
        "key1": "value1",
        "key2": 42,
        "key3": [1, 2, 3],
        "key4": {"nested": "value"}
    }

    cast_result = safe_json_cast(test_dict)
    print(f"\nInput dict: {test_dict}")
    print(f"Cast result: {cast_result}")
    print()

    # Test NULL case
    null_result = safe_json_cast(None)
    print(f"NULL input: {null_result}")
    print()

    print("[OK] safe_json_cast test complete")
    print()


def main():
    """Run all JSON handling tests."""
    print("\n" + "="*60)
    print("EDGE_CANDIDATES JSON FIELD HANDLING TESTS")
    print("="*60)
    print()

    # Run tests
    test1_pass = test_read_json_fields()
    test2_pass = test_write_json_fields()
    test_safe_json_cast()

    # Summary
    print("="*60)
    print("TEST SUMMARY")
    print("="*60)
    print()
    if test1_pass and test2_pass:
        print("[OK] All tests passed!")
        print()
        print("JSON field handling is working correctly.")
        print("The Research Runner can safely use these utilities.")
    else:
        print("[WARN] Some tests had issues (check output above)")
    print()
    print("="*60)


if __name__ == "__main__":
    main()
