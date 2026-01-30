"""
TIME LITERALS CHECKER (H1 Enforcement)
======================================

Prevents hardcoded session times, ORB times, and trading windows outside time_spec.py

Rules:
- All time constants MUST be in trading_app/time_spec.py
- Other files MUST import from time_spec.py
- No hardcoded "09:00", "0900", etc. in Python files (except time_spec.py)

Exceptions:
- Comments and docstrings (allowed for documentation)
- Test files (allowed for fixtures and test data)
- time_spec.py itself (the canonical source)
"""

import re
import sys
import json
from pathlib import Path
from typing import List, Tuple

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

# Forbidden time literals (ORB times and session times)
FORBIDDEN_PATTERNS = [
    r'\b0900\b',  # ORB times
    r'\b1000\b',
    r'\b1100\b',
    r'\b1800\b',
    r'\b2300\b',
    r'\b0030\b',
    r'time\(\s*9\s*,\s*0\s*\)',  # time(9, 0)
    r'time\(\s*10\s*,\s*0\s*\)',  # time(10, 0)
    r'time\(\s*11\s*,\s*0\s*\)',  # time(11, 0)
    r'time\(\s*18\s*,\s*0\s*\)',  # time(18, 0)
    r'time\(\s*23\s*,\s*0\s*\)',  # time(23, 0)
    r'time\(\s*0\s*,\s*30\s*\)',  # time(0, 30)
]

# Compiled patterns
PATTERN_REGEX = [re.compile(p) for p in FORBIDDEN_PATTERNS]

# Exception files (allowed to have time literals)
EXCEPTION_FILES = [
    'trading_app/time_spec.py',  # Canonical source
    'tests/',                     # Test files
    'scripts/check/check_time_literals.py',  # This file
]


def is_exception_file(file_path: Path, repo_root: Path) -> bool:
    """Check if file is allowed to have time literals"""
    rel_path = str(file_path.relative_to(repo_root)).replace('\\', '/')

    for exception in EXCEPTION_FILES:
        if rel_path == exception or rel_path.startswith(exception):
            return True

    return False


def is_code_line(line: str) -> bool:
    """
    Check if line is actual code (not comment or docstring marker)

    Returns:
        True if line is code, False if comment/docstring
    """
    stripped = line.strip()

    # Empty line
    if not stripped:
        return False

    # Comment line
    if stripped.startswith('#'):
        return False

    # Docstring markers (allow time examples in docs)
    if stripped.startswith('"""') or stripped.startswith("'''"):
        return False

    return True


def check_file(file_path: Path, repo_root: Path) -> List[Tuple[int, str, str]]:
    """
    Check a file for forbidden time literals

    Returns:
        List of (line_number, line_content, pattern) violations
    """
    violations = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                # Skip comments and docstrings
                if not is_code_line(line):
                    continue

                # Check all patterns
                for pattern_str, pattern in zip(FORBIDDEN_PATTERNS, PATTERN_REGEX):
                    if pattern.search(line):
                        violations.append((line_num, line.strip(), pattern_str))

    except Exception as e:
        print(f"{YELLOW}[WARN]{RESET} Could not read {file_path}: {e}")

    return violations


def safe_print(text):
    """Print text safely on Windows (prevent UnicodeEncodeError)"""
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback to ASCII with replacement
        print(text.encode('ascii', errors='replace').decode('ascii'))


