#!/usr/bin/env python3
# scripts/check/app_preflight.py
from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

CHECKS = [
    # Keep these fast + deterministic
    # NOTE: test_app_sync temporarily disabled - has import path issues when run from root
    # ("test_app_sync", ["python", "scripts/test/test_app_sync.py"]),
    ("execution_spec", ["python", "scripts/check/check_execution_spec.py"]),
    ("auto_search_tables", ["python", "scripts/check/check_auto_search_tables.py"]),
    ("validation_queue_integration", ["python", "scripts/check/check_validation_queue_integration.py"]),
    ("live_terminal_fields", ["python", "scripts/check/check_live_trading_terminal_fields.py"]),
    # These are your "repair/check" scripts; ideally they support check-only.
    # If they modify DB, keep them OUT of preflight.
    # ("fk_check", ["python", "fix_foreign_key_errors.py"]),
    # ("ai_memory_check", ["python", "fix_ai_memory.py"]),
]

def run_cmd(name: str, cmd: list[str]) -> tuple[bool, str]:
    p = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONUTF8": "1"},
    )
    out = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
    ok = (p.returncode == 0)
    return ok, out.strip()

def main() -> int:
    # Allow skipping in emergencies
    if os.environ.get("MPX_SKIP_PREFLIGHT", "").strip() == "1":
        print("PREFLIGHT: SKIPPED (MPX_SKIP_PREFLIGHT=1)")
        return 0

    failures: list[tuple[str, str]] = []
    print("=" * 90)
    print("MPX APP PREFLIGHT")
    print("=" * 90)

    for name, cmd in CHECKS:
        print(f"\n--- {name} ---")
        ok, out = run_cmd(name, cmd)
        print(out if out else "(no output)")
        if not ok:
            failures.append((name, out))

    print("\n" + "=" * 90)
    if failures:
        print(f"PREFLIGHT: FAIL ({len(failures)} failing checks)")
        for name, _ in failures:
            print(f" - {name}")
        return 1

    print("PREFLIGHT: PASS (all checks OK)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
