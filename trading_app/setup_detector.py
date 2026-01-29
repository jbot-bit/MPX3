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

    def __init__(self, db_path: Optional[str] = None, db_connection=None):
        # Accept existing connection to avoid "different configuration" errors
        # CRITICAL: Never close this connection - it's shared with parent app
        self.db_path = db_path  # Legacy parameter, kept for compatibility
        self._con = db_connection  # Use provided connection if available

    def _get_connection(self):
        """Get database connection, creating it if needed (cloud-aware)"""
        # If connection was provided at init, reuse it (NEVER close)
        if self._con is not None:
            return self._con

        # Otherwise create new connection (fallback for standalone usage)
        try:
            from cloud_mode import get_database_connection
            self._con = get_database_connection()

            if self._con is None:
                logger.warning("Database connection unavailable. Setup detection disabled.")
                return None

            logger.info("Connected to database for setup detection")
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            self._con = None
            return None

        return self._con

    def get_all_validated_setups(self, instrument: str = "MGC") -> List[Dict]:
        """Get all validated setups for an instrument (ACTIVE only, filters REJECTED)."""
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
                  AND (status IS NULL OR status != 'REJECTED')
                ORDER BY realized_expectancy DESC
            """, [instrument]).df()

            return result.to_dict('records')
        except Exception as e:
            logger.error(f"Error getting validated setups: {e}")
            return []

    def get_grouped_setups(self, instrument: str = "MGC") -> List[Dict]:
        """
        Get setups grouped by ORB time with variants collapsed.

        text.txt requirements:
        - Group by orb_time
        - Show ONE collapsed row per ORB with:
          - orb_time, variant count, best expectancy, sample size, win rate, friction gate pass rate
        - Each group contains all RR variants (1.5/2.0/2.5/3.0)

        Returns:
            List of dicts with keys: orb_time, variant_count, best_expectancy,
            sample_size, win_rate, friction_pass_rate, variants (list of individual setups)
        """
        try:
            con = self._get_connection()
            if con is None:
                return []

            # Get all setups with TCA-adjusted stats from validated_trades (ACTIVE only)
            result = con.execute("""
                WITH tca_stats AS (
                    SELECT
                        vs.id as setup_id,
                        vs.orb_time,
                        vs.rr,
                        vs.sl_mode,
                        vs.orb_size_filter,
                        vs.notes,
                        COUNT(*) as total_signals,
                        SUM(CASE WHEN vt.outcome NOT IN ('NO_TRADE', 'RISK_TOO_SMALL')
                                 AND (vt.friction_ratio IS NULL OR vt.friction_ratio <= 0.20)
                            THEN 1 ELSE 0 END) as tca_trades,
                        SUM(CASE WHEN vt.outcome = 'WIN'
                                 AND (vt.friction_ratio IS NULL OR vt.friction_ratio <= 0.20)
                            THEN 1 ELSE 0 END) as tca_wins,
                        SUM(CASE WHEN vt.outcome = 'LOSS'
                                 AND (vt.friction_ratio IS NULL OR vt.friction_ratio <= 0.20)
                            THEN 1 ELSE 0 END) as tca_losses,
                        AVG(CASE WHEN vt.outcome IN ('WIN', 'LOSS')
                                 AND (vt.friction_ratio IS NULL OR vt.friction_ratio <= 0.20)
                            THEN vt.realized_rr ELSE NULL END) as tca_expectancy
                    FROM validated_setups vs
                    LEFT JOIN validated_trades vt ON vs.id = vt.setup_id
                    WHERE vs.instrument = ?
                      AND (vs.status IS NULL OR vs.status != 'REJECTED')
                    GROUP BY vs.id, vs.orb_time, vs.rr, vs.sl_mode, vs.orb_size_filter, vs.notes
                )
                SELECT * FROM tca_stats
                ORDER BY orb_time, rr
            """, [instrument]).df()

            if result.empty:
                return []

            # Group by ORB time
            grouped = {}
            for _, row in result.iterrows():
                orb_time = row['orb_time']

                if orb_time not in grouped:
                    grouped[orb_time] = {
                        'orb_time': orb_time,
                        'variants': [],
                        'variant_count': 0,
                        'best_expectancy': float('-inf'),
                        'total_sample_size': 0,
                        'avg_win_rate': 0,
                        'friction_pass_rate': 0
                    }

                # Calculate variant stats
                tca_resolved = (row['tca_wins'] or 0) + (row['tca_losses'] or 0)
                tca_win_rate = (row['tca_wins'] / tca_resolved) if tca_resolved > 0 else 0
                friction_pass = (row['tca_trades'] / row['total_signals']) if row['total_signals'] > 0 else 0

                variant = {
                    'setup_id': int(row['setup_id']),
                    'rr': float(row['rr']),
                    'sl_mode': row['sl_mode'],
                    'filter': float(row['orb_size_filter']) if row['orb_size_filter'] else None,
                    'expectancy': float(row['tca_expectancy']) if row['tca_expectancy'] else 0,
                    'sample_size': int(tca_resolved),
                    'win_rate': float(tca_win_rate),
                    'friction_pass_rate': float(friction_pass),
                    'notes': row['notes']
                }

                grouped[orb_time]['variants'].append(variant)
                grouped[orb_time]['variant_count'] += 1

                # Track best expectancy for this ORB
                if variant['expectancy'] > grouped[orb_time]['best_expectancy']:
                    grouped[orb_time]['best_expectancy'] = variant['expectancy']

            # Calculate aggregate stats per ORB
            for orb_time in grouped:
                variants = grouped[orb_time]['variants']
                grouped[orb_time]['total_sample_size'] = sum(v['sample_size'] for v in variants)
                grouped[orb_time]['avg_win_rate'] = sum(v['win_rate'] for v in variants) / len(variants) if variants else 0
                grouped[orb_time]['friction_pass_rate'] = sum(v['friction_pass_rate'] for v in variants) / len(variants) if variants else 0

            # Convert to list and sort by ORB time
            result = sorted(grouped.values(), key=lambda x: x['orb_time'])

            return result
        except Exception as e:
            logger.error(f"Error getting grouped setups: {e}")
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

            # NULL PARAMETER FIX: Split query based on ATR availability
            # When ATR missing, can't apply size filter - return setups WITHOUT size filter requirement
            if orb_size_pct is not None:
                # ATR available - apply size filter
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
                      AND (status IS NULL OR status != 'REJECTED')
                    ORDER BY realized_expectancy DESC
                """
                result = con.execute(query, [instrument, orb_time, orb_size_pct]).df()
            else:
                # ATR missing - return only setups WITHOUT size filter
                # (Setups with size filters require ATR for validation)
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
                      AND orb_size_filter IS NULL
                      AND (status IS NULL OR status != 'REJECTED')
                    ORDER BY realized_expectancy DESC
                """
                result = con.execute(query, [instrument, orb_time]).df()
                logger.info(f"ATR unavailable - returning setups without size filter for {instrument} {orb_time}")

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
        """Get only S+ and S tier setups (elite performers, ACTIVE only)."""
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
                  AND (status IS NULL OR status != 'REJECTED')
                  AND realized_expectancy >= 0.15
                ORDER BY realized_expectancy DESC
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
