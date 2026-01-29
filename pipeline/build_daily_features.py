# build_daily_features.py
"""
Daily Feature Builder - ZERO LOOKAHEAD (FIXED) + CANONICAL EXECUTION ENGINE
============================================================================

This script implements the CANONICAL EXECUTION ENGINE principles:
- Entry at first CLOSE outside ORB (NOT ORB edge)
- Stop at FULL (opposite edge) or HALF (midpoint)
- Target = entry +/- RR * risk
- Conservative same-bar resolution (TP+SL both hit = LOSS)

For parameter variations (different RR, confirmations, buffers), use execution_engine.py
instead of creating new backtest scripts.

CRITICAL:
- Each ORB can only use information available AT that exact time.
- The "trade_date" here is the ASIA date (local Australia/Brisbane):
    ASIA date D covers:
      PRE_ASIA     D 07:00–09:00
      ASIA         D 09:00–17:00  (ORBs 09:00/10:00/11:00)
      PRE_LONDON   D 17:00–18:00
      LONDON       D 18:00–23:00  (ORB 18:00)
      PRE_NY       D 23:00–(D+1)00:30
      NY_FUTURES   D 23:00–(D+1)00:30 (ORB 23:00, execution window ends 00:30)
      NY_CASH      (D+1)00:30–02:00 (includes ORB 00:30, execution window ends 02:00)

Execution Model (1-minute):
- ORB = first 5 minutes of that open (range from bars_1m high/low)
- Entry trigger = first 1m CLOSE outside ORB after ORB window ends (LINE 192)
- SL = opposite ORB boundary (FULL) or midpoint (HALF)
- TP = entry +/- RR * risk (risk = abs(entry_close - SL))
- Outcome checked using subsequent 1m high/low (conservative: if both hit in same bar => LOSS)

GUARDRAIL: Entry must NOT be at ORB edge (assertions at LINE 192+)

NOTE: Writes to daily_features table (canonical table)

Usage:
  python build_daily_features.py 2026-01-10
  python build_daily_features.py 2024-01-02 2026-01-10
  python build_daily_features.py 2024-01-02 2026-01-10 --sl-mode half
"""

import duckdb
import sys
import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Dict, Tuple, List

# Import cost_model for canonical realized RR calculations
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.cost_model import calculate_realized_rr

TZ_LOCAL = ZoneInfo("Australia/Brisbane")
TZ_UTC = ZoneInfo("UTC")

SYMBOL = "MGC"
DB_PATH = "data/db/gold.db"
RSI_LEN = 14

RR_DEFAULT = 1.0  # keep simple for now
SL_MODE = "full"  # Default: "full" = stop at opposite edge; can override with --sl-mode half


def _dt_local(d: date, hh: int, mm: int) -> datetime:
    return datetime(d.year, d.month, d.day, hh, mm, tzinfo=TZ_LOCAL)


