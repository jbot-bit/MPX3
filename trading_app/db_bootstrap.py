"""
Database Bootstrap - Creates required tables if they don't exist.
This module ensures the application can start with an empty database.
"""

import duckdb
import logging
from pathlib import Path
import os

logger = logging.getLogger(__name__)


def get_database_connection():
    """Get database connection (cloud-aware)."""
    from cloud_mode import is_cloud_deployment, get_motherduck_connection
    
    if is_cloud_deployment():
        try:
            return get_motherduck_connection(read_only=False)
        except Exception as e:
            logger.error(f"Failed to connect to MotherDuck: {e}")
            return None
    else:
        db_path = Path(__file__).parent.parent / "data" / "db" / "gold.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return duckdb.connect(str(db_path))


def bootstrap_database() -> bool:
    """
    Bootstrap the database with required tables.
    
    Creates tables that are needed for the application to function:
    - live_journal: Trading journal entries
    - validated_setups: Strategy configurations
    - ai_memory: AI conversation history
    
    Returns:
        bool: True if successful, False if there were issues
    """
    try:
        conn = get_database_connection()
        if conn is None:
            logger.warning("Could not connect to database for bootstrapping")
            return False
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS live_journal (
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
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS validated_setups (
                id INTEGER PRIMARY KEY,
                instrument VARCHAR NOT NULL,
                orb_time VARCHAR NOT NULL,
                rr DOUBLE,
                sl_mode VARCHAR,
                orb_size_filter DOUBLE,
                win_rate DOUBLE,
                expected_r DOUBLE,
                sample_size INTEGER,
                notes VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_memory (
                id INTEGER PRIMARY KEY,
                session_id VARCHAR NOT NULL,
                role VARCHAR NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY,
                session_id VARCHAR NOT NULL,
                role VARCHAR NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.close()
        logger.info("Database bootstrap completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database bootstrap error: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = bootstrap_database()
    print(f"Bootstrap {'succeeded' if success else 'failed'}")
