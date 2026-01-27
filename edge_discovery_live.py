"""
LIVE Edge Discovery Engine - Uses Your Actual Backtest Data
=============================================================

Analyzes your existing backtest CSV files to find:
1. New edges not yet in validated_setups
2. Improvements to existing setups
3. Hidden patterns in the data

Auto-runs and auto-restarts. Press Ctrl+C to stop.
"""

import pandas as pd
import numpy as np
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
import duckdb
import random

# Configure logging
LOG_FILE = "edge_discovery_live.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Paths
DB_PATH = "data/db/gold.db"
BACKTEST_CSV = "data/exports/ALL_ORBS_EXTENDED_WINDOWS.csv"
RESULTS_DIR = Path("edge_discovery_results")
RESULTS_DIR.mkdir(exist_ok=True)

# Edge criteria
MIN_TRADES = 100  # Need at least 100 trades
MIN_WIN_RATE = 12.0  # At least 12% WR
MIN_AVG_R = 0.10  # At least +0.10R average
MIN_ANNUAL_R = 15.0  # At least +15R/year

class LiveEdgeDiscovery:
    """Discovers edges from backtest data"""

    def __init__(self):
        self.backtest_data = None
        self.validated_setups = []
        self.new_edges = []
        self.saved_edges = set()  # Track saved edges to avoid duplicates
        self.iteration = 0
        self.total_found = 0
        self.start_time = datetime.now()

    def load_backtest_data(self):
        """Load backtest CSV"""
        try:
            self.backtest_data = pd.read_csv(BACKTEST_CSV)
            logger.info(f"[OK] Loaded {len(self.backtest_data)} backtest results")
            logger.info(f"  ORBs: {sorted(self.backtest_data['orb'].unique())}")
            logger.info(f"  RR range: {self.backtest_data['rr'].min()}-{self.backtest_data['rr'].max()}")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Failed to load {BACKTEST_CSV}: {e}")
            return False

    def load_validated_setups(self):
        """Load current validated setups from database"""
        try:
            conn = duckdb.connect(DB_PATH, read_only=True)
            df = conn.execute("""
                SELECT orb_time, rr, sl_mode, win_rate, expected_r
                FROM validated_setups
                WHERE instrument = 'MGC'
            """).df()
            conn.close()

            self.validated_setups = df.to_dict('records')
            logger.info(f"[OK] Loaded {len(self.validated_setups)} validated MGC setups")

            # Show what we already have
            if self.validated_setups:
                logger.info("  Current validated setups:")
                for setup in sorted(self.validated_setups, key=lambda x: -x['expected_r'])[:3]:
                    logger.info(f"    {setup['orb_time']} ORB: RR={setup['rr']}, E[R]={setup['expected_r']:.3f}")

            return True
        except Exception as e:
            logger.error(f"[ERROR] Failed to load validated setups: {e}")
            return False

    def calculate_annual_r(self, avg_r, trades):
        """Estimate annual R given avg R and trade count"""
        # Assuming 740 days of data (from SCAN_WINDOW_BUG_FIX_SUMMARY.md)
        # and ~260 trading days per year
        trades_per_year = (trades / 740) * 260
        return avg_r * trades_per_year

    def is_new_edge(self, row):
        """Check if this backtest result is a new edge"""
        # Skip RR=1.0 (not viable per user request)
        if row['rr'] == 1.0:
            return False

        # Check minimum criteria
        if row['trades'] < MIN_TRADES:
            return False
        if row['win_rate'] < MIN_WIN_RATE / 100:  # Convert to decimal
            return False
        if row['avg_r'] < MIN_AVG_R:
            return False

        annual_r = self.calculate_annual_r(row['avg_r'], row['trades'])
        if annual_r < MIN_ANNUAL_R:
            return False

        # Check if already validated
        orb_str = f"{int(row['orb']):04d}"  # Convert 900 -> "0900"
        sl_mode = row['sl_mode'].upper()

        for setup in self.validated_setups:
            if (setup['orb_time'] == orb_str and
                setup['rr'] == row['rr'] and
                setup['sl_mode'] == sl_mode):
                return False  # Already validated

        return True

    def is_improvement(self, row):
        """Check if this improves an existing validated setup"""
        orb_str = f"{int(row['orb']):04d}"
        sl_mode = row['sl_mode'].upper()

        for setup in self.validated_setups:
            if (setup['orb_time'] == orb_str and
                setup['sl_mode'] == sl_mode):
                # Same ORB and SL mode, different RR
                if row['rr'] != setup['rr'] and row['avg_r'] > setup['expected_r'] * 1.05:
                    # At least 5% improvement
                    return True, setup

        return False, None

    def save_edge(self, row, edge_type="NEW"):
        """Save discovered edge"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        orb_str = f"{int(row['orb']):04d}"
        filename = RESULTS_DIR / f"{edge_type}_{timestamp}_{orb_str}_RR{row['rr']}.txt"

        annual_r = self.calculate_annual_r(row['avg_r'], row['trades'])

        with open(filename, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write(f"{edge_type} EDGE DISCOVERED!\n")
            f.write("=" * 70 + "\n\n")

            f.write(f"ORB Time: {orb_str}\n")
            f.write(f"RR Target: {row['rr']}\n")
            f.write(f"SL Mode: {row['sl_mode'].upper()}\n\n")

            f.write("PERFORMANCE:\n")
            f.write(f"  Sample Size: {row['trades']} trades\n")
            f.write(f"  Win Rate: {row['win_rate']*100:.1f}%\n")
            f.write(f"  Wins: {row['wins']}\n")
            f.write(f"  Losses: {row['trades'] - row['wins']}\n")
            f.write(f"  Avg R: {row['avg_r']:+.3f}\n")
            f.write(f"  Total R: {row['total_r']:+.1f}\n")
            f.write(f"  Estimated Annual R: {annual_r:+.1f}R/year\n\n")

            f.write(f"Discovered: {datetime.now()}\n")
            f.write(f"Iteration: {self.iteration}\n")
            f.write(f"Data Source: {BACKTEST_CSV}\n")

        return filename

    def run_iteration(self):
        """Run one discovery iteration"""
        self.iteration += 1
        logger.info("=" * 70)
        logger.info(f"ITERATION #{self.iteration}")
        logger.info("=" * 70)

        found_this_iteration = 0

        # Shuffle data to explore in different order each time
        df = self.backtest_data.sample(frac=1.0).reset_index(drop=True)

        for idx, row in df.iterrows():
            # Check for new edges
            if self.is_new_edge(row):
                # Create unique key for this edge
                orb_str = f"{int(row['orb']):04d}"
                edge_key = (orb_str, row['rr'], row['sl_mode'].upper())

                # Skip if already saved
                if edge_key in self.saved_edges:
                    continue

                found_this_iteration += 1
                self.total_found += 1
                self.saved_edges.add(edge_key)

                annual_r = self.calculate_annual_r(row['avg_r'], row['trades'])

                logger.info(f"   [NEW EDGE] #{self.total_found}!")
                logger.info(f"      {orb_str} ORB | RR={row['rr']} | SL={row['sl_mode'].upper()}")
                logger.info(f"      WR={row['win_rate']*100:.1f}% | Avg R={row['avg_r']:+.3f} | Annual~={annual_r:+.1f}R")

                filename = self.save_edge(row, "NEW")
                logger.info(f"      [SAVED] {filename.name}")

                self.new_edges.append(row.to_dict())

            # Check for improvements
            is_better, baseline = self.is_improvement(row)
            if is_better:
                # Create unique key for this improvement
                orb_str = f"{int(row['orb']):04d}"
                edge_key = (orb_str, row['rr'], row['sl_mode'].upper(), 'IMPROVE')

                # Skip if already saved
                if edge_key in self.saved_edges:
                    continue

                found_this_iteration += 1
                self.total_found += 1
                self.saved_edges.add(edge_key)

                improvement = (row['avg_r'] / baseline['expected_r'] - 1) * 100

                logger.info(f"   [IMPROVE] IMPROVEMENT #{self.total_found}!")
                logger.info(f"      {orb_str} ORB | RR={baseline['rr']}->{row['rr']}")
                logger.info(f"      E[R]: {baseline['expected_r']:.3f}->{row['avg_r']:.3f} ({improvement:+.1f}%)")

                filename = self.save_edge(row, "IMPROVEMENT")
                logger.info(f"      [SAVED] {filename.name}")

        # Summary
        logger.info("")
        logger.info("ITERATION COMPLETE")
        logger.info(f"  Edges found: {found_this_iteration}")
        logger.info(f"  Total found: {self.total_found}")

        if self.new_edges:
            best = max(self.new_edges, key=lambda x: self.calculate_annual_r(x['avg_r'], x['trades']))
            annual_r = self.calculate_annual_r(best['avg_r'], best['trades'])
            orb_str = f"{int(best['orb']):04d}"

            logger.info(f"\n  [BEST] BEST NEW EDGE:")
            logger.info(f"     {orb_str} ORB | RR={best['rr']} | Annual~={annual_r:+.1f}R")

        logger.info(f"\n  Runtime: {datetime.now() - self.start_time}")
        logger.info("=" * 70)
        logger.info("")

    def analyze_patterns(self):
        """Analyze backtest data for patterns"""
        logger.info("\n[DATA] DATA ANALYSIS:")

        # Best RR by ORB
        logger.info("\nOptimal RR by ORB (highest avg_r):")
        for orb in sorted(self.backtest_data['orb'].unique()):
            orb_data = self.backtest_data[self.backtest_data['orb'] == orb]
            best = orb_data.loc[orb_data['avg_r'].idxmax()]
            annual_r = self.calculate_annual_r(best['avg_r'], best['trades'])
            logger.info(f"  {int(orb):04d} ORB: RR={best['rr']:4.1f} | {best['sl_mode']:4s} | E[R]={best['avg_r']:+.3f} | Annual~={annual_r:+.0f}R")

        # SL mode comparison
        logger.info("\nFULL vs HALF SL comparison:")
        for sl_mode in ['full', 'half']:
            data = self.backtest_data[self.backtest_data['sl_mode'] == sl_mode]
            avg_r = data['avg_r'].mean()
            logger.info(f"  {sl_mode.upper():4s} SL: Average E[R] = {avg_r:+.3f}")

        logger.info("")

    def save_summary(self):
        """Save summary CSV of all discovered edges"""
        if not self.new_edges:
            logger.info("No edges to summarize")
            return

        import csv
        summary_file = RESULTS_DIR / "SUMMARY.csv"

        with open(summary_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'ORB', 'RR', 'SL_Mode', 'Trades', 'Win_Rate_%',
                'Avg_R', 'Total_R', 'Annual_R_Est'
            ])

            # Sort by annual R (best first)
            sorted_edges = sorted(
                self.new_edges,
                key=lambda x: self.calculate_annual_r(x['avg_r'], x['trades']),
                reverse=True
            )

            for edge in sorted_edges:
                annual_r = self.calculate_annual_r(edge['avg_r'], edge['trades'])
                orb_str = f"{int(edge['orb']):04d}"
                writer.writerow([
                    orb_str,
                    edge['rr'],
                    edge['sl_mode'].upper(),
                    edge['trades'],
                    f"{edge['win_rate']*100:.1f}",
                    f"{edge['avg_r']:+.3f}",
                    f"{edge['total_r']:+.1f}",
                    f"{annual_r:+.1f}"
                ])

        logger.info(f"[OK] Summary saved: {summary_file}")

    def run_forever(self):
        """Main loop"""
        logger.info("=" * 70)
        logger.info("LIVE EDGE DISCOVERY ENGINE")
        logger.info("=" * 70)
        logger.info(f"Data source: {BACKTEST_CSV}")
        logger.info(f"Results: {RESULTS_DIR}/")
        logger.info(f"Log: {LOG_FILE}")
        logger.info("")

        if not self.load_backtest_data():
            return

        if not self.load_validated_setups():
            return

        self.analyze_patterns()

        logger.info("[OK] Ready to discover edges!")
        logger.info("")

        # Run one thorough scan
        self.run_iteration()

        # Save summary
        logger.info("")
        self.save_summary()

        # Final summary
        logger.info("")
        logger.info("=" * 70)
        logger.info("DISCOVERY COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Unique edges found: {self.total_found}")
        logger.info(f"Runtime: {datetime.now() - self.start_time}")
        logger.info(f"\nResults saved to: {RESULTS_DIR}/")
        logger.info("=" * 70)


def main():
    engine = LiveEdgeDiscovery()
    engine.run_forever()


if __name__ == "__main__":
    main()
