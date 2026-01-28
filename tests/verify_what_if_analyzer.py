"""
What-If Analyzer - Comprehensive Verification Suite

Implements bugs.txt verification protocol:
- Step 2B: Determinism tests (3x runs, check drift)
- Step 2D: Invariants (baseline = match + non-match)
- Step 2C: Truth-table tests (10 dates, condition correctness)
- Step 2E: Cross-check known good (reproduce validated setup)
- Step 4: Red flag scan (TODO/stub/placeholder)

Usage:
    python tests/verify_what_if_analyzer.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import duckdb
from datetime import date
from analysis.what_if_engine import WhatIfEngine
from analysis.what_if_snapshots import SnapshotManager
import glob
import re


class VerificationReport:
    """Tracks verification results"""
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0

    def add_test(self, name: str, passed: bool, details: str):
        self.tests.append({
            'name': name,
            'passed': passed,
            'details': details
        })
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def print_report(self):
        print("\n" + "="*60)
        print("What-If Analyzer - Verification Report")
        print("="*60)

        for test in self.tests:
            status = "[PASS]" if test['passed'] else "[FAIL]"
            print(f"\n{status} {test['name']}")
            print(f"  {test['details']}")

        print("\n" + "="*60)
        print(f"Summary: {self.passed}/{len(self.tests)} tests passed")

        if self.failed == 0:
            print("\n*** ALL VERIFICATION TESTS PASSED ***")
            print("System is production-ready with zero skeletons detected.")
            return True
        else:
            print(f"\n[WARN] {self.failed} test(s) failed")
            print("Review failures before deploying to production.")
            return False


def test_determinism(conn, report):
    """
    Step 2B: Determinism Tests
    Run 3x with identical inputs, verify 0 drift
    """
    print("\n=== Step 2B: Determinism Tests ===")

    engine = WhatIfEngine(conn)

    # Test parameters (identical for all 3 runs)
    params = {
        'instrument': 'MGC',
        'orb_time': '1000',
        'direction': 'BOTH',
        'rr': 2.0,
        'sl_mode': 'FULL',
        'conditions': {'orb_size_min': 0.5, 'asia_travel_max': 2.5},
        'date_start': '2024-01-01',
        'date_end': '2025-12-31',
        'use_cache': False  # Force fresh calculation each time
    }

    # Run 3 times
    results = []
    for i in range(3):
        result = engine.analyze_conditions(**params)
        results.append({
            'baseline_sample': result['baseline'].sample_size,
            'baseline_wr': result['baseline'].win_rate,
            'baseline_expr': result['baseline'].expected_r,
            'conditional_sample': result['conditional'].sample_size,
            'conditional_wr': result['conditional'].win_rate,
            'conditional_expr': result['conditional'].expected_r,
            'delta_expr': result['delta']['expected_r']
        })

    # Check for drift
    drift_found = False
    drift_details = []

    for key in results[0].keys():
        val1, val2, val3 = results[0][key], results[1][key], results[2][key]

        if val1 != val2 or val2 != val3 or val1 != val3:
            drift_found = True
            drift_details.append(f"{key}: {val1} vs {val2} vs {val3}")

    if drift_found:
        details = "DRIFT DETECTED: " + ", ".join(drift_details)
        report.add_test("Determinism (3x runs)", False, details)
    else:
        details = f"All 3 runs identical: {results[0]['baseline_sample']} trades, {results[0]['conditional_expr']:.6f}R"
        report.add_test("Determinism (3x runs)", True, details)


def test_invariants(conn, report):
    """
    Step 2D: Invariants
    - baseline_sample = conditional_sample + non_matched_sample
    - baseline_wins = conditional_wins + non_matched_wins
    - baseline_ExpR = weighted average
    """
    print("\n=== Step 2D: Invariant Tests ===")

    engine = WhatIfEngine(conn)

    result = engine.analyze_conditions(
        instrument='MGC',
        orb_time='1000',
        direction='BOTH',
        rr=2.0,
        sl_mode='FULL',
        conditions={'orb_size_min': 0.5},
        date_start='2024-01-01',
        date_end='2025-12-31'
    )

    baseline = result['baseline']
    conditional = result['conditional']
    non_matched = result['non_matched']

    # Invariant 1: Sample size
    sample_check = baseline.sample_size == (conditional.sample_size + non_matched.sample_size)

    # Invariant 2: Wins (count wins from trades)
    baseline_wins = sum(1 for t in baseline.trades if t['outcome'] == 'WIN')
    conditional_wins = sum(1 for t in conditional.trades if t['outcome'] == 'WIN')
    non_matched_wins = sum(1 for t in non_matched.trades if t['outcome'] == 'WIN')
    wins_check = baseline_wins == (conditional_wins + non_matched_wins)

    # Invariant 3: Expected R is weighted average (within floating point tolerance)
    if baseline.sample_size > 0:
        weight_cond = conditional.sample_size / baseline.sample_size
        weight_non = non_matched.sample_size / baseline.sample_size
        expected_weighted = (conditional.expected_r * weight_cond) + (non_matched.expected_r * weight_non)
        weighted_check = abs(baseline.expected_r - expected_weighted) < 0.001
    else:
        weighted_check = False

    all_pass = sample_check and wins_check and weighted_check

    if all_pass:
        details = f"All invariants hold: {baseline.sample_size} = {conditional.sample_size} + {non_matched.sample_size}"
        report.add_test("Invariants (math checks)", True, details)
    else:
        issues = []
        if not sample_check:
            issues.append(f"Sample: {baseline.sample_size} != {conditional.sample_size} + {non_matched.sample_size}")
        if not wins_check:
            issues.append(f"Wins: {baseline_wins} != {conditional_wins} + {non_matched_wins}")
        if not weighted_check:
            issues.append(f"WeightedAvg: {baseline.expected_r:.6f} != {expected_weighted:.6f}")

        details = "INVARIANT VIOLATIONS: " + ", ".join(issues)
        report.add_test("Invariants (math checks)", False, details)


def test_truth_table(conn, report):
    """
    Step 2C: Truth-table tests
    Pick 10 random dates and verify condition evaluation
    """
    print("\n=== Step 2C: Truth-Table Tests ===")

    # Get 10 random dates from daily_features
    dates = conn.execute("""
        SELECT date_local, orb_1000_size, atr_20
        FROM daily_features
        WHERE instrument = 'MGC' AND orb_1000_size IS NOT NULL AND atr_20 IS NOT NULL
        ORDER BY RANDOM()
        LIMIT 10
    """).fetchall()

    if len(dates) < 10:
        report.add_test("Truth-table (10 dates)", False, f"Insufficient data: only {len(dates)} dates available")
        return

    # Test condition: orb_size_min = 0.5
    mismatches = []

    for date_local, orb_size, atr in dates:
        # Manual calculation
        orb_size_norm = orb_size / atr if atr > 0 else None
        expected_pass = orb_size_norm is not None and orb_size_norm >= 0.5

        # Engine calculation (query with that specific date)
        engine = WhatIfEngine(conn)
        result = engine.analyze_conditions(
            instrument='MGC',
            orb_time='1000',
            direction='BOTH',
            rr=2.0,
            sl_mode='FULL',
            conditions={'orb_size_min': 0.5},
            date_start=str(date_local),
            date_end=str(date_local)
        )

        # Check if this date was included in conditional
        engine_pass = result['conditional'].sample_size > 0

        if expected_pass != engine_pass:
            mismatches.append(f"{date_local}: expected {expected_pass}, got {engine_pass} (ORB={orb_size_norm:.3f})")

    if len(mismatches) == 0:
        details = f"All 10 dates evaluated correctly"
        report.add_test("Truth-table (10 dates)", True, details)
    else:
        details = "MISMATCHES: " + "; ".join(mismatches)
        report.add_test("Truth-table (10 dates)", False, details)


def test_known_good(conn, report):
    """
    Step 2E: Cross-check against known good
    Reproduce a validated setup and check metrics match
    """
    print("\n=== Step 2E: Known Good Cross-Check ===")

    # Get a validated setup from validated_setups
    validated = conn.execute("""
        SELECT instrument, orb_time, rr, sl_mode, orb_size_filter,
               win_rate, expected_r, sample_size
        FROM validated_setups
        WHERE instrument = 'MGC' AND orb_time = '1000' AND sample_size >= 30
        LIMIT 1
    """).fetchone()

    if not validated:
        report.add_test("Known good cross-check", False, "No validated MGC 1000 setup found in database")
        return

    inst, orb_time, rr, sl_mode, orb_filter, known_wr, known_expr, known_sample = validated

    # Recompute with What-If engine (no conditions to get baseline)
    engine = WhatIfEngine(conn)
    result = engine.analyze_conditions(
        instrument=inst,
        orb_time=orb_time,
        direction='BOTH',
        rr=rr,
        sl_mode=sl_mode,
        conditions=None,  # No filters for baseline comparison
        date_start='2024-01-01',
        date_end='2025-12-31'
    )

    # Compare metrics (allow small float tolerance)
    wr_match = abs(result['baseline'].win_rate - known_wr) < 0.05  # 5% tolerance
    expr_match = abs(result['baseline'].expected_r - known_expr) < 0.1  # 0.1R tolerance
    sample_match = result['baseline'].sample_size == known_sample

    if wr_match and expr_match and sample_match:
        details = f"Reproduced {inst} {orb_time} RR={rr}: {result['baseline'].sample_size} trades, {result['baseline'].expected_r:.3f}R"
        report.add_test("Known good cross-check", True, details)
    else:
        issues = []
        if not wr_match:
            issues.append(f"WR: {result['baseline'].win_rate:.1%} vs {known_wr:.1%}")
        if not expr_match:
            issues.append(f"ExpR: {result['baseline'].expected_r:.3f}R vs {known_expr:.3f}R")
        if not sample_match:
            issues.append(f"Sample: {result['baseline'].sample_size} vs {known_sample}")

        details = "MISMATCH: " + ", ".join(issues)
        report.add_test("Known good cross-check", False, details)


def scan_red_flags(report):
    """
    Step 4: Search for red flags in code
    TODO, pass, placeholder, stub, random, mock, return {}, print(, try/except swallows
    """
    print("\n=== Step 4: Red Flag Scan ===")

    # Files to scan
    files_to_scan = [
        'analysis/what_if_engine.py',
        'analysis/what_if_snapshots.py',
        'trading_app/live_scanner.py'
    ]

    red_flags = [
        (r'\bTODO\b', 'TODO'),
        (r'^\s*pass\s*$', 'pass (empty impl)'),
        (r'\bplaceholder\b', 'placeholder'),
        (r'\bstub\b', 'stub'),
        (r'\bmock\b', 'mock'),
        (r'return\s*\{\s*\}', 'return {}'),
        (r'print\s*\(', 'print( in core logic'),
        (r'except.*:\s*pass', 'except swallows')
    ]

    issues_found = []

    for file_path in files_to_scan:
        full_path = os.path.join(os.path.dirname(__file__), '..', file_path)

        if not os.path.exists(full_path):
            continue

        with open(full_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            for pattern, flag_name in red_flags:
                if re.search(pattern, line, re.IGNORECASE):
                    issues_found.append(f"{file_path}:{i} - {flag_name}")

    if len(issues_found) == 0:
        details = "No red flags detected in core logic files"
        report.add_test("Red flag scan", True, details)
    else:
        details = f"FOUND {len(issues_found)} RED FLAGS: " + "; ".join(issues_found[:5])
        if len(issues_found) > 5:
            details += f" (and {len(issues_found) - 5} more...)"
        report.add_test("Red flag scan", False, details)


def run_verification():
    """Run all verification tests"""
    print("="*60)
    print("What-If Analyzer - Comprehensive Verification")
    print("Implementing bugs.txt protocol")
    print("="*60)

    # Connect to database
    conn = duckdb.connect('data/db/gold.db')

    # Create report
    report = VerificationReport()

    # Run all tests
    try:
        test_determinism(conn, report)
        test_invariants(conn, report)
        test_truth_table(conn, report)
        test_known_good(conn, report)
        scan_red_flags(report)
    except Exception as e:
        print(f"\n[ERROR] Test suite crashed: {e}")
        import traceback
        traceback.print_exc()
        report.add_test("Test suite execution", False, str(e))
    finally:
        conn.close()

    # Print report
    success = report.print_report()

    return success


if __name__ == '__main__':
    success = run_verification()
    sys.exit(0 if success else 1)
