#!/usr/bin/env python3
"""
Run Dual-Track Implementation Test Suite
=========================================

Quick test runner for all dual-track tests.

Usage:
    python tests/run_dual_track_tests.py          # Run all tests
    python tests/run_dual_track_tests.py rr       # Run RR sync tests only
    python tests/run_dual_track_tests.py entry    # Run entry price tests only
    python tests/run_dual_track_tests.py calc     # Run calculation tests only
    python tests/run_dual_track_tests.py cost     # Run cost model tests only
    python tests/run_dual_track_tests.py outcome  # Run outcome tests only
"""

import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
TESTS_DIR = PROJECT_ROOT / "tests"

# Test file mapping
TEST_FILES = {
    'rr': 'test_rr_sync.py',
    'entry': 'test_entry_price.py',
    'calc': 'test_tradeable_calculations.py',
    'cost': 'test_cost_model_integration.py',
    'outcome': 'test_outcome_classification.py',
}

def run_tests(test_name=None):
    """Run tests with pytest"""
    if test_name:
        if test_name not in TEST_FILES:
            print(f"ERROR: Unknown test name '{test_name}'")
            print(f"Valid options: {', '.join(TEST_FILES.keys())}")
            return 1

        test_file = TESTS_DIR / TEST_FILES[test_name]
        if not test_file.exists():
            print(f"ERROR: Test file not found: {test_file}")
            return 1

        print(f"\n{'='*80}")
        print(f"Running: {TEST_FILES[test_name]}")
        print(f"{'='*80}\n")

        cmd = ['python', '-m', 'pytest', str(test_file), '-v', '--tb=short']
    else:
        print(f"\n{'='*80}")
        print("Running ALL dual-track tests")
        print(f"{'='*80}\n")

        # Run all test files in order
        cmd = [
            'python', '-m', 'pytest',
            str(TESTS_DIR / 'test_rr_sync.py'),
            str(TESTS_DIR / 'test_entry_price.py'),
            str(TESTS_DIR / 'test_tradeable_calculations.py'),
            str(TESTS_DIR / 'test_cost_model_integration.py'),
            str(TESTS_DIR / 'test_outcome_classification.py'),
            '-v', '--tb=short'
        ]

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return result.returncode


def main():
    if len(sys.argv) > 1:
        test_name = sys.argv[1].lower()
        return run_tests(test_name)
    else:
        return run_tests()


if __name__ == "__main__":
    sys.exit(main())
