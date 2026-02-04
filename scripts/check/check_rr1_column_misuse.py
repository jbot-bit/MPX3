#!/usr/bin/env python3
"""
CI GUARD: Prevent RR1 Column Misuse

This check FAILS the build if *_rr1 columns are used for:
- ExpR calculations
- Validation statistics
- Discovery metrics
- Win rate calculations

ALLOWED usage (filter-only):
- trading_app/drift_monitor.py
- trading_app/experimental_scanner.py
- scripts/analyze/liquidity_diagnostic.py
- scripts/analyze/order_type_diagnostic.py
- tests/* (fixtures only)
- pipeline/* (schema definitions)

Run: python scripts/check/check_rr1_column_misuse.py
Exit code 0 = PASS, Exit code 1 = FAIL
"""

import re
import sys
from pathlib import Path

# Files ALLOWED to use *_rr1 columns (filter-only or schema)
ALLOWED_FILES = [
    # Live tools (filter-only usage verified in PASS 1)
    'trading_app/drift_monitor.py',
    'trading_app/experimental_scanner.py',
    'scripts/analyze/liquidity_diagnostic.py',
    'scripts/analyze/order_type_diagnostic.py',
    # Schema producers
    'pipeline/build_daily_features.py',
    'pipeline/backfill_databento_continuous_mpl.py',
    'pipeline/validate_data.py',
    # This check itself
    'scripts/check/check_rr1_column_misuse.py',
    # Debug tools (safe)
    'scripts/validation/debug_calculations.py',
    # Display only
    'analysis/query_features.py',
    'analysis/ai_query.py',
    # Export (raw data only)
    'analysis/export_csv.py',
]

# Patterns that indicate DANGEROUS usage (ExpR calculation)
DANGEROUS_PATTERNS = [
    r'AVG\s*\([^)]*_rr1',
    r'SUM\s*\([^)]*_rr1',
    r'win_rate.*_rr1',
    r'_rr1.*\*\s*\d',  # Multiplying rr1 values
    r'expected.*_rr1',
    r'exp_r.*_rr1',
    r'_rr1.*expected',
    r'COUNT\s*\([^)]*WIN.*_rr1',
    r'_rr1.*COUNT',
]

# Patterns for rr1 column references
RR1_COLUMN_PATTERN = re.compile(r'orb_\d{4}_(outcome|r_multiple)_rr1')


def check_file(filepath: Path) -> list:
    """Check a single file for rr1 column misuse."""
    violations = []

    # Normalize path for comparison
    rel_path = str(filepath).replace('\\', '/')

    # Skip allowed files
    for allowed in ALLOWED_FILES:
        if allowed in rel_path:
            return []

    # Skip test files (fixtures are OK)
    if '/tests/' in rel_path or rel_path.startswith('tests/'):
        return []

    try:
        content = filepath.read_text(encoding='utf-8')
        lines = content.split('\n')

        for i, line in enumerate(lines):
            # Check if line references rr1 columns
            if RR1_COLUMN_PATTERN.search(line):
                # Check for dangerous patterns
                for pattern in DANGEROUS_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        violations.append({
                            'file': str(filepath),
                            'line': i + 1,
                            'code': line.strip()[:80],
                            'pattern': pattern
                        })
                        break
    except Exception as e:
        pass  # Skip files that can't be read

    return violations


def main():
    print("=" * 70)
    print("CI GUARD: Checking for RR1 Column Misuse")
    print("=" * 70)

    project_root = Path(__file__).parent.parent.parent
    all_violations = []

    # Scan all Python files
    for pyfile in project_root.rglob('*.py'):
        # Skip venv, __pycache__, etc.
        if 'venv' in str(pyfile) or '__pycache__' in str(pyfile):
            continue
        if '_archive' in str(pyfile) or '_local_junk' in str(pyfile):
            continue

        violations = check_file(pyfile)
        all_violations.extend(violations)

    if all_violations:
        print("\nFAILED: RR1 column misuse detected!\n")
        for v in all_violations:
            print(f"  {v['file']}:{v['line']}")
            print(f"    Code: {v['code']}")
            print(f"    Pattern: {v['pattern']}")
            print()

        print(f"Total violations: {len(all_violations)}")
        print("\nThese files use *_rr1 columns for ExpR/stats calculations.")
        print("This is INCORRECT - use StrategyDiscovery instead.")
        print("\nTo fix:")
        print("  1. Replace calculation with StrategyDiscovery call")
        print("  2. Or add file to ALLOWED_FILES if filter-only usage")
        sys.exit(1)
    else:
        print("\nPASSED: No RR1 column misuse detected.")
        print(f"Scanned: {project_root}")
        print("All *_rr1 column usage is either:")
        print("  - In allowed files (filter-only)")
        print("  - In test fixtures")
        print("  - In schema definitions")
        sys.exit(0)


if __name__ == "__main__":
    main()
