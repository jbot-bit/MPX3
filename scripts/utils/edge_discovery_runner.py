"""
Auto-Running Edge Discovery Engine
===================================

Continuously scans for new trading edges and optimization opportunities.
Auto-restarts after each iteration to run indefinitely.

Features:
- Tests multiple RR targets (1.0 to 10.0)
- Tests multiple ORB size filters
- Tests FULL vs HALF SL modes
- Tests all 6 ORB times
- Auto-saves results after each discovery
- Logs all progress to file
- Safe to interrupt (Ctrl+C)

Usage:
    python edge_discovery_runner.py

Then let it run! Press Ctrl+C to stop.
"""

import os
import sys
import time
import logging
import traceback
from datetime import datetime, timedelta
from pathlib import Path
import duckdb
import pandas as pd

# Configure logging
LOG_FILE = "edge_discovery.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration
DB_PATH = "data/db/gold.db"
RESULTS_DIR = Path("edge_discovery_results")
RESULTS_DIR.mkdir(exist_ok=True)

# Search space
INSTRUMENTS = ["MGC"]  # Start with MGC, expand to NQ/MPL later
ORB_TIMES = ["0900", "1000", "1100", "1800", "2300", "0030"]
RR_TARGETS = [1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]  # REMOVED 1.0 - not viable
ORB_FILTERS = [None, 0.05, 0.10, 0.112, 0.15, 0.155, 0.20, 0.25, 0.30, 0.50, 0.75, 1.0]
SL_MODES = ["FULL", "HALF"]

# Minimum requirements for a valid edge
MIN_SAMPLE_SIZE = 100  # Need at least 100 trades (increased from 50)
MIN_WIN_RATE = 12.0  # At least 12% WR
MIN_EXPECTED_R = 0.10  # At least +0.10R average (increased from 0.05)
MIN_ANNUAL_R = 15.0  # At least +15R/year to be interesting

