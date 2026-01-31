"""
Data Bridge - Automatically fills gaps between historical DB and live market data

CRITICAL PROBLEM:
- Historical data in DB ends at some date (e.g., 2026-01-10)
- Market scanner needs TODAY's data (2026-01-25)
- Gap = app is useless without current data

SOLUTION:
- Detect gap between last DB date and today
- Backfill from appropriate source:
  - Databento: For deep history (> 7 days old)
  - ProjectX: For recent data (< 7 days old)
- Handle timezone consistency (both sources → Australia/Brisbane)
- Run automatically when app starts

USAGE:
    from trading_app.data_bridge import DataBridge

    bridge = DataBridge()
    bridge.update_to_current()  # Auto-fills gap to today
"""

import duckdb
import subprocess
import sys
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

from trading_app.config import DB_PATH, TZ_LOCAL

# Phase 3B: Logging for subprocess visibility
logger = logging.getLogger(__name__)

# Phase 3B: Subprocess timeouts (seconds)
BACKFILL_TIMEOUT = 300  # 5 minutes for backfill operations
FEATURE_BUILD_TIMEOUT = 60  # 1 minute per day for feature building


class DataBridge:
    """Bridges historical DB data with live market data"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.tz_local = TZ_LOCAL

        # Source selection thresholds
        # IMPORTANT: Prefer single source for consistency
        # Price differences between Databento (settlement) and ProjectX (real-time) can cause:
        # - Slightly different ORB sizes (e.g., 0.08 vs 0.09)
        # - Price jump at stitching point (where sources meet)
        # Solution: Use ProjectX for ALL recent data to maintain consistency
        self.DATABENTO_CUTOFF_DAYS = 30  # Use Databento for data > 30 days old
        self.PROJECTX_CUTOFF_DAYS = 0    # Use ProjectX for recent data (0-30 days)

        # Path to backfill scripts
        self.root_dir = Path(__file__).parent.parent
        self.databento_script = self.root_dir / "pipeline" / "backfill_databento_continuous.py"
        self.projectx_script = self.root_dir / "pipeline" / "backfill_range.py"
        self.features_script = self.root_dir / "pipeline" / "build_daily_features.py"

    def get_last_db_date(self, instrument: str = 'MGC') -> Optional[date]:
        """
        Get the last date with data in daily_features.

        Returns:
            Last date with data, or None if no data exists
        """
        try:
            conn = duckdb.connect(self.db_path, read_only=True)
            query = """
                SELECT MAX(date_local) as last_date
                FROM daily_features
                WHERE instrument = ?
            """
            result = conn.execute(query, [instrument]).fetchone()
            conn.close()

            if result and result[0]:
                # Convert string to date if needed
                last_date = result[0]
                if isinstance(last_date, str):
                    last_date = date.fromisoformat(last_date)
                return last_date
            return None

        except Exception as e:
            print(f"Error getting last DB date: {e}")
            return None

    def get_current_date_local(self) -> date:
        """Get current date in local timezone (Australia/Brisbane)"""
        now_local = datetime.now(self.tz_local)
        return now_local.date()

    def detect_gap(self, instrument: str = 'MGC') -> Tuple[Optional[date], Optional[date], int]:
        """
        Detect gap between last DB date and current date.

        Returns:
            (last_db_date, current_date, gap_days)
            gap_days = 0 means no gap (data is current)
            gap_days = -1 means no historical data exists
        """
        last_db_date = self.get_last_db_date(instrument)
        current_date = self.get_current_date_local()

        if last_db_date is None:
            # No data in DB at all
            return (None, current_date, -1)

        # Calculate gap in days
        gap_days = (current_date - last_db_date).days

        return (last_db_date, current_date, gap_days)

    def select_backfill_source(self, start_date: date, end_date: date) -> str:
        """
        Select appropriate backfill source based on date range.

        Logic:
        - Databento: For historical data (> 7 days old from today)
        - ProjectX: For recent data (0-7 days old)

        This handles:
        - Different timezone handling per source
        - Different API capabilities (Databento better for deep history)
        - ProjectX may have limitations on historical range

        Returns:
            'databento' or 'projectx'
        """
        current_date = self.get_current_date_local()
        days_ago = (current_date - end_date).days

        if days_ago > self.DATABENTO_CUTOFF_DAYS:
            return 'databento'
        else:
            return 'projectx'

    def run_backfill(self, start_date: date, end_date: date, source: str) -> bool:
        """
        Run backfill script for date range.

        Args:
            start_date: Start of range (inclusive)
            end_date: End of range (inclusive)
            source: 'databento' or 'projectx'

        Returns:
            True if successful, False otherwise
        """
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()

        print(f"\n[INFO] Backfilling {start_str} to {end_str} from {source.upper()}...")

        try:
            if source == 'databento':
                if not self.databento_script.exists():
                    print(f"[ERROR] Databento script not found: {self.databento_script}")
                    return False

                # Phase 3B: Use sys.executable, shell=False, timeout
                cmd = [sys.executable, str(self.databento_script), start_str, end_str]
                print(f"[CMD] {' '.join(cmd)}")
                result = subprocess.run(
                    cmd,
                    cwd=str(self.root_dir),
                    capture_output=True,
                    text=True,
                    timeout=BACKFILL_TIMEOUT
                )

                # Phase 3B: Log stdout/stderr for visibility
                if result.stdout:
                    logger.debug(f"Databento backfill stdout: {result.stdout[-2000:]}")
                if result.returncode != 0:
                    print(f"[ERROR] Databento backfill failed:")
                    print(result.stderr)
                    logger.error(f"Databento backfill failed: {result.stderr}")
                    return False

                print(f"[OK] Databento backfill completed")
                return True

            elif source == 'projectx':
                if not self.projectx_script.exists():
                    print(f"[ERROR] ProjectX script not found: {self.projectx_script}")
                    return False

                # Phase 3B: Use sys.executable, shell=False, timeout
                cmd = [sys.executable, str(self.projectx_script), start_str, end_str]
                print(f"[CMD] {' '.join(cmd)}")
                result = subprocess.run(
                    cmd,
                    cwd=str(self.root_dir),
                    capture_output=True,
                    text=True,
                    timeout=BACKFILL_TIMEOUT
                )

                # Phase 3B: Log stdout/stderr for visibility
                if result.stdout:
                    logger.debug(f"ProjectX backfill stdout: {result.stdout[-2000:]}")
                if result.returncode != 0:
                    print(f"[ERROR] ProjectX backfill failed:")
                    print(result.stderr)
                    logger.error(f"ProjectX backfill failed: {result.stderr}")
                    return False

                print(f"[OK] ProjectX backfill completed")
                return True

            else:
                print(f"[ERROR] Unknown source: {source}")
                return False

        except subprocess.TimeoutExpired:
            print(f"[ERROR] Backfill timed out after {BACKFILL_TIMEOUT}s")
            logger.error(f"Backfill timed out after {BACKFILL_TIMEOUT}s for {source}")
            return False

        except Exception as e:
            print(f"[ERROR] Exception during backfill: {e}")
            logger.error(f"Exception during backfill: {e}")
            return False

    def build_features(self, start_date: date, end_date: date) -> bool:
        """
        Run build_daily_features.py for date range.

        This computes ORBs, session stats, etc. from raw bars data.

        Args:
            start_date: Start of range
            end_date: End of range

        Returns:
            True if successful, False otherwise
        """
        print(f"\n[INFO] Building daily features for {start_date} to {end_date}...")

        try:
            if not self.features_script.exists():
                print(f"[ERROR] Features script not found: {self.features_script}")
                return False

            # build_daily_features.py may only take single date at a time
            # Run for each date in range
            # Phase 3B: Calculate total days for progress visibility
            total_days = (end_date - start_date).days + 1
            current = start_date
            day_num = 0

            while current <= end_date:
                day_num += 1
                date_str = current.isoformat()

                # Phase 3B: Progress visibility
                print(f"[INFO] Building features: day {day_num} of {total_days} ({date_str})")

                # Phase 3B: Use sys.executable, shell=False, timeout
                cmd = [sys.executable, str(self.features_script), date_str]

                try:
                    result = subprocess.run(
                        cmd,
                        cwd=str(self.root_dir),
                        capture_output=True,
                        text=True,
                        timeout=FEATURE_BUILD_TIMEOUT
                    )

                    if result.returncode != 0:
                        print(f"[WARNING] Feature build failed for {date_str}:")
                        print(result.stderr)
                        logger.warning(f"Feature build failed for {date_str}: {result.stderr}")
                        # Continue with next date

                except subprocess.TimeoutExpired:
                    print(f"[WARNING] Feature build timed out for {date_str} (>{FEATURE_BUILD_TIMEOUT}s)")
                    logger.warning(f"Feature build timed out for {date_str}")
                    # Continue with next date

                current += timedelta(days=1)

            print(f"[OK] Feature building completed")
            return True

        except Exception as e:
            print(f"[ERROR] Exception during feature building: {e}")
            return False

    def fill_gap(self, last_db_date: Optional[date], current_date: date, instrument: str = 'MGC') -> bool:
        """
        Fill gap between last DB date and current date.

        Strategy:
        1. If no data exists, backfill last 30 days (reasonable default)
        2. If gap exists, backfill from (last_db_date + 1) to current_date
        3. Select source based on date range (Databento vs ProjectX)
        4. Run backfill
        5. Build features

        Args:
            last_db_date: Last date in DB (None if no data)
            current_date: Current date (today)
            instrument: Instrument to backfill

        Returns:
            True if successful, False otherwise
        """
        if last_db_date is None:
            # No data exists - backfill last 30 days as reasonable default
            print(f"\n[WARN] No historical data found for {instrument}")
            print(f"[INFO] Backfilling last 30 days as starting point...")
            start_date = current_date - timedelta(days=30)
            end_date = current_date
        else:
            # Gap exists - fill from day after last_db_date to current_date
            start_date = last_db_date + timedelta(days=1)
            end_date = current_date

            if start_date > end_date:
                print(f"[OK] No gap - data is current (last date: {last_db_date})")
                return True

        print(f"\n{'='*70}")
        print(f"DATA BRIDGE: Filling gap from {start_date} to {end_date}")
        print(f"{'='*70}")

        # Determine source
        source = self.select_backfill_source(start_date, end_date)

        # Run backfill
        backfill_success = self.run_backfill(start_date, end_date, source)
        if not backfill_success:
            print(f"[ERROR] Backfill failed - cannot fill gap")
            return False

        # Build features
        features_success = self.build_features(start_date, end_date)
        if not features_success:
            print(f"[WARN] Feature building had issues, but backfill succeeded")
            # Return True anyway - bars data is there, features can be rebuilt later
            return True

        print(f"\n[OK] Gap filled successfully!")
        print(f"[OK] Data is now current through {end_date}")
        return True

    def update_to_current(self, instrument: str = 'MGC', force: bool = False) -> bool:
        """
        Update database to current date (today).

        This is the main function to call when app starts.

        Args:
            instrument: Instrument to update
            force: If True, backfill even if data appears current

        Returns:
            True if successful or no update needed, False if failed
        """
        print(f"\n{'='*70}")
        print(f"DATA BRIDGE: Checking for updates")
        print(f"{'='*70}")

        # Detect gap
        last_db_date, current_date, gap_days = self.detect_gap(instrument)

        if gap_days == -1:
            print(f"[WARN] No data exists for {instrument}")
            print(f"[INFO] Will backfill last 30 days...")
            return self.fill_gap(None, current_date, instrument)

        elif gap_days == 0:
            print(f"[OK] Data is current (last date: {last_db_date})")
            if force:
                print(f"[INFO] Force flag set - re-running today's update...")
                return self.fill_gap(last_db_date, current_date, instrument)
            return True

        elif gap_days > 0:
            print(f"[WARN] Data gap detected:")
            print(f"  Last DB date: {last_db_date}")
            print(f"  Current date: {current_date}")
            print(f"  Gap: {gap_days} days")
            return self.fill_gap(last_db_date, current_date, instrument)

        else:
            # gap_days < 0 means last_db_date is in the FUTURE (clock issue?)
            print(f"[ERROR] Last DB date ({last_db_date}) is AFTER current date ({current_date})")
            print(f"[ERROR] Check system clock or database integrity")
            return False

    def check_stitching_quality(self, last_db_date: date, instrument: str = 'MGC') -> dict:
        """
        Check for price anomalies at the stitching point (where old data meets new data).

        This detects if there's a large price jump when switching from one data source to another.

        Args:
            last_db_date: The date where old data ends (before backfill)
            instrument: Instrument to check

        Returns:
            {
                'has_anomaly': bool,
                'price_jump': float or None,
                'details': str
            }
        """
        try:
            conn = duckdb.connect(self.db_path, read_only=True)

            # Get closing prices around stitching point
            query = """
                SELECT date_local, ny_low, ny_high
                FROM daily_features
                WHERE instrument = ?
                  AND date_local >= ?
                  AND date_local <= ?
                ORDER BY date_local
            """
            stitch_date = last_db_date + timedelta(days=1)
            end_check = stitch_date + timedelta(days=1)

            results = conn.execute(query, [instrument, last_db_date, end_check]).fetchall()
            conn.close()

            if len(results) < 2:
                return {
                    'has_anomaly': False,
                    'price_jump': None,
                    'details': 'Not enough data to check stitching quality'
                }

            # Calculate price jump
            old_high = results[0][2]  # ny_high from last old date
            new_low = results[1][1]   # ny_low from first new date

            if old_high and new_low:
                price_jump = abs(new_low - old_high)

                # Anomaly if price jump > 5 points (abnormal for MGC)
                # Normal intraday range is ~1-3 points
                if price_jump > 5.0:
                    return {
                        'has_anomaly': True,
                        'price_jump': price_jump,
                        'details': f'Large price gap ({price_jump:.2f} points) at stitching point. May indicate data source mismatch.'
                    }
                else:
                    return {
                        'has_anomaly': False,
                        'price_jump': price_jump,
                        'details': f'Price transition looks normal ({price_jump:.2f} points)'
                    }

            return {
                'has_anomaly': False,
                'price_jump': None,
                'details': 'Could not calculate price jump (missing data)'
            }

        except Exception as e:
            return {
                'has_anomaly': False,
                'price_jump': None,
                'details': f'Error checking stitching quality: {e}'
            }

    def get_status(self, instrument: str = 'MGC') -> dict:
        """
        Get current data bridge status.

        Returns:
            {
                'last_db_date': date or None,
                'current_date': date,
                'gap_days': int,
                'data_current': bool,
                'needs_update': bool
            }
        """
        last_db_date, current_date, gap_days = self.detect_gap(instrument)

        return {
            'instrument': instrument,
            'last_db_date': last_db_date,
            'current_date': current_date,
            'gap_days': gap_days,
            'data_current': gap_days == 0,
            'needs_update': gap_days > 0 or gap_days == -1,
            'has_data': gap_days != -1
        }


def main():
    """Demo: Check status and update to current"""
    bridge = DataBridge()

    # Check status
    status = bridge.get_status()
    print("\n" + "="*70)
    print("DATA BRIDGE STATUS")
    print("="*70)
    print(f"Instrument: {status['instrument']}")
    print(f"Last DB date: {status['last_db_date']}")
    print(f"Current date: {status['current_date']}")
    print(f"Gap: {status['gap_days']} days")
    print(f"Data current: {status['data_current']}")
    print(f"Needs update: {status['needs_update']}")

    if status['needs_update']:
        print("\n[INFO] Data needs update - running automatic backfill...")
        success = bridge.update_to_current()

        if success:
            print("\n" + "="*70)
            print("[OK] DATA BRIDGE COMPLETE")
            print("="*70)
            print("Your database is now current!")
            print("Market scanner will have today's data.")
        else:
            print("\n" + "="*70)
            print("[ERROR] DATA BRIDGE FAILED")
            print("="*70)
            print("Manual intervention required.")
            print("Check backfill scripts and data sources.")
    else:
        print("\n[OK] No update needed - data is current!")


if __name__ == "__main__":
    main()
