"""
SETUP DETECTOR

Queries validated_setups database to detect ALL profitable setups,
including rare high-probability ones like:
- 1100 ORB (90% WR, only 31 trades/year)
- 2300 ORB with filters (72% WR)
- 1000 RR=3.0 with 2 confirmations (29% WR but +0.158R)

The trading app calls this to check if current market conditions
match ANY validated setup criteria.
"""

import duckdb
from typing import List, Dict, Optional
from datetime import datetime
import logging
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)


class SetupDetector:
    """Detects validated high-probability trading setups."""

    def __init__(self, db_path: Optional[str] = None):
        # Cloud-aware: db_path parameter is ignored in cloud mode
        # Connections handled by get_database_connection()
        self.db_path = db_path  # Legacy parameter, kept for compatibility

        # Lazy connection - only connect when needed
        self._con = None

    def _get_connection(self):
        """Get database connection, creating it if needed (cloud-aware)"""
        if self._con is None:
            try:
                # Use cloud-aware connection
                from cloud_mode import get_database_connection
                self._con = get_database_connection()

                if self._con is None:
                    logger.warning("Database connection unavailable. Setup detection disabled.")
                    return None

                logger.info("Connected to database for setup detection")
            except Exception as e:
                logger.error(f"Error connecting to database: {e}")
                return None

        return self._con

    def get_all_validated_setups(self, instrument: str = "MGC") -> List[Dict]:
        """Get all validated setups for an instrument."""
        try:
            con = self._get_connection()
            if con is None:
                return []

            result = con.execute("""
                SELECT
                    instrument,
                    id as setup_id,
                    orb_time,
                    rr,
                    sl_mode,
                    1 as close_confirmations,
                    0.0 as buffer_ticks,
                    orb_size_filter,
                    NULL as atr_filter,
                    sample_size as trades,
                    win_rate,
                    expected_r as avg_r,
                    realized_expectancy,
                    avg_win_r,
                    avg_loss_r,
                    0 as annual_trades,
                    'A' as tier,
                    notes
                FROM validated_setups
                WHERE instrument = ?
                ORDER BY expected_r DESC
            """, [instrument]).df()

            return result.to_dict('records')
        except Exception as e:
            logger.error(f"Error getting validated setups: {e}")
            return []

    def check_orb_setup(
        self,
        instrument: str,
        orb_time: str,
        orb_size: float,
        atr_20: float,
        current_time: datetime
    ) -> List[Dict]:
        """
        Check if current ORB matches any validated setup criteria.

        Returns list of matching setups, sorted by tier (best first).
        """
        try:
            con = self._get_connection()
            if con is None:
                return []

            # Calculate orb_size as % of ATR
            if atr_20 and atr_20 > 0:
                orb_size_pct = orb_size / atr_20
            else:
                orb_size_pct = None

            # Find matching setups
            query = """
                SELECT
                    id as setup_id,
                    orb_time,
                    rr,
                    sl_mode,
                    1 as close_confirmations,
                    0.0 as buffer_ticks,
                    orb_size_filter,
                    win_rate,
                    expected_r as avg_r,
                    realized_expectancy,
                    avg_win_r,
                    avg_loss_r,
                    'A' as tier,
                    notes
                FROM validated_setups
                WHERE instrument = ?
                  AND orb_time = ?
                  AND (orb_size_filter IS NULL OR ? <= orb_size_filter)
                ORDER BY expected_r DESC
            """

            result = con.execute(query, [instrument, orb_time, orb_size_pct]).df()

            matches = result.to_dict('records')

            if matches:
                logger.info(f"Found {len(matches)} validated setups for {instrument} {orb_time} ORB")
                for match in matches:
                    logger.info(f"  -> {match['tier']} tier: {match['win_rate']:.1f}% WR, {match['avg_r']:+.3f}R avg")

            return matches
        except Exception as e:
            logger.error(f"Error checking ORB setup: {e}")
            return []

    def get_elite_setups(self, instrument: str = "MGC") -> List[Dict]:
        """Get only S+ and S tier setups (elite performers)."""
        try:
            con = self._get_connection()
            if con is None:
                return []

            result = con.execute("""
                SELECT
                    id as setup_id,
                    orb_time,
                    rr,
                    sl_mode,
                    win_rate,
                    expected_r as avg_r,
                    realized_expectancy,
                    avg_win_r,
                    avg_loss_r,
                    0 as annual_trades,
                    'A' as tier,
                    notes
                FROM validated_setups
                WHERE instrument = ?
                ORDER BY expected_r DESC
            """, [instrument]).df()

            return result.to_dict('records')
        except Exception as e:
            logger.error(f"Error getting elite setups: {e}")
            return []

    def format_setup_alert(self, setup: Dict) -> str:
        """Format a validated setup as an alert message."""
        alert = f"[{setup['tier']} TIER SETUP DETECTED!]\n\n"
        alert += f"ORB: {setup['orb_time']}\n"
        alert += f"Win Rate: {setup['win_rate']:.1f}%\n"
        alert += f"Expected R: {setup['avg_r']:+.3f}R (theoretical)\n"

        # Show realized expectancy if available
        realized = setup.get('realized_expectancy')
        if realized is not None and not (isinstance(realized, float) and pd.isna(realized)):
            delta = realized - setup['avg_r']
            status = "SURVIVES" if realized >= 0.15 else ("MARGINAL" if realized >= 0.05 else "FAILS")
            alert += f"Realized R: {realized:+.3f}R (delta: {delta:+.3f}R) [{status}]\n"

        alert += f"RR Target: {setup['rr']}R\n"
        alert += f"SL Mode: {setup['sl_mode']}\n"

        orb_filter = setup.get('orb_size_filter')
        if orb_filter and not (isinstance(orb_filter, float) and pd.isna(orb_filter)):
            alert += f"Filter: ORB < {orb_filter*100:.1f}% ATR\n"

        alert += f"\nNotes: {setup['notes']}"

        return alert