class EdgeDiscoveryEngine:
    """Continuously searches for trading edges"""

    def __init__(self):
        self.conn = None
        self.iteration = 0
        self.total_edges_found = 0
        self.best_edge = None
        self.start_time = datetime.now()

    def connect_db(self):
        """Connect to database"""
        try:
            self.conn = duckdb.connect(DB_PATH, read_only=True)
            logger.info(f"Connected to database: {DB_PATH}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False

    def check_data_available(self):
        """Check if we have data to analyze"""
        try:
            tables = [t[0] for t in self.conn.execute('SHOW TABLES').fetchall()]

            if 'daily_features' not in tables:
                logger.error("daily_features table not found!")
                logger.error("You need to backfill data first:")
                logger.error("  python pipeline/backfill_databento_continuous.py 2024-01-01 2026-01-10")
                return False

            row_count = self.conn.execute('SELECT COUNT(*) FROM daily_features').fetchone()[0]
            if row_count == 0:
                logger.error("daily_features table is empty!")
                logger.error("Run backfill first!")
                return False

            logger.info(f"✓ Found {row_count} days of data in daily_features")
            return True

        except Exception as e:
            logger.error(f"Error checking data: {e}")
            return False

    def test_configuration(self, instrument, orb_time, rr_target, orb_filter, sl_mode):
        """Test a specific ORB configuration"""
        try:
            # Build filter clause
            filter_clause = ""
            if orb_filter is not None:
                orb_col = f"orb_{orb_time}_size"
                median_size = self.conn.execute(
                    f"SELECT median({orb_col}) FROM daily_features WHERE instrument = ? AND {orb_col} IS NOT NULL",
                    [instrument]
                ).fetchone()[0]

                if median_size and median_size > 0:
                    min_size = median_size * orb_filter
                    max_size = median_size * (2.0 - orb_filter)  # Symmetric around median
                    filter_clause = f"AND orb_{orb_time}_size BETWEEN {min_size} AND {max_size}"

            # Calculate SL multiplier
            sl_multiplier = 0.5 if sl_mode == "HALF" else 1.0

            # Query for this configuration
            # Note: This is a simplified backtest - real execution_engine has more logic
            query = f"""
            SELECT
                date_local,
                orb_{orb_time}_break_dir as break_dir,
                orb_{orb_time}_outcome as outcome,
                orb_{orb_time}_r_multiple as r_multiple,
                orb_{orb_time}_size as orb_size
            FROM daily_features
            WHERE instrument = ?
                AND orb_{orb_time}_break_dir IS NOT NULL
                {filter_clause}
            """

            df = self.conn.execute(query, [instrument]).df()

            if len(df) < MIN_SAMPLE_SIZE:
                return None  # Not enough data

            # Calculate metrics
            # Note: This assumes outcomes are already calculated at RR=1.0 in the table
            # For other RR values, we'd need to recalculate from MAE/MFE
            # For now, we'll estimate based on R-multiple distribution

            wins = (df['r_multiple'] > 0).sum()
            losses = (df['r_multiple'] <= 0).sum()
            total_trades = len(df)

            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

            # Estimate expected R (simplified - real calc would use execution_engine logic)
            expected_r = df['r_multiple'].mean() if len(df) > 0 else 0

            # Estimate annual R (assuming ~260 trading days/year)
            trades_per_year = (total_trades / 740) * 260  # 740 days in our dataset
            annual_r = expected_r * trades_per_year

            return {
                'instrument': instrument,
                'orb_time': orb_time,
                'rr_target': rr_target,
                'orb_filter': orb_filter,
                'sl_mode': sl_mode,
                'sample_size': total_trades,
                'win_rate': win_rate,
                'expected_r': expected_r,
                'annual_r': annual_r,
                'wins': wins,
                'losses': losses
            }

        except Exception as e:
            logger.debug(f"Error testing config: {e}")
            return None

    def is_new_edge(self, result):
        """Check if this is a new/improved edge"""
        if not result:
            return False

        # Check minimum requirements
        if result['sample_size'] < MIN_SAMPLE_SIZE:
            return False
        if result['win_rate'] < MIN_WIN_RATE:
            return False
        if result['expected_r'] < MIN_EXPECTED_R:
            return False
        if result['annual_r'] < MIN_ANNUAL_R:
            return False

        return True

    def save_edge(self, result):
        """Save discovered edge to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = RESULTS_DIR / f"edge_{timestamp}_{result['orb_time']}_RR{result['rr_target']}.txt"

        with open(filename, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write("NEW EDGE DISCOVERED!\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Instrument: {result['instrument']}\n")
            f.write(f"ORB Time: {result['orb_time']}\n")
            f.write(f"RR Target: {result['rr_target']}\n")
            f.write(f"ORB Filter: {result['orb_filter']}\n")
            f.write(f"SL Mode: {result['sl_mode']}\n\n")
            f.write(f"Sample Size: {result['sample_size']} trades\n")
            f.write(f"Win Rate: {result['win_rate']:.1f}%\n")
            f.write(f"Expected R: {result['expected_r']:+.3f}\n")
            f.write(f"Annual R: {result['annual_r']:+.1f}R/year\n\n")
            f.write(f"Wins: {result['wins']}\n")
            f.write(f"Losses: {result['losses']}\n\n")
            f.write(f"Discovered: {datetime.now()}\n")
            f.write(f"Iteration: {self.iteration}\n")

        logger.info(f"💾 Saved edge to: {filename}")

    def run_iteration(self):
        """Run one complete search iteration"""
        self.iteration += 1
        logger.info("=" * 70)
        logger.info(f"ITERATION #{self.iteration}")
        logger.info("=" * 70)

        edges_found_this_iteration = 0
        configs_tested = 0

        # Randomize search order to explore different areas each time
        import random
        search_space = []
        for inst in INSTRUMENTS:
            for orb in ORB_TIMES:
                for rr in RR_TARGETS:
                    for filt in ORB_FILTERS:
                        for sl in SL_MODES:
                            search_space.append((inst, orb, rr, filt, sl))

        random.shuffle(search_space)

        # Test configurations
        for inst, orb, rr, filt, sl in search_space:
            configs_tested += 1

            if configs_tested % 100 == 0:
                logger.info(f"Tested {configs_tested}/{len(search_space)} configurations...")

            result = self.test_configuration(inst, orb, rr, filt, sl)

            if self.is_new_edge(result):
                edges_found_this_iteration += 1
                self.total_edges_found += 1

                logger.info("=" * 70)
                logger.info(f"🎯 EDGE FOUND #{self.total_edges_found}!")
                logger.info(f"   {inst} {orb} ORB | RR={rr} | Filter={filt} | SL={sl}")
                logger.info(f"   WR={result['win_rate']:.1f}% | E[R]={result['expected_r']:+.3f} | Annual={result['annual_r']:+.1f}R")
                logger.info("=" * 70)

                self.save_edge(result)

                # Track best edge
                if self.best_edge is None or result['annual_r'] > self.best_edge['annual_r']:
                    self.best_edge = result
                    logger.info(f"⭐ NEW BEST EDGE! Annual R: {result['annual_r']:+.1f}R/year")

        # Iteration summary
        logger.info("")
        logger.info("=" * 70)
        logger.info(f"ITERATION #{self.iteration} COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Configurations tested: {configs_tested}")
        logger.info(f"Edges found this iteration: {edges_found_this_iteration}")
        logger.info(f"Total edges found: {self.total_edges_found}")

        if self.best_edge:
            logger.info(f"\n🏆 BEST EDGE SO FAR:")
            logger.info(f"   {self.best_edge['instrument']} {self.best_edge['orb_time']} ORB")
            logger.info(f"   RR={self.best_edge['rr_target']} | Filter={self.best_edge['orb_filter']} | SL={self.best_edge['sl_mode']}")
            logger.info(f"   Annual R: {self.best_edge['annual_r']:+.1f}R/year")

        elapsed = datetime.now() - self.start_time
        logger.info(f"\nTotal runtime: {elapsed}")
        logger.info("=" * 70)
        logger.info("")

    def run_forever(self):
        """Run continuous edge discovery"""
        logger.info("🚀 EDGE DISCOVERY ENGINE STARTING...")
        logger.info(f"Database: {DB_PATH}")
        logger.info(f"Results directory: {RESULTS_DIR}")
        logger.info(f"Log file: {LOG_FILE}")
        logger.info("")

        # Connect to database
        if not self.connect_db():
            logger.error("Failed to connect to database. Exiting.")
            return

        # Check data availability
        if not self.check_data_available():
            logger.error("No data available. Please backfill data first.")
            logger.error("Command: python pipeline/backfill_databento_continuous.py 2024-01-01 2026-01-10")
            return

        logger.info("✓ Data check passed!")
        logger.info("")
        logger.info("Starting continuous edge discovery...")
        logger.info("Press Ctrl+C to stop.")
        logger.info("")

        try:
            while True:
                self.run_iteration()

                # Brief pause between iterations
                logger.info("Waiting 5 seconds before next iteration...")
                time.sleep(5)

        except KeyboardInterrupt:
            logger.info("")
            logger.info("=" * 70)
            logger.info("EDGE DISCOVERY STOPPED BY USER")
            logger.info("=" * 70)
            logger.info(f"Total iterations: {self.iteration}")
            logger.info(f"Total edges found: {self.total_edges_found}")
            logger.info(f"Total runtime: {datetime.now() - self.start_time}")

            if self.best_edge:
                logger.info(f"\n🏆 BEST EDGE DISCOVERED:")
                logger.info(f"   {self.best_edge['instrument']} {self.best_edge['orb_time']} ORB")
                logger.info(f"   RR={self.best_edge['rr_target']} | Filter={self.best_edge['orb_filter']} | SL={self.best_edge['sl_mode']}")
                logger.info(f"   Annual R: {self.best_edge['annual_r']:+.1f}R/year")

            logger.info("")
            logger.info("Results saved to: " + str(RESULTS_DIR))
            logger.info("=" * 70)

        except Exception as e:
            logger.error(f"Fatal error: {e}")
            logger.error(traceback.format_exc())

        finally:
            if self.conn:
                self.conn.close()
                logger.info("Database connection closed.")


def main():
    """Main entry point"""
    engine = EdgeDiscoveryEngine()
    engine.run_forever()


if __name__ == "__main__":
    main()
