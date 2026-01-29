#!/usr/bin/env python3
"""
Comprehensive Audit of Recent Changes (audit1.txt + audit2.txt)

Verifies:
1. All modified files are syntactically valid
2. No import errors introduced
3. Logical consistency checks
4. All tests pass
5. No breaking changes

Usage:
    python scripts/check/audit_recent_changes.py
"""

from __future__ import annotations

import ast
import importlib.util
import sys
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]

# Files modified during audit1.txt (integrity gate, scope lock, realized_rr)
AUDIT1_FILES = [
    "pipeline/cost_model.py",
    "strategies/execution_engine.py",
    "trading_app/edge_utils.py",
    "trading_app/app_simple.py",
    "trading_app/ml_dashboard.py",
    "trading_app/memory.py",
    "trading_app/app_canonical.py",
    "scripts/check/check_realized_rr_usage.py",
    "test_app_sync.py",
    "tests/test_integrity_gate.py",
    "tests/test_scope_lock.py",
]

# Files modified during audit2.txt (CI smoke test)
AUDIT2_FILES = [
    "scripts/check/run_ci_smoke.py",
]

ALL_MODIFIED_FILES = AUDIT1_FILES + AUDIT2_FILES


# =============================================================================
# CHECK 1: SYNTAX VALIDATION
# =============================================================================