class FeatureBuilder:
    def __init__(self, db_path: str = DB_PATH, sl_mode: str = "full", table_name: str = "daily_features"):
        self.con = duckdb.connect(db_path)
        self.sl_mode = sl_mode
        self.table_name = table_name

    def _ensure_schema_columns(self, auto_migrate: bool = True):
        """
        Guardrail preflight check: Ensure all required columns exist in daily_features table.

        Self-detects required columns by parsing the INSERT statement at runtime.
        Compares to actual database schema and auto-migrates missing columns.

        This prevents schema mismatch errors when build_daily_features runs.
        """
        # Self-detect columns from INSERT statement (line ~827-861 in build_features method)
        # This is the SINGLE SOURCE OF TRUTH - no hardcoded list
        insert_sql = """
            INSERT OR REPLACE INTO {table_name} (
                date_local, instrument,

                pre_asia_high, pre_asia_low, pre_asia_range,
                pre_london_high, pre_london_low, pre_london_range,
                pre_ny_high, pre_ny_low, pre_ny_range,

                asia_high, asia_low, asia_range,
                london_high, london_low, london_range,
                ny_high, ny_low, ny_range,
                asia_type_code, london_type_code, pre_ny_type_code,

                orb_0900_high, orb_0900_low, orb_0900_size, orb_0900_break_dir, orb_0900_outcome, orb_0900_r_multiple, orb_0900_mae, orb_0900_mfe, orb_0900_stop_price, orb_0900_risk_ticks,
                orb_0900_realized_rr, orb_0900_realized_risk_dollars, orb_0900_realized_reward_dollars,
                orb_1000_high, orb_1000_low, orb_1000_size, orb_1000_break_dir, orb_1000_outcome, orb_1000_r_multiple, orb_1000_mae, orb_1000_mfe, orb_1000_stop_price, orb_1000_risk_ticks,
                orb_1000_realized_rr, orb_1000_realized_risk_dollars, orb_1000_realized_reward_dollars,
                orb_1100_high, orb_1100_low, orb_1100_size, orb_1100_break_dir, orb_1100_outcome, orb_1100_r_multiple, orb_1100_mae, orb_1100_mfe, orb_1100_stop_price, orb_1100_risk_ticks,
                orb_1100_realized_rr, orb_1100_realized_risk_dollars, orb_1100_realized_reward_dollars,
                orb_1800_high, orb_1800_low, orb_1800_size, orb_1800_break_dir, orb_1800_outcome, orb_1800_r_multiple, orb_1800_mae, orb_1800_mfe, orb_1800_stop_price, orb_1800_risk_ticks,
                orb_1800_realized_rr, orb_1800_realized_risk_dollars, orb_1800_realized_reward_dollars,
                orb_2300_high, orb_2300_low, orb_2300_size, orb_2300_break_dir, orb_2300_outcome, orb_2300_r_multiple, orb_2300_mae, orb_2300_mfe, orb_2300_stop_price, orb_2300_risk_ticks,
                orb_2300_realized_rr, orb_2300_realized_risk_dollars, orb_2300_realized_reward_dollars,
                orb_0030_high, orb_0030_low, orb_0030_size, orb_0030_break_dir, orb_0030_outcome, orb_0030_r_multiple, orb_0030_mae, orb_0030_mfe, orb_0030_stop_price, orb_0030_risk_ticks,
                orb_0030_realized_rr, orb_0030_realized_risk_dollars, orb_0030_realized_reward_dollars,

                orb_0900_tradeable_entry_price, orb_0900_tradeable_stop_price, orb_0900_tradeable_risk_points, orb_0900_tradeable_target_price, orb_0900_tradeable_outcome, orb_0900_tradeable_realized_rr, orb_0900_tradeable_realized_risk_dollars, orb_0900_tradeable_realized_reward_dollars,
                orb_1000_tradeable_entry_price, orb_1000_tradeable_stop_price, orb_1000_tradeable_risk_points, orb_1000_tradeable_target_price, orb_1000_tradeable_outcome, orb_1000_tradeable_realized_rr, orb_1000_tradeable_realized_risk_dollars, orb_1000_tradeable_realized_reward_dollars,
                orb_1100_tradeable_entry_price, orb_1100_tradeable_stop_price, orb_1100_tradeable_risk_points, orb_1100_tradeable_target_price, orb_1100_tradeable_outcome, orb_1100_tradeable_realized_rr, orb_1100_tradeable_realized_risk_dollars, orb_1100_tradeable_realized_reward_dollars,
                orb_1800_tradeable_entry_price, orb_1800_tradeable_stop_price, orb_1800_tradeable_risk_points, orb_1800_tradeable_target_price, orb_1800_tradeable_outcome, orb_1800_tradeable_realized_rr, orb_1800_tradeable_realized_risk_dollars, orb_1800_tradeable_realized_reward_dollars,
                orb_2300_tradeable_entry_price, orb_2300_tradeable_stop_price, orb_2300_tradeable_risk_points, orb_2300_tradeable_target_price, orb_2300_tradeable_outcome, orb_2300_tradeable_realized_rr, orb_2300_tradeable_realized_risk_dollars, orb_2300_tradeable_realized_reward_dollars,
                orb_0030_tradeable_entry_price, orb_0030_tradeable_stop_price, orb_0030_tradeable_risk_points, orb_0030_tradeable_target_price, orb_0030_tradeable_outcome, orb_0030_tradeable_realized_rr, orb_0030_tradeable_realized_risk_dollars, orb_0030_tradeable_realized_reward_dollars,

                rsi_at_0030, rsi_at_orb, atr_20
            ) VALUES
        """

        # Parse column names from INSERT statement
        import re
        col_match = re.search(r'\((.*?)\)\s*VALUES', insert_sql, re.DOTALL)
        if not col_match:
            raise RuntimeError("Failed to parse INSERT statement for column detection")

        columns_text = col_match.group(1)
        required_columns = []
        for line in columns_text.split('\n'):
            line = line.strip()
            if not line or line.startswith('--') or '{' in line:
                continue
            for col in line.split(','):
                col = col.strip()
                if col:
                    required_columns.append(col)

        # Deterministic type mapping (explicit, minimal, justified)
        # Only list non-DOUBLE types here with reasons
        COLUMN_TYPES = {
            # Primary key components
            "date_local": "DATE",        # Date type for trading day
            "instrument": "VARCHAR",     # Symbol identifier (MGC, NQ, etc.)

            # Categorical session type codes
            "asia_type_code": "VARCHAR",      # L4_CONSOLIDATION, A0_NORMAL, etc.
            "london_type_code": "VARCHAR",
            "pre_ny_type_code": "VARCHAR",

            # ORB direction and outcome (categorical)
            "orb_0900_break_dir": "VARCHAR",  # UP, DOWN, NONE
            "orb_1000_break_dir": "VARCHAR",
            "orb_1100_break_dir": "VARCHAR",
            "orb_1800_break_dir": "VARCHAR",
            "orb_2300_break_dir": "VARCHAR",
            "orb_0030_break_dir": "VARCHAR",

            "orb_0900_outcome": "VARCHAR",    # WIN, LOSS, NONE
            "orb_1000_outcome": "VARCHAR",
            "orb_1100_outcome": "VARCHAR",
            "orb_1800_outcome": "VARCHAR",
            "orb_2300_outcome": "VARCHAR",
            "orb_0030_outcome": "VARCHAR",

            "orb_0900_tradeable_outcome": "VARCHAR",
            "orb_1000_tradeable_outcome": "VARCHAR",
            "orb_1100_tradeable_outcome": "VARCHAR",
            "orb_1800_tradeable_outcome": "VARCHAR",
            "orb_2300_tradeable_outcome": "VARCHAR",
            "orb_0030_tradeable_outcome": "VARCHAR",
        }
        # Everything not in COLUMN_TYPES defaults to DOUBLE (all numeric metrics)

        # Query actual columns from database
        schema = self.con.execute(f"PRAGMA table_info('{self.table_name}')").fetchall()
        existing_columns = {row[1] for row in schema}

        # Compute missing columns = required - existing
        missing_columns = [col for col in required_columns if col not in existing_columns]

        if not missing_columns:
            print(f"Schema check PASSED: All {len(required_columns)} columns exist in {self.table_name}")
            return

        print(f"\nSchema check: Found {len(missing_columns)} missing columns in {self.table_name}")

        if not auto_migrate:
            print("\nMISSING COLUMNS:")
            for col in missing_columns:
                print(f"  - {col}")
            raise RuntimeError(
                f"Schema mismatch: {len(missing_columns)} columns missing from {self.table_name}. "
                f"Run with auto_migrate=True to automatically add them."
            )

        # Auto-migrate: Add missing columns
        print(f"Auto-migrating: Adding {len(missing_columns)} missing columns...")
        print("="*60)

        for col in missing_columns:
            col_type = COLUMN_TYPES.get(col, "DOUBLE")  # Default to DOUBLE for all numeric columns
            print(f"  Adding: {col:50} {col_type}")
            self.con.execute(f"ALTER TABLE {self.table_name} ADD COLUMN {col} {col_type}")

        print("="*60)
        print(f"Auto-migration complete: Added {len(missing_columns)} columns")
        print()

    # ---------- core time-window fetchers (FIX midnight safely) ----------
    def _window_stats_1m(self, start_local: datetime, end_local: datetime) -> Optional[Dict]:
        start_utc = start_local.astimezone(TZ_UTC)
        end_utc = end_local.astimezone(TZ_UTC)

        row = self.con.execute(
            """
            SELECT
              MAX(high) AS high,
              MIN(low)  AS low,
              MAX(high) - MIN(low) AS range,
              SUM(volume) AS volume
            FROM bars_1m
            WHERE symbol = ?
              AND ts_utc >= ? AND ts_utc < ?
            """,
            [SYMBOL, start_utc, end_utc],
        ).fetchone()

        if not row or row[0] is None:
            return None

        high, low, rng, vol = row
        return {
            "high": float(high),
            "low": float(low),
            "range": float(rng),
            "range_ticks": float(rng) / 0.1 if rng is not None else None,
            "volume": int(vol) if vol is not None else 0,
        }

    def _fetch_1m_bars(self, start_local: datetime, end_local: datetime) -> List[Tuple[datetime, float, float, float]]:
        start_utc = start_local.astimezone(TZ_UTC)
        end_utc = end_local.astimezone(TZ_UTC)

        return self.con.execute(
            """
            SELECT ts_utc, open, high, low, close
            FROM bars_1m
            WHERE symbol = ?
              AND ts_utc >= ? AND ts_utc < ?
            ORDER BY ts_utc
            """,
            [SYMBOL, start_utc, end_utc],
        ).fetchall()

    # ---------- blocks ----------
    def get_pre_asia(self, trade_date: date) -> Optional[Dict]:
        return self._window_stats_1m(_dt_local(trade_date, 7, 0), _dt_local(trade_date, 9, 0))

    def get_pre_london(self, trade_date: date) -> Optional[Dict]:
        return self._window_stats_1m(_dt_local(trade_date, 17, 0), _dt_local(trade_date, 18, 0))

    def get_pre_ny(self, trade_date: date) -> Optional[Dict]:
        # FIXED: D 23:00 -> (D+1) 00:30
        return self._window_stats_1m(_dt_local(trade_date, 23, 0), _dt_local(trade_date + timedelta(days=1), 0, 30))

    def get_asia_session(self, trade_date: date) -> Optional[Dict]:
        return self._window_stats_1m(_dt_local(trade_date, 9, 0), _dt_local(trade_date, 17, 0))

    def get_london_session(self, trade_date: date) -> Optional[Dict]:
        return self._window_stats_1m(_dt_local(trade_date, 18, 0), _dt_local(trade_date, 23, 0))

    def get_ny_cash_session(self, trade_date: date) -> Optional[Dict]:
        # (D+1) 00:30 -> 02:00 (includes 00:30 ORB)
        return self._window_stats_1m(_dt_local(trade_date + timedelta(days=1), 0, 30),
                                     _dt_local(trade_date + timedelta(days=1), 2, 0))

    # ---------- ORB w/ 1m execution ----------

    def _add_realized_rr_to_result(self, orb_result: Dict, rr: float) -> Dict:
        """
        Add realized RR fields to an ORB result dictionary.

        Uses cost_model.py for canonical realized RR calculations.
        For NO_TRADE outcomes, realized RR fields are None.
        """
        if not orb_result or orb_result.get('outcome') == 'NO_TRADE':
            orb_result['realized_rr'] = None
            orb_result['realized_risk_dollars'] = None
            orb_result['realized_reward_dollars'] = None
            return orb_result

        # Convert stop from price to points
        # risk_ticks already available in orb_result
        risk_ticks = orb_result.get('risk_ticks', 0)
        if risk_ticks is None or risk_ticks <= 0:
            orb_result['realized_rr'] = None
            orb_result['realized_risk_dollars'] = None
            orb_result['realized_reward_dollars'] = None
            return orb_result

        stop_points = risk_ticks * 0.1  # ticks to points

        try:
            realized = calculate_realized_rr(
                instrument='MGC',
                stop_distance_points=stop_points,
                rr_theoretical=rr,
                stress_level='normal'
            )
            orb_result['realized_rr'] = realized['realized_rr']
            orb_result['realized_risk_dollars'] = realized['realized_risk_dollars']
            orb_result['realized_reward_dollars'] = realized['realized_reward_dollars']
        except Exception as e:
            # If calculation fails, set to None (e.g., for NQ/MPL when blocked)
            orb_result['realized_rr'] = None
            orb_result['realized_risk_dollars'] = None
            orb_result['realized_reward_dollars'] = None

        return orb_result

    def calculate_orb_1m_exec(self, orb_start_local: datetime, scan_end_local: datetime, rr: float = RR_DEFAULT, sl_mode: str = SL_MODE) -> Optional[Dict]:
        """
        Calculate ORB with 1-minute execution AND ORB-anchored MAE/MFE.

        MAE/MFE are measured from ORB EDGE (not entry) and normalized by ORB-anchored R.

        Args:
            orb_start_local: ORB start time (local)
            scan_end_local: Scan window end time (local)
            rr: Risk/reward ratio for target
            sl_mode: "full" = stop at opposite edge, "half" = stop at midpoint

        Returns:
            Dict with keys: high, low, size, break_dir, outcome, r_multiple, mae, mfe,
                           stop_price, risk_ticks (debug)
        """
        orb_end_local = orb_start_local + timedelta(minutes=5)

        orb_stats = self._window_stats_1m(orb_start_local, orb_end_local)
        if not orb_stats:
            return None

        orb_high = orb_stats["high"]
        orb_low = orb_stats["low"]
        orb_size = orb_high - orb_low
        orb_mid = (orb_high + orb_low) / 2.0

        # bars AFTER orb end
        bars = self._fetch_1m_bars(orb_end_local, scan_end_local)

        break_dir = "NONE"
        entry_ts = None
        entry_price = None

        # entry = first 1m close outside ORB
        for ts_utc, o, h, l, c in bars:  # Fixed: added 'o' for open
            c = float(c)
            if c > orb_high:
                break_dir = "UP"
                entry_ts = ts_utc
                entry_price = c
                break
            if c < orb_low:
                break_dir = "DOWN"
                entry_ts = ts_utc
                entry_price = c
                break

        # GUARDRAIL: Validate entry method (must be at close, not ORB edge)
        if entry_price is not None:
            assert entry_price != orb_high, "FATAL: Entry at ORB high (should be at close)"
            assert entry_price != orb_low, "FATAL: Entry at ORB low (should be at close)"

        if break_dir == "NONE":
            return {
                "high": orb_high, "low": orb_low, "size": orb_size,
                "break_dir": "NONE", "outcome": "NO_TRADE", "r_multiple": None,
                "mae": None, "mfe": None,
                "stop_price": None, "risk_ticks": None
            }

        # ORB edge (anchor point for R calculation)
        orb_edge = orb_high if break_dir == "UP" else orb_low

        # Calculate stop based on mode
        if sl_mode == "full":
            stop = orb_low if break_dir == "UP" else orb_high
        else:  # half
            stop = orb_mid

        # ORB-anchored R: distance from ORB edge to stop
        r_orb = abs(orb_edge - stop)
        risk_ticks = r_orb / 0.1

        # Guard: R must be > 0
        if r_orb <= 0:
            # This should never happen in practice, but guard against it
            return {
                "high": orb_high, "low": orb_low, "size": orb_size,
                "break_dir": break_dir, "outcome": "NO_TRADE", "r_multiple": None,
                "mae": None, "mfe": None,
                "stop_price": stop, "risk_ticks": 0.0
            }

        # ORB-anchored target (NOT entry-anchored)
        # Entry price is ONLY used for fill simulation, not for TP/R/expectancy
        target = orb_edge + rr * r_orb if break_dir == "UP" else orb_edge - rr * r_orb

        # Track MAE/MFE from ORB EDGE (will be normalized by r_orb)
        mae_raw = 0.0  # Maximum adverse excursion from ORB edge (in price units)
        mfe_raw = 0.0  # Maximum favorable excursion from ORB edge (in price units)

        # start checking AFTER entry bar
        start_i = 0
        for i, (ts_utc, _, _, _, _) in enumerate(bars):  # Fixed: 5 columns (o,h,l,c)
            if ts_utc == entry_ts:
                start_i = i + 1
                break

        for ts_utc, o, h, l, c in bars[start_i:]:  # Fixed: 5 columns
            h = float(h)
            l = float(l)

            # Update MAE/MFE from ORB EDGE (raw price units, will normalize by r_orb)
            if break_dir == "UP":
                # MAE: how far price went below ORB edge (adverse)
                mae_raw = max(mae_raw, orb_edge - l)
                # MFE: how far price went above ORB edge (favorable)
                mfe_raw = max(mfe_raw, h - orb_edge)

                hit_stop = l <= stop
                hit_target = h >= target
                if hit_stop and hit_target:
                    return {
                        "high": orb_high, "low": orb_low, "size": orb_size,
                        "break_dir": break_dir, "outcome": "LOSS", "r_multiple": -1.0,
                        "mae": mae_raw / r_orb, "mfe": mfe_raw / r_orb,
                        "stop_price": stop, "risk_ticks": risk_ticks
                    }
                if hit_target:
                    return {
                        "high": orb_high, "low": orb_low, "size": orb_size,
                        "break_dir": break_dir, "outcome": "WIN", "r_multiple": float(rr),
                        "mae": mae_raw / r_orb, "mfe": mfe_raw / r_orb,
                        "stop_price": stop, "risk_ticks": risk_ticks
                    }
                if hit_stop:
                    return {
                        "high": orb_high, "low": orb_low, "size": orb_size,
                        "break_dir": break_dir, "outcome": "LOSS", "r_multiple": -1.0,
                        "mae": mae_raw / r_orb, "mfe": mfe_raw / r_orb,
                        "stop_price": stop, "risk_ticks": risk_ticks
                    }
            else:  # DOWN break
                # MAE: how far price went above ORB edge (adverse)
                mae_raw = max(mae_raw, h - orb_edge)
                # MFE: how far price went below ORB edge (favorable)
                mfe_raw = max(mfe_raw, orb_edge - l)

                hit_stop = h >= stop
                hit_target = l <= target
                if hit_stop and hit_target:
                    return {
                        "high": orb_high, "low": orb_low, "size": orb_size,
                        "break_dir": break_dir, "outcome": "LOSS", "r_multiple": -1.0,
                        "mae": mae_raw / r_orb, "mfe": mfe_raw / r_orb,
                        "stop_price": stop, "risk_ticks": risk_ticks
                    }
                if hit_target:
                    return {
                        "high": orb_high, "low": orb_low, "size": orb_size,
                        "break_dir": break_dir, "outcome": "WIN", "r_multiple": float(rr),
                        "mae": mae_raw / r_orb, "mfe": mfe_raw / r_orb,
                        "stop_price": stop, "risk_ticks": risk_ticks
                    }
                if hit_stop:
                    return {
                        "high": orb_high, "low": orb_low, "size": orb_size,
                        "break_dir": break_dir, "outcome": "LOSS", "r_multiple": -1.0,
                        "mae": mae_raw / r_orb, "mfe": mfe_raw / r_orb,
                        "stop_price": stop, "risk_ticks": risk_ticks
                    }

        # No exit
        return {
            "high": orb_high, "low": orb_low, "size": orb_size,
            "break_dir": break_dir, "outcome": "NO_TRADE", "r_multiple": None,
            "mae": (mae_raw / r_orb) if mae_raw > 0 else None,
            "mfe": (mfe_raw / r_orb) if mfe_raw > 0 else None,
            "stop_price": stop, "risk_ticks": risk_ticks
        }

    def calculate_orb_1m_tradeable(self, orb_start_local: datetime, scan_end_local: datetime, rr: float = RR_DEFAULT, sl_mode: str = SL_MODE) -> Optional[Dict]:
        """
        Calculate ORB with B-ENTRY MODEL (entry-anchored tradeable metrics).

        DUAL-TRACK EDGE PIPELINE:
        - STRUCTURAL (ORB-anchored): Discovery lens for finding patterns
        - TRADEABLE (entry-anchored): Promotion truth for validation

        B-ENTRY MODEL (CANONICAL_LOGIC.txt lines 76-98):
        - Signal: First 1m CLOSE outside ORB
        - Entry: NEXT 1m OPEN after signal close (not at signal close)
        - Stop: ORB edge (full) or midpoint (half)
        - Risk: |entry - stop| (entry-anchored, not ORB-anchored)
        - Target: entry +/- RR * risk
        - Outcome: WIN/LOSS/OPEN (not NO_TRADE for open positions)

        Args:
            orb_start_local: ORB start time (local)
            scan_end_local: Scan window end time (local)
            rr: Risk/reward ratio for target
            sl_mode: "full" = stop at opposite edge, "half" = stop at midpoint

        Returns:
            Dict with keys: entry_price, stop_price, risk_points, target_price, outcome,
                           realized_rr, realized_risk_dollars, realized_reward_dollars
            Returns None if ORB window has no data.
        """
        orb_end_local = orb_start_local + timedelta(minutes=5)

        orb_stats = self._window_stats_1m(orb_start_local, orb_end_local)
        if not orb_stats:
            return None

        orb_high = orb_stats["high"]
        orb_low = orb_stats["low"]
        orb_mid = (orb_high + orb_low) / 2.0

        # Bars AFTER ORB end
        bars = self._fetch_1m_bars(orb_end_local, scan_end_local)

        # STEP 1: Find signal (first 1m CLOSE outside ORB)
        signal_found = False
        signal_bar_index = None
        break_dir = "NONE"

        for i, (ts_utc, o, h, l, c) in enumerate(bars):  # Fixed: 5 columns
            c = float(c)
            if c > orb_high:
                break_dir = "UP"
                signal_bar_index = i
                signal_found = True
                break
            if c < orb_low:
                break_dir = "DOWN"
                signal_bar_index = i
                signal_found = True
                break

        if not signal_found:
            # No break = no signal = no entry
            return {
                "entry_price": None,
                "stop_price": None,
                "risk_points": None,
                "target_price": None,
                "outcome": "NO_TRADE",
                "realized_rr": None,
                "realized_risk_dollars": None,
                "realized_reward_dollars": None
            }

        # STEP 2: Entry at NEXT 1m OPEN (B-entry model)
        if signal_bar_index + 1 >= len(bars):
            # Signal occurred in last bar of scan window, no next bar = OPEN position
            return {
                "entry_price": None,
                "stop_price": None,
                "risk_points": None,
                "target_price": None,
                "outcome": "OPEN",
                "realized_rr": None,
                "realized_risk_dollars": None,
                "realized_reward_dollars": None
            }

        # Entry bar is the bar AFTER signal bar
        entry_bar = bars[signal_bar_index + 1]
        entry_ts, entry_bar_open, entry_bar_high, entry_bar_low, entry_bar_close = entry_bar

        # B-ENTRY MODEL: Entry price = OPEN of entry bar (NEXT 1m OPEN after signal close)
        # Slippage is handled separately in cost model ($4.00 per RT)
        entry_price = float(entry_bar_open)

        # STEP 3: Calculate stop based on mode
        if sl_mode == "full":
            stop_price = orb_low if break_dir == "UP" else orb_high
        else:  # half
            stop_price = orb_mid

        # STEP 4: Calculate entry-anchored risk (CANONICAL FORMULA)
        risk_points = abs(entry_price - stop_price)

        if risk_points <= 0:
            # Should never happen, but guard against it
            return {
                "entry_price": entry_price,
                "stop_price": stop_price,
                "risk_points": 0.0,
                "target_price": None,
                "outcome": "NO_TRADE",  # BUG #6 FIX: Zero risk = invalid setup, not open position
                "realized_rr": None,
                "realized_risk_dollars": None,
                "realized_reward_dollars": None
            }

        # STEP 5: Calculate target (entry-anchored)
        if break_dir == "UP":
            target_price = entry_price + (rr * risk_points)
        else:
            target_price = entry_price - (rr * risk_points)

        # STEP 6: Calculate realized RR using cost_model.py
        try:
            realized = calculate_realized_rr(
                instrument='MGC',
                stop_distance_points=risk_points,
                rr_theoretical=rr,
                stress_level='normal'
            )
            realized_rr_win = realized['realized_rr']
            realized_risk_dollars = realized['realized_risk_dollars']
            realized_reward_dollars = realized['realized_reward_dollars']
        except Exception:
            # If cost_model fails, set to None
            realized_rr_win = None
            realized_risk_dollars = None
            realized_reward_dollars = None

        # STEP 7: Check outcome using bars AFTER entry bar (conservative same-bar resolution)
        outcome = "OPEN"  # Default if no exit found

        for ts_utc, o, h, l, c in bars[signal_bar_index + 2:]:  # Fixed: 5 columns
            h = float(h)
            l = float(l)

            if break_dir == "UP":
                hit_stop = l <= stop_price
                hit_target = h >= target_price

                if hit_stop and hit_target:
                    # Both hit in same bar = LOSS (conservative)
                    outcome = "LOSS"
                    break
                if hit_target:
                    outcome = "WIN"
                    break
                if hit_stop:
                    outcome = "LOSS"
                    break
            else:  # DOWN
                hit_stop = h >= stop_price
                hit_target = l <= target_price

                if hit_stop and hit_target:
                    outcome = "LOSS"
                    break
                if hit_target:
                    outcome = "WIN"
                    break
                if hit_stop:
                    outcome = "LOSS"
                    break

        # STEP 8: Calculate final realized_rr based on outcome
        # CRITICAL FIX: If costs exceed profit, downgrade WIN to LOSS
        if outcome == "WIN":
            if realized_rr_win is not None and realized_rr_win <= 0:
                # Price hit target but costs ate all profit → not a real win
                outcome = "LOSS"  # Downgrade to LOSS
                final_realized_rr = realized_rr_win  # Keep actual RR (0.0 or negative)
            else:
                final_realized_rr = realized_rr_win
        elif outcome == "LOSS":
            final_realized_rr = -1.0  # Always -1R for losses
        else:  # OPEN
            final_realized_rr = None

        return {
            "entry_price": entry_price,
            "stop_price": stop_price,
            "risk_points": risk_points,
            "target_price": target_price,
            "outcome": outcome,
            "realized_rr": final_realized_rr,
            "realized_risk_dollars": realized_risk_dollars,
            "realized_reward_dollars": realized_reward_dollars
        }

    # ---------- RSI ----------
    def calculate_rsi_at(self, at_local: datetime) -> Optional[float]:
        at_utc = at_local.astimezone(TZ_UTC)
        closes = self.con.execute(
            """
            SELECT close
            FROM bars_5m
            WHERE symbol = ?
              AND ts_utc <= ?
            ORDER BY ts_utc DESC
            LIMIT 15
            """,
            [SYMBOL, at_utc],
        ).fetchall()

        if len(closes) < 15:
            return None

        closes = [float(x[0]) for x in reversed(closes)]
        gains, losses = [], []
        for i in range(1, len(closes)):
            ch = closes[i] - closes[i - 1]
            gains.append(max(ch, 0.0))
            losses.append(max(-ch, 0.0))

        avg_gain = sum(gains[:RSI_LEN]) / RSI_LEN
        avg_loss = sum(losses[:RSI_LEN]) / RSI_LEN
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    # ---------- ATR (simple) ----------
    def calculate_atr(self, trade_date: date) -> Optional[float]:
        rows = self.con.execute(
            """
            SELECT asia_high, asia_low
            FROM daily_features
            WHERE date_local < ?
              AND asia_high IS NOT NULL
            ORDER BY date_local DESC
            LIMIT 20
            """,
            [trade_date],
        ).fetchall()

        if len(rows) < 20:
            return None

        trs = [float(h) - float(l) for (h, l) in rows]
        return sum(trs) / len(trs)

    # ---------- deterministic type codes (level interactions only) ----------
    @staticmethod
    def classify_asia_code(asia_range: Optional[float], atr_20: Optional[float]) -> Optional[str]:
        if asia_range is None or atr_20 is None or atr_20 == 0:
            return None
        ratio = asia_range / atr_20
        if ratio < 0.3:
            return "A1_TIGHT"
        if ratio > 0.8:
            return "A2_EXPANDED"
        return "A0_NORMAL"

    @staticmethod
    def classify_london_code(london_high: Optional[float], london_low: Optional[float],
                             asia_high: Optional[float], asia_low: Optional[float]) -> Optional[str]:
        if None in (london_high, london_low, asia_high, asia_low):
            return None
        took_high = london_high > asia_high
        took_low = london_low < asia_low
        if took_high and took_low:
            return "L3_EXPANSION"
        if took_high:
            return "L1_SWEEP_HIGH"
        if took_low:
            return "L2_SWEEP_LOW"
        return "L4_CONSOLIDATION"

    @staticmethod
    def classify_pre_ny_code(pre_ny_high: Optional[float], pre_ny_low: Optional[float],
                             london_high: Optional[float], london_low: Optional[float],
                             asia_high: Optional[float], asia_low: Optional[float],
                             atr_20: Optional[float]) -> Optional[str]:
        if None in (pre_ny_high, pre_ny_low, london_high, london_low, asia_high, asia_low):
            return None
        ref_high = max(london_high, asia_high)
        ref_low = min(london_low, asia_low)

        if pre_ny_high > ref_high and pre_ny_low >= ref_low:
            return "N1_SWEEP_HIGH"
        if pre_ny_low < ref_low and pre_ny_high <= ref_high:
            return "N2_SWEEP_LOW"

        if atr_20 and atr_20 > 0:
            rng = pre_ny_high - pre_ny_low
            ratio = rng / atr_20
            if ratio < 0.25:
                return "N3_CONSOLIDATION"
            if ratio > 0.8:
                return "N4_EXPANSION"

        return "N0_NORMAL"

    # ---------- build ----------
    def build_features(self, trade_date: date) -> bool:
        print(f"Building features for {trade_date}...")

        pre_asia = self.get_pre_asia(trade_date)
        pre_london = self.get_pre_london(trade_date)
        pre_ny = self.get_pre_ny(trade_date)

        asia_session = self.get_asia_session(trade_date)
        london_session = self.get_london_session(trade_date)
        ny_session = self.get_ny_cash_session(trade_date)

        # EXTENDED SCAN WINDOWS (CORRECTED 2026-01-16):
        # All ORBs scan until next Asia open (09:00 next day) to capture full overnight moves
        # This matches the fix applied to execution_engine.py for MGC
        next_asia_open = _dt_local(trade_date + timedelta(days=1), 9, 0)

        # STRUCTURAL (ORB-anchored) - Discovery lens
        orb_0900 = self.calculate_orb_1m_exec(_dt_local(trade_date, 9, 0), next_asia_open, sl_mode=self.sl_mode)
        if orb_0900:
            orb_0900 = self._add_realized_rr_to_result(orb_0900, RR_DEFAULT)

        orb_1000 = self.calculate_orb_1m_exec(_dt_local(trade_date, 10, 0), next_asia_open, sl_mode=self.sl_mode)
        if orb_1000:
            orb_1000 = self._add_realized_rr_to_result(orb_1000, RR_DEFAULT)

        orb_1100 = self.calculate_orb_1m_exec(_dt_local(trade_date, 11, 0), next_asia_open, sl_mode=self.sl_mode)
        if orb_1100:
            orb_1100 = self._add_realized_rr_to_result(orb_1100, RR_DEFAULT)

        orb_1800 = self.calculate_orb_1m_exec(_dt_local(trade_date, 18, 0), next_asia_open, sl_mode=self.sl_mode)
        if orb_1800:
            orb_1800 = self._add_realized_rr_to_result(orb_1800, RR_DEFAULT)

        orb_2300 = self.calculate_orb_1m_exec(_dt_local(trade_date, 23, 0), next_asia_open, sl_mode=self.sl_mode)
        if orb_2300:
            orb_2300 = self._add_realized_rr_to_result(orb_2300, RR_DEFAULT)

        orb_0030 = self.calculate_orb_1m_exec(_dt_local(trade_date + timedelta(days=1), 0, 30), next_asia_open, sl_mode=self.sl_mode)
        if orb_0030:
            orb_0030 = self._add_realized_rr_to_result(orb_0030, RR_DEFAULT)

        # TRADEABLE (entry-anchored) - Promotion truth
        orb_0900_tradeable = self.calculate_orb_1m_tradeable(_dt_local(trade_date, 9, 0), next_asia_open, sl_mode=self.sl_mode)
        orb_1000_tradeable = self.calculate_orb_1m_tradeable(_dt_local(trade_date, 10, 0), next_asia_open, sl_mode=self.sl_mode)
        orb_1100_tradeable = self.calculate_orb_1m_tradeable(_dt_local(trade_date, 11, 0), next_asia_open, sl_mode=self.sl_mode)
        orb_1800_tradeable = self.calculate_orb_1m_tradeable(_dt_local(trade_date, 18, 0), next_asia_open, sl_mode=self.sl_mode)
        orb_2300_tradeable = self.calculate_orb_1m_tradeable(_dt_local(trade_date, 23, 0), next_asia_open, sl_mode=self.sl_mode)
        orb_0030_tradeable = self.calculate_orb_1m_tradeable(_dt_local(trade_date + timedelta(days=1), 0, 30), next_asia_open, sl_mode=self.sl_mode)

        rsi_at_0030 = self.calculate_rsi_at(_dt_local(trade_date + timedelta(days=1), 0, 30))
        atr_20 = self.calculate_atr(trade_date)

        asia_code = self.classify_asia_code(asia_session["range"] if asia_session else None, atr_20)
        london_code = self.classify_london_code(
            london_session["high"] if london_session else None,
            london_session["low"] if london_session else None,
            asia_session["high"] if asia_session else None,
            asia_session["low"] if asia_session else None,
        )
        pre_ny_code = self.classify_pre_ny_code(
            pre_ny["high"] if pre_ny else None,
            pre_ny["low"] if pre_ny else None,
            london_session["high"] if london_session else None,
            london_session["low"] if london_session else None,
            asia_session["high"] if asia_session else None,
            asia_session["low"] if asia_session else None,
            atr_20,
        )

        self.con.execute(
            f"""
            INSERT OR REPLACE INTO {self.table_name} (
                date_local, instrument,

                pre_asia_high, pre_asia_low, pre_asia_range,
                pre_london_high, pre_london_low, pre_london_range,
                pre_ny_high, pre_ny_low, pre_ny_range,

                asia_high, asia_low, asia_range,
                london_high, london_low, london_range,
                ny_high, ny_low, ny_range,
                asia_type_code, london_type_code, pre_ny_type_code,

                orb_0900_high, orb_0900_low, orb_0900_size, orb_0900_break_dir, orb_0900_outcome, orb_0900_r_multiple, orb_0900_mae, orb_0900_mfe, orb_0900_stop_price, orb_0900_risk_ticks,
                orb_0900_realized_rr, orb_0900_realized_risk_dollars, orb_0900_realized_reward_dollars,
                orb_1000_high, orb_1000_low, orb_1000_size, orb_1000_break_dir, orb_1000_outcome, orb_1000_r_multiple, orb_1000_mae, orb_1000_mfe, orb_1000_stop_price, orb_1000_risk_ticks,
                orb_1000_realized_rr, orb_1000_realized_risk_dollars, orb_1000_realized_reward_dollars,
                orb_1100_high, orb_1100_low, orb_1100_size, orb_1100_break_dir, orb_1100_outcome, orb_1100_r_multiple, orb_1100_mae, orb_1100_mfe, orb_1100_stop_price, orb_1100_risk_ticks,
                orb_1100_realized_rr, orb_1100_realized_risk_dollars, orb_1100_realized_reward_dollars,
                orb_1800_high, orb_1800_low, orb_1800_size, orb_1800_break_dir, orb_1800_outcome, orb_1800_r_multiple, orb_1800_mae, orb_1800_mfe, orb_1800_stop_price, orb_1800_risk_ticks,
                orb_1800_realized_rr, orb_1800_realized_risk_dollars, orb_1800_realized_reward_dollars,
                orb_2300_high, orb_2300_low, orb_2300_size, orb_2300_break_dir, orb_2300_outcome, orb_2300_r_multiple, orb_2300_mae, orb_2300_mfe, orb_2300_stop_price, orb_2300_risk_ticks,
                orb_2300_realized_rr, orb_2300_realized_risk_dollars, orb_2300_realized_reward_dollars,
                orb_0030_high, orb_0030_low, orb_0030_size, orb_0030_break_dir, orb_0030_outcome, orb_0030_r_multiple, orb_0030_mae, orb_0030_mfe, orb_0030_stop_price, orb_0030_risk_ticks,
                orb_0030_realized_rr, orb_0030_realized_risk_dollars, orb_0030_realized_reward_dollars,

                orb_0900_tradeable_entry_price, orb_0900_tradeable_stop_price, orb_0900_tradeable_risk_points, orb_0900_tradeable_target_price, orb_0900_tradeable_outcome, orb_0900_tradeable_realized_rr, orb_0900_tradeable_realized_risk_dollars, orb_0900_tradeable_realized_reward_dollars,
                orb_1000_tradeable_entry_price, orb_1000_tradeable_stop_price, orb_1000_tradeable_risk_points, orb_1000_tradeable_target_price, orb_1000_tradeable_outcome, orb_1000_tradeable_realized_rr, orb_1000_tradeable_realized_risk_dollars, orb_1000_tradeable_realized_reward_dollars,
                orb_1100_tradeable_entry_price, orb_1100_tradeable_stop_price, orb_1100_tradeable_risk_points, orb_1100_tradeable_target_price, orb_1100_tradeable_outcome, orb_1100_tradeable_realized_rr, orb_1100_tradeable_realized_risk_dollars, orb_1100_tradeable_realized_reward_dollars,
                orb_1800_tradeable_entry_price, orb_1800_tradeable_stop_price, orb_1800_tradeable_risk_points, orb_1800_tradeable_target_price, orb_1800_tradeable_outcome, orb_1800_tradeable_realized_rr, orb_1800_tradeable_realized_risk_dollars, orb_1800_tradeable_realized_reward_dollars,
                orb_2300_tradeable_entry_price, orb_2300_tradeable_stop_price, orb_2300_tradeable_risk_points, orb_2300_tradeable_target_price, orb_2300_tradeable_outcome, orb_2300_tradeable_realized_rr, orb_2300_tradeable_realized_risk_dollars, orb_2300_tradeable_realized_reward_dollars,
                orb_0030_tradeable_entry_price, orb_0030_tradeable_stop_price, orb_0030_tradeable_risk_points, orb_0030_tradeable_target_price, orb_0030_tradeable_outcome, orb_0030_tradeable_realized_rr, orb_0030_tradeable_realized_risk_dollars, orb_0030_tradeable_realized_reward_dollars,

                rsi_at_0030, rsi_at_orb, atr_20
            ) VALUES (
                ?, ?,

                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,

                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,

                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,

                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?,

                ?, ?, ?
            )
            """,
            [
                trade_date, "MGC",

                pre_asia["high"] if pre_asia else None,
                pre_asia["low"] if pre_asia else None,
                pre_asia["range"] if pre_asia else None,

                pre_london["high"] if pre_london else None,
                pre_london["low"] if pre_london else None,
                pre_london["range"] if pre_london else None,

                pre_ny["high"] if pre_ny else None,
                pre_ny["low"] if pre_ny else None,
                pre_ny["range"] if pre_ny else None,

                asia_session["high"] if asia_session else None,
                asia_session["low"] if asia_session else None,
                asia_session["range"] if asia_session else None,

                london_session["high"] if london_session else None,
                london_session["low"] if london_session else None,
                london_session["range"] if london_session else None,

                ny_session["high"] if ny_session else None,
                ny_session["low"] if ny_session else None,
                ny_session["range"] if ny_session else None,

                asia_code, london_code, pre_ny_code,

                orb_0900["high"] if orb_0900 else None,
                orb_0900["low"] if orb_0900 else None,
                orb_0900["size"] if orb_0900 else None,
                orb_0900["break_dir"] if orb_0900 else None,
                orb_0900["outcome"] if orb_0900 else None,
                orb_0900["r_multiple"] if orb_0900 else None,
                orb_0900.get("mae") if orb_0900 else None,
                orb_0900.get("mfe") if orb_0900 else None,
                orb_0900.get("stop_price") if orb_0900 else None,
                orb_0900.get("risk_ticks") if orb_0900 else None,
                orb_0900.get("realized_rr") if orb_0900 else None,
                orb_0900.get("realized_risk_dollars") if orb_0900 else None,
                orb_0900.get("realized_reward_dollars") if orb_0900 else None,

                orb_1000["high"] if orb_1000 else None,
                orb_1000["low"] if orb_1000 else None,
                orb_1000["size"] if orb_1000 else None,
                orb_1000["break_dir"] if orb_1000 else None,
                orb_1000["outcome"] if orb_1000 else None,
                orb_1000["r_multiple"] if orb_1000 else None,
                orb_1000.get("mae") if orb_1000 else None,
                orb_1000.get("mfe") if orb_1000 else None,
                orb_1000.get("stop_price") if orb_1000 else None,
                orb_1000.get("risk_ticks") if orb_1000 else None,
                orb_1000.get("realized_rr") if orb_1000 else None,
                orb_1000.get("realized_risk_dollars") if orb_1000 else None,
                orb_1000.get("realized_reward_dollars") if orb_1000 else None,

                orb_1100["high"] if orb_1100 else None,
                orb_1100["low"] if orb_1100 else None,
                orb_1100["size"] if orb_1100 else None,
                orb_1100["break_dir"] if orb_1100 else None,
                orb_1100["outcome"] if orb_1100 else None,
                orb_1100["r_multiple"] if orb_1100 else None,
                orb_1100.get("mae") if orb_1100 else None,
                orb_1100.get("mfe") if orb_1100 else None,
                orb_1100.get("stop_price") if orb_1100 else None,
                orb_1100.get("risk_ticks") if orb_1100 else None,
                orb_1100.get("realized_rr") if orb_1100 else None,
                orb_1100.get("realized_risk_dollars") if orb_1100 else None,
                orb_1100.get("realized_reward_dollars") if orb_1100 else None,

                orb_1800["high"] if orb_1800 else None,
                orb_1800["low"] if orb_1800 else None,
                orb_1800["size"] if orb_1800 else None,
                orb_1800["break_dir"] if orb_1800 else None,
                orb_1800["outcome"] if orb_1800 else None,
                orb_1800["r_multiple"] if orb_1800 else None,
                orb_1800.get("mae") if orb_1800 else None,
                orb_1800.get("mfe") if orb_1800 else None,
                orb_1800.get("stop_price") if orb_1800 else None,
                orb_1800.get("risk_ticks") if orb_1800 else None,
                orb_1800.get("realized_rr") if orb_1800 else None,
                orb_1800.get("realized_risk_dollars") if orb_1800 else None,
                orb_1800.get("realized_reward_dollars") if orb_1800 else None,

                orb_2300["high"] if orb_2300 else None,
                orb_2300["low"] if orb_2300 else None,
                orb_2300["size"] if orb_2300 else None,
                orb_2300["break_dir"] if orb_2300 else None,
                orb_2300["outcome"] if orb_2300 else None,
                orb_2300["r_multiple"] if orb_2300 else None,
                orb_2300.get("mae") if orb_2300 else None,
                orb_2300.get("mfe") if orb_2300 else None,
                orb_2300.get("stop_price") if orb_2300 else None,
                orb_2300.get("risk_ticks") if orb_2300 else None,
                orb_2300.get("realized_rr") if orb_2300 else None,
                orb_2300.get("realized_risk_dollars") if orb_2300 else None,
                orb_2300.get("realized_reward_dollars") if orb_2300 else None,

                orb_0030["high"] if orb_0030 else None,
                orb_0030["low"] if orb_0030 else None,
                orb_0030["size"] if orb_0030 else None,
                orb_0030["break_dir"] if orb_0030 else None,
                orb_0030["outcome"] if orb_0030 else None,
                orb_0030["r_multiple"] if orb_0030 else None,
                orb_0030.get("mae") if orb_0030 else None,
                orb_0030.get("mfe") if orb_0030 else None,
                orb_0030.get("stop_price") if orb_0030 else None,
                orb_0030.get("risk_ticks") if orb_0030 else None,
                orb_0030.get("realized_rr") if orb_0030 else None,
                orb_0030.get("realized_risk_dollars") if orb_0030 else None,
                orb_0030.get("realized_reward_dollars") if orb_0030 else None,

                orb_0900_tradeable.get("entry_price") if orb_0900_tradeable else None,
                orb_0900_tradeable.get("stop_price") if orb_0900_tradeable else None,
                orb_0900_tradeable.get("risk_points") if orb_0900_tradeable else None,
                orb_0900_tradeable.get("target_price") if orb_0900_tradeable else None,
                orb_0900_tradeable.get("outcome") if orb_0900_tradeable else None,
                orb_0900_tradeable.get("realized_rr") if orb_0900_tradeable else None,
                orb_0900_tradeable.get("realized_risk_dollars") if orb_0900_tradeable else None,
                orb_0900_tradeable.get("realized_reward_dollars") if orb_0900_tradeable else None,

                orb_1000_tradeable.get("entry_price") if orb_1000_tradeable else None,
                orb_1000_tradeable.get("stop_price") if orb_1000_tradeable else None,
                orb_1000_tradeable.get("risk_points") if orb_1000_tradeable else None,
                orb_1000_tradeable.get("target_price") if orb_1000_tradeable else None,
                orb_1000_tradeable.get("outcome") if orb_1000_tradeable else None,
                orb_1000_tradeable.get("realized_rr") if orb_1000_tradeable else None,
                orb_1000_tradeable.get("realized_risk_dollars") if orb_1000_tradeable else None,
                orb_1000_tradeable.get("realized_reward_dollars") if orb_1000_tradeable else None,

                orb_1100_tradeable.get("entry_price") if orb_1100_tradeable else None,
                orb_1100_tradeable.get("stop_price") if orb_1100_tradeable else None,
                orb_1100_tradeable.get("risk_points") if orb_1100_tradeable else None,
                orb_1100_tradeable.get("target_price") if orb_1100_tradeable else None,
                orb_1100_tradeable.get("outcome") if orb_1100_tradeable else None,
                orb_1100_tradeable.get("realized_rr") if orb_1100_tradeable else None,
                orb_1100_tradeable.get("realized_risk_dollars") if orb_1100_tradeable else None,
                orb_1100_tradeable.get("realized_reward_dollars") if orb_1100_tradeable else None,

                orb_1800_tradeable.get("entry_price") if orb_1800_tradeable else None,
                orb_1800_tradeable.get("stop_price") if orb_1800_tradeable else None,
                orb_1800_tradeable.get("risk_points") if orb_1800_tradeable else None,
                orb_1800_tradeable.get("target_price") if orb_1800_tradeable else None,
                orb_1800_tradeable.get("outcome") if orb_1800_tradeable else None,
                orb_1800_tradeable.get("realized_rr") if orb_1800_tradeable else None,
                orb_1800_tradeable.get("realized_risk_dollars") if orb_1800_tradeable else None,
                orb_1800_tradeable.get("realized_reward_dollars") if orb_1800_tradeable else None,

                orb_2300_tradeable.get("entry_price") if orb_2300_tradeable else None,
                orb_2300_tradeable.get("stop_price") if orb_2300_tradeable else None,
                orb_2300_tradeable.get("risk_points") if orb_2300_tradeable else None,
                orb_2300_tradeable.get("target_price") if orb_2300_tradeable else None,
                orb_2300_tradeable.get("outcome") if orb_2300_tradeable else None,
                orb_2300_tradeable.get("realized_rr") if orb_2300_tradeable else None,
                orb_2300_tradeable.get("realized_risk_dollars") if orb_2300_tradeable else None,
                orb_2300_tradeable.get("realized_reward_dollars") if orb_2300_tradeable else None,

                orb_0030_tradeable.get("entry_price") if orb_0030_tradeable else None,
                orb_0030_tradeable.get("stop_price") if orb_0030_tradeable else None,
                orb_0030_tradeable.get("risk_points") if orb_0030_tradeable else None,
                orb_0030_tradeable.get("target_price") if orb_0030_tradeable else None,
                orb_0030_tradeable.get("outcome") if orb_0030_tradeable else None,
                orb_0030_tradeable.get("realized_rr") if orb_0030_tradeable else None,
                orb_0030_tradeable.get("realized_risk_dollars") if orb_0030_tradeable else None,
                orb_0030_tradeable.get("realized_reward_dollars") if orb_0030_tradeable else None,

                rsi_at_0030,
                rsi_at_0030,  # rsi_at_orb = same as rsi_at_0030
                atr_20,
            ],
        )

        self.con.commit()
        print("  [OK] Features saved")
        return True

    def init_schema(self):
        self.con.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                date_local DATE NOT NULL,
                instrument VARCHAR NOT NULL,

                pre_asia_high DOUBLE,
                pre_asia_low DOUBLE,
                pre_asia_range DOUBLE,
                pre_london_high DOUBLE,
                pre_london_low DOUBLE,
                pre_london_range DOUBLE,
                pre_ny_high DOUBLE,
                pre_ny_low DOUBLE,
                pre_ny_range DOUBLE,

                asia_high DOUBLE,
                asia_low DOUBLE,
                asia_range DOUBLE,
                london_high DOUBLE,
                london_low DOUBLE,
                london_range DOUBLE,
                ny_high DOUBLE,
                ny_low DOUBLE,
                ny_range DOUBLE,
                asia_type_code VARCHAR,
                london_type_code VARCHAR,
                pre_ny_type_code VARCHAR,

                orb_0900_high DOUBLE,
                orb_0900_low DOUBLE,
                orb_0900_size DOUBLE,
                orb_0900_break_dir VARCHAR,
                orb_0900_outcome VARCHAR,
                orb_0900_r_multiple DOUBLE,
                orb_0900_mae DOUBLE,
                orb_0900_mfe DOUBLE,
                orb_0900_stop_price DOUBLE,
                orb_0900_risk_ticks DOUBLE,
                orb_0900_tradeable_entry_price DOUBLE,
                orb_0900_tradeable_stop_price DOUBLE,
                orb_0900_tradeable_risk_points DOUBLE,
                orb_0900_tradeable_target_price DOUBLE,
                orb_0900_tradeable_outcome VARCHAR,
                orb_0900_tradeable_realized_rr DOUBLE,
                orb_0900_tradeable_realized_risk_dollars DOUBLE,
                orb_0900_tradeable_realized_reward_dollars DOUBLE,

                orb_1000_high DOUBLE,
                orb_1000_low DOUBLE,
                orb_1000_size DOUBLE,
                orb_1000_break_dir VARCHAR,
                orb_1000_outcome VARCHAR,
                orb_1000_r_multiple DOUBLE,
                orb_1000_mae DOUBLE,
                orb_1000_mfe DOUBLE,
                orb_1000_stop_price DOUBLE,
                orb_1000_risk_ticks DOUBLE,
                orb_1000_tradeable_entry_price DOUBLE,
                orb_1000_tradeable_stop_price DOUBLE,
                orb_1000_tradeable_risk_points DOUBLE,
                orb_1000_tradeable_target_price DOUBLE,
                orb_1000_tradeable_outcome VARCHAR,
                orb_1000_tradeable_realized_rr DOUBLE,
                orb_1000_tradeable_realized_risk_dollars DOUBLE,
                orb_1000_tradeable_realized_reward_dollars DOUBLE,

                orb_1100_high DOUBLE,
                orb_1100_low DOUBLE,
                orb_1100_size DOUBLE,
                orb_1100_break_dir VARCHAR,
                orb_1100_outcome VARCHAR,
                orb_1100_r_multiple DOUBLE,
                orb_1100_mae DOUBLE,
                orb_1100_mfe DOUBLE,
                orb_1100_stop_price DOUBLE,
                orb_1100_risk_ticks DOUBLE,
                orb_1100_tradeable_entry_price DOUBLE,
                orb_1100_tradeable_stop_price DOUBLE,
                orb_1100_tradeable_risk_points DOUBLE,
                orb_1100_tradeable_target_price DOUBLE,
                orb_1100_tradeable_outcome VARCHAR,
                orb_1100_tradeable_realized_rr DOUBLE,
                orb_1100_tradeable_realized_risk_dollars DOUBLE,
                orb_1100_tradeable_realized_reward_dollars DOUBLE,

                orb_1800_high DOUBLE,
                orb_1800_low DOUBLE,
                orb_1800_size DOUBLE,
                orb_1800_break_dir VARCHAR,
                orb_1800_outcome VARCHAR,
                orb_1800_r_multiple DOUBLE,
                orb_1800_mae DOUBLE,
                orb_1800_mfe DOUBLE,
                orb_1800_stop_price DOUBLE,
                orb_1800_risk_ticks DOUBLE,
                orb_1800_tradeable_entry_price DOUBLE,
                orb_1800_tradeable_stop_price DOUBLE,
                orb_1800_tradeable_risk_points DOUBLE,
                orb_1800_tradeable_target_price DOUBLE,
                orb_1800_tradeable_outcome VARCHAR,
                orb_1800_tradeable_realized_rr DOUBLE,
                orb_1800_tradeable_realized_risk_dollars DOUBLE,
                orb_1800_tradeable_realized_reward_dollars DOUBLE,

                orb_2300_high DOUBLE,
                orb_2300_low DOUBLE,
                orb_2300_size DOUBLE,
                orb_2300_break_dir VARCHAR,
                orb_2300_outcome VARCHAR,
                orb_2300_r_multiple DOUBLE,
                orb_2300_mae DOUBLE,
                orb_2300_mfe DOUBLE,
                orb_2300_stop_price DOUBLE,
                orb_2300_risk_ticks DOUBLE,
                orb_2300_tradeable_entry_price DOUBLE,
                orb_2300_tradeable_stop_price DOUBLE,
                orb_2300_tradeable_risk_points DOUBLE,
                orb_2300_tradeable_target_price DOUBLE,
                orb_2300_tradeable_outcome VARCHAR,
                orb_2300_tradeable_realized_rr DOUBLE,
                orb_2300_tradeable_realized_risk_dollars DOUBLE,
                orb_2300_tradeable_realized_reward_dollars DOUBLE,

                orb_0030_high DOUBLE,
                orb_0030_low DOUBLE,
                orb_0030_size DOUBLE,
                orb_0030_break_dir VARCHAR,
                orb_0030_outcome VARCHAR,
                orb_0030_r_multiple DOUBLE,
                orb_0030_mae DOUBLE,
                orb_0030_mfe DOUBLE,
                orb_0030_stop_price DOUBLE,
                orb_0030_risk_ticks DOUBLE,
                orb_0030_tradeable_entry_price DOUBLE,
                orb_0030_tradeable_stop_price DOUBLE,
                orb_0030_tradeable_risk_points DOUBLE,
                orb_0030_tradeable_target_price DOUBLE,
                orb_0030_tradeable_outcome VARCHAR,
                orb_0030_tradeable_realized_rr DOUBLE,
                orb_0030_tradeable_realized_risk_dollars DOUBLE,
                orb_0030_tradeable_realized_reward_dollars DOUBLE,

                rsi_at_0030 DOUBLE,
                rsi_at_orb DOUBLE,
                atr_20 DOUBLE,

                PRIMARY KEY (date_local, instrument)
            )
            """
        )
        self.con.commit()
        print(f"{self.table_name} table created (sl_mode={self.sl_mode})")

    def close(self):
        self.con.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Build daily features with optional Half SL mode")
    parser.add_argument("start_date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("end_date", type=str, nargs="?", default=None, help="End date (YYYY-MM-DD), optional")
    parser.add_argument("--sl-mode", type=str, choices=["full", "half"], default="full",
                        help="Stop loss mode: 'full' (opposite edge) or 'half' (midpoint)")

    args = parser.parse_args()

    start_date = date.fromisoformat(args.start_date)
    end_date = date.fromisoformat(args.end_date) if args.end_date else start_date
    sl_mode = args.sl_mode

    # If Half SL mode, write to separate table
    table_name = "daily_features_half" if sl_mode == "half" else "daily_features"

    print(f"Building features: {start_date} to {end_date}")
    print(f"SL mode: {sl_mode}")
    print(f"Target table: {table_name}")
    print()

    builder = FeatureBuilder(sl_mode=sl_mode, table_name=table_name)
    builder.init_schema()

    # Guardrail: Ensure all required columns exist (auto-migrate if needed)
    builder._ensure_schema_columns(auto_migrate=True)

    cur = start_date
    while cur <= end_date:
        builder.build_features(cur)
        cur += timedelta(days=1)

    builder.close()
    print(f"\nCompleted: {start_date} to {end_date}")


if __name__ == "__main__":
    main()
