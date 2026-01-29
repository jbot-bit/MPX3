"""
Experimental Strategy Scanner - Auto-Alert for Rare/Complex Edges

Scans experimental_strategies table and evaluates filter conditions:
- DAY_OF_WEEK: Trade only on specific days (Tuesday/Monday/Wednesday)
- SESSION_CONTEXT: Previous day session characteristics (Big/Huge Asia expansion)
- VOLATILITY_REGIME: High/low ATR environments
- COMBINED: Multiple filters (Big Asia + Tiny ORB)
- MULTI_DAY: Multi-day patterns (previous failures)

Usage:
    from experimental_scanner import ExperimentalScanner

    scanner = ExperimentalScanner(db_connection)
    alerts = scanner.scan_for_matches(instrument='MGC')

    for alert in alerts:
        print(f"🎁 BONUS EDGE: {alert['description']}")
"""

import duckdb
from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger(__name__)


class ExperimentalScanner:
    """Real-time scanner for experimental (rare/complex) strategies"""

    def __init__(self, db_connection: duckdb.DuckDBPyConnection):
        self.conn = db_connection
        self._check_table_exists()

    def _check_table_exists(self):
        """
        Check if experimental_strategies table exists

        Raises:
            RuntimeError: If table doesn't exist (user-friendly message)
        """
        try:
            table_exists = self.conn.execute("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = 'experimental_strategies'
            """).fetchone()[0] > 0

            if not table_exists:
                raise RuntimeError(
                    "Experimental strategies not configured yet. "
                    "Run pipeline/schema_experimental_strategies.sql to create table."
                )
        except RuntimeError:
            raise  # Re-raise our user-friendly error
        except Exception as e:
            # Database error (not missing table)
            logger.error(f"Failed to check experimental_strategies table: {e}")
            raise RuntimeError(f"Database error checking experimental strategies: {e}")

    def scan_for_matches(
        self,
        instrument: str = 'MGC',
        current_date: Optional[date] = None
    ) -> List[Dict]:
        """
        Scan experimental_strategies and return matches for current conditions

        Args:
            instrument: Trading instrument (default: 'MGC')
            current_date: Date to check (default: today in Brisbane timezone)

        Returns:
            List of matching strategies with alert info
        """
        if current_date is None:
            # Use trading timezone (Australia/Brisbane per CLAUDE.md)
            tz_brisbane = ZoneInfo("Australia/Brisbane")
            current_date = datetime.now(tz=tz_brisbane).date()

        # Get all ACTIVE experimental strategies
        try:
            strategies = self.conn.execute("""
                SELECT
                    id, orb_time, rr, sl_mode,
                    filter_type, filter_condition,
                    day_of_week,
                    win_rate, realized_expectancy,
                    sample_size, annual_frequency,
                    notes
                FROM experimental_strategies
                WHERE instrument = ?
                  AND status = 'ACTIVE'
                ORDER BY realized_expectancy DESC
            """, [instrument]).fetchall()
        except Exception as e:
            logger.error(f"Query failed for experimental_strategies: {e}")
            raise RuntimeError(f"Failed to query experimental strategies: {e}")

        if not strategies:
            return []

        # Get market conditions for evaluation
        market_conditions = self._get_market_conditions(instrument, current_date)

        # Evaluate each strategy
        matches = []
        for strat in strategies:
            (
                strat_id, orb_time, rr, sl_mode,
                filter_type, filter_condition, day_of_week,
                win_rate, exp_r, sample_size, annual_freq, notes
            ) = strat

            # Evaluate if conditions match
            is_match, reason = self._evaluate_strategy(
                filter_type=filter_type,
                filter_condition=filter_condition,
                day_of_week=day_of_week,
                orb_time=orb_time,
                market_conditions=market_conditions
            )

            if is_match:
                matches.append({
                    'id': strat_id,
                    'orb_time': orb_time,
                    'rr': rr,
                    'sl_mode': sl_mode,
                    'filter_type': filter_type,
                    'filter_condition': filter_condition,
                    'win_rate': win_rate,
                    'expected_r': exp_r,
                    'sample_size': sample_size,
                    'annual_frequency': annual_freq,
                    'notes': notes,
                    'match_reason': reason,
                    'description': f"{orb_time} RR={rr} {filter_type} (+{exp_r:.3f}R)"
                })

        return matches

    def _get_previous_trading_day(
        self,
        instrument: str,
        current_date: date
    ) -> Optional[date]:
        """
        Get the most recent trading day with data (skips weekends/holidays)

        Args:
            instrument: Trading instrument
            current_date: Reference date

        Returns:
            Previous trading day date, or None if not found
        """
        # Check up to 7 days back (handles long weekends)
        for days_back in range(1, 8):
            candidate = current_date - timedelta(days=days_back)
            try:
                row = self.conn.execute("""
                    SELECT 1 FROM daily_features
                    WHERE date_local = ? AND instrument = ?
                    LIMIT 1
                """, [candidate, instrument]).fetchone()
                if row:
                    return candidate
            except Exception:
                continue
        return None

    def _get_market_conditions(
        self,
        instrument: str,
        current_date: date
    ) -> Dict:
        """
        Get market conditions needed for filter evaluation

        Returns:
            Dict with:
            - current_date: Today's date
            - day_of_week: Current day name ('Monday', 'Tuesday', etc.)
            - prev_date: Previous trading day (skips weekends/holidays)
            - prev_asia_range: Previous trading day's Asia range
            - prev_atr: Previous trading day's ATR(20)
            - prev_asia_ratio: prev_asia_range / prev_atr
            - current_atr: Today's ATR(20)
            - atr_percentile_75: 75th percentile of ATR (last 100 days)
            - prev_0900_outcome: Previous trading day's 0900 ORB outcome
            - orb_data: Today's ORB sizes (when available)
        """
        # Get previous trading day (skips weekends/holidays)
        prev_date = self._get_previous_trading_day(instrument, current_date)

        conditions = {
            'current_date': current_date,
            'day_of_week': current_date.strftime('%A'),  # 'Monday', 'Tuesday', etc.
            'prev_date': prev_date  # Now properly handles weekends!
        }

        try:
            # Get previous trading day's data (for SESSION_CONTEXT and MULTI_DAY filters)
            if prev_date:
                prev_row = self.conn.execute("""
                    SELECT
                        asia_range,
                        atr_20,
                        orb_0900_outcome
                    FROM daily_features
                    WHERE date_local = ?
                      AND instrument = ?
                """, [prev_date, instrument]).fetchone()
            else:
                prev_row = None

            if prev_row:
                prev_asia_range, prev_atr, prev_0900_outcome = prev_row
                conditions['prev_asia_range'] = prev_asia_range
                conditions['prev_atr'] = prev_atr
                conditions['prev_0900_outcome'] = prev_0900_outcome

                # Calculate ratio
                if prev_atr and prev_atr > 0 and prev_asia_range:
                    conditions['prev_asia_ratio'] = prev_asia_range / prev_atr
                else:
                    conditions['prev_asia_ratio'] = None

            # Get today's data (for VOLATILITY_REGIME and COMBINED filters)
            today_row = self.conn.execute("""
                SELECT
                    atr_20,
                    orb_0900_size,
                    orb_1000_size,
                    orb_1100_size
                FROM daily_features
                WHERE date_local = ?
                  AND instrument = ?
            """, [current_date, instrument]).fetchone()

            if today_row:
                current_atr, orb_0900_size, orb_1000_size, orb_1100_size = today_row
                conditions['current_atr'] = current_atr

                # Store ORB sizes
                conditions['orb_data'] = {
                    '0900': orb_0900_size,
                    '1000': orb_1000_size,
                    '1100': orb_1100_size
                }

                # Calculate ORB size ratios (for COMBINED filters)
                if current_atr and current_atr > 0:
                    conditions['orb_ratios'] = {
                        '0900': orb_0900_size / current_atr if orb_0900_size else None,
                        '1000': orb_1000_size / current_atr if orb_1000_size else None,
                        '1100': orb_1100_size / current_atr if orb_1100_size else None
                    }

            # Get ATR 75th percentile (for VOLATILITY_REGIME filters)
            atr_75_row = self.conn.execute("""
                SELECT PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY atr_20)
                FROM daily_features
                WHERE instrument = ?
                  AND atr_20 IS NOT NULL
                  AND date_local >= ?
            """, [instrument, current_date - timedelta(days=100)]).fetchone()

            if atr_75_row:
                conditions['atr_percentile_75'] = atr_75_row[0]

        except Exception as e:
            logger.error(f"Error getting market conditions: {e}")

        return conditions

    def _evaluate_strategy(
        self,
        filter_type: str,
        filter_condition: str,
        day_of_week: Optional[str],
        orb_time: str,
        market_conditions: Dict
    ) -> tuple:
        """
        Evaluate if strategy conditions match current market

        Returns:
            (is_match: bool, reason: str)
        """
        # DAY_OF_WEEK filter
        if filter_type == 'DAY_OF_WEEK':
            if day_of_week and market_conditions.get('day_of_week') == day_of_week:
                return (True, f"{day_of_week} match")
            return (False, f"Today is {market_conditions.get('day_of_week')}, not {day_of_week}")

        # SESSION_CONTEXT filter (previous day Asia expansion)
        elif filter_type == 'SESSION_CONTEXT':
            prev_asia_ratio = market_conditions.get('prev_asia_ratio')

            if prev_asia_ratio is None:
                return (False, "No previous Asia data")

            # Check for different expansion levels
            if 'extreme expansion' in filter_condition.lower() or '1.5 ATR' in filter_condition:
                # HUGE_ASIA_EXPANSION: > 1.5 ATR
                if prev_asia_ratio > 1.5:
                    return (True, f"Huge Asia expansion ({prev_asia_ratio:.2f}x ATR)")
                return (False, f"Asia only {prev_asia_ratio:.2f}x ATR (need > 1.5x)")

            elif '1.0 ATR' in filter_condition:
                # BIG_ASIA_EXPANSION: > 1.0 ATR
                if prev_asia_ratio > 1.0:
                    return (True, f"Big Asia expansion ({prev_asia_ratio:.2f}x ATR)")
                return (False, f"Asia only {prev_asia_ratio:.2f}x ATR (need > 1.0x)")

            return (False, "Unknown session context filter")

        # COMBINED filter (Big Asia + Tiny ORB)
        elif filter_type == 'COMBINED':
            prev_asia_ratio = market_conditions.get('prev_asia_ratio')
            orb_ratios = market_conditions.get('orb_ratios', {})
            orb_ratio = orb_ratios.get(orb_time)

            if prev_asia_ratio is None:
                return (False, "No previous Asia data")

            if orb_ratio is None:
                return (False, f"{orb_time} ORB not yet formed")

            # Check: Big previous Asia (> 0.8 ATR) AND Tiny current ORB (< 0.15 ATR)
            if prev_asia_ratio > 0.8 and orb_ratio < 0.15:
                return (
                    True,
                    f"Big Asia ({prev_asia_ratio:.2f}x) + Tiny ORB ({orb_ratio:.2f}x)"
                )

            return (
                False,
                f"Asia {prev_asia_ratio:.2f}x (need > 0.8x), ORB {orb_ratio:.2f}x (need < 0.15x)"
            )

        # VOLATILITY_REGIME filter (high ATR environment)
        elif filter_type == 'VOLATILITY_REGIME':
            current_atr = market_conditions.get('current_atr')
            atr_75th = market_conditions.get('atr_percentile_75')

            if current_atr is None or atr_75th is None:
                return (False, "No ATR data")

            # HIGH_VOL: > 75th percentile
            if current_atr > atr_75th:
                return (True, f"High vol regime (ATR {current_atr:.1f} > 75th {atr_75th:.1f})")

            return (False, f"ATR {current_atr:.1f} below 75th percentile {atr_75th:.1f}")

        # MULTI_DAY filter (previous failure pattern)
        elif filter_type == 'MULTI_DAY':
            prev_0900_outcome = market_conditions.get('prev_0900_outcome')

            if prev_0900_outcome is None:
                return (False, "No previous 0900 outcome data")

            # Check for previous 0900 failure
            if 'Previous day 0900 ORB failed' in filter_condition:
                if prev_0900_outcome == 'LOSS':
                    return (True, "Previous 0900 ORB failed (mean reversion setup)")
                return (False, f"Previous 0900 was {prev_0900_outcome}, not LOSS")

            return (False, "Unknown multi-day filter")

        # Unknown filter type
        else:
            return (False, f"Unknown filter type: {filter_type}")

    def get_experimental_summary(self, instrument: str = 'MGC') -> Dict:
        """
        Get summary statistics for experimental strategies

        Returns:
            Dict with:
            - total_count: Total experimental strategies
            - by_filter_type: Count by filter type
            - total_expected_r: Sum of expected R across all strategies
            - total_annual_frequency: Sum of annual frequencies
        """
        try:
            # Get counts by filter type
            filter_counts = self.conn.execute("""
                SELECT
                    filter_type,
                    COUNT(*) as count,
                    ROUND(SUM(realized_expectancy), 2) as total_exp_r,
                    ROUND(SUM(annual_frequency), 1) as total_freq
                FROM experimental_strategies
                WHERE instrument = ?
                  AND status = 'ACTIVE'
                GROUP BY filter_type
                ORDER BY total_exp_r DESC
            """, [instrument]).fetchall()

            by_filter_type = {}
            total_exp_r = 0.0
            total_freq = 0.0

            for row in filter_counts:
                filter_type, count, exp_r, freq = row
                by_filter_type[filter_type] = {
                    'count': count,
                    'expected_r': exp_r,
                    'annual_frequency': freq
                }
                total_exp_r += exp_r if exp_r else 0
                total_freq += freq if freq else 0

            total_count = sum(fc['count'] for fc in by_filter_type.values())

            return {
                'total_count': total_count,
                'by_filter_type': by_filter_type,
                'total_expected_r': round(total_exp_r, 2),
                'total_annual_frequency': round(total_freq, 1)
            }

        except Exception as e:
            logger.error(f"Error getting experimental summary: {e}")
            return {
                'total_count': 0,
                'by_filter_type': {},
                'total_expected_r': 0.0,
                'total_annual_frequency': 0.0
            }

    def validate_strategies(self, instrument: str = 'MGC') -> tuple:
        """
        Validate experimental strategies data integrity

        Returns:
            (is_valid: bool, issues: List[str])
        """
        # Validation thresholds (from check_experimental_strategies.py)
        EXPECTED_R_MIN = -1.0
        EXPECTED_R_MAX = 2.0
        WIN_RATE_MIN = 0.20
        WIN_RATE_MAX = 0.90
        SAMPLE_SIZE_MIN = 15

        VALID_FILTER_TYPES = [
            'DAY_OF_WEEK', 'SESSION_CONTEXT', 'VOLATILITY_REGIME',
            'COMBINED', 'MULTI_DAY'
        ]

        VALID_DAYS_OF_WEEK = [
            'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', None
        ]

        issues = []

        try:
            strategies = self.conn.execute("""
                SELECT
                    id, instrument, orb_time, rr, filter_type, day_of_week,
                    win_rate, realized_expectancy, sample_size
                FROM experimental_strategies
                WHERE status = 'ACTIVE'
                  AND instrument = ?
            """, [instrument]).fetchall()

            if not strategies:
                return (True, ["No ACTIVE strategies to validate"])

            for strat in strategies:
                strat_id, inst, orb_time, rr, filter_type, day_of_week, win_rate, exp_r, sample_size = strat
                strat_name = f"{inst} {orb_time} RR={rr} {filter_type}"

                # Check expected_r bounds
                if exp_r and (exp_r < EXPECTED_R_MIN or exp_r > EXPECTED_R_MAX):
                    issues.append(
                        f"ERROR: {strat_name} (ID {strat_id}): "
                        f"realized_expectancy={exp_r:.3f}R outside [{EXPECTED_R_MIN}, {EXPECTED_R_MAX}]"
                    )

                # Check win rate bounds
                if win_rate and (win_rate < WIN_RATE_MIN or win_rate > WIN_RATE_MAX):
                    issues.append(
                        f"ERROR: {strat_name} (ID {strat_id}): "
                        f"win_rate={win_rate:.1%} outside [{WIN_RATE_MIN:.0%}, {WIN_RATE_MAX:.0%}]"
                    )

                # Check sample size
                if sample_size and sample_size < SAMPLE_SIZE_MIN:
                    issues.append(
                        f"WARNING: {strat_name} (ID {strat_id}): "
                        f"sample_size={sample_size} < {SAMPLE_SIZE_MIN}"
                    )

                # Check filter type
                if filter_type not in VALID_FILTER_TYPES:
                    issues.append(
                        f"ERROR: {strat_name} (ID {strat_id}): "
                        f"invalid filter_type '{filter_type}'"
                    )

                # Check day_of_week for DAY_OF_WEEK filters
                if filter_type == 'DAY_OF_WEEK' and day_of_week not in VALID_DAYS_OF_WEEK:
                    issues.append(
                        f"ERROR: {strat_name} (ID {strat_id}): "
                        f"invalid day_of_week '{day_of_week}'"
                    )

            is_valid = not any('ERROR' in issue for issue in issues)
            return (is_valid, issues)

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return (False, [f"Validation error: {e}"])


def test_scanner():
    """Test the experimental scanner"""
    import os
    from pathlib import Path

    db_path = Path(__file__).parent.parent / "data" / "db" / "gold.db"
    con = duckdb.connect(str(db_path))

    scanner = ExperimentalScanner(con)

    # Get summary
    summary = scanner.get_experimental_summary()
    print(f"\n{'='*70}")
    print(f"EXPERIMENTAL STRATEGIES SUMMARY")
    print(f"{'='*70}")
    print(f"Total strategies: {summary['total_count']}")
    print(f"Total expected R/year: +{summary['total_expected_r']}R")
    print(f"Total trades/year: {summary['total_annual_frequency']}")
    print(f"\nBy filter type:")
    for filter_type, stats in summary['by_filter_type'].items():
        print(f"  {filter_type}: {stats['count']} strategies, +{stats['expected_r']}R/year")

    # Scan for today's matches
    matches = scanner.scan_for_matches()
    print(f"\n{'='*70}")
    print(f"TODAY'S MATCHES")
    print(f"{'='*70}")

    if matches:
        print(f"Found {len(matches)} matching experimental strategies:\n")
        for match in matches:
            print(f"[EDGE] {match['description']}")
            print(f"   Condition: {match['filter_condition']}")
            print(f"   Reason: {match['match_reason']}")
            print(f"   Stats: {match['win_rate']:.1%} WR, {match['sample_size']} trades, ~{match['annual_frequency']:.0f}/year")
            print()
    else:
        print("No experimental strategies match today's conditions.")
        print("\nYour ACTIVE strategies are always available!")

    con.close()


if __name__ == "__main__":
    test_scanner()
