"""
Cloud Mode Handler - Uses MotherDuck for Streamlit Cloud deployment
"""

import os
from pathlib import Path
import duckdb
import logging

logger = logging.getLogger(__name__)

# Track if we've logged DB mode already (to avoid spam)
_db_mode_logged = False


def is_cloud_deployment() -> bool:
    """
    Detect if running in Streamlit Cloud.

    Returns True only if:
    - FORCE_LOCAL_DB override is NOT set, AND
    - CLOUD_MODE is explicitly enabled OR Streamlit Cloud env vars indicate cloud

    Local dev defaults to local DuckDB always.
    """
    # A) FORCE_LOCAL_DB override - ALWAYS LOCAL
    force_local = os.getenv("FORCE_LOCAL_DB", "0")
    if force_local.lower() in ["1", "true", "yes"]:
        return False

    # B) Check for explicit cloud mode setting
    cloud_mode = os.getenv("CLOUD_MODE", "0")
    if cloud_mode.lower() in ["1", "true", "yes"]:
        return True

    # B) Streamlit Cloud sets STREAMLIT_SHARING_MODE or has specific env vars
    if (os.getenv("STREAMLIT_SHARING_MODE") is not None or
        os.getenv("STREAMLIT_RUNTIME_ENV") == "cloud"):
        return True

    # C) Removed bad heuristic: "if data/db/gold.db does not exist => cloud"
    # Local dev defaults to local DuckDB always
    return False


def get_motherduck_connection(read_only: bool = True):
    """
    Get MotherDuck connection for cloud deployment.

    Args:
        read_only: If True, connection is read-only (default: True).
                   Note: MotherDuck handles permissions server-side, so this
                   parameter has no effect for cloud connections.

    Returns:
        duckdb.Connection to MotherDuck projectx_prod database
    """
    # Try from Streamlit secrets first, then environment
    try:
        import streamlit as st
        token = st.secrets.get("MOTHERDUCK_TOKEN", os.getenv("MOTHERDUCK_TOKEN"))
    except:
        token = os.getenv("MOTHERDUCK_TOKEN")

    if not token:
        raise ValueError(
            "MOTHERDUCK_TOKEN not found. Add it to Streamlit Cloud secrets:\n"
            "1. Go to https://share.streamlit.io/\n"
            "2. Open your app settings → Secrets\n"
            "3. Add: MOTHERDUCK_TOKEN = 'your_token_here'"
        )

    # Connect to MotherDuck projectx_prod database
    # Note: MotherDuck handles read/write permissions on the server side
    try:
        conn = duckdb.connect(f'md:projectx_prod?motherduck_token={token}')
        logger.info(f"Connected to MotherDuck: md:projectx_prod (read_only={read_only} - ignored for cloud)")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to MotherDuck: {e}")
        raise


def get_database_connection(read_only: bool = True):
    """
    Get appropriate database connection based on environment.

    Args:
        read_only: If True, connection is read-only (default: True).
                   For local databases, this enforces read-only mode.
                   For MotherDuck (cloud), permissions are handled server-side.

    Returns:
        duckdb.Connection - MotherDuck in cloud, local gold.db otherwise
    """
    global _db_mode_logged

    # Determine mode and log once
    is_cloud = is_cloud_deployment()

    if not _db_mode_logged:
        # F) Log DB mode on first connection
        if is_cloud:
            # Determine cloud reason
            if os.getenv("CLOUD_MODE", "0").lower() in ["1", "true", "yes"]:
                reason = "CLOUD_MODE env"
            elif os.getenv("STREAMLIT_SHARING_MODE") is not None:
                reason = "streamlit cloud env (STREAMLIT_SHARING_MODE)"
            elif os.getenv("STREAMLIT_RUNTIME_ENV") == "cloud":
                reason = "streamlit cloud env (STREAMLIT_RUNTIME_ENV)"
            else:
                reason = "unknown"
            logger.info(f"DB MODE: CLOUD (reason: {reason})")
        else:
            # Determine local reason
            force_local = os.getenv("FORCE_LOCAL_DB", "0")
            if force_local.lower() in ["1", "true", "yes"]:
                reason = "FORCE_LOCAL_DB"
            else:
                reason = "default local dev"
            logger.info(f"DB MODE: LOCAL (reason: {reason})")

        _db_mode_logged = True

    if is_cloud:
        # Cloud mode - use MotherDuck
        return get_motherduck_connection(read_only=read_only)
    else:
        # D) Local mode - use gold.db
        app_dir = Path(__file__).parent
        db_path = app_dir.parent / "data" / "db" / "gold.db"

        # Log resolved path
        logger.info(f"Using local DuckDB at: {db_path}")

        # E) Create parent directory and DB file if it doesn't exist
        if not db_path.exists():
            logger.info(f"Local DB file does not exist, creating: {db_path}")
            db_path.parent.mkdir(parents=True, exist_ok=True)

            # Create DB file by connecting once with read_only=False
            temp_conn = duckdb.connect(str(db_path), read_only=False)
            temp_conn.close()
            logger.info(f"Created local DB file: {db_path}")

        # Now connect with requested read_only flag
        return duckdb.connect(str(db_path), read_only=read_only)


