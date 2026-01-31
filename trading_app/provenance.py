"""
Provenance Tracking - Version and Metadata Capture

Tracks git commit, database path, timestamps, and version numbers
for reproducibility and auditing.

Usage:
    from provenance import create_provenance_dict

    prov = create_provenance_dict()
    # {'timestamp': '2026-01-29T...', 'git_commit': 'abc123', ...}
"""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
import logging

# Phase 3A: Logging for fail-closed visibility (debug level for metadata)
logger = logging.getLogger(__name__)

# Repo root (relative to this file)
REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "data" / "db" / "gold.db"


def get_git_commit() -> Optional[str]:
    """
    Get current git commit hash

    Returns:
        Commit hash (short) or None if not in git repo
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return None

    except Exception as e:
        # Phase 3A: Log git failures (debug level - metadata only)
        logger.debug(f"Could not get git commit: {e}")
        return None


def get_git_branch() -> Optional[str]:
    """
    Get current git branch name

    Returns:
        Branch name or None if not in git repo
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return None

    except Exception as e:
        # Phase 3A: Log git failures (debug level - metadata only)
        logger.debug(f"Could not get git branch: {e}")
        return None


def get_db_path() -> str:
    """
    Get database path (relative to repo root)

    Returns:
        Relative path string (e.g., "data/db/gold.db")
    """
    try:
        relative_path = DB_PATH.relative_to(REPO_ROOT)
        return str(relative_path).replace('\\', '/')  # Unix-style paths
    except Exception as e:
        # Phase 3A: Log path resolution failures (debug level - metadata only)
        logger.debug(f"Could not get relative db path: {e}")
        return str(DB_PATH)


def get_timestamp() -> str:
    """
    Get current timestamp in ISO 8601 format

    Returns:
        ISO 8601 timestamp string (e.g., "2026-01-29T15:30:45.123456")
    """
    return datetime.now().isoformat()


def create_provenance_dict(
    ruleset_version: str = "1.0",
    priority_version: str = "1.0",
    param_hash_version: str = "2.0"
) -> Dict:
    """
    Create provenance dictionary with all metadata

    Args:
        ruleset_version: Result classification ruleset version
        priority_version: Priority engine version
        param_hash_version: Parameter hashing version

    Returns:
        Dictionary with provenance metadata
    """
    return {
        'timestamp': get_timestamp(),
        'git_commit': get_git_commit(),
        'git_branch': get_git_branch(),
        'db_path': get_db_path(),
        'ruleset_version': ruleset_version,
        'priority_version': priority_version,
        'param_hash_version': param_hash_version
    }


if __name__ == "__main__":
    # Test provenance tracking
    print("=" * 70)
    print("PROVENANCE TRACKING TEST")
    print("=" * 70)
    print()

    prov = create_provenance_dict()

    print("Provenance metadata:")
    for key, value in prov.items():
        print(f"  {key:20} {value}")

    print()

    # Verify all required fields present
    required_fields = [
        'timestamp',
        'git_commit',
        'git_branch',
        'db_path',
        'ruleset_version',
        'priority_version',
        'param_hash_version'
    ]

    missing = [f for f in required_fields if f not in prov]

    if missing:
        print(f"[FAIL] Missing fields: {missing}")
    else:
        print("[OK] All required fields present")

    # Verify formats
    errors = []

    if not prov['timestamp']:
        errors.append("timestamp is empty")

    if not prov['db_path']:
        errors.append("db_path is empty")

    if not prov['ruleset_version']:
        errors.append("ruleset_version is empty")

    if errors:
        print(f"[FAIL] Format errors: {errors}")
    else:
        print("[OK] All fields have valid values")
