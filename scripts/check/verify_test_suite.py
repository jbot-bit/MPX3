#!/usr/bin/env python3
"""
Verify Dual-Track Test Suite Installation
==========================================

Quick verification that all test files are properly installed and can run.

This script checks:
1. All 5 test files exist
2. pytest is installed
3. Database exists
4. Test files can be imported
5. Basic test discovery works
"""

import sys
from pathlib import Path
import subprocess

PROJECT_ROOT = Path(__file__).parent
TESTS_DIR = PROJECT_ROOT / "tests"
DB_PATH = PROJECT_ROOT / "data" / "db" / "gold.db"

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BOLD = '\033[1m'


def check_mark(passed):
    """Return check mark or X based on pass/fail"""
    return f"{GREEN}[PASS]{RESET}" if passed else f"{RED}[FAIL]{RESET}"


def print_header(title):
    """Print section header"""
    print(f"\n{BOLD}{'='*80}{RESET}")
    print(f"{BOLD}{title}{RESET}")
    print(f"{BOLD}{'='*80}{RESET}\n")


def check_test_files():
    """Verify all test files exist"""
    print_header("1. Checking Test Files")

    test_files = [
        "test_rr_sync.py",
        "test_entry_price.py",
        "test_tradeable_calculations.py",
        "test_cost_model_integration.py",
        "test_outcome_classification.py"
    ]

    all_exist = True
    for test_file in test_files:
        path = TESTS_DIR / test_file
        exists = path.exists()
        all_exist = all_exist and exists

        if exists:
            size = path.stat().st_size / 1024
            print(f"{check_mark(True)} {test_file:<40} {size:>6.1f} KB")
        else:
            print(f"{check_mark(False)} {test_file:<40} MISSING")

    return all_exist


def check_pytest():
    """Verify pytest is installed"""
    print_header("2. Checking pytest Installation")

    try:
        result = subprocess.run(
            ['python', '-m', 'pytest', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"{check_mark(True)} pytest installed: {version}")
            return True
        else:
            print(f"{check_mark(False)} pytest not working correctly")
            return False

    except Exception as e:
        print(f"{check_mark(False)} pytest not installed: {e}")
        print(f"\n{YELLOW}Install with: pip install pytest{RESET}")
        return False


def check_database():
    """Verify database exists"""
    print_header("3. Checking Database")

    if DB_PATH.exists():
        size = DB_PATH.stat().st_size / (1024 * 1024)
        print(f"{check_mark(True)} Database exists: {DB_PATH}")
        print(f"           Size: {size:.1f} MB")

        # Check for required tables
        try:
            import duckdb
            conn = duckdb.connect(str(DB_PATH))

            # Check for validated_setups
            tables = conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]

            has_validated = 'validated_setups' in table_names
            has_features = 'daily_features' in table_names

            print(f"{check_mark(has_validated)} validated_setups table exists")
            print(f"{check_mark(has_features)} daily_features table exists")

            # Check for tradeable columns
            if has_features:
                cols = conn.execute("""
                    SELECT COUNT(*)
                    FROM information_schema.columns
                    WHERE table_name = 'daily_features'
                    AND column_name LIKE '%tradeable%'
                """).fetchone()

                tradeable_count = cols[0] if cols else 0
                has_tradeable = tradeable_count > 0

                print(f"{check_mark(has_tradeable)} Tradeable columns exist ({tradeable_count} columns)")

                if not has_tradeable:
                    print(f"\n{YELLOW}WARNING: No tradeable columns found.{RESET}")
                    print(f"{YELLOW}Run: python pipeline/populate_tradeable_metrics.py{RESET}")

            conn.close()
            return has_validated and has_features

        except Exception as e:
            print(f"{check_mark(False)} Error checking database: {e}")
            return False

    else:
        print(f"{check_mark(False)} Database not found: {DB_PATH}")
        return False


def check_imports():
    """Verify test files can be imported"""
    print_header("4. Checking Test File Imports")

    sys.path.insert(0, str(PROJECT_ROOT))

    test_modules = [
        "tests.test_entry_price",
        "tests.test_tradeable_calculations",
        "tests.test_cost_model_integration",
        "tests.test_outcome_classification"
    ]

    all_import = True
    for module in test_modules:
        try:
            __import__(module)
            print(f"{check_mark(True)} {module}")
        except Exception as e:
            print(f"{check_mark(False)} {module}: {str(e)[:60]}")
            all_import = False

    return all_import


def check_test_discovery():
    """Verify pytest can discover tests"""
    print_header("5. Checking Test Discovery")

    try:
        result = subprocess.run(
            ['python', '-m', 'pytest', '--collect-only', '-q', str(TESTS_DIR)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(PROJECT_ROOT)
        )

        output = result.stdout + result.stderr

        # Count test files
        test_count = output.count('<Module')

        if test_count >= 5:
            print(f"{check_mark(True)} pytest discovered {test_count} test modules")
            return True
        else:
            print(f"{check_mark(False)} pytest only found {test_count} test modules (expected 5+)")
            print(f"\nOutput:\n{output[:500]}")
            return False

    except Exception as e:
        print(f"{check_mark(False)} Test discovery failed: {e}")
        return False


def print_summary(checks):
    """Print final summary"""
    print_header("Summary")

    passed = sum(checks.values())
    total = len(checks)

    for check_name, result in checks.items():
        print(f"{check_mark(result)} {check_name}")

    print(f"\n{BOLD}Result: {passed}/{total} checks passed{RESET}")

    if passed == total:
        print(f"\n{GREEN}{BOLD}[SUCCESS] Test suite is ready to use!{RESET}")
        print(f"\nRun tests with:")
        print(f"  python tests/run_dual_track_tests.py")
        print(f"  pytest tests/ -v")
        return 0
    else:
        print(f"\n{RED}{BOLD}[FAILED] Test suite has issues{RESET}")
        print(f"\nFix the issues above before running tests.")
        return 1


def main():
    """Run all verification checks"""
    print(f"\n{BOLD}Dual-Track Test Suite Verification{RESET}")
    print(f"{'='*80}\n")

    checks = {
        "Test files exist": check_test_files(),
        "pytest installed": check_pytest(),
        "Database ready": check_database(),
        "Test imports work": check_imports(),
        "Test discovery works": check_test_discovery()
    }

    return print_summary(checks)


if __name__ == "__main__":
    sys.exit(main())
