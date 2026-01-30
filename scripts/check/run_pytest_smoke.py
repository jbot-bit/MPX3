#!/usr/bin/env python3
"""
PYTEST SMOKE TEST RUNNER (UPDATE17)
====================================

Runs critical UI contract tests to verify fail-closed behavior.

Tests:
- UI status derivation (PASS/WEAK/FAIL/UNKNOWN)
- Approval gating (only PASS allows approval)
- Approval wiring (calls real promotion function)

Exit codes:
    0 - All tests pass
    1 - Tests failed
"""

import sys
import subprocess
from pathlib import Path

# ANSI colors (ASCII-safe for Windows)
RED = '\033[91m'
GREEN = '\033[92m'
RESET = '\033[0m'


def main():
    """Run pytest smoke tests."""

    print("=" * 80)
    print("PYTEST SMOKE TESTS (UI FAIL-CLOSED CONTRACT)")
    print("=" * 80)
    print()

    # Get repo root
    repo_root = Path(__file__).parent.parent.parent
    test_file = repo_root / 'tests' / 'test_ui_fail_closed.py'

    if not test_file.exists():
        print(f"{RED}[FAIL] Test file not found: {test_file}{RESET}")
        return 1

    print(f"Running tests: {test_file.name}")
    print()

    # Run pytest with quiet output
    result = subprocess.run(
        ['python', '-m', 'pytest', str(test_file), '-q', '--tb=short'],
        cwd=str(repo_root),
        capture_output=False,  # Show pytest output directly
    )

    print()
    if result.returncode == 0:
        print(f"{GREEN}[PASS] All UI contract tests passed{RESET}")
        return 0
    else:
        print(f"{RED}[FAIL] Some UI contract tests failed{RESET}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
