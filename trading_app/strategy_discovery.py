"""
STRATEGY DISCOVERY ENGINE
Backtest new ORB configurations and add profitable setups to production.
"""

import duckdb
import pandas as pd
from dataclasses import dataclass
from typing import List, Optional, Dict
import logging
from pathlib import Path
import os

logger = logging.getLogger(__name__)

@dataclass
class DiscoveryConfig:
    """Configuration for backtesting"""
    instrument: str  # MGC, NQ, MPL
    orb_time: str    # 0900, 1000, 1100, 1800, 2300, 0030
    rr: float        # Risk/Reward multiple (1.0, 1.5, 3.0, 6.0, 8.0, etc.)
    sl_mode: str     # FULL or HALF
    orb_size_filter: Optional[float] = None  # % of ATR (0.10, 0.15, etc.) or None

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
    """Backtest engine for discovering profitable ORB configurations"""

    def __init__(self):
        self.feature_tables = {
            "MGC": "daily_features",
            "NQ": "daily_features_nq",
            "MPL": "daily_features_mpl"
        }

        # Instrument point values (for P&L calculation)
        self.point_values = {
            "MGC": 10,  # $10/point
            "NQ": 2,    # $2/point
            "MPL": 5    # $5/point (micro)
        }

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
        Backtest a single ORB configuration against historical data.

        Returns BacktestResult with win rate, avg R, and tier assignment.
        """
        table = self.feature_tables.get(config.instrument)
        if not table:
            raise ValueError(f"Unknown instrument: {config.instrument}")

        orb_prefix = f"orb_{config.orb_time}"

        query = f"""
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

        if config.orb_size_filter is not None:
            df = df[df['orb_size'] <= (df['atr'] * config.orb_size_filter)]

        total_trades = len(df)
        if total_trades == 0:
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
                rr=config.rr,
                sl_mode=config.sl_mode
            )
            outcomes_and_r.append((outcome, r_achieved))

        # Calculate metrics from evaluated trades
        metrics_data = calculate_metrics(outcomes_and_r)
        wins = metrics_data['wins']
        losses = metrics_data['losses']
        total_trades = metrics_data['total_trades']
        win_rate = (metrics_data['win_rate'] * 100) if total_trades > 0 else 0
        total_r = metrics_data['total_r']
        avg_r = metrics_data['avg_r']

        date_range_days = (df['date_local'].max() - df['date_local'].min()).days
        years = date_range_days / 365.25 if date_range_days > 0 else 1
        annual_trades = int(total_trades / years)

        tier = self._assign_tier(win_rate, avg_r)

        return BacktestResult(
            config=config,
            total_trades=total_trades,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            avg_r=avg_r,
            annual_trades=annual_trades,
            tier=tier,
            total_r=total_r
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
    if result.config.orb_time in ['2300', '0030']:
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
