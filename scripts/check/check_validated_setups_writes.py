#!/usr/bin/env python3
"""
CI GUARD: Enforce validated_setups Write Allowlist (DENY-BY-DEFAULT)

This check FAILS if any file writes to validated_setups that is NOT in the allowlist.

SSOT RULE: validated_setups is the ONLY production strategy source.
All writes MUST go through approved scripts only.

ALLOWLIST (authorized writers):
1. scripts/audit/autonomous_strategy_validator.py - 6-phase validation (CANONICAL)
2. strategies/archive_strategy.py - Archive to validated_setups_archive
3. tests/conftest.py - Test fixtures only
4. scripts/sync_validated_setups.py - Cloud sync (MotherDuck)

ALL OTHER WRITES ARE FORBIDDEN.

Run: python scripts/check/check_validated_setups_writes.py
Exit code 0 = PASS, Exit code 1 = FAIL
"""

import re
import sys
from pathlib import Path

# STRICT ALLOWLIST: Only these files may write to validated_setups
ALLOWED_WRITERS = [
    # Canonical validator (6-phase, HONESTY rule)
    'scripts/audit/autonomous_strategy_validator.py',
    # Archive operations (move to archive table)
    'strategies/archive_strategy.py',
    # Test fixtures (test DB only)
    'tests/conftest.py',
    # Cloud sync (MotherDuck)
    'scripts/sync_validated_setups.py',
]

# Patterns that indicate writes to validated_setups
WRITE_PATTERNS = [
    re.compile(r'INSERT\s+INTO\s+validated_setups', re.IGNORECASE),
    re.compile(r'UPDATE\s+validated_setups', re.IGNORECASE),
    re.compile(r'DELETE\s+FROM\s+validated_setups', re.IGNORECASE),
    re.compile(r"\.execute\s*\([^)]*['\"].*(?:INSERT|UPDATE|DELETE).*validated_setups", re.IGNORECASE),
]

# Exclude patterns (archive table is OK, comments are OK)
EXCLUDE_PATTERNS = [
    re.compile(r'validated_setups_archive'),  # Archive table is different
    re.compile(r'^\s*#'),  # Comments
    re.compile(r'^\s*["\'].*#'),  # Inline comments in strings
]


def is_allowed(filepath: Path) -> bool:
    """Check if file is in the strict allowlist."""
    rel_path = str(filepath).replace('\\', '/')
    for allowed in ALLOWED_WRITERS:
        if rel_path.endswith(allowed) or f'/{allowed}' in rel_path:
            return True
    return False


def should_exclude(line: str) -> bool:
    """Check if line should be excluded from violation detection."""
    for pattern in EXCLUDE_PATTERNS:
        if pattern.search(line):
            return True
    return False


def check_file(filepath: Path) -> list:
    """Check a single file for unauthorized validated_setups writes."""
    violations = []

    if is_allowed(filepath):
        return []

    try:
        content = filepath.read_text(encoding='utf-8')
        lines = content.split('\n')

        for i, line in enumerate(lines):
            # Skip if line should be excluded
            if should_exclude(line):
                continue

            # Check for write patterns
            for pattern in WRITE_PATTERNS:
                if pattern.search(line):
                    violations.append({
                        'file': str(filepath),
                        'line': i + 1,
                        'code': line.strip()[:70],
                        'pattern': pattern.pattern[:40],
                    })
                    break  # One violation per line

    except Exception:
        pass

    return violations


def main():
    print("=" * 70)
    print("CI GUARD: validated_setups Write Allowlist (DENY-BY-DEFAULT)")
    print("=" * 70)
    print(f"\nAllowlist ({len(ALLOWED_WRITERS)} authorized writers):")
    for f in ALLOWED_WRITERS:
        print(f"  - {f}")

    project_root = Path(__file__).parent.parent.parent
    all_violations = []

    py_count = 0
    for pyfile in project_root.rglob('*.py'):
        path_str = str(pyfile)
        if 'venv' in path_str or '__pycache__' in path_str:
            continue
        if '_archive' in path_str or '_local_junk' in path_str:
            continue

        py_count += 1
        violations = check_file(pyfile)
        all_violations.extend(violations)

    print(f"\nScanned: {py_count} Python files")

    if all_violations:
        print(f"\n{'='*70}")
        print(f"FAILED: {len(all_violations)} unauthorized validated_setups writes!")
        print(f"{'='*70}\n")

        by_file = {}
        for v in all_violations:
            f = v['file']
            if f not in by_file:
                by_file[f] = []
            by_file[f].append(v)

        for f, violations in sorted(by_file.items()):
            rel_path = str(Path(f).relative_to(project_root))
            print(f"FILE: {rel_path}")
            for v in violations[:3]:
                print(f"  L{v['line']}: {v['code'][:60]}")
            if len(violations) > 3:
                print(f"  ... +{len(violations) - 3} more")
            print()

        print(f"{'='*70}")
        print("SSOT VIOLATION: Only allowlisted scripts may write to validated_setups")
        print("")
        print("Authorized writers:")
        for f in ALLOWED_WRITERS:
            print(f"  - {f}")
        print("")
        print("To fix: Route all strategy writes through autonomous_strategy_validator.py")
        print(f"{'='*70}")
        sys.exit(1)
    else:
        print(f"\n{'='*70}")
        print("PASSED: All validated_setups writes are from authorized sources.")
        print(f"{'='*70}")
        sys.exit(0)


if __name__ == "__main__":
    main()