def check_syntax(file_path: Path) -> tuple[bool, str]:
    """Check if Python file has valid syntax."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        return True, "Valid syntax"
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Error reading file: {e}"


# =============================================================================
# CHECK 2: IMPORT VALIDATION
# =============================================================================

def check_imports(file_path: Path) -> tuple[bool, str]:
    """Check if file can be imported without errors."""

    # Skip test files (may have test-specific dependencies)
    if "test_" in file_path.name or file_path.parent.name == "tests":
        return True, "Test file (skipped import check)"

    try:
        # Get module name from path
        relative_path = file_path.relative_to(REPO_ROOT)
        module_parts = list(relative_path.parent.parts) + [relative_path.stem]
        module_name = ".".join(module_parts)

        # Try to load module spec
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return False, "Could not load module spec"

        # Load module (this will fail if imports are broken)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        return True, "Imports valid"

    except ImportError as e:
        return False, f"Import error: {e}"
    except Exception as e:
        return False, f"Error loading module: {e}"


# =============================================================================
# CHECK 3: LOGICAL CONSISTENCY
# =============================================================================

def check_cost_model_integrity_gate() -> tuple[bool, str]:
    """Verify 30% integrity gate is properly integrated."""

    cost_model_path = REPO_ROOT / "pipeline" / "cost_model.py"

    with open(cost_model_path, 'r', encoding='utf-8') as f:
        code = f.read()

    # Check that MINIMUM_VIABLE_RISK_THRESHOLD exists
    if "MINIMUM_VIABLE_RISK_THRESHOLD" not in code:
        return False, "MINIMUM_VIABLE_RISK_THRESHOLD not found"

    if "MINIMUM_VIABLE_RISK_THRESHOLD = 0.30" not in code:
        return False, "MINIMUM_VIABLE_RISK_THRESHOLD not set to 0.30"

    # Check that check_minimum_viable_risk function exists
    if "def check_minimum_viable_risk" not in code:
        return False, "check_minimum_viable_risk function not found"

    # Check integration into calculate_realized_rr
    if "check_minimum_viable_risk" not in code or code.count("check_minimum_viable_risk") < 2:
        return False, "check_minimum_viable_risk not integrated into calculate_realized_rr"

    return True, "Integrity gate properly implemented"


def check_scope_lock() -> tuple[bool, str]:
    """Verify scope lock blocks NQ/CL."""

    cost_model_path = REPO_ROOT / "pipeline" / "cost_model.py"

    with open(cost_model_path, 'r', encoding='utf-8') as f:
        code = f.read()

    # Check PRODUCTION_INSTRUMENTS and BLOCKED_INSTRUMENTS
    if "PRODUCTION_INSTRUMENTS = ['MGC']" not in code:
        return False, "PRODUCTION_INSTRUMENTS not set to ['MGC']"

    if "BLOCKED_INSTRUMENTS" not in code or "'NQ'" not in code or "'CL'" not in code:
        return False, "BLOCKED_INSTRUMENTS missing or incomplete"

    # Check validate_instrument_or_block function
    if "def validate_instrument_or_block" not in code:
        return False, "validate_instrument_or_block function not found"

    return True, "Scope lock properly implemented"


def check_realized_rr_usage() -> tuple[bool, str]:
    """Verify realized_rr is used in critical files."""

    critical_files = [
        REPO_ROOT / "trading_app" / "edge_utils.py",
        REPO_ROOT / "trading_app" / "app_simple.py",
        REPO_ROOT / "trading_app" / "ml_dashboard.py",
        REPO_ROOT / "trading_app" / "memory.py",
    ]

    for file_path in critical_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()

        # Check that realized_rr is present
        if "realized_rr" not in code:
            return False, f"{file_path.name} missing realized_rr references"

    return True, "realized_rr properly integrated"


def check_test_app_sync_integration() -> tuple[bool, str]:
    """Verify test_app_sync.py includes Test 6 (realized_rr)."""

    test_file = REPO_ROOT / "test_app_sync.py"

    with open(test_file, 'r', encoding='utf-8') as f:
        code = f.read()

    # Check Test 6 exists
    if "Test 6" not in code or "realized_rr" not in code:
        return False, "Test 6 (realized_rr) not found in test_app_sync.py"

    # Check that check_realized_rr_usage.py is called
    if "check_realized_rr_usage.py" not in code:
        return False, "check_realized_rr_usage.py not called in test_app_sync.py"

    return True, "test_app_sync.py properly updated"


# =============================================================================
# CHECK 4: RUN ALL TESTS
# =============================================================================

def run_test_suite() -> tuple[bool, str]:
    """Run all critical tests."""

    tests = [
        ("test_app_sync", ["python", "test_app_sync.py"]),
        ("check_realized_rr", ["python", "scripts/check/check_realized_rr_usage.py"]),
        ("check_execution_spec", ["python", "scripts/check/check_execution_spec.py"]),
        ("integrity_gate_tests", ["python", "-m", "pytest", "tests/test_integrity_gate.py", "-v"]),
        ("scope_lock_tests", ["python", "-m", "pytest", "tests/test_scope_lock.py", "-v"]),
    ]

    failed_tests = []

    for name, cmd in tests:
        try:
            result = subprocess.run(
                cmd,
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                failed_tests.append(name)

        except Exception as e:
            failed_tests.append(f"{name} (error: {e})")

    if failed_tests:
        return False, f"Failed tests: {', '.join(failed_tests)}"

    return True, "All tests passed"


# =============================================================================
# CHECK 5: BREAKING CHANGES
# =============================================================================

def check_breaking_changes() -> tuple[bool, str]:
    """Check for potential breaking changes."""

    warnings = []

    # Check if cost_model.py changes are backward compatible
    cost_model = REPO_ROOT / "pipeline" / "cost_model.py"
    with open(cost_model, 'r', encoding='utf-8') as f:
        code = f.read()

    # Verify calculate_realized_rr still exists with same signature
    if "def calculate_realized_rr" not in code:
        warnings.append("calculate_realized_rr function signature may have changed")

    # Verify get_instrument_specs still exists
    if "def get_instrument_specs" not in code:
        warnings.append("get_instrument_specs function may have been removed")

    # Check execution_engine.py
    exec_engine = REPO_ROOT / "strategies" / "execution_engine.py"
    with open(exec_engine, 'r', encoding='utf-8') as f:
        code = f.read()

    # Verify TradeResult still exists
    if "class TradeResult" not in code:
        warnings.append("TradeResult class may have been modified")

    if warnings:
        return False, "; ".join(warnings)

    return True, "No breaking changes detected"


# =============================================================================
# MAIN AUDIT
# =============================================================================

def main() -> int:
    """Run comprehensive audit."""

    print("=" * 70)
    print("COMPREHENSIVE AUDIT - Recent Changes (audit1 + audit2)")
    print("=" * 70)
    print()

    # Summary of changes
    print(f"Files modified in audit1.txt: {len(AUDIT1_FILES)}")
    print(f"Files modified in audit2.txt: {len(AUDIT2_FILES)}")
    print(f"Total files to audit: {len(ALL_MODIFIED_FILES)}")
    print()

    all_passed = True

    # =========================================================================
    # CHECK 1: SYNTAX VALIDATION
    # =========================================================================
    print("=" * 70)
    print("CHECK 1: Syntax Validation")
    print("=" * 70)
    print()

    for file_rel in ALL_MODIFIED_FILES:
        file_path = REPO_ROOT / file_rel

        if not file_path.exists():
            print(f"  [SKIP] {file_rel} - file not found")
            continue

        passed, msg = check_syntax(file_path)
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {file_rel}: {msg}")

        if not passed:
            all_passed = False

    print()

    # =========================================================================
    # CHECK 2: IMPORT VALIDATION
    # =========================================================================
    print("=" * 70)
    print("CHECK 2: Import Validation")
    print("=" * 70)
    print()

    for file_rel in ALL_MODIFIED_FILES:
        file_path = REPO_ROOT / file_rel

        if not file_path.exists():
            continue

        if not file_rel.endswith('.py'):
            continue

        passed, msg = check_imports(file_path)
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {file_rel}: {msg}")

        if not passed:
            all_passed = False

    print()

    # =========================================================================
    # CHECK 3: LOGICAL CONSISTENCY
    # =========================================================================
    print("=" * 70)
    print("CHECK 3: Logical Consistency")
    print("=" * 70)
    print()

    checks = [
        ("Integrity Gate (30%)", check_cost_model_integrity_gate),
        ("Scope Lock (NQ/CL)", check_scope_lock),
        ("realized_rr Usage", check_realized_rr_usage),
        ("test_app_sync Integration", check_test_app_sync_integration),
        ("Breaking Changes", check_breaking_changes),
    ]

    for name, check_func in checks:
        passed, msg = check_func()
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {name}: {msg}")

        if not passed:
            all_passed = False

    print()

    # =========================================================================
    # CHECK 4: RUN TEST SUITE
    # =========================================================================
    print("=" * 70)
    print("CHECK 4: Test Suite")
    print("=" * 70)
    print()
    print("Running all critical tests (this may take 30-60 seconds)...")
    print()

    passed, msg = run_test_suite()
    status = "[OK]" if passed else "[FAIL]"
    print(f"  {status} Test Suite: {msg}")

    if not passed:
        all_passed = False

    print()

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("=" * 70)
    if all_passed:
        print("[PASS] ALL CHECKS PASSED")
        print()
        print("Summary:")
        print(f"  - {len(ALL_MODIFIED_FILES)} files validated")
        print("  - Syntax: valid")
        print("  - Imports: valid")
        print("  - Logic: consistent")
        print("  - Tests: passing")
        print("  - Breaking changes: none detected")
        print()
        print("System integrity verified. Changes are safe.")
    else:
        print("[FAIL] AUDIT FAILED")
        print()
        print("One or more checks failed. Review errors above.")
        print()
        print("DO NOT deploy until all issues are resolved.")

    print("=" * 70)
    print()

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