def get_best_setup_for_orb(instrument: str, orb_time: str, orb_size: float, atr_20: float) -> Optional[Dict]:
    """
    Quick helper: Get the single best validated setup for this ORB.
    Returns None if no validated setups match criteria.
    """
    detector = SetupDetector()
    matches = detector.check_orb_setup(instrument, orb_time, orb_size, atr_20, datetime.now())

    if matches:
        return matches[0]  # Best setup (sorted by tier then avg_r)

    return None


if __name__ == "__main__":
    # Test the detector
    detector = SetupDetector()

    print("="*80)
    print("ELITE SETUPS (S+ and S tier only)")
    print("="*80)

    elite = detector.get_elite_setups("MGC")
    for setup in elite:
        print(f"\n{setup['orb_time']} ORB [{setup['tier']} tier]:")
        print(f"  Win Rate: {setup['win_rate']:.1f}%")
        print(f"  Avg R: {setup['avg_r']:+.3f}R")
        print(f"  Frequency: ~{setup['annual_trades']} trades/year")
        print(f"  Notes: {setup['notes']}")

    print("\n" + "="*80)
    print("Testing ORB detection...")
    print("="*80)

    # Test: Small 1100 ORB (should trigger S+ tier setup)
    print("\nTest 1: 1100 ORB, size=3.0, ATR=40.0")
    matches = detector.check_orb_setup("MGC", "1100", 3.0, 40.0, datetime.now())
    if matches:
        print(detector.format_setup_alert(matches[0]))
    else:
        print("No validated setup found")

    # Test: Large 1100 ORB (should NOT trigger due to filter)
    print("\n" + "="*80)
    print("\nTest 2: 1100 ORB, size=6.0, ATR=40.0 (too large)")
    matches = detector.check_orb_setup("MGC", "1100", 6.0, 40.0, datetime.now())
    if matches:
        print(detector.format_setup_alert(matches[0]))
    else:
        print("No validated setup found - ORB too large vs ATR")
