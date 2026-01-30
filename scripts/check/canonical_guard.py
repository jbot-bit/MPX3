#!/usr/bin/env python3
"""
CANONICAL GUARD (UPDATE18)
===========================

Blocks accidental edits to canonical documents.

Protected files:
- CLAUDE.md
- CANONICAL_LOGIC.txt
- GUARDIAN.md

Override:
- Set ALLOW_CANONICAL=1 environment variable
- Or include "CANONICAL-APPEND:" in commit message

Exit codes:
    0 - No canonical files modified (PASS)
    1 - Canonical files modified without override (FAIL)
"""

import os
import sys
import subprocess
from pathlib import Path

# ANSI colors
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RESET = '\033[0m'

# Canonical documents (READ-ONLY unless explicitly allowed)
CANONICAL_FILES = [
    'CLAUDE.md',
    'CANONICAL_LOGIC.txt',
    'GUARDIAN.md',
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


def check_canonical_guard() -> bool:
    """Check if canonical files were modified."""
    # Check for override
    allow_canonical = os.environ.get('ALLOW_CANONICAL', '').strip() == '1'

    modified_files = get_modified_files()

    # Check if any canonical files modified
    canonical_modified = []
    for file in modified_files:
        if file in CANONICAL_FILES:
            canonical_modified.append(file)

    if not canonical_modified:
        return True  # No canonical files modified

    # Canonical files were modified
    if allow_canonical:
        print(f"{YELLOW}[WARN] Canonical files modified (ALLOW_CANONICAL=1):{RESET}")
        for file in canonical_modified:
            print(f"  - {file}")
        return True  # With warning

    # FAIL - canonical files modified without override
    print(f"{RED}[FAIL] Canonical files modified without override:{RESET}")
    for file in canonical_modified:
        print(f"  - {file}")
    print()
    print("Canonical documents are READ-ONLY during normal work.")
    print()
    print("To override (if explicitly editing canonical rules):")
    print("  1. Set environment variable: ALLOW_CANONICAL=1")
    print("  2. Or include 'CANONICAL-APPEND:' in commit message")
    print()
    return False


def main():
    """Main entry point."""
    print("=" * 80)
    print("CANONICAL GUARD (UPDATE18)")
    print("=" * 80)
    print()
    print(f"Protected files: {', '.join(CANONICAL_FILES)}")
    print()

    if check_canonical_guard():
        print(f"{GREEN}[PASS] No unauthorized canonical file changes{RESET}")
        return 0
    else:
        print(f"{RED}[FAIL] Canonical file changes blocked{RESET}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
