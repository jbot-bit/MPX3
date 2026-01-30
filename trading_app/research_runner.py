"""
Research Runner - Phase 2

Automated backtest runner for edge_candidates table.
Takes a candidate spec, runs backtests, computes metrics, writes results back.

NO LLM DECISIONS - pure deterministic code.

Usage:
    from research_runner import ResearchRunner

    runner = ResearchRunner()
    runner.run_candidate(candidate_id=1)
"""

import duckdb
import json
import subprocess
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trading_app.edge_candidate_utils import parse_json_field, serialize_json_field
from trading_app.cloud_mode import get_database_connection

logger = logging.getLogger(__name__)


@dataclass
class BacktestMetrics:
    """Backtest performance metrics."""
    win_rate: float
    avg_r: float
    total_r: float
    n_trades: int
    max_drawdown_r: float
    mae_avg: float
    mfe_avg: float
    sharpe_ratio: Optional[float] = None
    profit_factor: Optional[float] = None


@dataclass
class RobustnessMetrics:
    """Robustness check results with stress testing."""
    walk_forward_periods: int
    walk_forward_avg_r: float
    walk_forward_std_r: float
    regime_split_results: Dict[str, Dict[str, float]]
    is_robust: bool
    # ✅ CANONICAL: Stress testing required (audit3.txt, CLAUDE.md)
    stress_25_exp_r: float = 0.0
    stress_50_exp_r: float = 0.0
    stress_25_pass: bool = False
    stress_50_pass: bool = False


