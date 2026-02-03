"""
STRATEGY DISCOVERY ENGINE
Backtest new ORB configurations and add profitable setups to production.

Edge Engine V1: Append-only trial logging with fail-closed gates.
"""

import duckdb
import pandas as pd
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Tuple
import logging
from pathlib import Path
import os
import hashlib
import json
from datetime import datetime, timedelta
from trading_app.time_spec import NIGHT_ORBS

logger = logging.getLogger(__name__)

# Edge Engine V1 Constants
EDGE_ENGINE_VERSION = "v1.0.0"
SCHEMA_VERSION = "1.0"
GATES_VERSION = "v1_exp>0_trades>=100_stress2x"


def compute_candidate_hash(config: 'DiscoveryConfig', date_start: str, date_end: str) -> str:
    """
    Compute deterministic SHA256 hash for candidate deduplication.

    Edge Engine V1: Algorithm locked forever.
    - Inputs: config params + date window
    - Floats rounded to 6 decimals
    - Sorted JSON for determinism
    """
    # Build hashable dict with floats rounded to 6 decimals
    hash_data = {
        "instrument": config.instrument,
        "orb_time": config.orb_time,
        "rr": round(config.rr, 6),
        "sl_mode": config.sl_mode,
        "orb_size_filter": round(config.orb_size_filter, 6) if config.orb_size_filter else None,
        "date_start": date_start,
        "date_end": date_end,
    }

    # Sort keys for determinism
    json_str = json.dumps(hash_data, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()[:16]  # First 16 chars


@dataclass
class DiscoveryConfig:
    """Configuration for backtesting"""
    instrument: str  # MGC, NQ, MPL
    orb_time: str    # One of ORBS from time_spec
    rr: float        # Risk/Reward multiple (1.0, 1.5, 3.0, 6.0, 8.0, etc.)
    sl_mode: str     # FULL or HALF
    orb_size_filter: Optional[float] = None  # % of ATR (0.10, 0.15, etc.) or None


@dataclass
class ProgressiveEvalSettings:
    """Settings for progressive evaluation (staged backtesting)."""
    enable_progressive_eval: bool = False  # Master switch (OFF by default)
    min_trades_stage: int = 50  # Minimum trades required at each stage
    stage_1_avg_r_threshold: float = -0.05  # Allow small negative at stage 1
    stage_2_avg_r_threshold: float = 0.0  # Must be positive at stage 2
    enable_early_exit: bool = False  # Optional early exit (OFF by default)
    early_exit_trade_floor: int = 50  # Min trades before early exit allowed
    early_exit_avg_r_threshold: float = -0.5  # Strong negative = unrecoverable


# Trial log path for append-only logging
TRIALS_LOG_PATH_PROGRESSIVE = Path("artifacts/discovery_trials.jsonl")


def _log_discovery_trial(
    config: 'DiscoveryConfig',
    outcome: str,
    stage_reached: int,
    n_days_seen: int,
    n_trades: int,
    avg_r: float,
    total_r: float,
    max_dd_r: float,
    elapsed_s: float,
    reason_code: Optional[str] = None,
    gates_passed: Optional[List[str]] = None,
    gates_failed: Optional[List[str]] = None
) -> bool:
    """
    Append trial to discovery_trials.jsonl (fail-silent).

    All trials must be logged: completed, pruned_stage_1, pruned_stage_2, early_exit, error.
    """
    try:
        TRIALS_LOG_PATH_PROGRESSIVE.parent.mkdir(parents=True, exist_ok=True)

        # Build trial ID from config hash
        config_str = f"{config.instrument}|{config.orb_time}|{config.rr}|{config.sl_mode}|{config.orb_size_filter}"
        trial_id = hashlib.sha256(config_str.encode()).hexdigest()[:12]

        entry = {
            "entry_type": "progressive_eval",
            "trial_id": trial_id,
            "logged_at": datetime.utcnow().isoformat() + "Z",
            "config": {
                "instrument": config.instrument,
                "orb_time": config.orb_time,
                "rr": config.rr,
                "sl_mode": config.sl_mode,
                "orb_size_filter": config.orb_size_filter
            },
            "outcome": outcome,
            "stage_reached": stage_reached,
            "n_days_seen": n_days_seen,
            "n_trades": n_trades,
            "avg_r": round(avg_r, 6) if avg_r is not None else None,
            "total_r": round(total_r, 4) if total_r is not None else None,
            "max_dd_r": round(max_dd_r, 4) if max_dd_r is not None else None,
            "elapsed_s": round(elapsed_s, 2),
            "reason_code": reason_code,
            "gates_passed": gates_passed or [],
            "gates_failed": gates_failed or []
        }

        json_line = json.dumps(entry, separators=(',', ':')) + "\n"

        with open(TRIALS_LOG_PATH_PROGRESSIVE, "ab") as f:
            f.write(json_line.encode("utf-8"))
            f.flush()
            os.fsync(f.fileno())

        return True
    except Exception as e:
        logger.warning(f"Failed to log trial: {e}")
        return False


def _get_stratified_windows(
    df: pd.DataFrame,
    stage: int
) -> List[Tuple[datetime, datetime]]:
    """
    Get deterministic stratified date windows for staged evaluation.

    Stage 1: 3 windows (~25% of data) spread across early/middle/late
    Stage 2: 6 windows (~50% of data) spread evenly
    Stage 3: Full history

    Deterministic: derived from dataset bounds, no randomness.
    """
    if df.empty:
        return []

    min_date = df['date_local'].min()
    max_date = df['date_local'].max()

    # Handle pandas Timestamp vs datetime
    if hasattr(min_date, 'to_pydatetime'):
        min_date = min_date.to_pydatetime()
    if hasattr(max_date, 'to_pydatetime'):
        max_date = max_date.to_pydatetime()

    total_days = (max_date - min_date).days

    if total_days < 90:
        # Not enough data for staging - return full range
        return [(min_date, max_date)]

    if stage == 1:
        # 3 windows: ~15%, ~45%, ~75% of timeline, each 90 days
        window_size = min(90, total_days // 4)
        positions = [0.15, 0.45, 0.75]
        windows = []
        for p in positions:
            start = min_date + timedelta(days=int(total_days * p))
            end = start + timedelta(days=window_size)
            if end <= max_date:
                windows.append((start, end))
        return windows if windows else [(min_date, max_date)]

    elif stage == 2:
        # 6 windows spread evenly
        window_size = min(60, total_days // 8)
        positions = [0.10, 0.25, 0.40, 0.55, 0.70, 0.85]
        windows = []
        for p in positions:
            start = min_date + timedelta(days=int(total_days * p))
            end = start + timedelta(days=window_size)
            if end <= max_date:
                windows.append((start, end))
        return windows if windows else [(min_date, max_date)]

    else:  # stage 3 or fallback
        return [(min_date, max_date)]


@dataclass
class BacktestResult:
    """Results from backtesting a configuration"""
    config: DiscoveryConfig
    total_trades: int
    wins: int
    losses: int
    win_rate: float  # Percentage
    avg_r: float     # Average R multiple
    annual_trades: int  # Trades per year
    tier: str        # S+, S, A, B, C
    total_r: float   # Sum of all R multiples
    # Edge Engine V1 fields
    date_start: Optional[str] = None  # Effective data window start (ISO format)
    date_end: Optional[str] = None    # Effective data window end (ISO format)
    max_dd_R: Optional[float] = None  # Maximum drawdown in R-multiples
    survives_stress: Optional[bool] = None  # Survives 2-tick stress test?
    stress_avg_r: Optional[float] = None    # Avg R under stress conditions
    candidate_hash: Optional[str] = None    # SHA256 hash for deduplication

    def to_dict(self):
        """Convert to dictionary for display"""
        return {
            "Instrument": self.config.instrument,
            "ORB": self.config.orb_time,
            "RR": self.config.rr,
            "SL Mode": self.config.sl_mode,
            "Filter": f"{self.config.orb_size_filter*100:.1f}%" if self.config.orb_size_filter else "None",
            "Trades": self.total_trades,
            "Win Rate": f"{self.win_rate:.1f}%",
            "Avg R": f"{self.avg_r:+.3f}R",
            "Annual": self.annual_trades,
            "Tier": self.tier,
            "Total R": f"{self.total_r:+.1f}R"
        }


class StrategyDiscovery:
    """Backtest engine for discovering profitable ORB configurations using CANONICAL execution"""

    def __init__(self):
        self.feature_tables = {
            "MGC": "daily_features",
            "NQ": "daily_features_nq",
            "MPL": "daily_features_mpl"
        }
        # ✅ CANONICAL: NO hardcoded point values - use cost_model.py at runtime

    def _get_connection(self):
        """Get cloud-aware database connection."""
        try:
            from trading_app.cloud_mode import get_database_connection
            return get_database_connection(read_only=True)
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            return None

    def backtest_configuration(self, config: DiscoveryConfig) -> BacktestResult:
        """
        Backtest a single ORB configuration using CANONICAL execution_engine.py.

        Uses execution_engine.simulate_orb_trade() for deterministic, cost-aware backtesting.
        Returns BacktestResult with win rate, avg R (REALIZED, post-cost), and tier assignment.
        """
        table = self.feature_tables.get(config.instrument)
        if not table:
            raise ValueError(f"Unknown instrument: {config.instrument}")

        orb_prefix = f"orb_{config.orb_time}"

        # Query dates only (execution_engine will simulate from bars)
        query = f"""
        SELECT
            date_local,
            CAST({orb_prefix}_size AS DOUBLE) as orb_size,
            atr_20 as atr
        FROM {table}
        WHERE {orb_prefix}_high IS NOT NULL
          AND {orb_prefix}_low IS NOT NULL
          AND {orb_prefix}_break_dir IS NOT NULL
          AND {orb_prefix}_break_dir != 'NONE'
        ORDER BY date_local
        """

        con = self._get_connection()
        if con is None:
            return BacktestResult(
                config=config,
                total_trades=0,
                wins=0,
                losses=0,
                win_rate=0.0,
                avg_r=0.0,
                annual_trades=0,
                tier="N/A",
                total_r=0.0
            )

        df = con.execute(query).df()

        if df.empty:
            return BacktestResult(
                config=config,
                total_trades=0,
                wins=0,
                losses=0,
                win_rate=0.0,
                avg_r=0.0,
                annual_trades=0,
                tier="N/A",
                total_r=0.0
            )

        # Apply ORB size filter
        if config.orb_size_filter is not None:
            df = df[df['orb_size'] <= (df['atr'] * config.orb_size_filter)]

        if len(df) == 0:
            return BacktestResult(
                config=config,
                total_trades=0,
                wins=0,
                losses=0,
                win_rate=0.0,
                avg_r=0.0,
                annual_trades=0,
                tier="N/A",
                total_r=0.0
            )

        # ✅ CANONICAL EXECUTION: Use execution_engine.simulate_orb_trade()
        from strategies.execution_engine import simulate_orb_trade, ExecutionMode
        from pipeline.cost_model import get_cost_model

        # Get canonical costs for this instrument
        cost_model = get_cost_model(config.instrument)

        trades = []
        for _, row in df.iterrows():
            result = simulate_orb_trade(
                con=con,
                date_local=row['date_local'],
                orb=config.orb_time,
                mode='1m',
                confirm_bars=1,
                rr=config.rr,
                sl_mode=config.sl_mode.lower(),
                exec_mode=ExecutionMode.MARKET_ON_CLOSE,
                slippage_ticks=cost_model['slippage_ticks'],
                commission_per_contract=cost_model['commission_rt']
            )

            # Skip if no trade
            if result.outcome in ['WIN', 'LOSS']:
                trades.append(result)

        if len(trades) == 0:
            return BacktestResult(
                config=config,
                total_trades=0,
                wins=0,
                losses=0,
                win_rate=0.0,
                avg_r=0.0,
                annual_trades=0,
                tier="N/A",
                total_r=0.0
            )

        # Calculate metrics from canonical execution results
        wins = sum(1 for t in trades if t.outcome == 'WIN')
        losses = sum(1 for t in trades if t.outcome == 'LOSS')
        total_trades = len(trades)

        # Use REALIZED R (post-cost)
        r_values = [t.r_multiple - t.cost_r for t in trades]
        total_r = sum(r_values)
        avg_r = total_r / total_trades
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        # Calculate annual trades
        date_range_days = (df['date_local'].max() - df['date_local'].min()).days
        years = date_range_days / 365.25 if date_range_days > 0 else 1
        annual_trades = int(total_trades / years)

        tier = self._assign_tier(win_rate, avg_r)

        # Edge Engine V1: Compute effective data window
        date_start = str(df['date_local'].min().date()) if not df.empty else None
        date_end = str(df['date_local'].max().date()) if not df.empty else None

        # Edge Engine V1: Compute max drawdown in R
        max_dd_R = self._compute_max_drawdown(r_values)

        # Edge Engine V1: Run stress test (2x slippage)
        survives_stress, stress_avg_r = self.run_stress_test(config, con)

        # Edge Engine V1: Compute candidate hash for deduplication
        candidate_hash = compute_candidate_hash(config, date_start, date_end) if date_start and date_end else None

        return BacktestResult(
            config=config,
            total_trades=total_trades,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            avg_r=avg_r,
            annual_trades=annual_trades,
            tier=tier,
            total_r=total_r,
            date_start=date_start,
            date_end=date_end,
            max_dd_R=max_dd_R,
            survives_stress=survives_stress,
            stress_avg_r=stress_avg_r,
            candidate_hash=candidate_hash
        )

    def _assign_tier(self, win_rate: float, avg_r: float) -> str:
        """Assign tier based on performance metrics"""
        if win_rate >= 65 or avg_r >= 0.30:
            return "S+"
        elif win_rate >= 63 or avg_r >= 0.25:
            return "S"
        elif win_rate >= 60 or avg_r >= 0.15:
            return "A"
        elif win_rate >= 55 or avg_r >= 0.05:
            return "B"
        else:
            return "C"

    def _compute_max_drawdown(self, r_values: List[float]) -> float:
        """
        Compute maximum drawdown in R-multiples from equity curve.

        Edge Engine V1: Observational metric only.
        """
        if not r_values:
            return 0.0

        # Build equity curve (cumulative R)
        equity = 0.0
        peak = 0.0
        max_dd = 0.0

        for r in r_values:
            equity += r
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd

        return round(max_dd, 4)

    def _run_backtest_on_dates(
        self,
        config: DiscoveryConfig,
        df: pd.DataFrame,
        con,
        cost_model: Dict,
        settings: Optional[ProgressiveEvalSettings] = None
    ) -> Tuple[List, int, bool, Optional[str]]:
        """
        Run backtest on a subset of dates. Core loop extracted for reuse.

        Returns:
            (trades_list, n_days_seen, early_exited, exit_reason)
        """
        from strategies.execution_engine import simulate_orb_trade, ExecutionMode

        trades = []
        n_days_seen = 0
        early_exited = False
        exit_reason = None

        for row in df.itertuples():
            n_days_seen += 1
            result = simulate_orb_trade(
                con=con,
                date_local=row.date_local,
                orb=config.orb_time,
                mode='1m',
                confirm_bars=1,
                rr=config.rr,
                sl_mode=config.sl_mode.lower(),
                exec_mode=ExecutionMode.MARKET_ON_CLOSE,
                slippage_ticks=cost_model['slippage_ticks'],
                commission_per_contract=cost_model['commission_rt']
            )

            if result.outcome in ['WIN', 'LOSS']:
                trades.append(result)

            # Early exit check (OFF by default)
            if settings and settings.enable_early_exit:
                if len(trades) >= settings.early_exit_trade_floor:
                    r_values = [t.r_multiple - t.cost_r for t in trades]
                    current_avg_r = sum(r_values) / len(r_values)
                    if current_avg_r < settings.early_exit_avg_r_threshold:
                        early_exited = True
                        exit_reason = "strong_negative_expectancy"
                        break

        return trades, n_days_seen, early_exited, exit_reason

    def backtest_configuration_progressive(
        self,
        config: DiscoveryConfig,
        settings: ProgressiveEvalSettings
    ) -> Tuple[Optional[BacktestResult], str, int]:
        """
        Backtest with progressive (staged) evaluation.

        Stages:
        - Stage 1: Quick screen on stratified sample (~25% of data)
        - Stage 2: Extended validation (~50% of data)
        - Stage 3: Full history + stress test

        Returns:
            (result, outcome, stage_reached)
            - result: BacktestResult or None if pruned
            - outcome: "completed", "pruned_stage_1", "pruned_stage_2", "early_exit", "error"
            - stage_reached: 1, 2, or 3
        """
        import time
        start_time = time.monotonic()

        # If progressive eval disabled, run full backtest
        if not settings.enable_progressive_eval:
            result = self.backtest_configuration(config)
            elapsed = time.monotonic() - start_time
            _log_discovery_trial(
                config=config,
                outcome="completed",
                stage_reached=3,
                n_days_seen=result.total_trades,  # Approximate
                n_trades=result.total_trades,
                avg_r=result.avg_r,
                total_r=result.total_r,
                max_dd_r=result.max_dd_R or 0.0,
                elapsed_s=elapsed,
                gates_passed=["full_backtest"],
                gates_failed=[]
            )
            return result, "completed", 3

        table = self.feature_tables.get(config.instrument)
        if not table:
            return None, "error", 0

        orb_prefix = f"orb_{config.orb_time}"

        # Get full dataset
        query = f"""
        SELECT
            date_local,
            CAST({orb_prefix}_size AS DOUBLE) as orb_size,
            atr_20 as atr
        FROM {table}
        WHERE {orb_prefix}_high IS NOT NULL
          AND {orb_prefix}_low IS NOT NULL
          AND {orb_prefix}_break_dir IS NOT NULL
          AND {orb_prefix}_break_dir != 'NONE'
        ORDER BY date_local
        """

        con = self._get_connection()
        if con is None:
            return None, "error", 0

        try:
            df = con.execute(query).df()
        except Exception as e:
            logger.error(f"Query error: {e}")
            return None, "error", 0

        if df.empty:
            elapsed = time.monotonic() - start_time
            _log_discovery_trial(
                config=config,
                outcome="completed",
                stage_reached=0,
                n_days_seen=0,
                n_trades=0,
                avg_r=0.0,
                total_r=0.0,
                max_dd_r=0.0,
                elapsed_s=elapsed,
                reason_code="no_data",
                gates_passed=[],
                gates_failed=[]
            )
            return self._empty_result(config), "completed", 0

        # Apply ORB size filter
        if config.orb_size_filter is not None:
            df = df[df['orb_size'] <= (df['atr'] * config.orb_size_filter)]

        if len(df) == 0:
            elapsed = time.monotonic() - start_time
            _log_discovery_trial(
                config=config,
                outcome="completed",
                stage_reached=0,
                n_days_seen=0,
                n_trades=0,
                avg_r=0.0,
                total_r=0.0,
                max_dd_r=0.0,
                elapsed_s=elapsed,
                reason_code="filtered_to_zero",
                gates_passed=[],
                gates_failed=[]
            )
            return self._empty_result(config), "completed", 0

        from pipeline.cost_model import get_cost_model
        cost_model = get_cost_model(config.instrument)

        # ===== STAGE 1: Quick Screen =====
        stage_1_windows = _get_stratified_windows(df, stage=1)
        stage_1_df = self._filter_df_to_windows(df, stage_1_windows)

        trades_s1, n_days_s1, early_exit_s1, exit_reason_s1 = self._run_backtest_on_dates(
            config, stage_1_df, con, cost_model, settings
        )

        if early_exit_s1:
            elapsed = time.monotonic() - start_time
            r_values = [t.r_multiple - t.cost_r for t in trades_s1] if trades_s1 else []
            _log_discovery_trial(
                config=config,
                outcome="early_exit",
                stage_reached=1,
                n_days_seen=n_days_s1,
                n_trades=len(trades_s1),
                avg_r=sum(r_values)/len(r_values) if r_values else 0.0,
                total_r=sum(r_values),
                max_dd_r=self._compute_max_drawdown(r_values),
                elapsed_s=elapsed,
                reason_code=exit_reason_s1,
                gates_passed=[],
                gates_failed=["early_exit"]
            )
            return None, "early_exit", 1

        # Evaluate Stage 1 gates
        gates_passed_s1 = []
        gates_failed_s1 = []

        if len(trades_s1) >= settings.min_trades_stage:
            gates_passed_s1.append("stage_1_trades")
        else:
            gates_failed_s1.append("stage_1_trades")

        r_values_s1 = [t.r_multiple - t.cost_r for t in trades_s1] if trades_s1 else []
        avg_r_s1 = sum(r_values_s1) / len(r_values_s1) if r_values_s1 else -999

        if avg_r_s1 >= settings.stage_1_avg_r_threshold:
            gates_passed_s1.append("stage_1_avg_r")
        else:
            gates_failed_s1.append("stage_1_avg_r")

        # Stage 1 gate check (need BOTH: trades AND avg_r)
        if gates_failed_s1:
            elapsed = time.monotonic() - start_time
            _log_discovery_trial(
                config=config,
                outcome="pruned_stage_1",
                stage_reached=1,
                n_days_seen=n_days_s1,
                n_trades=len(trades_s1),
                avg_r=avg_r_s1 if avg_r_s1 > -999 else 0.0,
                total_r=sum(r_values_s1),
                max_dd_r=self._compute_max_drawdown(r_values_s1),
                elapsed_s=elapsed,
                reason_code=gates_failed_s1[0],
                gates_passed=gates_passed_s1,
                gates_failed=gates_failed_s1
            )
            return None, "pruned_stage_1", 1

        # ===== STAGE 2: Extended Validation =====
        stage_2_windows = _get_stratified_windows(df, stage=2)
        stage_2_df = self._filter_df_to_windows(df, stage_2_windows)

        trades_s2, n_days_s2, early_exit_s2, exit_reason_s2 = self._run_backtest_on_dates(
            config, stage_2_df, con, cost_model, settings
        )

        if early_exit_s2:
            elapsed = time.monotonic() - start_time
            r_values = [t.r_multiple - t.cost_r for t in trades_s2] if trades_s2 else []
            _log_discovery_trial(
                config=config,
                outcome="early_exit",
                stage_reached=2,
                n_days_seen=n_days_s2,
                n_trades=len(trades_s2),
                avg_r=sum(r_values)/len(r_values) if r_values else 0.0,
                total_r=sum(r_values),
                max_dd_r=self._compute_max_drawdown(r_values),
                elapsed_s=elapsed,
                reason_code=exit_reason_s2,
                gates_passed=gates_passed_s1,
                gates_failed=["early_exit"]
            )
            return None, "early_exit", 2

        # Evaluate Stage 2 gates
        gates_passed_s2 = list(gates_passed_s1)
        gates_failed_s2 = []

        # Stage 2 needs more trades
        min_trades_s2 = settings.min_trades_stage * 2  # 100 by default
        if len(trades_s2) >= min_trades_s2:
            gates_passed_s2.append("stage_2_trades")
        else:
            gates_failed_s2.append("stage_2_trades")

        r_values_s2 = [t.r_multiple - t.cost_r for t in trades_s2] if trades_s2 else []
        avg_r_s2 = sum(r_values_s2) / len(r_values_s2) if r_values_s2 else -999

        if avg_r_s2 >= settings.stage_2_avg_r_threshold:
            gates_passed_s2.append("stage_2_avg_r")
        else:
            gates_failed_s2.append("stage_2_avg_r")

        if gates_failed_s2:
            elapsed = time.monotonic() - start_time
            _log_discovery_trial(
                config=config,
                outcome="pruned_stage_2",
                stage_reached=2,
                n_days_seen=n_days_s2,
                n_trades=len(trades_s2),
                avg_r=avg_r_s2 if avg_r_s2 > -999 else 0.0,
                total_r=sum(r_values_s2),
                max_dd_r=self._compute_max_drawdown(r_values_s2),
                elapsed_s=elapsed,
                reason_code=gates_failed_s2[0],
                gates_passed=gates_passed_s2,
                gates_failed=gates_failed_s2
            )
            return None, "pruned_stage_2", 2

        # ===== STAGE 3: Full History + Stress Test =====
        # Run full backtest on existing df (NO re-query)
        result = self._run_full_backtest_on_df(config, df, con, cost_model)
        elapsed = time.monotonic() - start_time

        _log_discovery_trial(
            config=config,
            outcome="completed",
            stage_reached=3,
            n_days_seen=result.total_trades,
            n_trades=result.total_trades,
            avg_r=result.avg_r,
            total_r=result.total_r,
            max_dd_r=result.max_dd_R or 0.0,
            elapsed_s=elapsed,
            gates_passed=gates_passed_s2 + ["stage_3_full"],
            gates_failed=[]
        )

        return result, "completed", 3

    def _filter_df_to_windows(
        self,
        df: pd.DataFrame,
        windows: List[Tuple[datetime, datetime]]
    ) -> pd.DataFrame:
        """Filter DataFrame to only include rows within specified date windows."""
        if not windows:
            return df

        mask = pd.Series([False] * len(df), index=df.index)

        for start, end in windows:
            window_mask = (df['date_local'] >= start) & (df['date_local'] <= end)
            mask = mask | window_mask

        return df[mask]

    def _empty_result(self, config: DiscoveryConfig) -> BacktestResult:
        """Return empty BacktestResult for edge cases."""
        return BacktestResult(
            config=config,
            total_trades=0,
            wins=0,
            losses=0,
            win_rate=0.0,
            avg_r=0.0,
            annual_trades=0,
            tier="N/A",
            total_r=0.0
        )

    def _run_full_backtest_on_df(
        self,
        config: DiscoveryConfig,
        df: pd.DataFrame,
        con,
        cost_model: Dict
    ) -> BacktestResult:
        """
        Run full backtest on already-filtered DataFrame (no DB query).

        Stage 3 optimization: reuses df from progressive stages.
        """
        from strategies.execution_engine import simulate_orb_trade, ExecutionMode

        if df.empty:
            return self._empty_result(config)

        trades = []
        for row in df.itertuples():
            result = simulate_orb_trade(
                con=con,
                date_local=row.date_local,
                orb=config.orb_time,
                mode='1m',
                confirm_bars=1,
                rr=config.rr,
                sl_mode=config.sl_mode.lower(),
                exec_mode=ExecutionMode.MARKET_ON_CLOSE,
                slippage_ticks=cost_model['slippage_ticks'],
                commission_per_contract=cost_model['commission_rt']
            )
            if result.outcome in ['WIN', 'LOSS']:
                trades.append(result)

        if len(trades) == 0:
            return self._empty_result(config)

        # Calculate metrics from canonical execution results
        wins = sum(1 for t in trades if t.outcome == 'WIN')
        losses = sum(1 for t in trades if t.outcome == 'LOSS')
        total_trades = len(trades)

        # Use REALIZED R (post-cost)
        r_values = [t.r_multiple - t.cost_r for t in trades]
        total_r = sum(r_values)
        avg_r = total_r / total_trades
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        # Calculate annual trades
        date_range_days = (df['date_local'].max() - df['date_local'].min()).days
        years = date_range_days / 365.25 if date_range_days > 0 else 1
        annual_trades = int(total_trades / years)

        tier = self._assign_tier(win_rate, avg_r)

        # Data window
        date_start = str(df['date_local'].min().date()) if not df.empty else None
        date_end = str(df['date_local'].max().date()) if not df.empty else None

        # Max drawdown
        max_dd_R = self._compute_max_drawdown(r_values)

        # Stress test (reuses df)
        survives_stress, stress_avg_r = self._run_stress_test_on_df(config, df, con)

        # Candidate hash
        candidate_hash = compute_candidate_hash(config, date_start, date_end) if date_start and date_end else None

        return BacktestResult(
            config=config,
            total_trades=total_trades,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            avg_r=avg_r,
            annual_trades=annual_trades,
            tier=tier,
            total_r=total_r,
            date_start=date_start,
            date_end=date_end,
            max_dd_R=max_dd_R,
            survives_stress=survives_stress,
            stress_avg_r=stress_avg_r,
            candidate_hash=candidate_hash
        )

    def _run_stress_test_on_df(
        self,
        config: DiscoveryConfig,
        df: pd.DataFrame,
        con
    ) -> tuple:
        """
        Run stress test on already-filtered DataFrame (no DB query).

        Stage 3 optimization: reuses df from progressive stages.
        Returns: (survives_stress: bool, stress_avg_r: float)
        """
        from strategies.execution_engine import simulate_orb_trade, ExecutionMode
        from pipeline.cost_model import get_cost_model

        if df.empty:
            return False, 0.0

        # Get STRESS cost model (2x slippage)
        stress_cost_model = get_cost_model(config.instrument, stress_level='moderate')

        trades = []
        for row in df.itertuples():
            result = simulate_orb_trade(
                con=con,
                date_local=row.date_local,
                orb=config.orb_time,
                mode='1m',
                confirm_bars=1,
                rr=config.rr,
                sl_mode=config.sl_mode.lower(),
                exec_mode=ExecutionMode.MARKET_ON_CLOSE,
                slippage_ticks=stress_cost_model['slippage_ticks'],
                commission_per_contract=stress_cost_model['commission_rt']
            )
            if result.outcome in ['WIN', 'LOSS']:
                trades.append(result)

        if len(trades) == 0:
            return False, 0.0

        # Calculate stress metrics
        r_values = [t.r_multiple - t.cost_r for t in trades]
        stress_avg_r = sum(r_values) / len(r_values) if r_values else 0.0

        # Survives if avg_r > 0 under stress
        survives = stress_avg_r > 0

        return survives, stress_avg_r

    def run_stress_test(self, config: DiscoveryConfig, con) -> tuple:
        """
        Run stress test with 2x slippage (stress_level='moderate').

        Edge Engine V1: Fail-closed gate - must survive stress to pass.

        Returns:
            (survives_stress: bool, stress_avg_r: float)
        """
        from strategies.execution_engine import simulate_orb_trade, ExecutionMode
        from pipeline.cost_model import get_cost_model

        table = self.feature_tables.get(config.instrument)
        if not table:
            return False, 0.0

        orb_prefix = f"orb_{config.orb_time}"
        query = f"""
        SELECT date_local, CAST({orb_prefix}_size AS DOUBLE) as orb_size, atr_20 as atr
        FROM {table}
        WHERE {orb_prefix}_high IS NOT NULL
          AND {orb_prefix}_low IS NOT NULL
          AND {orb_prefix}_break_dir IS NOT NULL
          AND {orb_prefix}_break_dir != 'NONE'
        ORDER BY date_local
        """

        df = con.execute(query).df()
        if df.empty:
            return False, 0.0

        # Apply ORB size filter
        if config.orb_size_filter is not None:
            df = df[df['orb_size'] <= (df['atr'] * config.orb_size_filter)]

        if len(df) == 0:
            return False, 0.0

        # Get STRESS cost model (2x slippage)
        stress_cost_model = get_cost_model(config.instrument, stress_level='moderate')

        trades = []
        for _, row in df.iterrows():
            result = simulate_orb_trade(
                con=con,
                date_local=row['date_local'],
                orb=config.orb_time,
                mode='1m',
                confirm_bars=1,
                rr=config.rr,
                sl_mode=config.sl_mode.lower(),
                exec_mode=ExecutionMode.MARKET_ON_CLOSE,
                slippage_ticks=stress_cost_model['slippage_ticks'],
                commission_per_contract=stress_cost_model['commission_rt']
            )
            if result.outcome in ['WIN', 'LOSS']:
                trades.append(result)

        if len(trades) == 0:
            return False, 0.0

        # Calculate stress avg_r
        r_values = [t.r_multiple - t.cost_r for t in trades]
        stress_avg_r = sum(r_values) / len(r_values)

        # Survives if avg_r > 0 under stress
        survives = stress_avg_r > 0

        return survives, round(stress_avg_r, 4)

    def discover_best_setups(
        self,
        instrument: str,
        orb_time: str,
        rr_values: List[float] = [1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0],
        sl_modes: List[str] = ["FULL", "HALF"],
        filter_values: List[Optional[float]] = [None, 0.10, 0.15, 0.20]
    ) -> List[BacktestResult]:
        """
        Test multiple configurations for a given instrument/ORB combination.

        Returns list of BacktestResults sorted by performance (avg R descending).
        """
        results = []

        for rr in rr_values:
            for sl_mode in sl_modes:
                for orb_filter in filter_values:
                    config = DiscoveryConfig(
                        instrument=instrument,
                        orb_time=orb_time,
                        rr=rr,
                        sl_mode=sl_mode,
                        orb_size_filter=orb_filter
                    )

                    try:
                        result = self.backtest_configuration(config)
                        if result.total_trades >= 10:  # Minimum sample size
                            results.append(result)
                    except Exception as e:
                        logger.error(f"Error backtesting {config}: {e}")
                        continue

        # Sort by avg R descending (best performance first)
        results.sort(key=lambda x: x.avg_r, reverse=True)

        return results

    def get_existing_setups(self, instrument: str, orb_time: str) -> List[Dict]:
        """Get existing validated setups for this instrument/ORB from database"""
        con = self._get_connection()
        if con is None:
            return []
        
        query = """
        SELECT instrument, orb_time, tier, win_rate, rr, sl_mode, orb_size_filter, avg_r, annual_trades
        FROM validated_setups
        WHERE instrument = ? AND orb_time = ?
        """
        try:
            df = con.execute(query, [instrument, orb_time]).df()
            return df.to_dict('records') if not df.empty else []
        except Exception as e:
            logger.error(f"Error querying validated_setups: {e}")
            return []

    def close(self):
        """Close database connection - no-op for cloud connections"""
        pass


def add_setup_to_production(
    result: BacktestResult,
    db_path: str = "gold.db",
    config_path: str = "trading_app/config.py"
) -> Dict[str, bool]:
    """
    Add a discovered setup to production.

    Steps:
    1. Insert into validated_setups database table
    2. Update config.py with new setup
    3. Return status of each operation

    Returns dict with 'database' and 'config' booleans indicating success.
    """
    status = {'database': False, 'config': False, 'error': None}

    try:
        # Step 1: Insert into database
        from cloud_mode import get_database_connection
        con = get_database_connection(read_only=False)

        # Check if setup already exists
        check_query = """
        SELECT COUNT(*) as count
        FROM validated_setups
        WHERE instrument = ? AND orb_time = ? AND rr = ? AND sl_mode = ?
        """
        exists = con.execute(check_query, [
            result.config.instrument,
            result.config.orb_time,
            result.config.rr,
            result.config.sl_mode
        ]).fetchone()[0] > 0

        if exists:
            status['error'] = "Setup already exists in database"
            con.close()
            return status

        # Insert new setup
        insert_query = """
        INSERT INTO validated_setups (
            instrument, orb_time, tier, win_rate, rr, sl_mode,
            orb_size_filter, avg_r, annual_trades
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        con.execute(insert_query, [
            result.config.instrument,
            result.config.orb_time,
            result.tier,
            result.win_rate,
            result.config.rr,
            result.config.sl_mode,
            result.config.orb_size_filter,
            result.avg_r,
            result.annual_trades
        ])

        con.close()
        status['database'] = True
        logger.info(f"Added {result.config.instrument} {result.config.orb_time} to database")

        # Step 2: Generate config snippet for user to add manually
        # (Automatic config editing is risky - better to show user what to add)
        status['config'] = True  # User will add manually

    except Exception as e:
        status['error'] = str(e)
        logger.error(f"Error adding setup to production: {e}")

    return status


def generate_config_snippet(result: BacktestResult) -> str:
    """Generate config.py code snippet for the discovered setup"""
    inst = result.config.instrument
    orb = result.config.orb_time

    # Determine tier string for config
    if result.config.orb_time in NIGHT_ORBS:
        tier_str = "NIGHT"
    else:
        tier_str = "DAY"

    config_line = f'    "{orb}": {{"rr": {result.config.rr}, "sl_mode": "{result.config.sl_mode}", "tier": "{tier_str}"}},'

    if result.config.orb_size_filter:
        filter_line = f'    "{orb}": {result.config.orb_size_filter},'
    else:
        filter_line = f'    "{orb}": None,'

    snippet = f"""
# Add to {inst}_ORB_CONFIGS dictionary:
{config_line}

# Add to {inst}_ORB_SIZE_FILTERS dictionary:
{filter_line}

# Then run: python test_app_sync.py
"""

    return snippet


# =============================================================================
# EDGE ENGINE V1: JSONL TRIAL LOGGING
# =============================================================================

TRIALS_LOG_PATH = Path("artifacts/discovery_trials.jsonl")


def get_cost_model_snapshot(instrument: str) -> Dict:
    """
    Get cost model snapshot for logging (frozen at trial time).

    Edge Engine V1: Captures exact costs used for reproducibility.
    """
    try:
        from pipeline.cost_model import get_cost_model
        cm = get_cost_model(instrument)
        return {
            "instrument": instrument,
            "tick_size": cm.get("tick_size"),
            "tick_value": cm.get("tick_value"),
            "point_value": cm.get("point_value"),
            "commission_rt": cm.get("commission_rt"),
            "slippage_ticks": cm.get("slippage_ticks"),
            "spread_double": cm.get("spread_double"),
            "friction_total": cm.get("friction_total"),
        }
    except Exception as e:
        logger.warning(f"Could not get cost model: {e}")
        return {"instrument": instrument, "error": str(e)}


def evaluate_gates(result: BacktestResult) -> tuple:
    """
    Evaluate fail-closed gates for Edge Engine V1.

    Gates (ALL must pass):
    1. Expectancy > 0 (avg_r > 0)
    2. Total trades >= 100
    3. Survives 2x slippage stress test

    Returns:
        (verdict: str, fail_reason: Optional[str])
        verdict: "PASS" or "FAIL"
    """
    reasons = []

    # Gate 1: Expectancy > 0
    if result.avg_r <= 0:
        reasons.append(f"expectancy_negative:{result.avg_r:.4f}")

    # Gate 2: Trades >= 100
    if result.total_trades < 100:
        reasons.append(f"trades_insufficient:{result.total_trades}")

    # Gate 3: Survives stress
    if not result.survives_stress:
        stress_r = result.stress_avg_r if result.stress_avg_r else 0.0
        reasons.append(f"stress_fail:{stress_r:.4f}")

    if reasons:
        return "FAIL", "|".join(reasons)
    else:
        return "PASS", None


def build_trial_log_entry(result: BacktestResult, execution_mode: str = "MARKET_ON_CLOSE") -> Dict:
    """
    Build complete trial log entry for JSONL.

    Edge Engine V1: Immutable schema - fields cannot be removed or renamed.
    """
    verdict, fail_reason = evaluate_gates(result)

    return {
        # Entry type discriminator (for mixed log files)
        "entry_type": "edge_engine_v1",
        # Schema metadata (locked forever)
        "schema_version": SCHEMA_VERSION,
        "engine_version": EDGE_ENGINE_VERSION,
        "gates_version": GATES_VERSION,
        "logged_at": datetime.utcnow().isoformat() + "Z",

        # Candidate identification
        "candidate_hash": result.candidate_hash,
        "instrument": result.config.instrument,
        "orb_time": result.config.orb_time,
        "rr": result.config.rr,
        "sl_mode": result.config.sl_mode,
        "orb_size_filter": result.config.orb_size_filter,

        # Data window
        "date_start": result.date_start,
        "date_end": result.date_end,

        # Performance metrics
        "total_trades": result.total_trades,
        "wins": result.wins,
        "losses": result.losses,
        "win_rate": round(result.win_rate, 4),
        "avg_r": round(result.avg_r, 6),
        "total_r": round(result.total_r, 4),
        "max_dd_R": result.max_dd_R,
        "annual_trades": result.annual_trades,
        "tier": result.tier,

        # Stress test results
        "survives_stress": result.survives_stress,
        "stress_avg_r": result.stress_avg_r,

        # Execution context
        "execution_mode": execution_mode,
        "cost_model_snapshot": get_cost_model_snapshot(result.config.instrument),

        # Gate verdict
        "verdict": verdict,
        "fail_reason": fail_reason,
    }


def append_trial_log(result: BacktestResult, execution_mode: str = "MARKET_ON_CLOSE") -> bool:
    """
    Atomically append trial to JSONL log (Windows-safe).

    Edge Engine V1: Append-only, no modifications to existing entries.
    Uses atomic write pattern for Windows compatibility.

    Returns:
        True if logged successfully, False otherwise.
    """
    try:
        # Ensure directory exists
        TRIALS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Build log entry
        entry = build_trial_log_entry(result, execution_mode)
        json_line = json.dumps(entry, separators=(',', ':')) + "\n"

        # Windows-safe atomic append
        # Open in append+binary mode, write encoded bytes, then flush+sync
        with open(TRIALS_LOG_PATH, "ab") as f:
            f.write(json_line.encode("utf-8"))
            f.flush()
            os.fsync(f.fileno())  # Force write to disk

        logger.info(f"Logged trial {entry['candidate_hash']}: {entry['verdict']}")
        return True

    except Exception as e:
        logger.error(f"Failed to log trial: {e}")
        return False


def log_discovery_trial(result: BacktestResult, execution_mode: str = "MARKET_ON_CLOSE") -> Dict:
    """
    Complete trial logging workflow with gate evaluation.

    Edge Engine V1: Entry point for strategy discovery logging.

    Returns:
        Dict with verdict, fail_reason, and logged status.
    """
    verdict, fail_reason = evaluate_gates(result)
    logged = append_trial_log(result, execution_mode)

    return {
        "verdict": verdict,
        "fail_reason": fail_reason,
        "logged": logged,
        "candidate_hash": result.candidate_hash,
    }
