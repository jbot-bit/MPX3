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
    """Robustness check results."""
    walk_forward_periods: int
    walk_forward_avg_r: float
    walk_forward_std_r: float
    regime_split_results: Dict[str, Dict[str, float]]
    is_robust: bool


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
        Run backtest for a candidate using daily_features data.
        
        Queries the database for ORB breakout data and simulates trades
        based on the candidate's filter_spec configuration.
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
            
            sql = f"""
            SELECT
                date_local,
                CAST({orb_prefix}_high AS DOUBLE) as orb_high,
                CAST({orb_prefix}_low AS DOUBLE) as orb_low,
                CAST({orb_prefix}_size AS DOUBLE) as orb_size,
                {orb_prefix}_break_dir as break_dir,
                CAST({orb_prefix}_mae AS DOUBLE) as mae,
                CAST({orb_prefix}_mfe AS DOUBLE) as mfe,
                atr_20 as atr
            FROM {table}
            WHERE {orb_prefix}_high IS NOT NULL
              AND {orb_prefix}_low IS NOT NULL
              AND {orb_prefix}_break_dir IS NOT NULL
              AND {orb_prefix}_break_dir != 'NONE'
              AND {orb_prefix}_mae IS NOT NULL
              AND {orb_prefix}_mfe IS NOT NULL
            """
            
            if test_window_start:
                sql += f" AND date_local >= '{test_window_start}'"
            if test_window_end:
                sql += f" AND date_local <= '{test_window_end}'"
            
            sql += " ORDER BY date_local"
            
            df = con.execute(sql).df()
            con.close()
            
            if df.empty:
                logger.warning("No data found for backtest")
                return BacktestMetrics(
                    win_rate=0.0, avg_r=0.0, total_r=0.0, n_trades=0,
                    max_drawdown_r=0.0, mae_avg=0.0, mfe_avg=0.0
                )
            
            if orb_size_filter is not None:
                df = df[df['orb_size'] <= (df['atr'] * orb_size_filter)]
            
            n_trades = len(df)
            if n_trades == 0:
                return BacktestMetrics(
                    win_rate=0.0, avg_r=0.0, total_r=0.0, n_trades=0,
                    max_drawdown_r=0.0, mae_avg=0.0, mfe_avg=0.0
                )
            
            # Evaluate each trade using MAE/MFE for the specified RR and sl_mode
            from trading_app.strategy_evaluation import evaluate_trade_outcome, calculate_metrics

            outcomes_and_r = []
            for _, row in df.iterrows():
                outcome, r_achieved = evaluate_trade_outcome(
                    break_dir=row['break_dir'],
                    orb_high=row['orb_high'],
                    orb_low=row['orb_low'],
                    mae=row['mae'],
                    mfe=row['mfe'],
                    rr=rr,
                    sl_mode=sl_mode
                )
                outcomes_and_r.append((outcome, r_achieved))

            # Calculate metrics from evaluated trades
            metrics_data = calculate_metrics(outcomes_and_r)
            wins = metrics_data['wins']
            losses = metrics_data['losses']
            win_rate = metrics_data['win_rate']
            avg_r = metrics_data['avg_r']
            total_r = metrics_data['total_r']
            n_trades_actual = metrics_data['total_trades']  # Trades with resolution (excludes NO_TRADE)
            r_values = [r for _, r in outcomes_and_r if _ in ['WIN', 'LOSS']]

            if n_trades_actual == 0:
                return BacktestMetrics(
                    win_rate=0.0, avg_r=0.0, total_r=0.0, n_trades=0,
                    max_drawdown_r=0.0, mae_avg=0.0, mfe_avg=0.0
                )

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

            # Calculate MAE/MFE averages from actual data
            mae_avg = df['mae'].mean() if not df.empty else 0.0
            mfe_avg = df['mfe'].mean() if not df.empty else 0.0

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

            logger.info(f"  Backtest complete: {metrics.n_trades} trades, {metrics.win_rate:.1%} WR, {metrics.avg_r:+.3f}R avg")
            return metrics
            
        except Exception as e:
            logger.error(f"Backtest error: {e}")
            return None

    def run_robustness_checks(self, candidate: Dict[str, Any]) -> Optional[RobustnessMetrics]:
        """
        Run robustness checks on a candidate using real data.

        Checks:
        1. Walk-forward analysis (split into N windows, test on each)
        2. Regime split (high vol vs low vol based on ATR)
        """
        logger.info(f"Running robustness checks for candidate {candidate['candidate_id']}")

        test_config = candidate.get('test_config') or {}
        walk_forward_windows = test_config.get('walk_forward_windows', 4)
        filter_spec = candidate.get('filter_spec') or {}
        
        instrument = candidate['instrument']
        rr = filter_spec.get('rr', 2.0)
        orb_time = filter_spec.get('orb_time', '0900')
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
            
            sql = f"""
            SELECT
                date_local,
                CAST({orb_prefix}_high AS DOUBLE) as orb_high,
                CAST({orb_prefix}_low AS DOUBLE) as orb_low,
                CAST({orb_prefix}_size AS DOUBLE) as orb_size,
                {orb_prefix}_break_dir as break_dir,
                CAST({orb_prefix}_mae AS DOUBLE) as mae,
                CAST({orb_prefix}_mfe AS DOUBLE) as mfe,
                atr_20 as atr
            FROM {table}
            WHERE {orb_prefix}_high IS NOT NULL
              AND {orb_prefix}_low IS NOT NULL
              AND {orb_prefix}_break_dir IS NOT NULL
              AND {orb_prefix}_break_dir != 'NONE'
              AND {orb_prefix}_mae IS NOT NULL
              AND {orb_prefix}_mfe IS NOT NULL
            """
            if test_window_start:
                sql += f" AND date_local >= '{test_window_start}'"
            if test_window_end:
                sql += f" AND date_local <= '{test_window_end}'"
            sql += " ORDER BY date_local"
            
            df = con.execute(sql).df()
            con.close()
            
            if df.empty or len(df) < walk_forward_windows:
                return RobustnessMetrics(
                    walk_forward_periods=walk_forward_windows,
                    walk_forward_avg_r=0.0,
                    walk_forward_std_r=0.0,
                    regime_split_results={},
                    is_robust=False
                )
            
            if orb_size_filter is not None:
                df = df[df['orb_size'] <= (df['atr'] * orb_size_filter)]
            
            window_size = len(df) // walk_forward_windows
            wf_results = []
            
            from trading_app.strategy_evaluation import evaluate_trade_outcome, calculate_metrics

            for i in range(walk_forward_windows):
                start_idx = i * window_size
                end_idx = start_idx + window_size if i < walk_forward_windows - 1 else len(df)
                window_df = df.iloc[start_idx:end_idx]

                if len(window_df) == 0:
                    continue

                # Evaluate trades in this window
                outcomes_and_r = []
                for _, row in window_df.iterrows():
                    outcome, r_achieved = evaluate_trade_outcome(
                        break_dir=row['break_dir'],
                        orb_high=row['orb_high'],
                        orb_low=row['orb_low'],
                        mae=row['mae'],
                        mfe=row['mfe'],
                        rr=rr,
                        sl_mode=filter_spec.get('sl_mode', 'FULL')
                    )
                    outcomes_and_r.append((outcome, r_achieved))

                metrics_data = calculate_metrics(outcomes_and_r)
                avg_r = metrics_data['avg_r']
                wf_results.append(avg_r)
            
            import statistics
            wf_avg_r = statistics.mean(wf_results) if wf_results else 0.0
            wf_std_r = statistics.stdev(wf_results) if len(wf_results) > 1 else 0.0
            
            median_atr = df['atr'].median() if 'atr' in df.columns else 0
            high_vol_df = df[df['atr'] > median_atr]
            low_vol_df = df[df['atr'] <= median_atr]
            
            regime_results = {}
            for regime_name, regime_df in [("high_vol", high_vol_df), ("low_vol", low_vol_df)]:
                if len(regime_df) > 0:
                    # Evaluate trades in this regime
                    outcomes_and_r = []
                    for _, row in regime_df.iterrows():
                        outcome, r_achieved = evaluate_trade_outcome(
                            break_dir=row['break_dir'],
                            orb_high=row['orb_high'],
                            orb_low=row['orb_low'],
                            mae=row['mae'],
                            mfe=row['mfe'],
                            rr=rr,
                            sl_mode=filter_spec.get('sl_mode', 'FULL')
                        )
                        outcomes_and_r.append((outcome, r_achieved))

                    metrics_data = calculate_metrics(outcomes_and_r)
                    regime_results[regime_name] = {
                        "avg_r": metrics_data['avg_r'],
                        "n": metrics_data['total_trades'],
                        "win_rate": metrics_data['win_rate']
                    }
            
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
                is_robust=is_robust
            )

            logger.info(f"  Robustness: WF avg_r={robustness.walk_forward_avg_r:+.3f}R, std={robustness.walk_forward_std_r:.3f}R, robust={robustness.is_robust}")
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

        # Build robustness JSON
        robustness_json = {
            "walk_forward_periods": robustness.walk_forward_periods,
            "walk_forward_avg_r": robustness.walk_forward_avg_r,
            "walk_forward_std_r": robustness.walk_forward_std_r,
            "regime_split_results": robustness.regime_split_results,
            "is_robust": robustness.is_robust
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
            # Default test config
            test_config = {
                "random_seed": 42,
                "walk_forward_windows": 4,
                "train_pct": 0.7,
                "regime_detection": "volatility_quartiles",
                "slippage_ticks": 1,
                "commission_per_side": 0.62
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
