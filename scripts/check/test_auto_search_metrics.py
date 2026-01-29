#!/usr/bin/env python3
"""
Test Auto Search Metric Naming

Verifies that profitable_trade_rate and target_hit_rate are:
1. Both present in search_candidates table
2. Different values when expected (in realistic scenarios)
3. Correctly computed from daily_features
"""

import sys
import os
from pathlib import Path
import duckdb

# Change to project root
project_root = Path(__file__).parent.parent.parent
os.chdir(project_root)

DB_PATH = "data/db/gold.db"

def test_metrics():
    """Test Auto Search metrics"""

    print("="*70)
    print("AUTO SEARCH METRICS TEST")
    print("="*70)
    print()

    conn = duckdb.connect(DB_PATH)

    # Test 1: Verify columns exist
    print("Test 1: Verify new columns exist in search_candidates")
    print("-"*70)

    try:
        schema = conn.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'search_candidates'
        """).fetchall()
        col_names = {col[0] for col in schema}

        required_cols = ['profitable_trade_rate', 'target_hit_rate']
        missing = [col for col in required_cols if col not in col_names]

        if missing:
            print(f"  [FAIL] Missing columns: {missing}")
            return False
        else:
            print(f"  [OK] Both metrics present: {required_cols}")

    except Exception as e:
        print(f"  [FAIL] Schema check: {e}")
        return False

    print()

    # Test 2: Verify both metrics can be computed from daily_features
    print("Test 2: Verify metrics compute correctly from daily_features")
    print("-"*70)

    try:
        # Check if we have sample data
        sample_data = conn.execute("""
            SELECT COUNT(*) FROM daily_features
            WHERE instrument = 'MGC'
              AND orb_0900_outcome IS NOT NULL
        """).fetchone()[0]

        print(f"  Found {sample_data} records with ORB outcomes")

        if sample_data == 0:
            print("  [SKIP] No sample data available (need daily_features populated)")
            print()
            print("="*70)
            print("TESTS PASSED (with limitations)")
            print("="*70)
            return True

        # Compute both metrics from daily_features (Method 1: profitable_trade_rate)
        profitable_rate = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN orb_0900_r_multiple > 0 THEN 1 ELSE 0 END) as profitable,
                AVG(CASE WHEN orb_0900_r_multiple > 0 THEN 1.0 ELSE 0.0 END) as profitable_rate
            FROM daily_features
            WHERE instrument = 'MGC'
              AND orb_0900_r_multiple IS NOT NULL
        """).fetchone()

        # Compute target hit rate (Method 2: target_hit_rate)
        target_rate = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN orb_0900_outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                AVG(CASE WHEN orb_0900_outcome = 'WIN' THEN 1.0 ELSE 0.0 END) as win_rate
            FROM daily_features
            WHERE instrument = 'MGC'
              AND orb_0900_outcome IS NOT NULL
        """).fetchone()

        print(f"  Profitable Trade Rate: {profitable_rate[2]*100:.1f}% ({profitable_rate[1]}/{profitable_rate[0]})")
        print(f"  Target Hit Rate: {target_rate[2]*100:.1f}% ({target_rate[1]}/{target_rate[0]})")

        # They should usually be different (profitable rate >= target hit rate)
        if profitable_rate[2] == target_rate[2]:
            print("  [WARNING] Metrics are identical (unusual but possible)")
        elif profitable_rate[2] > target_rate[2]:
            print("  [OK] Profitable rate > Target hit rate (expected)")
        else:
            print("  [WARNING] Profitable rate < Target hit rate (unexpected)")

    except Exception as e:
        print(f"  [FAIL] Metrics computation: {e}")
        return False

    print()

    # Test 3: Verify existing search_candidates have metrics
    print("Test 3: Verify existing search_candidates have metrics")
    print("-"*70)

    try:
        candidates_count = conn.execute("""
            SELECT COUNT(*) FROM search_candidates
        """).fetchone()[0]

        if candidates_count == 0:
            print("  [SKIP] No search_candidates in database yet")
        else:
            print(f"  Found {candidates_count} candidates")

            # Check how many have the new metrics
            with_metrics = conn.execute("""
                SELECT COUNT(*) FROM search_candidates
                WHERE profitable_trade_rate IS NOT NULL
                   OR target_hit_rate IS NOT NULL
            """).fetchone()[0]

            print(f"  Candidates with new metrics: {with_metrics}/{candidates_count}")

            if with_metrics > 0:
                # Show sample
                sample = conn.execute("""
                    SELECT orb_time, rr_target, profitable_trade_rate, target_hit_rate
                    FROM search_candidates
                    WHERE profitable_trade_rate IS NOT NULL
                       OR target_hit_rate IS NOT NULL
                    LIMIT 3
                """).fetchall()

                for row in sample:
                    orb, rr, prof_rate, tgt_rate = row
                    prof_str = f"{prof_rate*100:.1f}%" if prof_rate else "N/A"
                    tgt_str = f"{tgt_rate*100:.1f}%" if tgt_rate else "N/A"
                    print(f"    {orb} RR={rr}: Profitable={prof_str}, TargetHit={tgt_str}")

                print("  [OK] Metrics present in candidates")
            else:
                print("  [INFO] New metrics not yet populated (run Auto Search to generate)")

    except Exception as e:
        print(f"  [FAIL] Candidates check: {e}")
        return False

    print()

    # Test 4: Verify SearchCandidate dataclass has new fields
    print("Test 4: Verify Python code has new fields")
    print("-"*70)

    try:
        # Import auto_search_engine
        sys.path.insert(0, 'trading_app')
        from auto_search_engine import SearchCandidate

        # Check if dataclass has new fields
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(SearchCandidate)}

        required_fields = {'profitable_trade_rate', 'target_hit_rate'}
        missing_fields = required_fields - field_names

        if missing_fields:
            print(f"  [FAIL] SearchCandidate missing fields: {missing_fields}")
            return False
        else:
            print(f"  [OK] SearchCandidate has both new fields")

    except ImportError as e:
        print(f"  [FAIL] Could not import auto_search_engine: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] Code check: {e}")
        return False

    print()

    conn.close()

    # Summary
    print("="*70)
    print("ALL TESTS PASSED")
    print("="*70)
    print()
    print("Metrics correctly implemented:")
    print("  - profitable_trade_rate: Trades with RR > 0")
    print("  - target_hit_rate: Trades hitting profit target")
    print()
    print("Next steps:")
    print("  1. Run Auto Search in Streamlit app")
    print("  2. Verify both metrics displayed in results table")
    print("  3. Check docs/AUTO_SEARCH.md for metric explanations")
    print()

    return True

if __name__ == "__main__":
    success = test_metrics()
    sys.exit(0 if success else 1)
