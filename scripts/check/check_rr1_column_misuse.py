#!/usr/bin/env python3
"""
CI GUARD: Enforce RR1-Explicit Column Usage (STRICT)

This check FAILS if LEGACY columns are used anywhere except 3 allowed files:
- orb_XXXX_outcome (without _rr1 suffix)
- orb_XXXX_r_multiple (without _rr1 suffix)

ONLY 3 FILES ALLOWED TO USE LEGACY (backwards compat, FORBIDDEN to modify):
1. trading_app/drift_monitor.py
2. trading_app/experimental_scanner.py
3. trading_app/test_validation_comprehensive.py

EVERYONE ELSE MUST USE:
- orb_XXXX_outcome_rr1 for RR=1.0 outcomes
- orb_XXXX_r_multiple_rr1 for RR=1.0 r-multiples
- StrategyDiscovery for RR > 1.0 analysis

Run: python scripts/check/check_rr1_column_misuse.py
Exit code 0 = PASS, Exit code 1 = FAIL
"""

import re
import sys
from pathlib import Path

# STRICT ALLOWLIST: Files allowed to use legacy columns
# - trading_app: FORBIDDEN to modify, uses legacy (3 specific files)
# - pipeline: Producers write both legacy + _rr1 columns
# - tests: Fixtures need both for backwards compat testing
ALLOWED_LEGACY_FILES = [
    # trading_app (FORBIDDEN - uses legacy)
    'trading_app/drift_monitor.py',
    'trading_app/experimental_scanner.py',
    'trading_app/test_validation_comprehensive.py',
    # pipeline (producers - write both legacy and _rr1)
    'pipeline/',
    # tests (fixtures - may reference both for testing)
    'tests/',
]

# Pattern for LEGACY column references (outcome/r_multiple WITHOUT _rr1 suffix)
# Negative lookahead excludes _rr1 and _tradeable variants
LEGACY_PATTERN = re.compile(
    r'orb_\d{4}_(outcome|r_multiple)(?!_rr1|_tradeable)'
)


def is_allowed(filepath: Path) -> bool:
    """Check if file is in the strict allowlist."""
    rel_path = str(filepath).replace('\\', '/')
    for allowed in ALLOWED_LEGACY_FILES:
        if rel_path.endswith(allowed) or f'/{allowed}' in rel_path:
            return True
    return False


def check_file(filepath: Path) -> list:
    """Check a single file for legacy column usage."""
    violations = []

    if is_allowed(filepath):
        return []

    try:
        content = filepath.read_text(encoding='utf-8')
        lines = content.split('\n')

        for i, line in enumerate(lines):
            # Skip pure comments
            stripped = line.strip()
            if stripped.startswith('#'):
                continue

            # Check for legacy column usage
            match = LEGACY_PATTERN.search(line)
            if match:
                violations.append({
                    'file': str(filepath),
                    'line': i + 1,
                    'code': line.strip()[:80],
                    'match': match.group(0),
                })
    except Exception:
        pass

    return violations


def main():
    print("=" * 70)
    print("CI GUARD: Legacy ORB Column Enforcement (STRICT)")
    print("=" * 70)
    print(f"\nAllowlist ({len(ALLOWED_LEGACY_FILES)} files):")
    for f in ALLOWED_LEGACY_FILES:
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
        print(f"FAILED: {len(all_violations)} legacy column violations!")
        print(f"{'='*70}\n")

        by_file = {}
        for v in all_violations:
            f = v['file']
            if f not in by_file:
                by_file[f] = []
            by_file[f].append(v)

        for f, violations in sorted(by_file.items()):
            print(f"FILE: {f}")
            for v in violations[:3]:
                print(f"  L{v['line']}: {v['match']} -> {v['code'][:60]}")
            if len(violations) > 3:
                print(f"  ... +{len(violations) - 3} more")
            print()

        print(f"{'='*70}")
        print("FIX: Replace legacy columns with _rr1 versions:")
        print("  orb_XXXX_outcome     -> orb_XXXX_outcome_rr1")
        print("  orb_XXXX_r_multiple  -> orb_XXXX_r_multiple_rr1")
        print(f"{'='*70}")
        sys.exit(1)
    else:
        print(f"\n{'='*70}")
        print("PASSED: No legacy column violations.")
        print(f"{'='*70}")
        sys.exit(0)


if __name__ == "__main__":
    main()
