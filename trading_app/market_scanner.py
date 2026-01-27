"""
Real-Time Market Scanner & Setup Validator

Scans current market conditions and automatically determines which validated setups
are worth trading TODAY based on:
- Current session data (Asia travel, London chop, liquidity)
- ORB size filters from config.py
- Anomaly detection (traps, low liquidity, wide spreads)
- Historical pattern matching

This is the AI "brain" that says:
- "0900 ORB: SKIP (conditions unfavorable)"
- "1100 ORB: TAKE (high confidence setup)"
"""

import duckdb
import numpy as np
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import existing config
from trading_app.config import (
    MGC_ORB_SIZE_FILTERS,
    MGC_ORB_CONFIGS,
    DB_PATH,
    TZ_LOCAL  # Already a ZoneInfo object
)


class MarketScanner:
    """Real-time market scanner and setup validator"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.tz_local = TZ_LOCAL

        # Statistical thresholds (from historical data)
        # These will be calculated from daily_features, or use defaults
        self.thresholds = {
            'orb_size': {
                '0900': {'mean': 0.10, 'std': 0.04},
                '1000': {'mean': 0.08, 'std': 0.03},
                '1100': {'mean': 0.09, 'std': 0.04},
                '1800': {'mean': 0.12, 'std': 0.05},
                '2300': {'mean': 0.15, 'std': 0.06},
                '0030': {'mean': 0.13, 'std': 0.05},
            },
            'asia_travel': {'mean': 2.0, 'std': 0.8},
            'london_reversals': {'mean': 3.5, 'std': 1.5},
        }

        self._initialize_thresholds()

    def _initialize_thresholds(self):
        """Calculate statistical thresholds from historical data"""
        try:
            conn = duckdb.connect(self.db_path, read_only=True)

            # Calculate ORB size thresholds for each time
            for orb_time in ['0900', '1000', '1100', '1800', '2300', '0030']:
                col = f'orb_{orb_time}_size'
                query = f"""
                    SELECT
                        AVG({col}) as mean,
                        STDDEV({col}) as std,
                        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY {col}) as p25,
                        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY {col}) as p75
                    FROM daily_features
                    WHERE instrument = 'MGC'
                      AND {col} IS NOT NULL
                      AND date_local >= CURRENT_DATE - INTERVAL '365 days'
                """
                result = conn.execute(query).fetchone()

                if result and result[0]:
                    self.thresholds['orb_size'][orb_time] = {
                        'mean': result[0],
                        'std': result[1] if result[1] else 0.03,
                        'p25': result[2],
                        'p75': result[3]
                    }

            conn.close()

        except Exception as e:
            print(f"Warning: Could not initialize thresholds: {e}")
            # Use defaults
            for orb_time in ['0900', '1000', '1100', '1800', '2300', '0030']:
                self.thresholds['orb_size'][orb_time] = {
                    'mean': 0.10, 'std': 0.04, 'p25': 0.07, 'p75': 0.13
                }

    def get_today_conditions(self, date_local: Optional[date] = None) -> Dict:
        """
        Get current market conditions for today.

        Returns dict with:
        - asia_travel, london_reversals, etc.
        - Current ORB sizes
        - london_type_code (for L4_CONSOLIDATION filter)
        - rsi_at_0030 (for RSI filter)
        - Liquidity state
        - Contract days to roll
        """
        if date_local is None:
            date_local = datetime.now(self.tz_local).date()

        try:
            conn = duckdb.connect(self.db_path, read_only=True)

            query = """
                SELECT
                    date_local,
                    asia_high, asia_low,
                    asia_high - asia_low as asia_travel,
                    london_high, london_low,
                    london_type_code,
                    rsi_at_0030,
                    -- ORB sizes
                    orb_0900_size, orb_1000_size, orb_1100_size,
                    orb_1800_size, orb_2300_size, orb_0030_size,
                    -- ORB break directions (to check if already broken)
                    orb_0900_break_dir, orb_1000_break_dir, orb_1100_break_dir,
                    orb_1800_break_dir, orb_2300_break_dir, orb_0030_break_dir
                FROM daily_features
                WHERE instrument = 'MGC'
                  AND date_local = ?
            """

            result = conn.execute(query, [date_local]).fetchone()
            conn.close()

            if not result:
                # No data for today yet - return empty conditions
                return {
                    'date_local': date_local,
                    'data_available': False,
                    'asia_travel': None,
                    'london_reversals': None,
                    'london_type_code': None,
                    'rsi_at_0030': None,
                    'orb_sizes': {},
                    'orb_broken': {},
                }

            # Parse result
            conditions = {
                'date_local': result[0],
                'data_available': True,
                'asia_high': result[1],
                'asia_low': result[2],
                'asia_travel': result[3],
                'london_high': result[4],
                'london_low': result[5],
                'london_type_code': result[6],
                'rsi_at_0030': result[7],
                'orb_sizes': {},
                'orb_broken': {},
                # TODO: Add london_reversals when available in daily_features
                'london_reversals': None,  # Not yet in schema
            }

            # Safely populate ORB data (adjusted for london_type_code and rsi_at_0030)
            orb_times = ['0900', '1000', '1100', '1800', '2300', '0030']
            try:
                conditions['orb_sizes'] = {
                    '0900': result[8] if len(result) > 8 else None,
                    '1000': result[9] if len(result) > 9 else None,
                    '1100': result[10] if len(result) > 10 else None,
                    '1800': result[11] if len(result) > 11 else None,
                    '2300': result[12] if len(result) > 12 else None,
                    '0030': result[13] if len(result) > 13 else None,
                }
                conditions['orb_broken'] = {
                    '0900': result[14] != 'NONE' if len(result) > 14 and result[14] else False,
                    '1000': result[15] != 'NONE' if len(result) > 15 and result[15] else False,
                    '1100': result[16] != 'NONE' if len(result) > 16 and result[16] else False,
                    '1800': result[17] != 'NONE' if len(result) > 17 and result[17] else False,
                    '2300': result[18] != 'NONE' if len(result) > 18 and result[18] else False,
                    '0030': result[19] != 'NONE' if len(result) > 19 and result[19] else False,
                }
            except (IndexError, TypeError):
                # If columns don't exist, set to None
                for orb_time in orb_times:
                    if orb_time not in conditions['orb_sizes']:
                        conditions['orb_sizes'][orb_time] = None
                    if orb_time not in conditions['orb_broken']:
                        conditions['orb_broken'][orb_time] = False

            return conditions

        except Exception as e:
            print(f"Error getting today's conditions: {e}")
            return {'date_local': date_local, 'data_available': False}

    def check_orb_size_anomaly(self, orb_time: str, orb_size: float) -> Dict:
        """
        Check if ORB size is anomalous (too large = trap, too small = low probability).

        Returns:
            {
                'is_anomaly': bool,
                'severity': 'CRITICAL'|'HIGH'|'MEDIUM'|'NONE',
                'reason': str,
                'z_score': float
            }
        """
        if orb_size is None:
            return {'is_anomaly': False, 'severity': 'NONE', 'reason': 'ORB not formed yet'}

        thresholds = self.thresholds['orb_size'].get(orb_time)
        if not thresholds:
            return {'is_anomaly': False, 'severity': 'NONE', 'reason': 'No threshold data'}

        mean = thresholds['mean']
        std = thresholds['std']
        z_score = (orb_size - mean) / std if std > 0 else 0

        # Anomaly detection
        if z_score > 3.0:
            # Abnormally LARGE (trap risk)
            return {
                'is_anomaly': True,
                'severity': 'CRITICAL',
                'reason': f'ORB size {orb_size:.3f} is {z_score:.1f} std devs above normal ({mean:.3f}). Potential trap/manipulation.',
                'z_score': z_score,
                'direction': 'LARGE'
            }
        elif z_score > 2.0:
            return {
                'is_anomaly': True,
                'severity': 'HIGH',
                'reason': f'ORB size {orb_size:.3f} is unusually large. Caution advised.',
                'z_score': z_score,
                'direction': 'LARGE'
            }
        elif z_score < -2.0:
            # Abnormally SMALL (low probability)
            return {
                'is_anomaly': True,
                'severity': 'MEDIUM',
                'reason': f'ORB size {orb_size:.3f} is unusually small. Low breakout probability.',
                'z_score': z_score,
                'direction': 'SMALL'
            }
        else:
            return {
                'is_anomaly': False,
                'severity': 'NONE',
                'reason': 'ORB size within normal range',
                'z_score': z_score
            }

    def check_orb_size_filter(self, orb_time: str, orb_size: float) -> Dict:
        """
        Check if ORB passes the size filter from config.py.

        Returns:
            {
                'passes_filter': bool,
                'filter_value': float or None,
                'orb_size': float,
                'reason': str
            }
        """
        if orb_size is None:
            return {
                'passes_filter': False,
                'filter_value': None,
                'orb_size': None,
                'reason': 'ORB not formed yet'
            }

        filter_values = MGC_ORB_SIZE_FILTERS.get(orb_time)

        # Handle None or empty list
        if not filter_values:
            return {
                'passes_filter': True,
                'filter_value': None,
                'orb_size': orb_size,
                'reason': 'No size filter configured (all sizes valid)'
            }

        # Convert single value to list for consistency
        if not isinstance(filter_values, list):
            filter_values = [filter_values]

        # If ANY config has no filter (None), setup always passes
        if None in filter_values:
            return {
                'passes_filter': True,
                'filter_value': None,
                'orb_size': orb_size,
                'reason': 'At least one config has no filter (all sizes valid)'
            }

        # Use most permissive filter (minimum value = easiest to pass)
        filter_value = min(filter_values)

        # Filter logic: ORB size must be >= filter_value
        passes = orb_size >= filter_value

        return {
            'passes_filter': passes,
            'filter_value': filter_value,
            'orb_size': orb_size,
            'reason': f'ORB size {orb_size:.3f} {"passes" if passes else "fails"} filter (>= {filter_value:.3f})'
        }

    def check_l4_consolidation_filter(self, london_type_code: Optional[str]) -> Dict:
        """
        Check if London session was L4_CONSOLIDATION (stayed within Asia range).

        L4_CONSOLIDATION = London did not take Asia high or low (consolidation pattern)
        This favors ORB breakouts as price is coiled/compressed.

        Returns:
            {
                'passes_filter': bool,
                'london_type': str or None,
                'reason': str
            }
        """
        if london_type_code is None:
            return {
                'passes_filter': False,
                'london_type': None,
                'reason': 'London session data not available yet'
            }

        passes = london_type_code == 'L4_CONSOLIDATION'

        return {
            'passes_filter': passes,
            'london_type': london_type_code,
            'reason': f'London {london_type_code} - {"PASS (consolidation favors breakouts)" if passes else "FAIL (need L4_CONSOLIDATION)"}'
        }

    def check_rsi_filter(self, rsi_value: Optional[float], threshold: float = 70.0) -> Dict:
        """
        Check if RSI is above threshold (overbought condition).

        RSI > 70 = overbought, momentum favors continuation breakouts.

        Returns:
            {
                'passes_filter': bool,
                'rsi_value': float or None,
                'threshold': float,
                'reason': str
            }
        """
        if rsi_value is None:
            return {
                'passes_filter': False,
                'rsi_value': None,
                'threshold': threshold,
                'reason': 'RSI data not available yet'
            }

        passes = rsi_value > threshold

        return {
            'passes_filter': passes,
            'rsi_value': rsi_value,
            'threshold': threshold,
            'reason': f'RSI {rsi_value:.1f} {"PASS" if passes else "FAIL"} (need > {threshold})'
        }

    def get_required_filters(self, orb_time: str) -> List[str]:
        """
        Query validated_setups to determine which filters are required for this ORB.

        Parses the 'notes' field to extract filter types.

        Returns list of filter types: ['L4_CONSOLIDATION'], ['RSI>70'], or []
        """
        try:
            conn = duckdb.connect(self.db_path, read_only=True)

            query = """
                SELECT DISTINCT notes
                FROM validated_setups
                WHERE instrument = 'MGC'
                  AND orb_time = ?
            """

            results = conn.execute(query, [orb_time]).fetchall()
            conn.close()

            if not results:
                return []

            # Parse filters from notes
            filters = set()
            for (notes,) in results:
                if notes:
                    if 'L4_CONSOLIDATION' in notes:
                        filters.add('L4_CONSOLIDATION')
                    if 'RSI > 70' in notes or 'RSI>70' in notes:
                        filters.add('RSI>70')

            return list(filters)

        except Exception as e:
            print(f"Warning: Could not query validated_setups: {e}")
            return []

    def validate_setup(self, orb_time: str, date_local: Optional[date] = None) -> Dict:
        """
        Comprehensive validation of a single setup.

        Checks:
        1. ORB size filter (from config.py)
        2. ORB size anomaly (trap detection)
        3. Session conditions (Asia travel, London chop)
        4. Already broken (don't suggest if already traded)

        Returns:
            {
                'orb_time': str,
                'valid': bool,
                'confidence': 'HIGH'|'MEDIUM'|'LOW'|'INVALID',
                'recommendation': 'TAKE'|'SKIP'|'CAUTION',
                'reasons': List[str],
                'conditions': Dict,
                'filters': Dict,
                'anomalies': Dict
            }
        """
        conditions = self.get_today_conditions(date_local)

        if not conditions['data_available']:
            return {
                'orb_time': orb_time,
                'valid': False,
                'confidence': 'INVALID',
                'recommendation': 'SKIP',
                'reasons': ['No market data available for today'],
                'conditions': conditions,
                'orb_size_filter': {},
                'validated_filters': {},
                'anomalies': {}
            }

        orb_size = conditions['orb_sizes'].get(orb_time)
        already_broken = conditions['orb_broken'].get(orb_time, False)

        reasons = []
        valid = True
        confidence = 'HIGH'

        # Check 1: Already broken?
        if already_broken:
            reasons.append(f'{orb_time} ORB already broken (trade opportunity passed)')
            return {
                'orb_time': orb_time,
                'valid': False,
                'confidence': 'INVALID',
                'recommendation': 'SKIP',
                'reasons': reasons,
                'conditions': conditions,
                'orb_size_filter': {},
                'validated_filters': {},
                'anomalies': {}
            }

        # Check 2: ORB formed yet?
        if orb_size is None:
            reasons.append(f'{orb_time} ORB not formed yet (wait for formation)')
            return {
                'orb_time': orb_time,
                'valid': False,
                'confidence': 'INVALID',
                'recommendation': 'WAIT',
                'reasons': reasons,
                'conditions': conditions,
                'orb_size_filter': {},
                'validated_filters': {},
                'anomalies': {}
            }

        # Check 3: ORB size filter
        filter_check = self.check_orb_size_filter(orb_time, orb_size)
        if not filter_check['passes_filter']:
            reasons.append(filter_check['reason'])
            valid = False

        # Check 4: ORB size anomaly
        anomaly_check = self.check_orb_size_anomaly(orb_time, orb_size)
        if anomaly_check['is_anomaly']:
            reasons.append(anomaly_check['reason'])
            if anomaly_check['severity'] == 'CRITICAL':
                valid = False
                confidence = 'INVALID'
            elif anomaly_check['severity'] == 'HIGH':
                confidence = 'LOW'
            elif anomaly_check['severity'] == 'MEDIUM':
                confidence = 'MEDIUM'

        # Check 5: Validated filter requirements (L4_CONSOLIDATION or RSI>70)
        required_filters = self.get_required_filters(orb_time)
        filter_results = {}

        if required_filters:
            # Check if ANY of the required filters pass (OR logic)
            # This allows trading different filter variants of the same ORB
            any_filter_passed = False

            for filter_type in required_filters:
                if filter_type == 'L4_CONSOLIDATION':
                    l4_check = self.check_l4_consolidation_filter(conditions.get('london_type_code'))
                    filter_results['L4_CONSOLIDATION'] = l4_check
                    if l4_check['passes_filter']:
                        any_filter_passed = True
                        reasons.append(l4_check['reason'])

                elif filter_type == 'RSI>70':
                    rsi_check = self.check_rsi_filter(conditions.get('rsi_at_0030'), threshold=70.0)
                    filter_results['RSI>70'] = rsi_check
                    if rsi_check['passes_filter']:
                        any_filter_passed = True
                        reasons.append(rsi_check['reason'])

            # If NO filters passed, setup is INVALID
            if not any_filter_passed:
                valid = False
                # Add reasons for failed filters
                for filter_type, result in filter_results.items():
                    if not result['passes_filter']:
                        reasons.append(result['reason'])

        # Check 6: Session conditions (TODO: Add pattern matching from learned_patterns)
        # For now, check basic Asia travel
        if conditions['asia_travel'] is not None:
            if conditions['asia_travel'] > 2.5:
                reasons.append(f'High Asia travel ({conditions["asia_travel"]:.2f}) - favorable for breakouts')
                # Boosts confidence
                if confidence == 'MEDIUM':
                    confidence = 'HIGH'
            elif conditions['asia_travel'] < 1.5:
                reasons.append(f'Low Asia travel ({conditions["asia_travel"]:.2f}) - lower breakout probability')
                if confidence == 'HIGH':
                    confidence = 'MEDIUM'

        # Determine recommendation
        if not valid:
            recommendation = 'SKIP'
        elif confidence == 'HIGH':
            recommendation = 'TAKE'
        elif confidence == 'MEDIUM':
            recommendation = 'CAUTION'
        else:
            recommendation = 'SKIP'

        # Add positive reason if valid
        if valid and not reasons:
            reasons.append(f'{orb_time} ORB passes all checks - setup valid')

        return {
            'orb_time': orb_time,
            'valid': valid,
            'confidence': confidence,
            'recommendation': recommendation,
            'reasons': reasons,
            'conditions': conditions,
            'orb_size_filter': filter_check,
            'validated_filters': filter_results,  # L4_CONSOLIDATION and/or RSI>70
            'anomalies': anomaly_check
        }

    def scan_all_setups(self, date_local: Optional[date] = None, auto_update: bool = False) -> Dict:
        """
        Scan ALL validated MGC setups and return which ones are valid today.

        Args:
            date_local: Date to scan (default: today)
            auto_update: If True, automatically backfill data gaps before scanning

        Returns:
            {
                'date_local': date,
                'scan_time': datetime,
                'valid_setups': List[Dict],  # Setups with recommendation TAKE
                'caution_setups': List[Dict],  # Setups with recommendation CAUTION
                'invalid_setups': List[Dict],  # Setups with recommendation SKIP
                'summary': str
            }
        """
        if date_local is None:
            date_local = datetime.now(self.tz_local).date()

        # Auto-update data if requested
        if auto_update:
            try:
                from trading_app.data_bridge import DataBridge
                print(f"\n[INFO] Auto-update enabled - checking for data gaps...")
                bridge = DataBridge(self.db_path)
                bridge.update_to_current()
            except Exception as e:
                print(f"[WARN] Auto-update failed: {e}")
                print(f"[INFO] Continuing with existing data...")

        # Get all MGC ORB times from config
        all_orb_times = list(MGC_ORB_CONFIGS.keys())

        valid_setups = []
        caution_setups = []
        invalid_setups = []

        for orb_time in all_orb_times:
            validation = self.validate_setup(orb_time, date_local)

            if validation['recommendation'] == 'TAKE':
                valid_setups.append(validation)
            elif validation['recommendation'] == 'CAUTION':
                caution_setups.append(validation)
            else:  # SKIP or WAIT
                invalid_setups.append(validation)

        # Generate summary
        summary_parts = []
        if valid_setups:
            orbs = ', '.join([s['orb_time'] for s in valid_setups])
            summary_parts.append(f"[OK] VALID: {orbs}")
        if caution_setups:
            orbs = ', '.join([s['orb_time'] for s in caution_setups])
            summary_parts.append(f"[!] CAUTION: {orbs}")
        if not valid_setups and not caution_setups:
            summary_parts.append("[X] No valid setups today")

        summary = ' | '.join(summary_parts)

        return {
            'date_local': date_local,
            'scan_time': datetime.now(self.tz_local),
            'valid_setups': valid_setups,
            'caution_setups': caution_setups,
            'invalid_setups': invalid_setups,
            'summary': summary,
            'total_checked': len(all_orb_times),
            'valid_count': len(valid_setups),
            'caution_count': len(caution_setups),
            'invalid_count': len(invalid_setups)
        }

    def print_scan_report(self, scan_results: Dict):
        """Pretty-print scan results"""
        print("\n" + "="*70)
        print(f"MARKET SCAN REPORT - {scan_results['date_local']}")
        print(f"Scan time: {scan_results['scan_time'].strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print("="*70)

        print(f"\nSUMMARY: {scan_results['summary']}")
        print(f"Total setups checked: {scan_results['total_checked']}")
        print(f"  Valid: {scan_results['valid_count']}")
        print(f"  Caution: {scan_results['caution_count']}")
        print(f"  Invalid: {scan_results['invalid_count']}")

        if scan_results['valid_setups']:
            print("\n[OK] VALID SETUPS (High confidence - TAKE TRADE):")
            print("-" * 70)
            for setup in scan_results['valid_setups']:
                orb_size = setup['conditions']['orb_sizes'].get(setup['orb_time'])
                size_str = f"{orb_size:.3f}" if orb_size is not None else "Not formed"
                print(f"\n{setup['orb_time']} ORB - {setup['confidence']} confidence")
                print(f"  ORB size: {size_str}")
                for reason in setup['reasons']:
                    print(f"  - {reason}")

        if scan_results['caution_setups']:
            print("\n[!] CAUTION SETUPS (Medium confidence - trade with care):")
            print("-" * 70)
            for setup in scan_results['caution_setups']:
                orb_size = setup['conditions']['orb_sizes'].get(setup['orb_time'])
                size_str = f"{orb_size:.3f}" if orb_size is not None else "Not formed"
                print(f"\n{setup['orb_time']} ORB - {setup['confidence']} confidence")
                print(f"  ORB size: {size_str}")
                for reason in setup['reasons']:
                    print(f"  - {reason}")

        if scan_results['invalid_setups']:
            print("\n[X] INVALID SETUPS (Skip today):")
            print("-" * 70)
            for setup in scan_results['invalid_setups']:
                orb_size = setup['conditions']['orb_sizes'].get(setup['orb_time'])
                size_str = f"{orb_size:.3f}" if orb_size is not None else "Not formed"
                print(f"\n{setup['orb_time']} ORB - {setup['recommendation']}")
                print(f"  ORB size: {size_str}")
                for reason in setup['reasons']:
                    print(f"  - {reason}")

        print("\n" + "="*70)


def main():
    """Demo: Scan today's market and show valid setups"""
    scanner = MarketScanner()

    # Option 1: Scan all setups for today
    results = scanner.scan_all_setups()
    scanner.print_scan_report(results)

    # Option 2: Validate a specific setup
    print("\n\nDETAILED CHECK: 1100 ORB")
    print("="*70)
    validation = scanner.validate_setup('1100')
    print(f"Valid: {validation['valid']}")
    print(f"Confidence: {validation['confidence']}")
    print(f"Recommendation: {validation['recommendation']}")
    print("\nReasons:")
    for reason in validation['reasons']:
        print(f"  • {reason}")


if __name__ == "__main__":
    main()
