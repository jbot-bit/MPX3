"""
UTILITY FUNCTIONS
Helper functions for position sizing, formatting, logging, etc.
"""

import duckdb
import pandas as pd
from datetime import datetime
from typing import Optional
import logging
import re

from config import DB_PATH, JOURNAL_TABLE, TZ_LOCAL

logger = logging.getLogger(__name__)

# Phase 3B: JOURNAL_TABLE allowlist for safe SQL interpolation
VALID_JOURNAL_TABLES = frozenset({'live_journal', 'strategy_journal', 'trade_journal'})


def _validate_journal_table(table_name: str) -> str:
    """
    Phase 3B: Validate JOURNAL_TABLE against allowlist.

    Args:
        table_name: Table name to validate

    Returns:
        Validated table name

    Raises:
        ValueError: If table name is not in allowlist
    """
    if table_name not in VALID_JOURNAL_TABLES:
        raise ValueError(
            f"Invalid JOURNAL_TABLE '{table_name}'. "
            f"Valid values: {sorted(VALID_JOURNAL_TABLES)}"
        )
    return table_name


def calculate_position_size(
    account_size: float,
    risk_pct: float,
    entry_price: float,
    stop_price: float,
    tick_value: float
) -> int:
    """
    Calculate position size in contracts.

    Args:
        account_size: Total account value
        risk_pct: Risk percentage (e.g., 0.25 for 0.25%)
        entry_price: Entry price
        stop_price: Stop loss price
        tick_value: Dollar value per point (e.g., $10 for MGC, $2 for MNQ)

    Returns:
        Number of contracts to trade
    """
    risk_dollars = account_size * (risk_pct / 100)
    risk_points = abs(entry_price - stop_price)
    risk_per_contract = risk_points * tick_value

    if risk_per_contract <= 0:
        return 0

    contracts = int(risk_dollars / risk_per_contract)
    return max(contracts, 0)


def format_price(price: float, symbol: str) -> str:
    """Format price based on instrument."""
    if symbol in ["MNQ", "NQ"]:
        return f"${price:.2f}"
    elif symbol in ["MGC", "GC"]:
        return f"${price:.1f}"
    else:
        return f"${price:.2f}"


def log_to_journal(evaluation):
    """
    Log strategy evaluation to journal database.

    Args:
        evaluation: StrategyEvaluation object
    """
    try:
        # Phase 3B: Validate table name before SQL interpolation
        table_name = _validate_journal_table(JOURNAL_TABLE)

        con = duckdb.connect(DB_PATH)

        # Create journal table if not exists
        con.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                ts_local TIMESTAMPTZ NOT NULL,
                strategy_name VARCHAR,
                state VARCHAR,
                action VARCHAR,
                reasons VARCHAR,
                next_instruction VARCHAR,
                entry_price DOUBLE,
                stop_price DOUBLE,
                target_price DOUBLE,
                risk_pct DOUBLE
            )
        """)

        # Insert log entry
        con.execute(f"""
            INSERT INTO {table_name}
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            datetime.now(TZ_LOCAL),
            evaluation.strategy_name,
            evaluation.state.value,
            evaluation.action.value,
            " | ".join(evaluation.reasons),
            evaluation.next_instruction,
            evaluation.entry_price,
            evaluation.stop_price,
            evaluation.target_price,
            evaluation.risk_pct,
        ])

        con.close()

    except Exception as e:
        logger.error(f"Journal logging error: {e}", exc_info=True)


def get_recent_journal_entries(limit: int = 50):
    """
    Retrieve recent journal entries.

    Args:
        limit: Max number of entries to return

    Returns:
        DataFrame of journal entries
    """
    try:
        # Phase 3B: Validate table name before SQL interpolation
        table_name = _validate_journal_table(JOURNAL_TABLE)

        # Don't use read_only to avoid connection conflicts
        con = duckdb.connect(DB_PATH)

        # Check if table exists first
        table_exists = con.execute(f"""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = '{table_name}'
        """).fetchone()[0]

        if not table_exists:
            con.close()
            return pd.DataFrame()

        result = con.execute(f"""
            SELECT * FROM {table_name}
            ORDER BY ts_local DESC
            LIMIT ?
        """, [limit]).fetchdf()

        con.close()
        return result

    except Exception as e:
        logger.error(f"Journal retrieval error: {e}", exc_info=True)
        return pd.DataFrame()
