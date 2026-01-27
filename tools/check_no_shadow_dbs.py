#!/usr/bin/env python3
"""
SHADOW DATABASE GUARD

Fails if duplicate/shadow database files are found outside canonical locations.
This enforces police.txt "NO OLD DB" rule.

Usage:
    python tools/check_no_shadow_dbs.py

Returns:
    Exit code 0: No shadow DBs found (PASS)
    Exit code 1: Shadow DBs found (FAIL)

Run this in CI/CD or as pre-commit hook to prevent shadow DBs from being committed.
"""

import sys
from pathlib import Path
import json

# Colors for terminal output (disabled on Windows to avoid Unicode issues)
RED = ""
GREEN = ""
YELLOW = ""
RESET = ""
BOLD = ""


def load_canonical_config():
    """Load CANONICAL.json from repo root."""
    repo_root = Path(__file__).parent.parent
    canonical_file = repo_root / "CANONICAL.json"

    if not canonical_file.exists():
        print(f"{RED}✗ CANONICAL.json not found{RESET}")
        sys.exit(1)

    with open(canonical_file, 'r') as f:
        return json.load(f)


def check_shadow_databases():
    """
    Check for shadow database files outside canonical locations.

    Returns:
        tuple: (has_violations: bool, violations: list)
    """
    config = load_canonical_config()
    repo_root = Path(__file__).parent.parent

    violations = []

    # Get allowed and forbidden locations
    allowed = config["databases"]["allowed_locations"]
    forbidden = config["databases"]["forbidden_locations"]

    print(f"\n{BOLD}SHADOW DATABASE GUARD{RESET}")
    print("=" * 70)

    # Check 1: Forbidden patterns
    print(f"\n1. Checking forbidden locations...")
    for pattern in forbidden:
        matches = list(repo_root.glob(pattern))
        for match in matches:
            if match.suffix in [".db", ".duckdb", ".sqlite"]:
                rel_path = match.relative_to(repo_root)
                violations.append({
                    "path": str(rel_path),
                    "reason": f"Matches forbidden pattern: {pattern}",
                    "size": match.stat().st_size if match.exists() else 0
                })
                print(f"   {RED}[X] Found:{RESET} {rel_path}")

    # Check 2: All .db files in repo (excluding allowed patterns)
    print(f"\n2. Scanning for all .db files...")
    all_dbs = []

    # Scan common locations
    scan_dirs = ["trading_app", "scripts", "tools", "tests", "ml_training", "ml_monitoring"]
    for scan_dir in scan_dirs:
        scan_path = repo_root / scan_dir
        if scan_path.exists():
            for db_file in scan_path.rglob("*.db"):
                rel_path = db_file.relative_to(repo_root)

                # Skip if in ignore patterns
                should_ignore = False
                for ignore_pattern in config.get("ignore_patterns", []):
                    if ignore_pattern.endswith("/**"):
                        ignore_dir = ignore_pattern.replace("/**", "")
                        if str(rel_path).startswith(ignore_dir):
                            should_ignore = True
                            break

                if not should_ignore:
                    all_dbs.append(str(rel_path))
                    print(f"   {YELLOW}[!] Found:{RESET} {rel_path}")

    # Check 3: Verify only canonical DBs exist in root
    print(f"\n3. Checking root directory...")
    root_dbs = list(repo_root.glob("*.db"))
    for db_file in root_dbs:
        if db_file.name not in allowed:
            violations.append({
                "path": db_file.name,
                "reason": "Database in root but not in allowed list",
                "size": db_file.stat().st_size
            })
            print(f"   {RED}[X] Unexpected:{RESET} {db_file.name}")
        else:
            print(f"   {GREEN}[OK] Canonical:{RESET} {db_file.name}")

    # Check 4: Old/backup patterns in names
    print(f"\n4. Checking for old/backup patterns in filenames...")
    suspicious_patterns = ["_old", "_backup", "_copy", "_deprecated", ".backup", ".bak"]
    for db_path in repo_root.rglob("*.db"):
        rel_path = db_path.relative_to(repo_root)

        # Skip ignore patterns
        should_ignore = False
        for ignore_pattern in config.get("ignore_patterns", []):
            if ignore_pattern.endswith("/**"):
                ignore_dir = ignore_pattern.replace("/**", "")
                if str(rel_path).startswith(ignore_dir):
                    should_ignore = True
                    break

        if should_ignore:
            continue

        # Check for suspicious patterns
        for pattern in suspicious_patterns:
            if pattern in db_path.name.lower():
                violations.append({
                    "path": str(rel_path),
                    "reason": f"Suspicious filename pattern: {pattern}",
                    "size": db_path.stat().st_size if db_path.exists() else 0
                })
                print(f"   {RED}[X] Suspicious:{RESET} {rel_path} (contains '{pattern}')")
                break

    return len(violations) > 0, violations


def main():
    """Run shadow database check."""
    has_violations, violations = check_shadow_databases()

    print("\n" + "=" * 70)

    if has_violations:
        print(f"{RED}{BOLD}[FAIL] GUARD FAILED{RESET}")
        print(f"\nFound {len(violations)} shadow database violation(s):\n")

        for v in violations:
            size_mb = v["size"] / (1024 * 1024)
            print(f"  {RED}[X]{RESET} {v['path']}")
            print(f"    Reason: {v['reason']}")
            if v["size"] > 0:
                print(f"    Size: {size_mb:.2f} MB")
            print()

        print(f"{YELLOW}Action required:{RESET}")
        print("  1. Remove shadow database files")
        print("  2. Or move to backups/ directory")
        print("  3. Ensure .gitignore blocks these patterns")
        print()
        print(f"Canonical database locations (root only):")
        config = load_canonical_config()
        for db in config["databases"]["allowed_locations"]:
            print(f"  - {db}")

        sys.exit(1)

    else:
        print(f"{GREEN}{BOLD}[OK] GUARD PASSED{RESET}")
        print(f"\nNo shadow databases found.")
        print(f"Repository follows canonical database structure.")

        config = load_canonical_config()
        print(f"\nCanonical databases (root):")
        for db in config["databases"]["allowed_locations"]:
            print(f"  [OK] {db}")

        sys.exit(0)


if __name__ == "__main__":
    main()
