#!/usr/bin/env python3
"""
CI GUARD: Entry Logic Consistency Check

Verifies that entry detection logic is consistent across all implementation files.

CANONICAL RULE: Entry on first 1m bar that CLOSES outside ORB range
- close > orb_high = LONG
- close < orb_low = SHORT

Files checked (READ ONLY):
1. strategies/execution_engine.py
2. trading_app/entry_rules.py
3. pipeline/build_daily_features.py

Run: python scripts/check/check_entry_logic_consistency.py
Exit code 0 = PASS (consistent), Exit code 1 = FAIL (drift detected)
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent

# Files to check for entry logic consistency
ENTRY_LOGIC_FILES = [
    'strategies/execution_engine.py',
    'trading_app/entry_rules.py',
    'pipeline/build_daily_features.py',
]

# Canonical patterns that MUST exist in entry logic
REQUIRED_PATTERNS = [
    # Must use CLOSE for detection (not high/low touch)
    (r'close\s*[>]\s*orb.*high|close\s*[>]\s*orb_high', 'LONG detection: close > orb_high'),
    (r'close\s*[<]\s*orb.*low|close\s*[<]\s*orb_low', 'SHORT detection: close < orb_low'),
]

# Forbidden patterns that indicate WRONG implementation
# NOTE: limit_at_orb uses touch-based detection (correct for that rule)
# Only flag if in close-based context
FORBIDDEN_PATTERNS = [
    # Inclusive comparison (WRONG - should be strict)
    (r'close\s*[>]=\s*orb.*high', 'WRONG: Using >= instead of > for LONG'),
    (r'close\s*[<]=\s*orb.*low', 'WRONG: Using <= instead of < for SHORT'),
]


def check_file(filepath: Path) -> dict:
    """Check a single file for entry logic patterns."""
    result = {
        'file': str(filepath),
        'exists': filepath.exists(),
        'has_entry_logic': False,
        'required_found': [],
        'required_missing': [],
        'forbidden_found': [],
    }

    if not filepath.exists():
        return result

    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        result['error'] = str(e)
        return result

    # Check if file has entry logic at all
    entry_indicators = ['close.*orb', 'entry.*trigger', 'break.*dir', 'first.*close.*outside']
    for indicator in entry_indicators:
        if re.search(indicator, content, re.IGNORECASE):
            result['has_entry_logic'] = True
            break

    if not result['has_entry_logic']:
        return result

    # Check required patterns
    for pattern, description in REQUIRED_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            result['required_found'].append(description)
        else:
            result['required_missing'].append(description)

    # Check forbidden patterns
    for pattern, description in FORBIDDEN_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            result['forbidden_found'].append(description)

    return result


def main():
    print("=" * 70)
    print("CI GUARD: Entry Logic Consistency Check")
    print("=" * 70)
    print()
    print("Canonical rule: Entry on first 1m bar that CLOSES outside ORB")
    print("  - close > orb_high = LONG")
    print("  - close < orb_low = SHORT")
    print()

    all_results = []
    has_entry_logic_count = 0

    for file_path in ENTRY_LOGIC_FILES:
        full_path = REPO_ROOT / file_path
        result = check_file(full_path)
        all_results.append(result)
        if result['has_entry_logic']:
            has_entry_logic_count += 1

    # Report
    print(f"Files checked: {len(ENTRY_LOGIC_FILES)}")
    print(f"Files with entry logic: {has_entry_logic_count}")
    print()

    violations = []
    warnings = []

    for result in all_results:
        file_name = result['file'].split('/')[-1]
        print(f"--- {file_name} ---")

        if not result['exists']:
            print("  [SKIP] File not found")
            continue

        if not result['has_entry_logic']:
            print("  [SKIP] No entry logic detected")
            continue

        # Required patterns
        if result['required_found']:
            for desc in result['required_found']:
                print(f"  [OK] {desc}")

        if result['required_missing']:
            for desc in result['required_missing']:
                print(f"  [WARN] Missing: {desc}")
                warnings.append((result['file'], desc))

        # Forbidden patterns
        if result['forbidden_found']:
            for desc in result['forbidden_found']:
                print(f"  [FAIL] {desc}")
                violations.append((result['file'], desc))

        print()

    # Summary
    print("=" * 70)
    if violations:
        print(f"FAILED: {len(violations)} consistency violation(s)")
        print()
        for file, desc in violations:
            print(f"  - {file}: {desc}")
        print()
        print("Entry logic has DRIFTED. Fix the violations above.")
        print("See: docs/ENTRY_LOGIC_SSOT.md for canonical rules.")
        print("=" * 70)
        return 1

    if warnings:
        print(f"PASSED with {len(warnings)} warning(s)")
        print()
        for file, desc in warnings:
            print(f"  [WARN] {file}: {desc}")
        print()
        print("Entry logic is consistent. Warnings are informational.")
    else:
        print("PASSED: Entry logic is consistent across all files")

    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
