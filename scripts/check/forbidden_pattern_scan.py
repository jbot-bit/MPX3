"""
FORBIDDEN PATTERN SCANNER (UPDATE16)
=====================================

Truth enforcement - blocks fake logic, stubs, and drift.

This script would have prevented:
- Mock ExpR values
- Fake PASS states
- TODO validation stubs
- Half-wired approve buttons

Usage:
    python scripts/check/forbidden_pattern_scan.py

Exit codes:
    0 - CLEAN (no forbidden patterns)
    1 - FAIL (forbidden patterns detected)
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

# ANSI colors (ASCII-safe for Windows)
RED = '\033[91m'
GREEN = '\033[92m'
RESET = '\033[0m'


# Forbidden patterns (case-insensitive)
# These catch FAKE LOGIC (pretend-to-work code) that was actually shipped
#
# Focus on EXACT PHRASES from real bugs:
# 1. Comments indicating fake data: "# example baseline", "# mock", "# simulated"
# 2. Hardcoded test values with suspicious comments
# 3. Very specific dangerous patterns that are NEVER legitimate
#
# Philosophy: Better to miss some edge cases than block legitimate code
FORBIDDEN_PATTERNS = [
    # Comments that indicate fake/mock/example data (HIGH CONFIDENCE)
    "# example baseline",
    "# mock data",
    "# simulated pass",
    "# fake pass",
    "# TODO: use real data",
    "# TODO: wire to database",

    # Hardcoded values with suspicious comments (HIGH CONFIDENCE)
    "= 0.25  # example",
    "= 0.250  # example",
    "= 0.15  # baseline",
    "= 0.15  # mock",

    # Specific dangerous variable assignments (HIGH CONFIDENCE)
    "baseline_exp_r = 0.25",
    "mock_exp_r = 0.25",
    "fake_exp_r = 0.25",

    # Hardcoded pass states with literal "True" in stub context (HIGH CONFIDENCE)
    "return True  # pass",
    "return True # stub",
    "return True # fake",
    "return True # TODO",

    # Obvious fake data structures (HIGH CONFIDENCE)
    "mock_data = {",
    "fake_data = {",
]


def scan_file(file_path: Path, patterns: List[str]) -> List[Tuple[str, int, str]]:
    """
    Scan a file for forbidden patterns.

    Returns:
        List of (pattern, line_number, line_content) tuples
    """
    violations = []

    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        for line_num, line in enumerate(lines, start=1):
            line_lower = line.lower()

            for pattern in patterns:
                if pattern.lower() in line_lower:
                    violations.append((pattern, line_num, line.strip()))

    except Exception:
        # Skip files we can't read
        pass

    return violations


def scan_repository(repo_root: Path, patterns: List[str]) -> List[Tuple[Path, str, int, str]]:
    """
    Scan repository for forbidden patterns.

    Focus on:
    - trading_app/
    - scripts/
    - tests/

    File types: .py, .sql, .md

    Returns:
        List of (file_path, pattern, line_number, line_content) tuples
    """
    violations = []

    # Directories to scan
    scan_dirs = [
        repo_root / 'trading_app',
        repo_root / 'scripts',
        repo_root / 'tests',
    ]

    # Directories to exclude
    exclude_dirs = {'.git', '__pycache__', 'venv', '.venv', 'node_modules', 'build', 'dist'}

    # File patterns to scan
    file_patterns = ['**/*.py', '**/*.sql', '**/*.md']

    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue

        for file_pattern in file_patterns:
            for file_path in scan_dir.glob(file_pattern):
                # Skip if in excluded directory
                if any(excluded in file_path.parts for excluded in exclude_dirs):
                    continue

                # Skip scanner itself (contains patterns in comments)
                if file_path.name == 'forbidden_pattern_scan.py':
                    continue

                # Scan file
                file_violations = scan_file(file_path, patterns)
                for pattern, line_num, line_content in file_violations:
                    violations.append((file_path, pattern, line_num, line_content))

    return violations


def main():
    """Main entry point for forbidden pattern scanner."""

    print("=" * 80)
    print("FORBIDDEN PATTERN SCANNER (UPDATE16)")
    print("=" * 80)
    print()

    # Get repo root
    repo_root = Path(__file__).parent.parent.parent
    print(f"Repo root: {repo_root}")
    print(f"Patterns: {len(FORBIDDEN_PATTERNS)}")
    print()

    # Scan repository
    print("Scanning for forbidden patterns...")
    violations = scan_repository(repo_root, FORBIDDEN_PATTERNS)
    print()

    # Report results
    if violations:
        print(f"{RED}[FAIL] FORBIDDEN PATTERN DETECTED{RESET}")
        print()

        # Print first violation (fail fast)
        file_path, pattern, line_num, line_content = violations[0]
        relative_path = file_path.relative_to(repo_root)

        print(f"Pattern: \"{pattern}\"")
        print(f"File: {relative_path}")
        print(f"Line: {line_num}")
        # ASCII-safe encoding for Windows console
        try:
            print(f"Code: {line_content}")
        except UnicodeEncodeError:
            print(f"Code: {line_content.encode('ascii', errors='replace').decode('ascii')}")
        print()

        if len(violations) > 1:
            print(f"(+{len(violations) - 1} more violation(s) found)")
            print()

        print(f"{RED}Build FAILED.{RESET}")
        print()
        print("Remove forbidden patterns to proceed.")
        return 1

    else:
        print(f"{GREEN}[PASS] No forbidden patterns detected{RESET}")
        print()
        print("Repository is clean!")
        return 0


if __name__ == '__main__':
    sys.exit(main())
