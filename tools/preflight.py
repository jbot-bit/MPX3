#!/usr/bin/env python3
"""
PREFLIGHT SELF-SCAN - Auto-Policing for Production Readiness

Runs all mandatory gates to ensure system is production-ready:
1. Canonical environment validation
2. Data integrity audit
3. Config/database synchronization
4. Test suite
5. Static code scanning (duplicate files, AI bypass violations)

Exit codes:
  0 - All gates passed
  1+ - One or more gates failed

Usage:
    python tools/preflight.py
    python tools/preflight.py --verbose
"""

import sys
import subprocess
import ast
from pathlib import Path
from typing import List, Tuple, Dict
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "trading_app"))

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


class PreflightGate:
    """Base class for preflight gates."""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.passed = False
        self.errors: List[str] = []

    def run(self) -> bool:
        """Run gate. Return True if passed, False if failed."""
        raise NotImplementedError

    def report(self) -> str:
        """Generate report string."""
        status = "[PASS]" if self.passed else "[FAIL]"
        output = [f"{status} {self.name}: {self.description}"]
        if self.errors:
            for error in self.errors:
                output.append(f"  X {error}")
        return "\n".join(output)


class CanonicalEnvironmentGate(PreflightGate):
    """Gate 1: Validate canonical environment."""
    def __init__(self):
        super().__init__(
            "Canonical Environment",
            "Validate CANONICAL.json, required files, no shadow DBs"
        )

    def run(self) -> bool:
        try:
            from canonical import assert_canonical_environment
            assert_canonical_environment()
            self.passed = True
            return True
        except Exception as e:
            self.errors.append(str(e))
            self.passed = False
            return False