class ResearchRunner:
    """
    Automated backtest runner for edge candidates.

    Workflow:
    1. Load candidate from edge_candidates table
    2. Extract filter_spec and feature_spec
    3. Run backtest on daily_features + bars data
    4. Compute metrics (WR, avg R, total R, drawdown, MAE/MFE)
    5. Run robustness checks (walk-forward, regime splits)
    6. Write results back to edge_candidates
    7. Update status to TESTED
    """

    def __init__(self):
        pass

    def get_connection(self, read_only: bool = True):
        """Get cloud-aware database connection."""
        return get_database_connection(read_only=read_only)

    def load_candidate(self, candidate_id: int) -> Optional[Dict[str, Any]]:
        """
        Load edge candidate from database.

        Returns:
            Dict with all candidate fields, or None if not found
        """
        con = self.get_connection(read_only=True)

        result = con.execute("""
            SELECT
                candidate_id,
                instrument,
                name,
                hypothesis_text,
                feature_spec_json,
                filter_spec_json,
                test_window_start,
                test_window_end,
                status,
                code_version,
                data_version,
                test_config_json
            FROM edge_candidates
            WHERE candidate_id = ?
        """, [candidate_id]).fetchone()

        con.close()

        if not result:
            logger.error(f"Candidate {candidate_id} not found")
            return None

        # Parse JSON fields
        candidate = {
            'candidate_id': result[0],
            'instrument': result[1],
            'name': result[2],
            'hypothesis_text': result[3],
            'feature_spec': parse_json_field(result[4]),
            'filter_spec': parse_json_field(result[5]),
            'test_window_start': result[6],
            'test_window_end': result[7],
            'status': result[8],
            'code_version': result[9],
            'data_version': result[10],
            'test_config': parse_json_field(result[11])
        }

        return candidate

    def run_backtest(self, candidate: Dict[str, Any]) -> Optional[BacktestMetrics]:
        """
        Run backtest for a candidate using CANONICAL execution_engine.py.

        Uses execution_engine.simulate_orb_trade() for deterministic, cost-aware backtesting.
        NO parallel execution paths - all research uses same engine as production.
        """
        logger.info(f"Running backtest for candidate {candidate['candidate_id']}: {candidate['name']}")

        instrument = candidate['instrument']
        filter_spec = candidate.get('filter_spec') or {}
        test_window_start = candidate.get('test_window_start')
        test_window_end = candidate.get('test_window_end')

        logger.info(f"  Instrument: {instrument}")
        logger.info(f"  Test window: {test_window_start} to {test_window_end}")

        orb_time = filter_spec.get('orb_time', '0900')
        rr = filter_spec.get('rr', 2.0)
        sl_mode = filter_spec.get('sl_mode', 'FULL')
        orb_size_filter = filter_spec.get('orb_size_filter')

        feature_tables = {
            "MGC": "daily_features",
            "NQ": "daily_features_nq",
            "MPL": "daily_features_mpl"
        }

        table = feature_tables.get(instrument)
        if not table:
            logger.error(f"Unknown instrument: {instrument}")
            return None

        orb_prefix = f"orb_{orb_time}"

        try:
            con = self.get_connection(read_only=True)

            # Query dates with ORB breaks only (execution_engine will simulate from bars)
            sql = f"""
            SELECT
                date_local,
                CAST({orb_prefix}_size AS DOUBLE) as orb_size,
                atr_20 as atr
            FROM {table}
            WHERE {orb_prefix}_high IS NOT NULL
              AND {orb_prefix}_low IS NOT NULL
              AND {orb_prefix}_break_dir IS NOT NULL
              AND {orb_prefix}_break_dir != 'NONE'
            """

            if test_window_start:
                sql += f" AND date_local >= '{test_window_start}'"
            if test_window_end:
                sql += f" AND date_local <= '{test_window_end}'"

            sql += " ORDER BY date_local"

            df = con.execute(sql).df()

            if df.empty:
                logger.warning("No data found for backtest")
                con.close()
                return BacktestMetrics(
                    win_rate=0.0, avg_r=0.0, total_r=0.0, n_trades=0,
                    max_drawdown_r=0.0, mae_avg=0.0, mfe_avg=0.0
                )

            # Apply ORB size filter if specified
            if orb_size_filter is not None:
                df = df[df['orb_size'] <= (df['atr'] * orb_size_filter)]

            n_dates = len(df)
            if n_dates == 0:
                con.close()
                return BacktestMetrics(
                    win_rate=0.0, avg_r=0.0, total_r=0.0, n_trades=0,
                    max_drawdown_r=0.0, mae_avg=0.0, mfe_avg=0.0
                )

            # ✅ CANONICAL EXECUTION: Use execution_engine.simulate_orb_trade()
            from strategies.execution_engine import simulate_orb_trade, ExecutionMode
            from pipeline.cost_model import get_cost_model

            # Get canonical costs for this instrument
            cost_model = get_cost_model(instrument)

            trades = []
            logger.info(f"  Simulating {n_dates} dates with canonical execution engine...")

            for _, row in df.iterrows():
                result = simulate_orb_trade(
                    con=con,
                    date_local=row['date_local'],
                    orb=orb_time,
                    mode='1m',
                    confirm_bars=1,
                    rr=rr,
                    sl_mode=sl_mode.lower(),
                    exec_mode=ExecutionMode.MARKET_ON_CLOSE,
                    slippage_ticks=cost_model['slippage_ticks'],
                    commission_per_contract=cost_model['commission_rt'] / 2  # Per side
                )

                # Skip if no trade
                if result.outcome in ['SKIPPED_NO_ORB', 'SKIPPED_NO_BARS', 'SKIPPED_NO_ENTRY', 'NO_TRADE']:
                    continue

                trades.append(result)

            con.close()

            if len(trades) == 0:
                return BacktestMetrics(
                    win_rate=0.0, avg_r=0.0, total_r=0.0, n_trades=0,
                    max_drawdown_r=0.0, mae_avg=0.0, mfe_avg=0.0
                )

            # Calculate metrics from canonical execution results
            wins = sum(1 for t in trades if t.outcome == 'WIN')
            losses = sum(1 for t in trades if t.outcome == 'LOSS')
            n_trades_actual = wins + losses

            if n_trades_actual == 0:
                return BacktestMetrics(
                    win_rate=0.0, avg_r=0.0, total_r=0.0, n_trades=0,
                    max_drawdown_r=0.0, mae_avg=0.0, mfe_avg=0.0
                )

            win_rate = wins / n_trades_actual

            # Use REALIZED R (post-cost)
            r_values = [t.r_multiple - t.cost_r for t in trades if t.outcome in ['WIN', 'LOSS']]
            total_r = sum(r_values)
            avg_r = total_r / n_trades_actual

            # Calculate drawdown curve
            running_r = 0.0
            max_dd = 0.0
            peak = 0.0
            for r in r_values:
                running_r += r
                if running_r > peak:
                    peak = running_r
                dd = running_r - peak
                if dd < max_dd:
                    max_dd = dd

            # Calculate MAE/MFE averages from execution results
            mae_avg = sum(t.mae_r for t in trades if t.mae_r is not None) / len([t for t in trades if t.mae_r is not None]) if any(t.mae_r is not None for t in trades) else 0.0
            mfe_avg = sum(t.mfe_r for t in trades if t.mfe_r is not None) / len([t for t in trades if t.mfe_r is not None]) if any(t.mfe_r is not None for t in trades) else 0.0

            # Calculate profit factor
            gross_profit = sum(r for r in r_values if r > 0)
            gross_loss = abs(sum(r for r in r_values if r < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 99.0

            # Calculate Sharpe ratio
            if len(r_values) > 1:
                import statistics
                r_std = statistics.stdev(r_values)
                sharpe = avg_r / r_std if r_std > 0 else 0.0
            else:
                sharpe = 0.0

            metrics = BacktestMetrics(
                win_rate=win_rate,
                avg_r=avg_r,
                total_r=total_r,
                n_trades=n_trades_actual,
                max_drawdown_r=max_dd,
                mae_avg=mae_avg,
                mfe_avg=mfe_avg,
                sharpe_ratio=sharpe,
                profit_factor=profit_factor
            )

            logger.info(f"  Backtest complete: {metrics.n_trades} trades, {metrics.win_rate:.1%} WR, {metrics.avg_r:+.3f}R avg (REALIZED, post-cost)")
            return metrics

        except Exception as e:
            logger.error(f"Backtest error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def run_robustness_checks(self, candidate: Dict[str, Any]) -> Optional[RobustnessMetrics]:
        """
        Run robustness checks using CANONICAL execution_engine.py.

        Checks:
        1. Walk-forward analysis (split into N windows, test on each)
        2. Regime split (high vol vs low vol based on ATR)
        3. Stress testing (+25%, +50% costs)
        """
        logger.info(f"Running robustness checks for candidate {candidate['candidate_id']}")

        test_config = candidate.get('test_config') or {}
        walk_forward_windows = test_config.get('walk_forward_windows', 4)
        filter_spec = candidate.get('filter_spec') or {}

        instrument = candidate['instrument']
        rr = filter_spec.get('rr', 2.0)
        orb_time = filter_spec.get('orb_time', '0900')
        sl_mode = filter_spec.get('sl_mode', 'FULL')
        orb_size_filter = filter_spec.get('orb_size_filter')
        test_window_start = candidate.get('test_window_start')
        test_window_end = candidate.get('test_window_end')

        feature_tables = {
            "MGC": "daily_features",
            "NQ": "daily_features_nq",
            "MPL": "daily_features_mpl"
        }
        table = feature_tables.get(instrument, "daily_features")
        orb_prefix = f"orb_{orb_time}"

        logger.info(f"  Walk-forward windows: {walk_forward_windows}")

        try:
            con = self.get_connection(read_only=True)

            # Query dates only (execution_engine will simulate from bars)
            sql = f"""
            SELECT
                date_local,
                CAST({orb_prefix}_size AS DOUBLE) as orb_size,
                atr_20 as atr
            FROM {table}
            WHERE {orb_prefix}_high IS NOT NULL
              AND {orb_prefix}_low IS NOT NULL
              AND {orb_prefix}_break_dir IS NOT NULL
              AND {orb_prefix}_break_dir != 'NONE'
            """
            if test_window_start:
                sql += f" AND date_local >= '{test_window_start}'"
            if test_window_end:
                sql += f" AND date_local <= '{test_window_end}'"
            sql += " ORDER BY date_local"

            df = con.execute(sql).df()

            if df.empty or len(df) < walk_forward_windows:
                con.close()
                return RobustnessMetrics(
                    walk_forward_periods=walk_forward_windows,
                    walk_forward_avg_r=0.0,
                    walk_forward_std_r=0.0,
                    regime_split_results={},
                    is_robust=False
                )

            # Apply ORB size filter
            if orb_size_filter is not None:
                df = df[df['orb_size'] <= (df['atr'] * orb_size_filter)]

            # ✅ CANONICAL EXECUTION: Use execution_engine
            from strategies.execution_engine import simulate_orb_trade, ExecutionMode
            from pipeline.cost_model import get_cost_model

            cost_model = get_cost_model(instrument)

            window_size = len(df) // walk_forward_windows
            wf_results = []

            for i in range(walk_forward_windows):
                start_idx = i * window_size
                end_idx = start_idx + window_size if i < walk_forward_windows - 1 else len(df)
                window_df = df.iloc[start_idx:end_idx]

                if len(window_df) == 0:
                    continue

                # Simulate trades in this window using canonical engine
                trades = []
                for _, row in window_df.iterrows():
                    result = simulate_orb_trade(
                        con=con,
                        date_local=row['date_local'],
                        orb=orb_time,
                        mode='1m',
                        confirm_bars=1,
                        rr=rr,
                        sl_mode=sl_mode.lower(),
                        exec_mode=ExecutionMode.MARKET_ON_CLOSE,
                        slippage_ticks=cost_model['slippage_ticks'],
                        commission_per_contract=cost_model['commission_rt'] / 2
                    )

                    if result.outcome in ['WIN', 'LOSS']:
                        trades.append(result)

                if len(trades) > 0:
                    # Use REALIZED R (post-cost)
                    r_values = [t.r_multiple - t.cost_r for t in trades]
                    avg_r = sum(r_values) / len(r_values)
                    wf_results.append(avg_r)
                else:
                    wf_results.append(0.0)

            import statistics
            wf_avg_r = statistics.mean(wf_results) if wf_results else 0.0
            wf_std_r = statistics.stdev(wf_results) if len(wf_results) > 1 else 0.0

            # Regime split analysis
            median_atr = df['atr'].median() if 'atr' in df.columns else 0
            high_vol_df = df[df['atr'] > median_atr]
            low_vol_df = df[df['atr'] <= median_atr]

            regime_results = {}
            for regime_name, regime_df in [("high_vol", high_vol_df), ("low_vol", low_vol_df)]:
                if len(regime_df) > 0:
                    # Simulate trades in this regime
                    trades = []
                    for _, row in regime_df.iterrows():
                        result = simulate_orb_trade(
                            con=con,
                            date_local=row['date_local'],
                            orb=orb_time,
                            mode='1m',
                            confirm_bars=1,
                            rr=rr,
                            sl_mode=sl_mode.lower(),
                            exec_mode=ExecutionMode.MARKET_ON_CLOSE,
                            slippage_ticks=cost_model['slippage_ticks'],
                            commission_per_contract=cost_model['commission_rt'] / 2
                        )

                        if result.outcome in ['WIN', 'LOSS']:
                            trades.append(result)

                    if len(trades) > 0:
                        wins = sum(1 for t in trades if t.outcome == 'WIN')
                        r_values = [t.r_multiple - t.cost_r for t in trades]
                        regime_results[regime_name] = {
                            "avg_r": sum(r_values) / len(r_values),
                            "n": len(trades),
                            "win_rate": wins / len(trades)
                        }

            con.close()

            # ✅ ADD STRESS TESTING (CANONICAL requirement)
            # Reload all trades for stress testing
            con = self.get_connection(read_only=True)
            all_trades = []
            for _, row in df.iterrows():
                result = simulate_orb_trade(
                    con=con,
                    date_local=row['date_local'],
                    orb=orb_time,
                    mode='1m',
                    confirm_bars=1,
                    rr=rr,
                    sl_mode=sl_mode.lower(),
                    exec_mode=ExecutionMode.MARKET_ON_CLOSE,
                    slippage_ticks=cost_model['slippage_ticks'],
                    commission_per_contract=cost_model['commission_rt'] / 2
                )

                if result.outcome in ['WIN', 'LOSS']:
                    all_trades.append(result)

            con.close()

            # Calculate stress test metrics
            if len(all_trades) > 0:
                r_values = [t.r_multiple - t.cost_r for t in all_trades]

                # Stress tests: increase costs by 25% and 50%
                stress_25_r = [t.r_multiple - (t.cost_r * 1.25) for t in all_trades]
                stress_50_r = [t.r_multiple - (t.cost_r * 1.50) for t in all_trades]

                stress_25_exp_r = sum(stress_25_r) / len(stress_25_r)
                stress_50_exp_r = sum(stress_50_r) / len(stress_50_r)

                stress_25_pass = stress_25_exp_r >= 0.15
                stress_50_pass = stress_50_exp_r >= 0.15
            else:
                stress_25_exp_r = 0.0
                stress_50_exp_r = 0.0
                stress_25_pass = False
                stress_50_pass = False

            is_robust = (
                wf_avg_r > 0 and
                wf_std_r < abs(wf_avg_r) * 0.5 and
                all(r > 0 for r in wf_results) if wf_results else False
            )
            
            robustness = RobustnessMetrics(
                walk_forward_periods=walk_forward_windows,
                walk_forward_avg_r=wf_avg_r,
                walk_forward_std_r=wf_std_r,
                regime_split_results=regime_results,
                is_robust=is_robust,
                stress_25_exp_r=stress_25_exp_r,
                stress_50_exp_r=stress_50_exp_r,
                stress_25_pass=stress_25_pass,
                stress_50_pass=stress_50_pass
            )

            logger.info(f"  Robustness: WF avg_r={robustness.walk_forward_avg_r:+.3f}R, std={robustness.walk_forward_std_r:.3f}R, robust={robustness.is_robust}")
            logger.info(f"  Stress Tests: +25%={robustness.stress_25_exp_r:+.3f}R ({'PASS' if robustness.stress_25_pass else 'FAIL'}), +50%={robustness.stress_50_exp_r:+.3f}R ({'PASS' if robustness.stress_50_pass else 'FAIL'})")
            return robustness
            
        except Exception as e:
            logger.error(f"Robustness check error: {e}")
            return None

    def write_results(
        self,
        candidate_id: int,
        metrics: BacktestMetrics,
        robustness: RobustnessMetrics
    ) -> bool:
        """
        Write backtest results back to edge_candidates table.

        Updates:
        - metrics_json
        - robustness_json
        - status (DRAFT -> TESTED)
        """
        con = self.get_connection(read_only=False)

        # Build metrics JSON
        metrics_json = {
            "win_rate": metrics.win_rate,
            "avg_r": metrics.avg_r,
            "total_r": metrics.total_r,
            "n_trades": metrics.n_trades,
            "max_drawdown_r": metrics.max_drawdown_r,
            "mae_avg": metrics.mae_avg,
            "mfe_avg": metrics.mfe_avg,
            "sharpe_ratio": metrics.sharpe_ratio,
            "profit_factor": metrics.profit_factor
        }

        # Build robustness JSON (with stress tests)
        robustness_json = {
            "walk_forward_periods": robustness.walk_forward_periods,
            "walk_forward_avg_r": robustness.walk_forward_avg_r,
            "walk_forward_std_r": robustness.walk_forward_std_r,
            "regime_split_results": robustness.regime_split_results,
            "is_robust": robustness.is_robust,
            "stress_25_exp_r": robustness.stress_25_exp_r,
            "stress_50_exp_r": robustness.stress_50_exp_r,
            "stress_25_pass": robustness.stress_25_pass,
            "stress_50_pass": robustness.stress_50_pass
        }

        try:
            # Update candidate
            con.execute("""
                UPDATE edge_candidates
                SET
                    metrics_json = ?::JSON,
                    robustness_json = ?::JSON,
                    status = 'TESTED'
                WHERE candidate_id = ?
            """, [
                serialize_json_field(metrics_json),
                serialize_json_field(robustness_json),
                candidate_id
            ])

            con.commit()
            logger.info(f"Results written to candidate {candidate_id}, status updated to TESTED")
            return True

        except Exception as e:
            logger.error(f"Failed to write results: {e}")
            return False

        finally:
            con.close()

    def auto_populate_reproducibility_fields(self, candidate_id: int) -> None:
        """
        Auto-populate reproducibility fields if not set.

        Populates:
        - code_version (from git if available)
        - data_version (current date)
        - test_config_json (defaults if not set)
        """
        con = self.get_connection(read_only=False)

        # Check if fields are already set
        result = con.execute("""
            SELECT code_version, data_version, test_config_json
            FROM edge_candidates
            WHERE candidate_id = ?
        """, [candidate_id]).fetchone()

        code_version, data_version, test_config_json = result

        # Auto-populate if missing
        if code_version is None:
            # Try to get git commit
            try:
                git_hash = subprocess.check_output(
                    ['git', 'rev-parse', '--short', 'HEAD'],
                    cwd=Path(__file__).parent.parent,
                    stderr=subprocess.DEVNULL
                ).decode().strip()
                code_version = git_hash
            except (subprocess.CalledProcessError, FileNotFoundError, UnicodeDecodeError) as e:
                # Git not available or command failed
                code_version = f"manual-{datetime.now().strftime('%Y%m%d')}"

        if data_version is None:
            data_version = datetime.now().strftime('%Y-%m-%d')

        if test_config_json is None or parse_json_field(test_config_json) is None:
            # Default test config (NO hardcoded costs - loaded from cost_model.py at runtime)
            test_config = {
                "random_seed": 42,
                "walk_forward_windows": 4,
                "train_pct": 0.7,
                "regime_detection": "volatility_quartiles"
                # ✅ CANONICAL: NO hardcoded costs - use cost_model.py at runtime
            }
            test_config_json = serialize_json_field(test_config)

        # Update
        con.execute("""
            UPDATE edge_candidates
            SET
                code_version = ?,
                data_version = ?,
                test_config_json = COALESCE(test_config_json, ?::JSON)
            WHERE candidate_id = ?
        """, [code_version, data_version, test_config_json, candidate_id])

        con.commit()
        con.close()

        logger.info(f"Reproducibility fields populated: code_version={code_version}, data_version={data_version}")

    def run_candidate(self, candidate_id: int) -> bool:
        """
        Run complete research workflow for a candidate.

        Steps:
        1. Load candidate
        2. Auto-populate reproducibility fields if needed
        3. Run backtest
        4. Run robustness checks
        5. Write results
        6. Update status to TESTED

        Returns:
            True if successful, False otherwise
        """
        logger.info("="*60)
        logger.info(f"RESEARCH RUNNER: Processing Candidate {candidate_id}")
        logger.info("="*60)

        # Load candidate
        candidate = self.load_candidate(candidate_id)
        if not candidate:
            logger.error(f"Candidate {candidate_id} not found")
            return False

        logger.info(f"Loaded: {candidate['name']}")
        logger.info(f"Status: {candidate['status']}")

        # Auto-populate reproducibility fields
        self.auto_populate_reproducibility_fields(candidate_id)

        # Reload to get updated fields
        candidate = self.load_candidate(candidate_id)

        # Run backtest
        metrics = self.run_backtest(candidate)
        if not metrics:
            logger.error("Backtest failed")
            return False

        # Run robustness checks
        robustness = self.run_robustness_checks(candidate)
        if not robustness:
            logger.error("Robustness checks failed")
            return False

        # Write results
        success = self.write_results(candidate_id, metrics, robustness)
        if not success:
            logger.error("Failed to write results")
            return False

        logger.info("="*60)
        logger.info(f"COMPLETE: Candidate {candidate_id} tested successfully")
        logger.info("="*60)

        return True


def main():
    """CLI entry point for research runner."""
    import argparse

    parser = argparse.ArgumentParser(description="Run backtest for edge candidate")
    parser.add_argument("candidate_id", type=int, help="Candidate ID to test")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(message)s'
    )

    # Run candidate
    runner = ResearchRunner()
    success = runner.run_candidate(args.candidate_id)

    if success:
        print("\n[OK] Research runner completed successfully")
        print(f"     Candidate {args.candidate_id} status updated to TESTED")
        print()
    else:
        print("\n[ERROR] Research runner failed")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
