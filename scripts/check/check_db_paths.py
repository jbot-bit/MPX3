#!/usr/bin/env python3
"""
CI GUARD: Enforce Canonical Database Path Usage

This check WARNS if files hardcode GOLD_DB_PATH instead of using pipeline.paths.

Canonical path: data/db/gold.db
Import from: pipeline.paths.GOLD_DB_PATH

Run: python scripts/check/check_db_paths.py
Exit code 0 = PASS (warnings only), Exit code 1 = FAIL (if --strict)
"""

import re
import sys
from pathlib import Path

# Files allowed to have hardcoded paths (legacy, migration in progress)
ALLOWED_FILES = [
    'pipeline/paths.py',  # The SSOT itself
    'pipeline/backfill_databento_continuous.py',  # Uses env with proper default
    'pipeline/backfill_databento_continuous_mpl.py',  # Uses env with proper default
    'pipeline/backfill_range.py',  # Uses env with proper default
    'scripts/check/check_db_paths.py',  # This file
]

# Pattern for hardcoded gold.db (without data/db/ prefix or proper import)
BAD_PATTERNS = [
    # Direct GOLD_DB_PATH without data/db prefix
    (re.compile(r'["\']gold\.db["\']'), 'Hardcoded GOLD_DB_PATH - use pipeline.paths.GOLD_DB_PATH'),
    # DB_PATH = GOLD_DB_PATH or similar
    (re.compile(r'DB_PATH\s*=\s*["\']gold\.db["\']'), 'DB_PATH set to GOLD_DB_PATH - use pipeline.paths.GOLD_DB_PATH'),
]

# Pattern for GOOD usage (should be ignored)
GOOD_PATTERNS = [
    re.compile(r'data/db/gold\.db'),  # Canonical path
    re.compile(r'from pipeline\.paths import'),  # Proper import
    re.compile(r'pipeline\.paths\.GOLD_DB_PATH'),  # Using the constant
]


def is_allowed(filepath: Path) -> bool:
    """Check if file is in the allowlist."""
    rel_path = str(filepath).replace('\\', '/')
    for allowed in ALLOWED_FILES:
        if rel_path.endswith(allowed) or f'/{allowed}' in rel_path:
            return True
    return False


def has_good_pattern(line: str) -> bool:
    """Check if line uses the good pattern."""
    return any(p.search(line) for p in GOOD_PATTERNS)


def check_file(filepath: Path) -> list:
    """Check a single file for bad database path usage."""
    violations = []

    if is_allowed(filepath):
        return []

    try:
        content = filepath.read_text(encoding='utf-8')
        lines = content.split('\n')

        for i, line in enumerate(lines):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith('#'):
                continue

            # Skip if line has good pattern
            if has_good_pattern(line):
                continue

            # Check for bad patterns
            for pattern, message in BAD_PATTERNS:
                if pattern.search(line):
                    violations.append({
                        'file': str(filepath),
                        'line': i + 1,
                        'code': line.strip()[:60],
                        'message': message,
                    })
                    break  # One violation per line

    except Exception:
        pass

    return violations


def main():
    strict = '--strict' in sys.argv

    print("=" * 70)
    print("CI GUARD: Database Path Consistency Check")
    print("=" * 70)
    print(f"\nCanonical path: data/db/gold.db")
    print(f"Import from: pipeline.paths.GOLD_DB_PATH")
    print(f"Mode: {'STRICT (will fail)' if strict else 'WARNING (advisory)'}")

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
        print(f"{'FAILED' if strict else 'WARNING'}: {len(all_violations)} inconsistent DB paths!")
        print(f"{'='*70}\n")

        by_file = {}
        for v in all_violations:
            f = v['file']
            if f not in by_file:
                by_file[f] = []
            by_file[f].append(v)

        for f, violations in sorted(by_file.items())[:10]:  # Limit output
            rel_path = str(Path(f).relative_to(project_root))
            print(f"FILE: {rel_path}")
            for v in violations[:2]:
                print(f"  L{v['line']}: {v['code']}")
            if len(violations) > 2:
                print(f"  ... +{len(violations) - 2} more")
            print()

        if len(by_file) > 10:
            print(f"... +{len(by_file) - 10} more files\n")

        print(f"{'='*70}")
        print("FIX: Import and use the canonical path:")
        print("  from pipeline.paths import GOLD_DB_PATH")
        print("  con = duckdb.connect(str(GOLD_DB_PATH))")
        print(f"{'='*70}")

        if strict:
            sys.exit(1)
        else:
            print("\nRun with --strict to fail on these warnings.")
            sys.exit(0)
    else:
        print(f"\n{'='*70}")
        print("PASSED: All database paths are consistent.")
        print(f"{'='*70}")
        sys.exit(0)


if __name__ == "__main__":
    main()