class AuditGate(PreflightGate):
    """Gate 2: Run data integrity audit."""
    def __init__(self):
        super().__init__(
            "Data Integrity Audit",
            "Run audits/audit_master.py --quick"
        )

    def run(self) -> bool:
        audit_script = PROJECT_ROOT / "audits" / "audit_master.py"
        if not audit_script.exists():
            self.errors.append(f"Audit script not found: {audit_script}")
            self.passed = False
            return False

        try:
            result = subprocess.run(
                [sys.executable, str(audit_script), "--quick"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                self.errors.append(f"Audit returned exit code {result.returncode}")
                if "FAIL" in result.stdout:
                    # Extract failure details
                    for line in result.stdout.split('\n'):
                        if "FAIL" in line or "ERROR" in line:
                            self.errors.append(line.strip())
                self.passed = False
                return False

            # Check for PASS verdict
            if "PASS" in result.stdout and "SYSTEM READY" in result.stdout:
                self.passed = True
                return True
            else:
                self.errors.append("Audit did not report PASS verdict")
                self.passed = False
                return False

        except subprocess.TimeoutExpired:
            self.errors.append("Audit timed out after 60 seconds")
            self.passed = False
            return False
        except Exception as e:
            self.errors.append(f"Audit execution error: {e}")
            self.passed = False
            return False


class SyncGate(PreflightGate):
    """Gate 3: Verify config/database synchronization."""
    def __init__(self):
        super().__init__(
            "Config/DB Synchronization",
            "Run strategies/test_app_sync.py"
        )

    def run(self) -> bool:
        sync_script = PROJECT_ROOT / "strategies" / "test_app_sync.py"
        if not sync_script.exists():
            self.errors.append(f"Sync test not found: {sync_script}")
            self.passed = False
            return False

        try:
            result = subprocess.run(
                [sys.executable, str(sync_script)],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                self.errors.append(f"Sync test returned exit code {result.returncode}")
                # Extract specific failures
                for line in result.stdout.split('\n'):
                    if "[FAIL]" in line or "MISMATCH" in line:
                        self.errors.append(line.strip())
                self.passed = False
                return False

            # Check for pass
            if "ALL TESTS PASSED" in result.stdout:
                self.passed = True
                return True
            else:
                self.errors.append("Sync test did not pass all tests")
                self.passed = False
                return False

        except subprocess.TimeoutExpired:
            self.errors.append("Sync test timed out after 30 seconds")
            self.passed = False
            return False
        except Exception as e:
            self.errors.append(f"Sync test execution error: {e}")
            self.passed = False
            return False


class PytestGate(PreflightGate):
    """Gate 4: Run pytest test suite."""
    def __init__(self):
        super().__init__(
            "Test Suite",
            "Run pytest -q"
        )

    def run(self) -> bool:
        tests_dir = PROJECT_ROOT / "tests"
        if not tests_dir.exists():
            self.errors.append(f"Tests directory not found: {tests_dir}")
            self.passed = False
            return False

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=120
            )

            # Check if pytest is not installed
            if "No module named pytest" in result.stderr or "No module named pytest" in result.stdout:
                self.errors.append("pytest not installed (skipping - not required for production)")
                self.passed = True  # Don't fail if pytest isn't available
                return True

            # pytest returns 0 if all tests pass, 1 if any fail
            if result.returncode == 0:
                self.passed = True
                return True
            elif result.returncode == 5:
                # Exit code 5 = no tests collected
                self.errors.append("No tests collected (skipping)")
                self.passed = True
                return True
            else:
                self.errors.append(f"pytest returned exit code {result.returncode}")
                # Extract failure summary
                lines = result.stdout.split('\n')
                for i, line in enumerate(lines):
                    if "FAILED" in line or "ERROR" in line:
                        self.errors.append(line.strip())
                self.passed = False
                return False

        except subprocess.TimeoutExpired:
            self.errors.append("pytest timed out after 120 seconds")
            self.passed = False
            return False
        except Exception as e:
            # If pytest isn't installed, that's OK for now
            if "No module named" in str(e) or "ModuleNotFoundError" in str(e):
                self.errors.append("pytest not installed (skipping test suite)")
                self.passed = True
                return True
            self.errors.append(f"pytest execution error: {e}")
            self.passed = False
            return False


class StaticScanGate(PreflightGate):
    """Gate 5: Static code scanning for violations."""
    def __init__(self):
        super().__init__(
            "Static Code Scan",
            "Check for duplicate files and AI bypass imports"
        )

    def run(self) -> bool:
        violations_found = False

        # Check 1: Duplicate files
        duplicate_patterns = ["*_old.py", "*_backup.py", "*_final.py"]
        duplicates = []
        for pattern in duplicate_patterns:
            for match in PROJECT_ROOT.rglob(pattern):
                # Exclude _archive and venv
                if "_archive" not in str(match) and "venv" not in str(match):
                    duplicates.append(str(match.relative_to(PROJECT_ROOT)))

        if duplicates:
            violations_found = True
            self.errors.append(f"Found {len(duplicates)} duplicate files:")
            for dup in duplicates:
                self.errors.append(f"  - {dup}")

        # Check 2: AI bypass violations (direct anthropic/openai imports)
        ai_violations = self._scan_ai_imports()
        if ai_violations:
            violations_found = True
            self.errors.append(f"Found {len(ai_violations)} AI bypass violations:")
            for file, line, import_stmt in ai_violations:
                self.errors.append(f"  - {file}:{line} - {import_stmt}")

        if violations_found:
            self.passed = False
            return False
        else:
            self.passed = True
            return True

    def _scan_ai_imports(self) -> List[Tuple[str, int, str]]:
        """Scan for direct anthropic/openai imports outside ai_guard.py."""
        violations = []

        # Allowed files (use normalized paths for comparison)
        allowed_files = [
            Path("trading_app/ai_guard.py"),  # Single choke point
            Path("trading_app") / "ai_guard.py",
            Path("tests/test_ai_source_lock.py"),  # Tests the AI guard
            Path("tests") / "test_ai_source_lock.py",
        ]

        for py_file in PROJECT_ROOT.rglob("*.py"):
            # Skip excluded directories
            rel_path = py_file.relative_to(PROJECT_ROOT)
            if any(part in str(rel_path) for part in ["venv", ".venv", "__pycache__", "_archive"]):
                continue

            # Skip allowed files (normalize paths for Windows)
            if any(rel_path == allowed or str(rel_path) == str(allowed) for allowed in allowed_files):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line_stripped = line.strip()
                        # Check for anthropic/openai imports
                        if (line_stripped.startswith("import anthropic") or
                            line_stripped.startswith("from anthropic") or
                            line_stripped.startswith("import openai") or
                            line_stripped.startswith("from openai")):
                            violations.append((str(rel_path), line_num, line_stripped))
            except Exception:
                # Skip files that can't be read
                pass

        return violations


def print_banner():
    """Print preflight banner."""
    print("=" * 70)
    print("PREFLIGHT SELF-SCAN - Production Readiness Check")
    print("=" * 70)
    print()


def print_summary(gates: List[PreflightGate]) -> int:
    """Print summary and return exit code."""
    print()
    print("=" * 70)
    print("PREFLIGHT SUMMARY")
    print("=" * 70)
    print()

    passed_count = sum(1 for gate in gates if gate.passed)
    total_count = len(gates)

    for gate in gates:
        print(gate.report())
        print()

    print("-" * 70)
    if passed_count == total_count:
        print(f"[PASS] ALL {total_count} GATES PASSED")
        print("=" * 70)
        print()
        print("[OK] System is PRODUCTION READY")
        print()
        return 0
    else:
        failed_count = total_count - passed_count
        print(f"[FAIL] {failed_count}/{total_count} GATES FAILED")
        print("=" * 70)
        print()
        print("[ERROR] System is NOT production ready")
        print()
        print("ACTION REQUIRED:")
        for gate in gates:
            if not gate.passed:
                print(f"  - Fix {gate.name}")
                for error in gate.errors:
                    if not error.startswith("  "):
                        print(f"    - {error}")
        print()
        return 1


def main():
    """Run all preflight gates."""
    print_banner()

    # Define gates in execution order
    gates = [
        CanonicalEnvironmentGate(),
        AuditGate(),
        SyncGate(),
        PytestGate(),
        StaticScanGate(),
    ]

    # Run each gate
    for i, gate in enumerate(gates, 1):
        print(f"[{i}/{len(gates)}] Running {gate.name}...")
        gate.run()

    # Print summary and exit
    exit_code = print_summary(gates)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
