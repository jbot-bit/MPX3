"""
TRADING APP CONFIGURATION
All constants, thresholds, and settings in one place.
"""

import os
from datetime import timezone, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from dotenv import load_dotenv
import sys

# Add tools directory to path for config_generator import
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
from config_generator import load_instrument_configs

# Load .env from parent directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# ============================================================================
# TIMEZONE & TIME CONSTANTS
# ============================================================================
TZ_LOCAL = ZoneInfo("Australia/Brisbane")  # UTC+10, no DST
TZ_UTC = ZoneInfo("UTC")

# ============================================================================
# INSTRUMENT CONFIGURATION
# ============================================================================
PRIMARY_INSTRUMENT = os.getenv("PRIMARY_INSTRUMENT", "MGC")  # Default: Micro Gold (ONLY suitable instrument)
SECONDARY_INSTRUMENT = None  # NQ not suitable for ORB strategy (RR=1.0 only, slippage kills edge)
TERTIARY_INSTRUMENT = None   # MPL not suitable for ORB strategy (RR=1.0 only, slippage kills edge)
ENABLE_SECONDARY = False  # No secondary instruments available

# ============================================================================
# SESSION DEFINITIONS (LOCAL TIME UTC+10)
# ============================================================================
SESSIONS = {
    "ASIA": {"start_hour": 9, "start_min": 0, "end_hour": 17, "end_min": 0},
    "LONDON": {"start_hour": 18, "start_min": 0, "end_hour": 23, "end_min": 0},
    "NY_FUTURES": {"start_hour": 23, "start_min": 0, "end_hour": 2, "end_min": 0},  # Next day
}

# ORB times (local)
ORB_TIMES = [
    {"hour": 9, "min": 0, "name": "0900"},
    {"hour": 10, "min": 0, "name": "1000"},
    {"hour": 11, "min": 0, "name": "1100"},
    {"hour": 18, "min": 0, "name": "1800"},   # London open (Asia close)
    {"hour": 23, "min": 0, "name": "2300"},
    {"hour": 0, "min": 30, "name": "0030"},  # Next day
]

ORB_DURATION_MIN = 5  # 5-minute ORB window

# ============================================================================
# STRATEGY HIERARCHY (PRIORITY ORDER)
# ============================================================================
STRATEGY_PRIORITY = [
    "MULTI_LIQUIDITY_CASCADE",  # A+ tier
    # "PROXIMITY_PRESSURE",        # FAILED: -0.50R avg, 1.1% freq (DISABLED 2026-01-15)
    "NIGHT_ORB",                 # B tier (23:00, 00:30)
    "SINGLE_LIQUIDITY",          # B-Backup tier
    "DAY_ORB",                   # C tier (09:00, 10:00, 11:00)
]

# ============================================================================
# CASCADE STRATEGY PARAMETERS (From validation testing)
# ============================================================================
CASCADE_MIN_GAP_POINTS = 9.5  # Minimum gap between liquidity levels
CASCADE_ENTRY_TOLERANCE = 0.1  # Entry within 0.1 points of level
CASCADE_FAILURE_BARS = 3  # Check next 3 bars for acceptance failure
CASCADE_MAX_HOLD_MINUTES = 90  # Maximum hold time

# ============================================================================
# PROXIMITY PRESSURE PARAMETERS (DISABLED - FAILED TESTING)
# ============================================================================
# WARNING: This strategy tested at -0.50R avg, 1.1% frequency. FAILED.
# Disabled in STRATEGY_PRIORITY list above (2026-01-15).
# Kept for reference but not evaluated by strategy engine.
PROXIMITY_MAX_DISTANCE_POINTS = 5.0  # Levels within 5 points
PROXIMITY_ATR_MULTIPLIER = 0.3  # OR within 0.3 * ATR
PROXIMITY_TAG_WINDOW_MIN = 5  # Minutes to tag second level

# ============================================================================
# ORB STRATEGY PARAMETERS (INSTRUMENT-SPECIFIC)
# ============================================================================

# IMPORTANT: Configurations now AUTO-GENERATED from validated_setups database!
# This eliminates manual sync errors between database and config.
# Single source of truth: gold.db → validated_setups table
# See: config_generator.py for implementation

