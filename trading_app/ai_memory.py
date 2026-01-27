"""
AI Memory Manager - Persistent conversation history in DuckDB

Uses canonical DB routing (cloud-aware via cloud_mode.get_database_connection).
"""

from datetime import datetime
from typing import List, Dict, Optional
import json
import logging

from cloud_mode import get_database_connection

logger = logging.getLogger(__name__)


class AIMemoryManager:
    """Manages persistent AI conversation history in canonical DB (cloud-aware)"""

    def __init__(self):
        """Initialize AI memory manager (uses canonical DB connection)."""
        self._init_schema()

    def _init_schema(self):
        """Create ai_chat_history table if not exists"""
        try:
            conn = get_database_connection()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_chat_history (
                    id INTEGER PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_id VARCHAR,
                    role VARCHAR,
                    content TEXT,
                    context_data JSON,
                    instrument VARCHAR,
                    tags VARCHAR[]
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_timestamp ON ai_chat_history(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_session ON ai_chat_history(session_id)")
            conn.close()
            logger.info("AI memory schema initialized in canonical DB")
        except Exception as e:
            logger.error(f"Error initializing AI memory schema: {e}")

    def save_message(self, session_id: str, role: str, content: str,
                     context_data: Dict = None, instrument: str = "MGC", tags: List[str] = None):
        """Save a single message to history"""
        try:
            conn = get_database_connection()
            conn.execute("""
                INSERT INTO ai_chat_history (session_id, role, content, context_data, instrument, tags)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, [session_id, role, content, json.dumps(context_data or {}), instrument, tags or []])
            conn.close()
        except Exception as e:
            logger.error(f"Error saving message to memory: {e}")

    def load_session_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Load conversation history for a session"""
        try:
            conn = get_database_connection()
            result = conn.execute("""
                SELECT role, content, timestamp, context_data, tags
                FROM ai_chat_history
                WHERE session_id = $1
                ORDER BY timestamp DESC
                LIMIT $2
            """, [session_id, limit]).fetchall()
            conn.close()

            # Reverse to get chronological order
            return [
                {
                    "role": row[0],
                    "content": row[1],
                    "timestamp": row[2],
                    "context_data": json.loads(row[3]) if row[3] else {},
                    "tags": row[4] or []
                }
                for row in reversed(result)
            ]
        except Exception as e:
            logger.error(f"Error loading session history: {e}")
            return []

    def search_history(self, query: str, instrument: str = None, limit: int = 10) -> List[Dict]:
        """Search conversation history by content"""
        try:
            conn = get_database_connection()

            # Use DuckDB parameter syntax ($1, $2, etc.)
            if instrument:
                sql = """
                    SELECT session_id, role, content, timestamp, instrument, tags
                    FROM ai_chat_history
                    WHERE content LIKE $1
                      AND instrument = $2
                    ORDER BY timestamp DESC LIMIT $3
                """
                result = conn.execute(sql, [f"%{query}%", instrument, limit]).fetchall()
            else:
                sql = """
                    SELECT session_id, role, content, timestamp, instrument, tags
                    FROM ai_chat_history
                    WHERE content LIKE $1
                    ORDER BY timestamp DESC LIMIT $2
                """
                result = conn.execute(sql, [f"%{query}%", limit]).fetchall()

            conn.close()

            return [
                {
                    "session_id": row[0],
                    "role": row[1],
                    "content": row[2],
                    "timestamp": row[3],
                    "instrument": row[4],
                    "tags": row[5]
                }
                for row in result
            ]
        except Exception as e:
            logger.error(f"Error searching history: {e}")
            return []

    def get_recent_trades(self, session_id: str = None, days: int = 7) -> List[Dict]:
        """Get recent trade-related conversations"""
        try:
            conn = get_database_connection()

            # INTERVAL syntax doesn't support parameters in DuckDB/MotherDuck
            # Use string formatting for the interval value (safe since days is an int)
            if session_id:
                sql = f"""
                    SELECT role, content, timestamp, context_data
                    FROM ai_chat_history
                    WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '{days}' DAY
                      AND list_has(tags, 'trade')
                      AND session_id = $1
                    ORDER BY timestamp DESC LIMIT 20
                """
                result = conn.execute(sql, [session_id]).fetchall()
            else:
                sql = f"""
                    SELECT role, content, timestamp, context_data
                    FROM ai_chat_history
                    WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '{days}' DAY
                      AND list_has(tags, 'trade')
                    ORDER BY timestamp DESC LIMIT 20
                """
                result = conn.execute(sql).fetchall()

            conn.close()

            return [
                {
                    "role": row[0],
                    "content": row[1],
                    "timestamp": row[2],
                    "context_data": json.loads(row[3]) if row[3] else {}
                }
                for row in result
            ]
        except Exception as e:
            logger.error(f"Error getting recent trades: {e}")
            return []

    def clear_session(self, session_id: str):
        """Clear all messages for a session"""
        try:
            conn = get_database_connection()
            conn.execute("DELETE FROM ai_chat_history WHERE session_id = $1", [session_id])
            conn.close()
            logger.info(f"Cleared session: {session_id}")
        except Exception as e:
            logger.error(f"Error clearing session: {e}")
