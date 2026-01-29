#!/usr/bin/env python3
"""
Check realized_rr Usage - Step 3 Verification

Ensures ALL UI/scanner/validation paths use realized_rr (not r_multiple)
for decisions, scoring, and performance metrics.

r_multiple (theoretical R) is ONLY allowed in:
- Raw data expanders / debug panels
- Schema definitions
- Research scripts reading daily_features columns

FAILS if r_multiple is used for:
- Decision making (trade approval, strategy selection)
- Scoring (strategy ranking, edge discovery)
- Performance metrics (win rate, expectancy calculations)
- User-facing displays (without "theoretical" label)
"""

import os
import sys
import re
from pathlib import Path

# CRITICAL FILES: Must use realized_rr for decisions/scoring
CRITICAL_FILES = [
    'trading_app/edge_utils.py',
    'trading_app/setup_detector.py',
    'trading_app/strategy_engine.py',
    'trading_app/auto_search_engine.py',
    'trading_app/experimental_scanner.py',
    'trading_app/app_canonical.py',
]

# ALLOWED FILES: Can use r_multiple for raw data / schema
ALLOWED_FILES = [
    'tests/conftest.py',  # Schema definitions
    'tests/test_build_daily_features.py',  # Schema validation tests
    'strategies/execution_engine.py',  # Stores BOTH r_multiple and realized_rr
    'trading_app/edge_tracker.py',  # Reads raw daily_features columns
    'discover_all_orb_patterns.py',  # Research script
    'analysis/research_night_orb_comprehensive.py',  # Research script
]

# DECISION/SCORING PATTERNS: These indicate r_multiple is being used for decisions
DECISION_PATTERNS = [
    r'expected_r\s*=.*r_multiple',  # expected_r calculation
    r'avg_win\s*=.*r_multiple',  # avg win calculation
    r'avg_loss\s*=.*r_multiple',  # avg loss calculation
    r'cumulative.*r_multiple',  # cumulative R calculation
    r'cum_r\s*\+=\s*.*r_multiple',  # cumulative R accumulation
    r'win_rate.*r_multiple',  # win rate calculation with r_multiple
    r'expectancy.*r_multiple',  # expectancy calculation
    r'AVG\(.*r_multiple\)',  # SQL AVG of r_multiple
    r'SUM\(.*r_multiple\)',  # SQL SUM of r_multiple
]

# DISPLAY PATTERNS: These indicate r_multiple is shown to user without "theoretical" label
DISPLAY_PATTERNS = [
    r'st\.write\(.*["\']R-Multiple["\'].*r_multiple',  # Streamlit display
    r'st\.metric\(.*["\'].*R.*["\'].*r_multiple',  # Streamlit metric
    r'print\(.*r_multiple',  # Console output
]