# MGC (Micro Gold) - DYNAMICALLY LOADED FROM DATABASE
# Source: validated_setups table (automatically updated by populate_validated_setups.py)
# History: CORRECTED Configuration (2026-01-16 SCAN WINDOW BUG FIX)
# - Extended scan windows to 09:00 next day (was stopping too early!)
# - OLD BUG: Night ORBs scanned only 85min, missed 30+ point moves
# - NEW FIX: All ORBs scan until next Asia open - captures full overnight moves
# - RESULT: System improved from +400R/year to +600R/year (+50%!)
# Expected configs (auto-loaded):
#   0900: RR=6.0, FULL SL (A TIER) ~+51R/year
#   1000: RR=8.0, FULL SL (S+ TIER - CROWN JEWEL!) ~+98R/year
#   1100: RR=3.0, FULL SL (A TIER) ~+56R/year
#   1800: RR=1.5, FULL SL (S TIER) ~+72R/year
#   2300: RR=1.5, HALF SL, Filter=0.155 (S+ TIER - BEST OVERALL!) ~+105R/year
#   0030: RR=3.0, HALF SL, Filter=0.112 (S TIER) ~+66R/year

MGC_ORB_CONFIGS, MGC_ORB_SIZE_FILTERS = load_instrument_configs('MGC')

# NQ (Micro Nasdaq) - DYNAMICALLY LOADED FROM DATABASE
# Source: validated_setups table (extended scan window validation 2024-01-01 to 2026-01-10)
# History: NOT SUITABLE FOR ORB STRATEGY (2026-01-16 ANALYSIS)
# - FINDING: Optimal RR=1.0 for all ORBs, but moves don't extend enough
# - PROBLEM: Sharp dropoff in WR at RR=1.25+ (e.g., 62% → 32% for 1100 ORB)
# - REALITY: Slippage (~0.2R per trade) makes RR=1.0 breakeven or negative in live trading
# - CONCLUSION: NQ moves are too tight/choppy for this ORB strategy
# - RECOMMENDATION: Focus on MGC which has RR=3.0-8.0 with huge slippage buffers
# Note: Database may contain RR=1.0 configs for reference, but not recommended for live trading

NQ_ORB_CONFIGS, NQ_ORB_SIZE_FILTERS = load_instrument_configs('NQ')

# MPL (Platinum) - DYNAMICALLY LOADED FROM DATABASE
# Source: validated_setups table (extended scan window validation 2025-01-13 to 2026-01-12)
# History: NOT SUITABLE FOR ORB STRATEGY (2026-01-16 ANALYSIS)
# - FINDING: Optimal RR=1.0 for all ORBs, but moves don't extend enough
# - PROBLEM: Sharp dropoff in WR at RR=1.25+ (e.g., 67% → 38% for 1100 ORB)
# - REALITY: Slippage (~0.2R per trade) makes RR=1.0 breakeven or negative in live trading
# - CONCLUSION: MPL moves are too tight/choppy for this ORB strategy
# - RECOMMENDATION: Focus on MGC which has RR=3.0-8.0 with huge slippage buffers
# Note: Database may contain RR=1.0 configs for reference, but not recommended for live trading

MPL_ORB_CONFIGS, MPL_ORB_SIZE_FILTERS = load_instrument_configs('MPL')

# Dynamic configs (loaded based on selected instrument)
ORB_CONFIGS = MGC_ORB_CONFIGS  # Default to MGC
ORB_SIZE_FILTERS = MGC_ORB_SIZE_FILTERS

# Enable/disable filters globally
ENABLE_ORB_SIZE_FILTERS = True

# ============================================================================
# SINGLE LIQUIDITY PARAMETERS
# ============================================================================
SINGLE_LIQ_ENTRY_TOLERANCE = 0.1
SINGLE_LIQ_FAILURE_BARS = 3

# ============================================================================
# DATA INGESTION
# ============================================================================
DATA_WINDOW_HOURS = 48  # Keep 48 hours of rolling data
DATA_REFRESH_SECONDS = 5  # Refresh every 5 seconds

# ProjectX API (for live data)
PROJECTX_USERNAME = os.getenv("PROJECTX_USERNAME", "")
PROJECTX_API_KEY = os.getenv("PROJECTX_API_KEY", "")
PROJECTX_BASE_URL = os.getenv("PROJECTX_BASE_URL", "https://api.topstepx.com")
PROJECTX_LIVE = os.getenv("PROJECTX_LIVE", "false").lower() == "true"

