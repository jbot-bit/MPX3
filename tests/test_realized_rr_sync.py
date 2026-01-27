#!/usr/bin/env python3
"""
TEST: Realized RR Sync

Verifies daily_features realized_rr matches execution_engine calculations.

CRITICAL: daily_features.orb_XXXX_realized_rr must match what execution_engine
would produce for the same trade (deterministic verification).
"""

import sys
from pathlib import Path
import duckdb
from datetime import datetime

# Add project root to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from pipeline.cost_model import calculate_realized_rr

DB_PATH = "../gold.db"  # Root directory database


def test_daily_features_schema():
    """Verify daily_features has realized_rr columns."""
    print("=" * 70)
    print("TEST: daily_features Schema")
    print("=" * 70)
    print()

    con = duckdb.connect(DB_PATH)

    schema = con.execute("PRAGMA table_info(daily_features)").fetchall()
    columns = [col[1] for col in schema]

    # Check for realized_rr columns (6 ORBs × 3 columns = 18 total)
    orb_times = ['0900', '1000', '1100', '1800', '2300', '0030']
    expected_columns = []
    for orb in orb_times:
        expected_columns.append(f'orb_{orb}_realized_rr')
        expected_columns.append(f'orb_{orb}_realized_risk_dollars')
        expected_columns.append(f'orb_{orb}_realized_reward_dollars')

    missing = [col for col in expected_columns if col not in columns]

    con.close()

    if missing:
        print(f"[FAIL] Missing {len(missing)} columns:")
        for col in missing:
            print(f"  - {col}")
        print()
        print("REQUIRED FIX: Run Phase 3 schema migration")
        return False
    else:
        print(f"[OK] All {len(expected_columns)} realized_rr columns present")
        print()
        return True


def test_realized_rr_populated():
    """Verify daily_features has non-NULL realized_rr values."""
    print("=" * 70)
    print("TEST: daily_features Realized RR Populated")
    print("=" * 70)
    print()

    con = duckdb.connect(DB_PATH)

    # Check 1000 ORB (most active)
    result = con.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN orb_1000_realized_rr IS NOT NULL THEN 1 ELSE 0 END) as populated
        FROM daily_features
        WHERE instrument = 'MGC'
        AND orb_1000_break_dir != 'NONE'
    """).fetchone()

    total, populated = result
    coverage_pct = (populated / total * 100) if total > 0 else 0

    con.close()

    print(f"1000 ORB coverage: {populated}/{total} ({coverage_pct:.1f}%)")
    print()

    if coverage_pct < 95.0:
        print(f"[FAIL] Coverage too low ({coverage_pct:.1f}% < 95%)")
        print("REQUIRED FIX: Rebuild daily_features with realized_rr")
        return False
    else:
        print(f"[OK] Coverage acceptable ({coverage_pct:.1f}% >= 95%)")
        return True


def test_realized_rr_calculations_match():
    """Verify daily_features realized_rr matches cost_model calculations."""
    print("=" * 70)
    print("TEST: Realized RR Calculations Match cost_model")
    print("=" * 70)
    print()

    con = duckdb.connect(DB_PATH)

    # Get recent 1000 ORB trades
    trades = con.execute("""
        SELECT
            date_local,
            orb_1000_size,
            orb_1000_risk_ticks,
            orb_1000_realized_rr,
            orb_1000_realized_risk_dollars,
            orb_1000_realized_reward_dollars
        FROM daily_features
        WHERE instrument = 'MGC'
        AND orb_1000_break_dir != 'NONE'
        AND orb_1000_realized_rr IS NOT NULL
        ORDER BY date_local DESC
        LIMIT 10
    """).fetchall()

    con.close()

    if not trades:
        print("[SKIP] No trades found to verify")
        return True

    print(f"Verifying {len(trades)} recent trades...")
    print()

    mismatches = []
    for trade in trades:
        date_local, orb_size, risk_ticks, stored_rr, stored_risk, stored_reward = trade

        # Recalculate using cost_model
        stop_points = risk_ticks * 0.1  # ticks to points

        try:
            calculated = calculate_realized_rr(
                instrument='MGC',
                stop_distance_points=stop_points,
                rr_theoretical=1.0,  # daily_features uses RR=1.0
                stress_level='normal'
            )

            calc_rr = calculated['realized_rr']
            calc_risk = calculated['realized_risk_dollars']
            calc_reward = calculated['realized_reward_dollars']

            # Allow 0.001 tolerance for floating point
            rr_match = abs(stored_rr - calc_rr) < 0.001
            risk_match = abs(stored_risk - calc_risk) < 0.01
            reward_match = abs(stored_reward - calc_reward) < 0.01

            if not (rr_match and risk_match and reward_match):
                mismatches.append({
                    'date': date_local,
                    'stored_rr': stored_rr,
                    'calc_rr': calc_rr,
                    'stored_risk': stored_risk,
                    'calc_risk': calc_risk,
                    'stored_reward': stored_reward,
                    'calc_reward': calc_reward,
                })

        except Exception as e:
            print(f"[ERROR] Calculation failed for {date_local}: {e}")
            return False

    if mismatches:
        print(f"[FAIL] {len(mismatches)} mismatches found:")
        for mm in mismatches:
            print(f"\n  Date: {mm['date']}")
            print(f"  Realized RR: stored={mm['stored_rr']:.3f}, calculated={mm['calc_rr']:.3f}")
            print(f"  Risk $: stored=${mm['stored_risk']:.2f}, calculated=${mm['calc_risk']:.2f}")
            print(f"  Reward $: stored=${mm['stored_reward']:.2f}, calculated=${mm['calc_reward']:.2f}")
        print()
        print("REQUIRED FIX: Rebuild daily_features using cost_model")
        return False
    else:
        print(f"[OK] All {len(trades)} trades match cost_model calculations")
        print()
        return True


def run_all_tests():
    """Run all realized RR sync tests."""
    print()
    print("=" * 70)
    print("REALIZED RR SYNC TESTS")
    print("=" * 70)
    print()

    tests = [
        test_daily_features_schema,
        test_realized_rr_populated,
        test_realized_rr_calculations_match,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"[ERROR] Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")
    print()

    if passed == total:
        print("[OK] ALL TESTS PASSED")
        print()
        print("daily_features realized_rr values match execution_engine/cost_model calculations.")
        return True
    else:
        print("[FAIL] SOME TESTS FAILED")
        print()
        print("CRITICAL: daily_features and cost_model must produce identical values.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
