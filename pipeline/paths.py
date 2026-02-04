"""
SINGLE SOURCE OF TRUTH FOR ALL FILE PATHS

Every file in this project should import paths from here.
DO NOT hardcode paths anywhere else.

Usage:
    from pipeline.paths import GOLD_DB_PATH, PROJECT_ROOT

    # In any file:
    con = duckdb.connect(str(GOLD_DB_PATH))
"""

import os
from pathlib import Path

# Project root (directory containing this file's parent)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# ============================================================================
# DATABASE PATHS (CANONICAL)
# ============================================================================

# Main gold database - ALWAYS use this, not "gold.db"
GOLD_DB_PATH = PROJECT_ROOT / "data" / "db" / "gold.db"

# Trade journal database
TRADES_DB_PATH = PROJECT_ROOT / "data" / "db" / "trades.db"

# Allow env override but default to canonical path
def get_gold_db_path() -> Path:
    """Get gold database path, with env override support."""
    env_path = os.getenv("DUCKDB_PATH")
    if env_path:
        return Path(env_path)
    return GOLD_DB_PATH


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def ensure_db_dir():
    """Ensure data/db directory exists."""
    GOLD_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


# Validation on import
if not GOLD_DB_PATH.parent.exists():
    # First run - create the directory
    GOLD_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
