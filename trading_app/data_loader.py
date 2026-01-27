"""
LIVE DATA LOADER - Databento Integration
Handles real-time 1-minute bar ingestion and rolling window management.
"""

import pandas as pd
import duckdb
import httpx
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from parent directory (where the main .env file is)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

from config import (
    PROJECTX_USERNAME,
    PROJECTX_API_KEY,
    PROJECTX_BASE_URL,
    PROJECTX_LIVE,
    DATA_WINDOW_HOURS,
    DB_PATH,
    TZ_LOCAL,
    TZ_UTC,
)

logger = logging.getLogger(__name__)


class LiveDataLoader:
    """
    Manages live 1-minute bar data from ProjectX API.
    Maintains a rolling window of bars in memory and DuckDB.
    """

    def __init__(self, symbol: str):
        """
        Initialize data loader for a symbol.

        Args:
            symbol: Trading symbol (e.g., "MNQ", "MGC")
        """
        self.symbol = symbol

        # Use cloud_mode connection in cloud, local DB_PATH otherwise
        from cloud_mode import get_database_connection, is_cloud_deployment
        if is_cloud_deployment():
            # Cloud mode - use MotherDuck
            self.con = get_database_connection()
            logger.info(f"Cloud mode: Connected to MotherDuck for {symbol}")
        else:
            # Local mode - use gold.db
            self.con = duckdb.connect(DB_PATH, read_only=False)
            logger.info(f"Local mode: Connected to {DB_PATH} for {symbol}")

        self._setup_tables()
        self.bars_df = pd.DataFrame()  # In-memory cache

        # ProjectX API client
        self.projectx_token: Optional[str] = None
        self.projectx_contract_id: Optional[str] = None
        self.projectx_source_symbol: Optional[str] = None

        # Initialize ProjectX session if credentials available
        if PROJECTX_USERNAME and PROJECTX_API_KEY:
            try:
                self._login_projectx()
                self._get_active_contract()
                logger.info(f"ProjectX initialized for {symbol}: {self.projectx_source_symbol}")
            except Exception as e:
                logger.warning(f"ProjectX initialization failed: {e}. Will use database only.")
        else:
            logger.warning("ProjectX credentials not found in .env. Using database only mode.")

    def _setup_tables(self):
        """Create live bars table if not exists (local only)."""
        try:
            self.con.execute(f"""
                CREATE TABLE IF NOT EXISTS live_bars (
                    ts_utc TIMESTAMPTZ NOT NULL,
                    symbol VARCHAR NOT NULL,
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    close DOUBLE,
                    volume BIGINT,
                    PRIMARY KEY (symbol, ts_utc)
                )
            """)
        except Exception as e:
            # In cloud mode (MotherDuck), can't create tables - that's OK
            logger.info(f"Could not create live_bars table (cloud mode): {e}")

    def _login_projectx(self):
        """Login to ProjectX API and get auth token."""
        url = f"{PROJECTX_BASE_URL}/api/Auth/loginKey"
        payload = {
            "userName": PROJECTX_USERNAME,
            "apiKey": PROJECTX_API_KEY,
        }
        headers = {"Accept": "text/plain", "Content-Type": "application/json"}

        with httpx.Client(timeout=30.0) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()

        if not data.get("success"):
            raise RuntimeError(f"ProjectX login failed: {data}")

        self.projectx_token = data["token"]
        logger.info("ProjectX authentication successful")

    def _get_active_contract(self):
        """Get active contract ID for the symbol."""
        url = f"{PROJECTX_BASE_URL}/api/Contract/search"
        payload = {"searchText": self.symbol, "live": PROJECTX_LIVE}
        headers = {
            "Accept": "text/plain",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.projectx_token}"
        }

        with httpx.Client(timeout=30.0) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()

        contracts = data.get("contracts", [])
        active = [c for c in contracts if c.get("activeContract")]

        if not active:
            raise RuntimeError(f"No active {self.symbol} contract found")

        contract = active[0]
        self.projectx_contract_id = contract["id"]
        self.projectx_source_symbol = contract.get("name", self.symbol)
        logger.info(f"Active contract: {self.projectx_source_symbol} (ID: {self.projectx_contract_id})")

    def fetch_latest_bars(self, lookback_minutes: int = None) -> pd.DataFrame:
        """
        Fetch latest bars from ProjectX API or database.

        Args:
            lookback_minutes: How far back to fetch (default: DATA_WINDOW_HOURS)

        Returns:
            DataFrame with columns: ts_utc, open, high, low, close, volume
        """
        if lookback_minutes is None:
            lookback_minutes = DATA_WINDOW_HOURS * 60

        # Try ProjectX API first if available
        if self.projectx_token and self.projectx_contract_id:
            try:
                return self._fetch_from_projectx(lookback_minutes)
            except Exception as e:
                logger.warning(f"ProjectX fetch failed: {e}. Falling back to database.")

        # Fall back to database
        cutoff = datetime.now(TZ_UTC) - timedelta(minutes=lookback_minutes)

        # Try live_bars first (cache), then fall back to historical bars_1m
        try:
            result = self.con.execute(f"""
                SELECT ts_utc, open, high, low, close, volume
                FROM live_bars
                WHERE symbol = ? AND ts_utc >= ?
                ORDER BY ts_utc
            """, [self.symbol, cutoff]).fetchdf()
        except:
            # live_bars doesn't exist (cloud mode), use historical bars_1m
            result = pd.DataFrame()

        if len(result) == 0:
            # Fall back to historical bars from bars_1m (MotherDuck)
            logger.info(f"No live_bars found, querying bars_1m for {self.symbol}")
            try:
                result = self.con.execute(f"""
                    SELECT ts_utc, open, high, low, close, volume
                    FROM bars_1m
                    WHERE symbol = ? AND ts_utc >= ?
                    ORDER BY ts_utc
                """, [self.symbol, cutoff]).fetchdf()
            except Exception as e:
                logger.warning(f"No bars found in bars_1m for {self.symbol}: {e}")
                return pd.DataFrame(columns=["ts_utc", "open", "high", "low", "close", "volume"])

        if len(result) == 0:
            logger.warning(f"No bars found for {self.symbol}")
            return pd.DataFrame(columns=["ts_utc", "open", "high", "low", "close", "volume"])

        # Convert to local timezone for display
        result["ts_local"] = pd.to_datetime(result["ts_utc"]).dt.tz_convert(TZ_LOCAL)

        self.bars_df = result
        return result

    def _fetch_from_projectx(self, lookback_minutes: int) -> pd.DataFrame:
        """Fetch bars from ProjectX API and update database."""
        end_utc = datetime.now(TZ_UTC)
        start_utc = end_utc - timedelta(minutes=lookback_minutes)

        # Format as ISO strings
        start_iso = start_utc.isoformat().replace("+00:00", "Z")
        end_iso = end_utc.isoformat().replace("+00:00", "Z")

        url = f"{PROJECTX_BASE_URL}/api/History/retrieveBars"
        payload = {
            "contractId": self.projectx_contract_id,
            "live": PROJECTX_LIVE,
            "startTime": start_iso,
            "endTime": end_iso,
            "unit": 2,  # Minutes
            "unitNumber": 1,  # 1-minute bars
            "limit": 20000,
            "includePartialBar": True,  # Include current forming bar
        }
        headers = {
            "Accept": "text/plain",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.projectx_token}"
        }

        with httpx.Client(timeout=60.0) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()

        if not data.get("success"):
            raise RuntimeError(f"retrieveBars failed: {data}")

        bars = data.get("bars") or []

        if not bars:
            logger.warning(f"No bars returned from ProjectX for {self.symbol}")
            return pd.DataFrame(columns=["ts_utc", "open", "high", "low", "close", "volume"])

        # Convert bars to DataFrame directly (skip database in cloud mode for performance)
        from cloud_mode import is_cloud_deployment

        if is_cloud_deployment():
            # Cloud mode: Process bars directly without database writes
            rows = []
            for bar in bars:
                rows.append({
                    "ts_utc": pd.to_datetime(bar["t"]),
                    "open": float(bar["o"]),
                    "high": float(bar["h"]),
                    "low": float(bar["l"]),
                    "close": float(bar["c"]),
                    "volume": int(bar["v"]),
                })

            result = pd.DataFrame(rows)
            result["ts_local"] = result["ts_utc"].dt.tz_convert(TZ_LOCAL)

            self.bars_df = result
            logger.info(f"Fetched {len(bars)} bars from ProjectX for {self.symbol} (cloud mode)")
            return result

        else:
            # Local mode: Insert into database
            for bar in bars:
                self.insert_bar({
                    "ts_utc": bar["t"],
                    "open": float(bar["o"]),
                    "high": float(bar["h"]),
                    "low": float(bar["l"]),
                    "close": float(bar["c"]),
                    "volume": int(bar["v"]),
                })

            # Fetch from database to get standardized format
            cutoff = datetime.now(TZ_UTC) - timedelta(minutes=lookback_minutes)
            result = self.con.execute(f"""
                SELECT ts_utc, open, high, low, close, volume
                FROM live_bars
                WHERE symbol = ? AND ts_utc >= ?
                ORDER BY ts_utc
            """, [self.symbol, cutoff]).fetchdf()

            # Convert to local timezone for display
            result["ts_local"] = pd.to_datetime(result["ts_utc"]).dt.tz_convert(TZ_LOCAL)

            self.bars_df = result
            logger.info(f"Fetched {len(bars)} bars from ProjectX for {self.symbol}")
            return result

    def get_bars_in_range(self, start_local: datetime, end_local: datetime) -> pd.DataFrame:
        """
        Get bars within a time range (local timezone).

        Args:
            start_local: Start time (local timezone)
            end_local: End time (local timezone)

        Returns:
            DataFrame of bars in range
        """
        if self.bars_df.empty:
            self.fetch_latest_bars()

        if self.bars_df.empty:
            return pd.DataFrame()

        # Convert to UTC for filtering
        start_utc = start_local.astimezone(TZ_UTC)
        end_utc = end_local.astimezone(TZ_UTC)

        mask = (self.bars_df["ts_utc"] >= start_utc) & (self.bars_df["ts_utc"] < end_utc)
        return self.bars_df[mask].copy()

    def get_latest_bar(self) -> Optional[dict]:
        """Get the most recent bar."""
        if self.bars_df.empty:
            self.fetch_latest_bars()

        if self.bars_df.empty:
            return None

        latest = self.bars_df.iloc[-1]
        return {
            "ts_utc": latest["ts_utc"],
            "ts_local": latest["ts_local"],
            "open": float(latest["open"]),
            "high": float(latest["high"]),
            "low": float(latest["low"]),
            "close": float(latest["close"]),
            "volume": int(latest["volume"]),
        }

    def get_session_high_low(self, session_start: datetime, session_end: datetime) -> Optional[dict]:
        """
        Calculate high/low for a session.

        Args:
            session_start: Session start (local time)
            session_end: Session end (local time)

        Returns:
            {"high": float, "low": float, "range": float} or None
        """
        bars = self.get_bars_in_range(session_start, session_end)

        if bars.empty:
            return None

        high = float(bars["high"].max())
        low = float(bars["low"].min())

        return {
            "high": high,
            "low": low,
            "range": high - low,
        }

    def calculate_vwap(self, start_local: datetime, end_local: datetime = None) -> Optional[float]:
        """
        Calculate VWAP from start time to end (or current).

        Args:
            start_local: Start time (local)
            end_local: End time (local), None = current

        Returns:
            VWAP value or None
        """
        if end_local is None:
            end_local = datetime.now(TZ_LOCAL)

        bars = self.get_bars_in_range(start_local, end_local)

        if bars.empty:
            return None

        # VWAP = sum(price * volume) / sum(volume)
        bars["typical_price"] = (bars["high"] + bars["low"] + bars["close"]) / 3
        bars["pv"] = bars["typical_price"] * bars["volume"]

        total_pv = bars["pv"].sum()
        total_volume = bars["volume"].sum()

        if total_volume == 0:
            return None

        return float(total_pv / total_volume)

    def insert_bar(self, bar: dict):
        """
        Insert a new bar into database (for testing/backfilling).

        Args:
            bar: {"ts_utc": datetime, "open": float, ...}
        """
        self.con.execute("""
            INSERT OR REPLACE INTO live_bars
            (ts_utc, symbol, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            bar["ts_utc"],
            self.symbol,
            bar["open"],
            bar["high"],
            bar["low"],
            bar["close"],
            bar["volume"],
        ])

    def backfill_from_gold_db(self, gold_db_path: str, days: int = 2):
        """
        Backfill recent data from existing gold.db for testing.

        Args:
            gold_db_path: Path to gold.db
            days: How many days to backfill
        """
        logger.info(f"Backfilling {days} days from {gold_db_path} for {self.symbol}")

        # If gold_db_path is same as DB_PATH, use existing connection
        from pathlib import Path
        if Path(gold_db_path).resolve() == Path(DB_PATH).resolve():
            gold_con = self.con
            close_con = False
        else:
            gold_con = duckdb.connect(gold_db_path, read_only=True)
            close_con = True
        cutoff = datetime.now(TZ_UTC) - timedelta(days=days)

        # Determine table name based on symbol
        if self.symbol == "NQ" or self.symbol == "MNQ":
            table_name = "bars_1m_nq"
            symbol_filter = ""  # No symbol column in bars_1m_nq
        else:
            table_name = "bars_1m"
            symbol_filter = "WHERE symbol = ?"

        # Build query
        if symbol_filter:
            query = f"""
                SELECT ts_utc, open, high, low, close, volume
                FROM {table_name}
                {symbol_filter} AND ts_utc >= ?
                ORDER BY ts_utc
            """
            params = [self.symbol, cutoff]
        else:
            query = f"""
                SELECT ts_utc, open, high, low, close, volume
                FROM {table_name}
                WHERE ts_utc >= ?
                ORDER BY ts_utc
            """
            params = [cutoff]

        bars = gold_con.execute(query, params).fetchall()
        logger.info(f"Found {len(bars)} bars to backfill from {table_name}")

        for bar in bars:
            self.insert_bar({
                "ts_utc": bar[0],
                "open": bar[1],
                "high": bar[2],
                "low": bar[3],
                "close": bar[4],
                "volume": bar[5],
            })

        if close_con:
            gold_con.close()
        logger.info("Backfill complete")

    def refresh(self):
        """Refresh in-memory cache from database."""
        self.fetch_latest_bars()

    def close(self):
        """Close database connection."""
        self.con.close()

    def get_today_atr(self) -> Optional[float]:
        """
        Get ATR(20) for today from daily_features table.

        Returns:
            ATR value or None if not available
        """
        today = datetime.now(TZ_LOCAL).date()

        # Map symbol to instrument name and features table
        if self.symbol == "NQ" or self.symbol == "MNQ":
            instrument = "NQ"
            features_table = "daily_features_v2_nq"
        elif self.symbol == "MPL":
            instrument = "MPL"
            features_table = "daily_features_v2_mpl"
        else:
            instrument = "MGC"
            features_table = "daily_features_v2"

        # Try from gold.db if available (separate tables per instrument)
        try:
            # Use absolute path to avoid working directory issues
            gold_db_path = os.getenv("GOLD_DB_PATH", str(Path(__file__).parent.parent / "data/db/gold.db"))
            gold_con = duckdb.connect(gold_db_path, read_only=True)
            result = gold_con.execute(f"""
                SELECT atr_20
                FROM {features_table}
                WHERE date_local = ? AND instrument = ?
            """, [today, instrument]).fetchone()

            if result and result[0] is not None:
                gold_con.close()
                return float(result[0])

            # Try yesterday if today not available yet
            yesterday = today - timedelta(days=1)
            result = gold_con.execute(f"""
                SELECT atr_20
                FROM {features_table}
                WHERE date_local = ? AND instrument = ?
            """, [yesterday, instrument]).fetchone()

            gold_con.close()

            if result and result[0] is not None:
                return float(result[0])
        except Exception as e:
            # In cloud mode, gold.db doesn't exist - this is expected
            from cloud_mode import is_cloud_deployment
            if not is_cloud_deployment():
                logger.warning(f"Could not get ATR from gold.db: {e}")
            else:
                logger.debug(f"ATR not available from gold.db in cloud mode (expected): {e}")

        return None

    def check_orb_size_filter(self, orb_high: float, orb_low: float, orb_name: str) -> dict:
        """
        Check if ORB passes size filter.

        Args:
            orb_high: ORB high price
            orb_low: ORB low price
            orb_name: ORB name ("0900", "1000", etc.)

        Returns:
            {
                "pass": bool,
                "orb_size": float,
                "orb_size_norm": float,
                "threshold": float,
                "atr": float,
                "reason": str
            }
        """
        from config import ENABLE_ORB_SIZE_FILTERS, MGC_ORB_SIZE_FILTERS, NQ_ORB_SIZE_FILTERS

        # Select instrument-specific filters
        if self.symbol in ["NQ", "MNQ"]:
            ORB_SIZE_FILTERS = NQ_ORB_SIZE_FILTERS
        else:
            ORB_SIZE_FILTERS = MGC_ORB_SIZE_FILTERS

        orb_size = orb_high - orb_low

        # Check if filter enabled and exists for this ORB
        if not ENABLE_ORB_SIZE_FILTERS or orb_name not in ORB_SIZE_FILTERS:
            return {
                "pass": True,
                "orb_size": orb_size,
                "orb_size_norm": None,
                "threshold": None,
                "atr": None,
                "reason": "No filter for this ORB"
            }

        threshold = ORB_SIZE_FILTERS[orb_name]

        if threshold is None:
            return {
                "pass": True,
                "orb_size": orb_size,
                "orb_size_norm": None,
                "threshold": None,
                "atr": None,
                "reason": "No filter for this ORB"
            }

        # Get ATR
        atr = self.get_today_atr()

        if atr is None or atr == 0:
            # Cannot apply filter without ATR - default to pass
            return {
                "pass": True,
                "orb_size": orb_size,
                "orb_size_norm": None,
                "threshold": threshold,
                "atr": None,
                "reason": "ATR not available, cannot apply filter"
            }

        # Calculate normalized ORB size
        orb_size_norm = orb_size / atr

        # Check filter
        if orb_size_norm > threshold:
            return {
                "pass": False,
                "orb_size": orb_size,
                "orb_size_norm": orb_size_norm,
                "threshold": threshold,
                "atr": atr,
                "reason": f"ORB too large: {orb_size:.2f}pts ({orb_size_norm*100:.1f}% of ATR) > {threshold*100:.1f}% threshold"
            }
        else:
            return {
                "pass": True,
                "orb_size": orb_size,
                "orb_size_norm": orb_size_norm,
                "threshold": threshold,
                "atr": atr,
                "reason": f"ORB size OK: {orb_size:.2f}pts ({orb_size_norm*100:.1f}% of ATR) <= {threshold*100:.1f}% threshold"
            }

    def get_position_size_multiplier(self, orb_name: str, filter_passed: bool) -> float:
        """
        Get position size multiplier based on filter status.

        Uses Kelly-optimal sizing from position sizing analysis.

        Args:
            orb_name: ORB name ("0900", "1000", etc.)
            filter_passed: Whether the ORB passed the size filter

        Returns:
            Position size multiplier (1.0 = baseline, >1.0 = increased size)
        """
        # Position sizing from Kelly analysis
        KELLY_MULTIPLIERS = {
            "2300": 1.15,  # 15% increase for filtered trades
            "0030": 1.61,  # 61% increase
            "1100": 1.78,  # 78% increase
            "1000": 1.23,  # 23% increase
        }

        # Only increase size if filter PASSED (small ORB, better edge)
        if filter_passed and orb_name in KELLY_MULTIPLIERS:
            return KELLY_MULTIPLIERS[orb_name]

        # Baseline sizing for everything else
        return 1.0


# ===========================================================================
# TESTING / DEVELOPMENT HELPERS
# ===========================================================================

def simulate_live_bar(loader: LiveDataLoader, symbol: str):
    """
    Simulate a live bar update (for testing without live feed).
    Generates a random bar based on last close.
    """
    import random

    latest = loader.get_latest_bar()
    if latest is None:
        # Start with a seed price
        close = 18000.0 if symbol == "MNQ" else 2700.0
    else:
        close = latest["close"]

    # Random walk
    change = random.uniform(-10, 10)
    new_close = close + change
    new_high = new_close + random.uniform(0, 5)
    new_low = new_close - random.uniform(0, 5)
    new_open = close + random.uniform(-2, 2)

    bar = {
        "ts_utc": datetime.now(TZ_UTC),
        "open": new_open,
        "high": new_high,
        "low": new_low,
        "close": new_close,
        "volume": random.randint(100, 1000),
    }

    loader.insert_bar(bar)
    loader.refresh()

    return bar


if __name__ == "__main__":
    # Test data loader
    logging.basicConfig(level=logging.INFO)

    loader = LiveDataLoader("MGC")

    # Backfill from gold.db for testing
    gold_db_path = os.getenv("GOLD_DB_PATH", str(Path(__file__).parent.parent / "data/db/gold.db"))
    loader.backfill_from_gold_db(gold_db_path, days=2)

    # Fetch and display
    bars = loader.fetch_latest_bars(lookback_minutes=60)
    print(f"Loaded {len(bars)} bars")
    print(bars.tail())

    # Test session calculation
    now = datetime.now(TZ_LOCAL)
    session_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
    session_end = now.replace(hour=17, minute=0, second=0, microsecond=0)

    session_hl = loader.get_session_high_low(session_start, session_end)
    if session_hl:
        print(f"\nAsia session: High {session_hl['high']:.2f}, Low {session_hl['low']:.2f}")

    # Test VWAP
    vwap = loader.calculate_vwap(session_start)
    if vwap:
        print(f"VWAP from 09:00: {vwap:.2f}")

    loader.close()