# Databento API (backup/alternative)
DATABENTO_API_KEY = os.getenv("DATABENTO_API_KEY", "")

# ============================================================================
# RISK MANAGEMENT
# ============================================================================
DEFAULT_ACCOUNT_SIZE = 50000.0  # $50k default
RISK_LIMITS = {
    "CASCADE": {"min": 0.10, "max": 0.25, "default": 0.25},  # % of account
    "PROXIMITY": {"min": 0.10, "max": 0.50, "default": 0.25},
    "NIGHT_ORB": {"min": 0.25, "max": 0.50, "default": 0.50},
    "SINGLE_LIQ": {"min": 0.25, "max": 0.50, "default": 0.25},
    "DAY_ORB": {"min": 0.10, "max": 0.25, "default": 0.10},
}

# ============================================================================
# DATABASE
# ============================================================================
# Use absolute path - database is one level up from trading_app/
from pathlib import Path
DB_PATH = str(Path(__file__).parent.parent / "data" / "db" / "gold.db")
JOURNAL_TABLE = "live_journal"

# ============================================================================
# UI SETTINGS
# ============================================================================
CHART_HEIGHT = 400  # Reduced from 600 for better layout (Phase 3)
CHART_LOOKBACK_BARS = 200
UPDATE_INTERVAL_MS = 5000  # 5 seconds

# ============================================================================
# MOBILE UI CONFIGURATION
# ============================================================================
MOBILE_MODE = os.getenv("MOBILE_MODE", "false").lower() == "true"  # Toggle for mobile layout
MOBILE_CHART_HEIGHT = 350  # Smaller chart for mobile (vs 600 desktop)
MOBILE_BUTTON_SIZE = 48  # Minimum touch target (px) - iOS/Android standard
MOBILE_FONT_SCALE = 1.2  # Scale fonts up for readability on small screens

# Card configuration
ENABLE_CARDS = ["dashboard", "chart", "trade", "positions", "ai"]  # All cards enabled
DEFAULT_CARD = "dashboard"  # Start on dashboard card

# Touch optimization
ENABLE_SWIPE_GESTURES = True  # Enable swipe navigation between cards
SNAP_TO_CARDS = True  # CSS scroll-snap for card alignment

# ============================================================================
# ML/AI CONFIGURATION
# ============================================================================
# ML is disabled by default (Phase 1 does not include ML)
# Enable via env var: ENABLE_ML=1 or ML_ENABLED=true
# Accept both ENABLE_ML and ML_ENABLED for backward compatibility
_enable_ml_flag = os.getenv("ENABLE_ML", os.getenv("ML_ENABLED", "0"))
ML_ENABLED = _enable_ml_flag.lower() in ["1", "true", "yes"]
ML_CONFIDENCE_THRESHOLD = float(os.getenv("ML_CONFIDENCE_THRESHOLD", "0.55"))  # Minimum confidence to show
ML_HIGH_CONFIDENCE = float(os.getenv("ML_HIGH_CONFIDENCE", "0.65"))  # High confidence threshold
ML_CACHE_TTL = int(os.getenv("ML_CACHE_TTL", "300"))  # Cache TTL in seconds (5 minutes)
ML_MAX_INFERENCE_TIME = float(os.getenv("ML_MAX_INFERENCE_TIME", "0.1"))  # Max inference time in seconds
ML_SHADOW_MODE = os.getenv("ML_SHADOW_MODE", "true").lower() == "true"  # Shadow mode: log only, don't act
ML_RISK_ADJUSTMENT_ENABLED = os.getenv("ML_RISK_ADJUSTMENT", "false").lower() == "true"  # Adjust position size based on ML confidence

# ML Model versions (set to 'latest' to auto-load newest)
ML_DIRECTIONAL_MODEL_VERSION = os.getenv("ML_DIRECTIONAL_VERSION", "latest")
ML_ENTRY_QUALITY_MODEL_VERSION = os.getenv("ML_ENTRY_QUALITY_VERSION", "latest")
ML_R_MULTIPLE_MODEL_VERSION = os.getenv("ML_R_MULTIPLE_VERSION", "latest")

# ============================================================================
# LOGGING
# ============================================================================
LOG_LEVEL = "INFO"
LOG_FILE = "trading_app.log"