def load_baseline(baseline_path="artifacts/tsot_baseline.json"):
    """Load baseline violations from JSON file"""
    baseline_file = Path(baseline_path)
    if not baseline_file.exists():
        return None

    try:
        with open(baseline_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        safe_print(f"{YELLOW}[WARN]{RESET} Could not load baseline: {e}")
        return None


def compute_new_violations(current_violations, baseline, repo_root):
    """
    Compute NEW violations (current - baseline)

    Returns:
        list of (file_path, line_num, line_content, pattern, category)
    """
    if baseline is None:
        # No baseline = treat all as existing (WARN only)
        return []

    new_violations = []

    for file_path, violations in current_violations:
        # Get relative path (same format as baseline)
        rel_path = file_path.relative_to(repo_root)
        file_key = str(rel_path).replace('/', '\\')  # Normalize to backslash (Windows)

        # Get baseline data for this file
        baseline_file = baseline.get('by_file', {}).get(file_key, {})

        # Build set of (line, pattern) pairs from baseline
        baseline_violations = set()
        for v in baseline_file.get('violations', []):
            baseline_violations.add((v['line'], v['pattern']))

        for line_num, line_content, pattern in violations:
            # Check if this (line, pattern) pair is in baseline
            if (line_num, pattern) not in baseline_violations:
                # NEW violation detected
                # Determine category (STRUCTURAL vs UI)
                is_ui = False

                # Simple heuristic: if line contains UI keywords, treat as UI
                ui_keywords = ['placeholder', 'help_text', 'st.', 'label=', 'z-index', 'css',
                               'markdown', 'docstring', '"""', "'''", 'example']
                if any(kw in line_content.lower() for kw in ui_keywords):
                    is_ui = True

                category = 'UI_OPERATIONAL' if is_ui else 'STRUCTURAL'
                new_violations.append((file_path, line_num, line_content, pattern, category))

    return new_violations


def main():
    """Run time literals checker with NEW-only enforcement"""
    import argparse

    parser = argparse.ArgumentParser(description='Check for hardcoded time literals (TSOT enforcement)')
    parser.add_argument('--update-baseline', action='store_true',
                        help='Update baseline with current violations')
    args = parser.parse_args()

    safe_print("=" * 80)
    safe_print("TIME LITERALS CHECKER (H1 Enforcement + NEW-only)")
    safe_print("=" * 80)
    safe_print("")

    # Find repo root
    repo_root = Path(__file__).resolve().parents[2]
    safe_print(f"Repo root: {repo_root}")
    safe_print("")

    # Find all Python files in trading_app/ and pipeline/
    python_files = []
    for directory in ['trading_app', 'pipeline', 'strategies', 'analysis']:
        dir_path = repo_root / directory
        if dir_path.exists():
            python_files.extend(dir_path.rglob('*.py'))

    safe_print(f"Scanning {len(python_files)} Python files...")
    safe_print("")

    # Check each file
    all_violations = []
    for file_path in python_files:
        # Skip exception files
        if is_exception_file(file_path, repo_root):
            continue

        violations = check_file(file_path, repo_root)
        if violations:
            all_violations.append((file_path, violations))

    # Load baseline
    baseline = load_baseline()

    if baseline:
        safe_print(f"{GREEN}[INFO]{RESET} Loaded baseline: {baseline['total_violations']} known violations")
        safe_print(f"  Files: {baseline['total_files']}")
        safe_print("")
    else:
        safe_print(f"{YELLOW}[WARN]{RESET} No baseline found (all violations will be treated as existing)")
        safe_print("")

    # Update baseline mode
    if args.update_baseline:
        safe_print(f"{YELLOW}[UPDATE]{RESET} Updating baseline...")
        # Re-run generate_tsot_baseline_v2.py
        import subprocess
        result = subprocess.run([sys.executable, 'scripts/check/generate_tsot_baseline_v2.py'],
                              capture_output=True, text=True)
        safe_print(result.stdout)
        if result.returncode == 0:
            safe_print(f"{GREEN}[SUCCESS]{RESET} Baseline updated")
            return 0
        else:
            safe_print(f"{RED}[ERROR]{RESET} Baseline update failed")
            safe_print(result.stderr)
            return 1

    # Report all violations (for reference)
    total_violations = sum(len(v) for _, v in all_violations)
    safe_print(f"Current violations: {total_violations} in {len(all_violations)} files")
    safe_print("")

    # Compute NEW violations
    new_violations = compute_new_violations(all_violations, baseline, repo_root)

    if not new_violations:
        safe_print(f"{GREEN}[PASS]{RESET} No NEW violations detected")
        safe_print("")
        if all_violations:
            safe_print(f"{YELLOW}[INFO]{RESET} {total_violations} existing violations are grandfathered (baseline)")
        else:
            safe_print("All time definitions are in time_spec.py")
        return 0

    # Report NEW violations
    new_structural = [v for v in new_violations if v[4] == 'STRUCTURAL']
    new_ui = [v for v in new_violations if v[4] == 'UI_OPERATIONAL']

    if new_structural:
        safe_print(f"{RED}[FAIL]{RESET} Found {len(new_structural)} NEW STRUCTURAL violations")
        safe_print("")

        for file_path, line_num, line_content, pattern, category in new_structural:
            rel_path = file_path.relative_to(repo_root)
            safe_print(f"{RED}[X]{RESET} {rel_path}:{line_num}")
            safe_print(f"  {line_content[:80]}")
            safe_print(f"  Pattern: {pattern}")
            safe_print("")

        safe_print("=" * 80)
        safe_print("FIX REQUIRED - NEW STRUCTURAL VIOLATIONS")
        safe_print("=" * 80)
        safe_print("")
        safe_print("All time constants must be in trading_app/time_spec.py")
        safe_print("Import from time_spec instead of hardcoding:")
        safe_print("")
        safe_print("  # WRONG:")
        safe_print("  ORB_TIMES = ['0900', '1000', '1100']")
        safe_print("")
        safe_print("  # CORRECT:")
        safe_print("  from trading_app.time_spec import ORBS")
        safe_print("")
        return 1

    if new_ui:
        safe_print(f"{YELLOW}[WARN]{RESET} Found {len(new_ui)} NEW UI/OPERATIONAL violations (allowed)")
        safe_print("")
        safe_print(f"{GREEN}[PASS]{RESET} No new structural violations")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