def get_database_path() -> str:
    """
    Get database path for legacy code that expects a path string.

    Returns:
        str: Path to database (or MotherDuck connection string)
    """
    if is_cloud_deployment():
        # For cloud, return connection string
        try:
            import streamlit as st
            token = st.secrets.get("MOTHERDUCK_TOKEN", os.getenv("MOTHERDUCK_TOKEN"))
        except:
            token = os.getenv("MOTHERDUCK_TOKEN")

        if token:
            return f'md:projectx_prod?motherduck_token={token}'
        else:
            # Fallback to empty local db for demo mode
            app_dir = Path(__file__).parent
            return str(app_dir / "trading_app.db")
    else:
        # Local - use gold.db
        app_dir = Path(__file__).parent
        db_path = app_dir.parent / "data/db/gold.db"
        return str(db_path)


def show_cloud_setup_instructions():
    """Display instructions for setting up MotherDuck in cloud"""
    import streamlit as st

    st.warning("⚠️ MotherDuck Token Required")

    st.info("""
    **Your app needs MotherDuck to access data!**

    MotherDuck is your cloud database that stores all historical data, strategies, and features.
    With MotherDuck configured, your app works on any device without needing your PC on.

    ## Setup Steps:

    1. **Add Token to Streamlit Secrets:**
       - Go to: https://share.streamlit.io/
       - Find your app: **myprojectx**
       - Click **⋮** → **Settings** → **Secrets**
       - Add this line:
       ```
       MOTHERDUCK_TOKEN = "your_token_here"
       ```
       - Click **Save**

    2. **Reboot App:**
       - Click **⋮** → **Reboot app**
       - Wait 30-60 seconds

    3. **Verify Connection:**
       - App should now load with live data
       - All strategies and signals will be available

    ## Where to Get Your Token:

    Your MotherDuck token is already in your local `.env` file.

    Just copy it from:
    ```
    C:\\Users\\sydne\\OneDrive\\myprojectx\\.env
    ```

    Look for the line:
    ```
    MOTHERDUCK_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    ```

    ## What MotherDuck Provides:

    ✅ **Historical data** - bars_1m, bars_5m (MGC, MPL, NQ)
    ✅ **Daily features** - ORBs, ATR, session stats
    ✅ **Validated setups** - 19 production strategies
    ✅ **Works offline** - No need for PC to be on
    ✅ **Accessible anywhere** - Phone, tablet, any browser

    ## Total data in cloud:
    - bars_1m: 1,397,853 rows
    - bars_5m: 320,534 rows
    - daily_features: 1,780 rows (MGC, MPL, NQ)
    - validated_setups: 19 strategies

    Once configured, your mobile app will have full access to all strategies and live signals!
    """)


def get_demo_data():
    """Return demo/placeholder data when MotherDuck not configured"""
    from datetime import datetime, timedelta
    import pandas as pd

    # Generate some demo bars for visualization
    now = datetime.now()
    demo_bars = []

    for i in range(100):
        ts = now - timedelta(minutes=100-i)
        price = 2700 + (i % 20) - 10  # Oscillating around 2700
        demo_bars.append({
            "ts_local": ts,
            "open": price,
            "high": price + 2,
            "low": price - 2,
            "close": price + 1,
            "volume": 1000
        })

    return pd.DataFrame(demo_bars)


def get_demo_strategy_result():
    """Return demo strategy evaluation when MotherDuck not configured"""
    return {
        "strategy_name": "DEMO_MODE",
        "action": "STAND_DOWN",
        "state": "SETUP_REQUIRED",
        "reasons": [
            "MotherDuck token not configured",
            "Add MOTHERDUCK_TOKEN to Streamlit secrets",
            "See instructions above"
        ],
        "next_action": "Configure MotherDuck token in Streamlit Cloud settings",
        "entry_price": None,
        "stop_price": None,
        "target_price": None,
        "risk_pct": None
    }


def test_motherduck_connection():
    """Test MotherDuck connection and return status"""
    try:
        conn = get_motherduck_connection()

        # Test query
        result = conn.execute("SELECT COUNT(*) FROM bars_1m").fetchone()[0]

        conn.close()

        return {
            "success": True,
            "message": f"Connected to MotherDuck successfully! Found {result:,} bars in bars_1m.",
            "bars_count": result
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"MotherDuck connection failed: {str(e)}",
            "error": str(e)
        }


if __name__ == "__main__":
    # Test connection
    import logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

    print("Testing database connection...")

    # Test get_database_connection (will trigger logging)
    try:
        conn = get_database_connection()
        result = conn.execute("SELECT 1").fetchone()
        print(f"[OK] Connection successful, test query result: {result}")
        conn.close()
    except Exception as e:
        print(f"[FAIL] Connection failed: {e}")

    if is_cloud_deployment():
        print("\n[INFO] Cloud mode active")
    else:
        print("\n[INFO] Local mode active")
        db_path = get_database_path()
        print(f"[INFO] Database path: {db_path}")
