#!/usr/bin/env python3
"""
FORBIDDEN PATHS MODIFIED CHECK (UPDATE18)
==========================================

Hard blocks commits that modify forbidden paths (canonical trading logic).

Forbidden paths:
- strategies/
- pipeline/
- schema/migrations/
- trading_app/cost_model.py
- trading_app/entry_rules.py
- trading_app/execution_engine.py

Exit codes:
    0 - No forbidden paths modified (PASS)
    1 - Forbidden paths modified (FAIL - HARD BLOCK)
"""

import sys
import subprocess
from pathlib import Path

# ANSI colors
RED = '\033[91m'
GREEN = '\033[92m'
RESET = '\033[0m'

# Forbidden paths (CANNOT be modified during normal UI work)
FORBIDDEN_DIRS = [
    'strategies/',
    'pipeline/',
    'schema/migrations/',
]

FORBIDDEN_FILES = [
    'trading_app/cost_model.py',
    'trading_app/entry_rules.py',
    'trading_app/execution_engine.py',
]


def get_modified_files() -> list[str]:
    """Get list of modified files from git diff."""
    try:
        # Get modified files (staged + unstaged)
        result = subprocess.run(
            ['git', 'diff', '--name-only', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
        modified = result.stdout.strip().split('\n') if result.stdout.strip() else []

        # Also check staged files
        result = subprocess.run(
            ['git', 'diff', '--name-only', '--cached'],
            capture_output=True,
            text=True,
            check=True
        )
        staged = result.stdout.strip().split('\n') if result.stdout.strip() else []

        return list(set(modified + staged))
    except subprocess.CalledProcessError:
        # Not a git repo or no changes
        return []


def check_forbidden_paths() -> tuple[bool, list[str]]:
    """Check if forbidden paths were modified."""
    modified_files = get_modified_files()

    violations = []

    for file in modified_files:
        # Check forbidden directories
        for forbidden_dir in FORBIDDEN_DIRS:
            if file.startswith(forbidden_dir):
                violations.append(file)
                break

        # Check forbidden files
        if file in FORBIDDEN_FILES:
            violations.append(file)

    return len(violations) == 0, violations


def main():
    """Main entry point."""
    print("=" * 80)
    print("FORBIDDEN PATHS MODIFIED CHECK (UPDATE18)")
    print("=" * 80)
    print()
    print("Forbidden directories:")
    for d in FORBIDDEN_DIRS:
        print(f"  - {d}")
    print()
    print("Forbidden files:")
    for f in FORBIDDEN_FILES:
        print(f"  - {f}")
    print()

    passed, violations = check_forbidden_paths()

    if passed:
        print(f"{GREEN}[PASS] No forbidden paths modified{RESET}")
        return 0
    else:
        print(f"{RED}[FAIL] Forbidden paths modified:{RESET}")
        print()
        for file in violations:
            print(f"  {RED}[X]{RESET} {file}")
        print()
        print("=" * 80)
        print("FORBIDDEN PATHS CANNOT BE MODIFIED DURING UI WORK")
        print("=" * 80)
        print()
        print("These paths contain canonical trading logic:")
        print("- strategies/ - Strategy execution logic")
        print("- pipeline/ - Data pipeline and feature building")
        print("- schema/migrations/ - Database migrations")
        print("- cost_model.py - Transaction cost model (CANONICAL)")
        print("- entry_rules.py - Entry rule implementations")
        print("- execution_engine.py - Trade execution logic (CANONICAL)")
        print()
        print("If you need to modify these files:")
        print("1. Create a separate branch for trading logic changes")
        print("2. Get explicit approval before proceeding")
        print("3. Do NOT mix UI work with trading logic changes")
        print()
        return 1


if __name__ == '__main__':
    sys.exit(main())
