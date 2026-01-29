#!/usr/bin/env python3
"""
CI Smoke Test - MPX3 System Integrity Verification

Runs all critical checks in safe order to verify:
- Database and config synchronization
- Table schemas and migrations
- Import paths and module loading
- Realized RR usage (audit1.txt Step 3)
- ExecutionSpec system (UPDATE14)
- Validation queue integration

Generates machine-readable JSON report for CI/CD.

Usage:
    python scripts/check/run_ci_smoke.py

Output:
    - Console: PASS/FAIL summary
    - File: artifacts/smoke_report.json

Exit codes:
    0 = All checks passed
    1 = One or more checks failed
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


# Repo root (2 levels up from scripts/check/)
REPO_ROOT = Path(__file__).resolve().parents[2]

# Output directory for artifacts
ARTIFACTS_DIR = REPO_ROOT / "artifacts"

# Database path
DB_PATH = REPO_ROOT / "data" / "db" / "gold.db"


# =============================================================================
# CHECK DEFINITIONS
# =============================================================================

CHECKS = [
    # Check 1: Main app synchronization (config.py <-> validated_setups)
    {
        "name": "app_sync",
        "description": "Config and database synchronization",
        "command": ["python", "test_app_sync.py"],
        "critical": True,
        "timeout": 30,
    },

    # Check 2: Realized RR usage (audit1.txt Step 3)
    {
        "name": "realized_rr_usage",
        "description": "Realized RR usage verification",
        "command": ["python", "scripts/check/check_realized_rr_usage.py"],
        "critical": True,
        "timeout": 10,
    },

    # Check 3: ExecutionSpec integrity (UPDATE14)
    {
        "name": "execution_spec",
        "description": "ExecutionSpec system integrity",
        "command": ["python", "scripts/check/check_execution_spec.py"],
        "critical": True,
        "timeout": 10,
    },

    # Check 4: Validation queue integration
    {
        "name": "validation_queue",
        "description": "Validation queue integration",
        "command": ["python", "scripts/check/check_validation_queue_integration.py"],
        "critical": False,  # Non-critical (newer feature)
        "timeout": 10,
    },

    # Check 5: Auto search tables
    {
        "name": "auto_search_tables",
        "description": "Auto search table schemas",
        "command": ["python", "scripts/check/check_auto_search_tables.py"],
        "critical": False,  # Non-critical (newer feature)
        "timeout": 10,
    },
]


# =============================================================================
# CHECK EXECUTION
# =============================================================================

def run_check(check: dict[str, Any]) -> dict[str, Any]:
    """
    Run a single check and return result metadata.

    Returns:
        Dictionary with check result including:
        - name, description, passed, duration_sec, output, error
    """
    name = check["name"]
    cmd = check["command"]
    timeout = check.get("timeout", 30)

    print(f"\n{'='*70}")
    print(f"Running: {name}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*70}\n")

    start = datetime.now()

    try:
        result = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "PYTHONUTF8": "1"},
        )

        duration = (datetime.now() - start).total_seconds()
        passed = (result.returncode == 0)

        # Print output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        return {
            "name": name,
            "description": check["description"],
            "passed": passed,
            "duration_sec": round(duration, 2),
            "exit_code": result.returncode,
            "output": result.stdout or "",
            "error": result.stderr or "",
        }

    except subprocess.TimeoutExpired:
        duration = (datetime.now() - start).total_seconds()
        print(f"\n[TIMEOUT] Check '{name}' exceeded {timeout}s")

        return {
            "name": name,
            "description": check["description"],
            "passed": False,
            "duration_sec": round(duration, 2),
            "exit_code": -1,
            "output": "",
            "error": f"Timeout after {timeout}s",
        }

    except Exception as e:
        duration = (datetime.now() - start).total_seconds()
        print(f"\n[ERROR] Check '{name}' failed: {e}")

        return {
            "name": name,
            "description": check["description"],
            "passed": False,
            "duration_sec": round(duration, 2),
            "exit_code": -1,
            "output": "",
            "error": str(e),
        }


# =============================================================================
# GIT METADATA
# =============================================================================

def get_git_commit() -> str | None:
    """Get current git commit hash (if available)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_git_branch() -> str | None:
    """Get current git branch (if available)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


# =============================================================================
# DATABASE METADATA
# =============================================================================

def get_db_counts() -> dict[str, int]:
    """Get key table counts from database (read-only)."""
    counts = {}

    if not DB_PATH.exists():
        return {"error": "Database not found"}

    try:
        import duckdb

        with duckdb.connect(str(DB_PATH), read_only=True) as con:
            # Get validated_setups count
            result = con.execute("SELECT COUNT(*) FROM validated_setups").fetchone()
            counts["validated_setups"] = result[0] if result else 0

            # Get daily_features count
            result = con.execute("SELECT COUNT(*) FROM daily_features").fetchone()
            counts["daily_features"] = result[0] if result else 0

            # Get bars_1m count
            result = con.execute("SELECT COUNT(*) FROM bars_1m").fetchone()
            counts["bars_1m"] = result[0] if result else 0

    except Exception as e:
        counts["error"] = str(e)

    return counts


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_report(check_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate machine-readable JSON report."""

    # Calculate summary stats
    total_checks = len(check_results)
    passed_checks = sum(1 for r in check_results if r["passed"])
    failed_checks = total_checks - passed_checks

    critical_failures = [
        r for r in check_results
        if not r["passed"] and CHECKS[check_results.index(r)]["critical"]
    ]

    total_duration = sum(r["duration_sec"] for r in check_results)

    # Build report
    report = {
        "timestamp": datetime.now().isoformat(),
        "repo_root": str(REPO_ROOT),
        "db_path": str(DB_PATH),
        "db_exists": DB_PATH.exists(),

        # Git metadata
        "git": {
            "commit": get_git_commit(),
            "branch": get_git_branch(),
        },

        # Summary
        "summary": {
            "total_checks": total_checks,
            "passed": passed_checks,
            "failed": failed_checks,
            "critical_failures": len(critical_failures),
            "total_duration_sec": round(total_duration, 2),
            "overall_passed": (failed_checks == 0),
        },

        # Database counts
        "db_counts": get_db_counts(),

        # Check results
        "checks": check_results,
    }

    return report


