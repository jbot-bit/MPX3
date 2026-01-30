#!/usr/bin/env python3
"""
SCOPE GUARD (UPDATE18)
======================

Enforces task scope to prevent "helpful refactors" that touch canonical code.

Scopes:
- UI_ONLY (default) - Only allows changes to:
  - trading_app/ui/
  - trading_app/app_*.py (UI pages)
  - trading_app/*_components.py (UI components)
  - tests/ (UI tests)
  - scripts/check/ (preflight checks)
  - docs/ (documentation)

- UNRESTRICTED - Allows all changes (use with caution)

Usage:
    SCOPE=UI_ONLY python scripts/check/app_preflight.py  (default)
    SCOPE=UNRESTRICTED python scripts/check/app_preflight.py

Exit codes:
    0 - Scope not violated (PASS)
    1 - Scope violated (FAIL)
"""

import os
import sys
import subprocess

# ANSI colors
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RESET = '\033[0m'

# UI_ONLY scope: allowed path patterns
UI_ONLY_ALLOWED = [
    'trading_app/ui/',
    'trading_app/app_',  # Matches app_canonical.py, app_trading_hub.py, etc.
    'trading_app/redesign_components.py',
    'trading_app/position_calculator.py',
    'trading_app/ui_contract.py',
    'trading_app/sync_guard.py',  # Startup sync guard (C5 fix)
    'trading_app/edge_utils.py',  # Naming/ID helpers (UPDATE21)
    'trading_app/edge_pipeline.py',  # Auto-naming integration (UPDATE21)
    'trading_app/time_spec.py',  # TSOT canonical source (parked)
    'trading_app/orb_time_logic.py',  # TSOT integration (parked)
    'tests/',
    'scripts/check/',
    'artifacts/',  # TSOT baseline and other artifacts
    'docs/',
    'WORKFLOW_GUARDRAILS.md',
    'GUARDIAN.md',
    'APP_COMPLETE_SURVEY.md',
    '.claude/',  # Claude Code IDE configuration
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


def is_allowed_in_ui_only(file: str) -> bool:
    """Check if file is allowed in UI_ONLY scope."""
    for pattern in UI_ONLY_ALLOWED:
        if file.startswith(pattern):
            return True
    return False


def check_scope_guard(scope: str) -> tuple[bool, list[str]]:
    """Check if scope is respected."""
    if scope == 'UNRESTRICTED':
        return True, []  # No restrictions

    # UI_ONLY scope
    modified_files = get_modified_files()
    violations = []

    for file in modified_files:
        if not is_allowed_in_ui_only(file):
            violations.append(file)

    return len(violations) == 0, violations


def main():
    """Main entry point."""
    # Get scope from environment variable (default: UI_ONLY)
    scope = os.environ.get('SCOPE', 'UI_ONLY').strip().upper()

    print("=" * 80)
    print("SCOPE GUARD (UPDATE18)")
    print("=" * 80)
    print()
    print(f"Current scope: {scope}")
    print()

    if scope == 'UNRESTRICTED':
        print(f"{YELLOW}[WARN] UNRESTRICTED scope - all changes allowed{RESET}")
        print()
        print("Use with caution. UNRESTRICTED scope bypasses scope protections.")
        print()
        return 0

    # UI_ONLY scope
    print("UI_ONLY scope allows changes to:")
    for pattern in UI_ONLY_ALLOWED:
        print(f"  - {pattern}*")
    print()

    passed, violations = check_scope_guard(scope)

    if passed:
        print(f"{GREEN}[PASS] Scope respected (UI_ONLY){RESET}")
        return 0
    else:
        print(f"{RED}[FAIL] Scope violated (UI_ONLY):{RESET}")
        print()
        for file in violations:
            print(f"  {RED}[X]{RESET} {file}")
        print()
        print("=" * 80)
        print("SCOPE VIOLATION")
        print("=" * 80)
        print()
        print("UI_ONLY scope limits changes to UI code only.")
        print("These files are outside the allowed scope.")
        print()
        print("If you need to modify these files:")
        print("1. Set SCOPE=UNRESTRICTED (if you have explicit permission)")
        print("2. Or move the changes to a separate task/branch")
        print()
        return 1


if __name__ == '__main__':
    sys.exit(main())