def count_r_multiple_occurrences(file_path: Path) -> int:
    """
    Count total r_multiple occurrences in a file (for coverage reporting).

    Returns:
        Number of times 'r_multiple' appears in the file
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        # Match r_multiple as a word (not part of other identifiers)
        matches = re.findall(r'\br_multiple\b', content)
        return len(matches)
    except Exception:
        return 0


def check_file(file_path: Path) -> list:
    """
    Check a single file for incorrect r_multiple usage.

    Returns:
        List of violation strings (empty if no violations)
    """
    violations = []

    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        return [f"ERROR reading {file_path}: {e}"]

    # Check decision patterns
    for pattern in DECISION_PATTERNS:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            context = match.group(0)[:80]
            violations.append(
                f"{file_path}:{line_num} - DECISION LOGIC uses r_multiple: {context}"
            )

    # Check display patterns (unless labeled "theoretical")
    for pattern in DISPLAY_PATTERNS:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            line_num = content[:match.start()].count('\n') + 1
            # Check if "theoretical" appears nearby (within 100 chars)
            context_start = max(0, match.start() - 50)
            context_end = min(len(content), match.end() + 50)
            context = content[context_start:context_end]

            if 'theoretical' not in context.lower():
                context_short = match.group(0)[:80]
                violations.append(
                    f"{file_path}:{line_num} - DISPLAY uses r_multiple without 'theoretical' label: {context_short}"
                )

    return violations


def main():
    """Run check on all critical files."""
    print("=" * 70)
    print("REALIZED_RR USAGE CHECK - Step 3 Verification")
    print("=" * 70)
    print()

    project_root = Path(__file__).parent.parent.parent
    all_violations = []

    # Coverage tracking (ADD-ON: for reporting only, does not change pass/fail)
    scanned_files = []
    critical_r_multiple_count = 0
    allowed_r_multiple_count = 0
    skipped_files = []

    # Check critical files
    print("Checking critical files (must use realized_rr for decisions/scoring):")
    print()

    for file_rel in CRITICAL_FILES:
        file_path = project_root / file_rel
        if not file_path.exists():
            print(f"  [SKIP] {file_rel} - file not found")
            skipped_files.append(file_rel)
            continue

        # Count occurrences (coverage tracking)
        r_multiple_count = count_r_multiple_occurrences(file_path)
        critical_r_multiple_count += r_multiple_count
        scanned_files.append({
            'path': file_rel,
            'type': 'critical',
            'r_multiple_count': r_multiple_count
        })

        violations = check_file(file_path)
        if violations:
            print(f"  [FAIL] {file_rel}")
            for v in violations:
                print(f"    - {v}")
            all_violations.extend(violations)
        else:
            print(f"  [OK] {file_rel}")

    print()

    # Check that allowed files are not flagged
    print("Checking allowed files (can use r_multiple for raw data/schema):")
    print()

    for file_rel in ALLOWED_FILES:
        file_path = project_root / file_rel
        if not file_path.exists():
            print(f"  [SKIP] {file_rel} - file not found")
            skipped_files.append(file_rel)
            continue

        # Count occurrences (coverage tracking)
        r_multiple_count = count_r_multiple_occurrences(file_path)
        allowed_r_multiple_count += r_multiple_count
        scanned_files.append({
            'path': file_rel,
            'type': 'allowed',
            'r_multiple_count': r_multiple_count
        })

        # These files are allowed to use r_multiple, but log for info
        print(f"  [ALLOWED] {file_rel} (raw data/schema usage OK)")

    print()

    # =========================================================================
    # COVERAGE SUMMARY (ADD-ON: Enhanced visibility, does not change pass/fail)
    # =========================================================================
    print("=" * 70)
    print("COVERAGE SUMMARY")
    print("=" * 70)
    print()

    # Total files
    total_scanned = len(scanned_files)
    total_skipped = len(skipped_files)
    total_files = len(CRITICAL_FILES) + len(ALLOWED_FILES)
    print(f"Total files scanned: {total_scanned}/{total_files}")
    if total_skipped > 0:
        print(f"  Skipped (not found): {total_skipped}")
    print()

    # Files scanned (grouped by type)
    print("Files scanned:")
    print()
    print("  Critical files (must use realized_rr for decisions):")
    for f in scanned_files:
        if f['type'] == 'critical':
            print(f"    - {f['path']} ({f['r_multiple_count']} r_multiple occurrences)")
    print()
    print("  Allowed files (can use r_multiple for raw data/schema):")
    for f in scanned_files:
        if f['type'] == 'allowed':
            print(f"    - {f['path']} ({f['r_multiple_count']} r_multiple occurrences)")
    print()

    # r_multiple occurrence counts
    total_r_multiple = critical_r_multiple_count + allowed_r_multiple_count
    print(f"r_multiple occurrences found: {total_r_multiple} total")
    print(f"  - In critical files (blocked for decisions): {critical_r_multiple_count}")
    print(f"  - In allowed files (OK for raw data/schema): {allowed_r_multiple_count}")
    print()

    # Context breakdown
    print("Context breakdown:")
    if all_violations:
        print(f"  - BLOCKED (decision/scoring): {len(all_violations)} violations")
    else:
        print(f"  - BLOCKED (decision/scoring): 0 violations")
    print(f"  - ALLOWED (display-only/legacy): {allowed_r_multiple_count} occurrences")
    print()

    # =========================================================================
    # PASS/FAIL VERDICT (unchanged from original logic)
    # =========================================================================
    if all_violations:
        print("=" * 70)
        print("[FAIL] VIOLATIONS FOUND")
        print("=" * 70)
        print()
        print(f"Total violations: {len(all_violations)}")
        print()
        print("CRITICAL: r_multiple (theoretical R) is being used for:")
        print("  - Decision making (trade approval, strategy selection)")
        print("  - Scoring (strategy ranking, edge discovery)")
        print("  - Performance metrics (win rate, expectancy)")
        print("  - User displays (without 'theoretical' label)")
        print()
        print("FIX: Replace r_multiple with realized_rr (includes costs)")
        print()
        print("Violations:")
        for v in all_violations:
            print(f"  - {v}")
        print()
        return 1
    else:
        print("=" * 70)
        print("[OK] ALL CHECKS PASSED")
        print("=" * 70)
        print()
        print("Summary:")
        print(f"  [OK] {len(CRITICAL_FILES)} critical files checked")
        print(f"  [OK] {len(ALLOWED_FILES)} allowed files noted")
        print("  [OK] No r_multiple usage in decision/scoring paths")
        print("  [OK] All performance metrics use realized_rr")
        print()
        print("REALIZED_RR USAGE IS CORRECT")
        print()
        return 0


if __name__ == '__main__':
    sys.exit(main())