def write_report(report: dict[str, Any]) -> Path:
    """Write JSON report to artifacts directory."""

    # Ensure artifacts directory exists
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    # Write report
    report_path = ARTIFACTS_DIR / "smoke_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report_path


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:
    """Run all checks and generate report."""

    print("=" * 70)
    print("MPX3 CI SMOKE TEST")
    print("=" * 70)
    print(f"Repo root: {REPO_ROOT}")
    print(f"Database: {DB_PATH} ({'exists' if DB_PATH.exists() else 'NOT FOUND'})")
    print(f"Git commit: {get_git_commit() or 'N/A'}")
    print(f"Git branch: {get_git_branch() or 'N/A'}")
    print()

    # Run all checks
    check_results = []
    for check in CHECKS:
        result = run_check(check)
        check_results.append(result)

        # Hard fail on critical check failure
        if not result["passed"] and check["critical"]:
            print(f"\n[CRITICAL FAILURE] {check['name']} failed (critical check)")
            print("Stopping smoke test (hard fail on critical check)")
            break

    # Generate report
    report = generate_report(check_results)
    report_path = write_report(report)

    # Print summary
    print("\n" + "=" * 70)
    print("SMOKE TEST SUMMARY")
    print("=" * 70)

    summary = report["summary"]
    print(f"Total checks: {summary['total_checks']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Critical failures: {summary['critical_failures']}")
    print(f"Duration: {summary['total_duration_sec']}s")
    print()

    # Show failed checks
    if summary["failed"] > 0:
        print("Failed checks:")
        for result in check_results:
            if not result["passed"]:
                critical_marker = " (CRITICAL)" if CHECKS[check_results.index(result)]["critical"] else ""
                print(f"  - {result['name']}{critical_marker}")
        print()

    # Show database counts
    if "error" not in report["db_counts"]:
        print("Database counts:")
        for table, count in report["db_counts"].items():
            print(f"  - {table}: {count:,}")
        print()

    # Final verdict
    print("=" * 70)
    if summary["overall_passed"]:
        print("[PASS] System wired correctly")
    else:
        print("[FAIL] Broken link detected")
    print("=" * 70)
    print()
    print(f"Report: {report_path}")
    print()

    return 0 if summary["overall_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
