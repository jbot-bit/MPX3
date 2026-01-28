"""
Live Setup Scanner - Real-Time Market Analysis

Analyzes current market conditions and determines which validated edges
have their filter conditions met.

Usage:
    from live_scanner import LiveScanner

    scanner = LiveScanner(db_connection)
    active_setups = scanner.scan_current_market()

    for setup in active_setups:
        print(f"{setup['edge_id']}: {setup['status']} - {setup['reason']}")
"""

import duckdb
from typing import Dict, List, Optional
from datetime import datetime, date, time, timedelta
import json


class LiveScanner:
    """Real-time market scanner for validated edges"""

    def __init__(self, db_connection: duckdb.DuckDBPyConnection):
        self.conn = db_connection

    def get_current_market_state(self, instrument: str = 'MGC') -> Dict:
        """
        Get current market state for instrument

        Returns:
            Dict with:
            - date_local: Today's date
            - current_time_local: Current time in Brisbane
            - available_orbs: List of ORBs that have completed
            - orb_data: Dict of ORB sizes and directions for completed ORBs
        """
        now_local = datetime.now()  # Assumes system is in Brisbane timezone
        today_date = now_local.date()
        current_time = now_local.time()

        # Check which ORBs have completed
        orb_times = {
            '0900': time(9, 5),   # 09:00-09:05
            '1000': time(10, 5),  # 10:00-10:05
            '1100': time(11, 5),  # 11:00-11:05
            '1800': time(18, 5),  # 18:00-18:05
            '2300': time(23, 5),  # 23:00-23:05
            '0030': time(0, 35)   # 00:30-00:35
        }

        available_orbs = []
        for orb_name, orb_end_time in orb_times.items():
            if current_time >= orb_end_time:
                available_orbs.append(orb_name)

        # Get ORB data from daily_features
        orb_data = {}
        try:
            row = self.conn.execute("""
                SELECT
                    date_local, atr_20,
                    orb_0900_size, orb_0900_break_dir,
                    orb_1000_size, orb_1000_break_dir,
                    orb_1100_size, orb_1100_break_dir,
                    orb_1800_size, orb_1800_break_dir,
                    orb_2300_size, orb_2300_break_dir,
                    orb_0030_size, orb_0030_break_dir
                FROM daily_features
                WHERE date_local = ? AND instrument = ?
            """, [today_date, instrument]).fetchone()

            if row:
                atr = row[1]
                orb_data['atr_20'] = atr

                orb_columns = [
                    ('0900', row[2], row[3]),
                    ('1000', row[4], row[5]),
                    ('1100', row[6], row[7]),
                    ('1800', row[8], row[9]),
                    ('2300', row[10], row[11]),
                    ('0030', row[12], row[13])
                ]

                for orb_name, orb_size, break_dir in orb_columns:
                    if orb_name in available_orbs and orb_size is not None:
                        orb_size_norm = orb_size / atr if atr and atr > 0 else None
                        orb_data[orb_name] = {
                            'size': orb_size,
                            'size_norm': orb_size_norm,
                            'break_dir': break_dir,
                            'atr': atr
                        }
        except Exception as e:
            orb_data['error'] = str(e)

        return {
            'date_local': today_date,
            'current_time_local': current_time,
            'available_orbs': available_orbs,
            'orb_data': orb_data,
            'instrument': instrument
        }

    def scan_current_market(self, instrument: str = 'MGC') -> List[Dict]:
        """
        Scan current market and return active setups

        Returns:
            List of dicts with:
            - edge_id: The edge ID
            - instrument, orb_time, direction, rr, sl_mode: Edge definition
            - status: 'ACTIVE' | 'WAITING' | 'INVALID'
            - reason: Why it's active/waiting/invalid
            - orb_size: Current ORB size (if available)
            - orb_size_norm: Normalized ORB size (if available)
            - filter_threshold: Required threshold
            - passes_filter: Boolean
        """
        # Get current market state
        market_state = self.get_current_market_state(instrument)
        available_orbs = market_state['available_orbs']
        orb_data = market_state['orb_data']

        # Get all PROMOTED edges for this instrument
        edges = self.conn.execute("""
            SELECT
                edge_id, instrument, orb_time, direction,
                trigger_definition, filters_applied, rr, sl_mode,
                notes
            FROM edge_registry
            WHERE status = 'PROMOTED' AND instrument = ?
        """, [instrument]).fetchall()

        results = []

        for edge in edges:
            edge_id, inst, orb_time, direction, trigger, filters_json, rr, sl_mode, notes = edge

            # Parse filters
            filters = {}
            if filters_json:
                if isinstance(filters_json, str):
                    filters = json.loads(filters_json)
                else:
                    filters = filters_json

            orb_size_filter = filters.get('orb_size_filter')

            # Check if ORB has completed
            if orb_time not in available_orbs:
                results.append({
                    'edge_id': edge_id,
                    'instrument': inst,
                    'orb_time': orb_time,
                    'direction': direction,
                    'rr': rr,
                    'sl_mode': sl_mode,
                    'trigger_definition': trigger,
                    'status': 'WAITING',
                    'reason': f'ORB {orb_time} has not completed yet',
                    'orb_size': None,
                    'orb_size_norm': None,
                    'filter_threshold': orb_size_filter,
                    'passes_filter': False
                })
                continue

            # Check if ORB data is available
            if orb_time not in orb_data or orb_data.get('error'):
                results.append({
                    'edge_id': edge_id,
                    'instrument': inst,
                    'orb_time': orb_time,
                    'direction': direction,
                    'rr': rr,
                    'sl_mode': sl_mode,
                    'trigger_definition': trigger,
                    'status': 'INVALID',
                    'reason': f'No ORB data available for today (check data pipeline)',
                    'orb_size': None,
                    'orb_size_norm': None,
                    'filter_threshold': orb_size_filter,
                    'passes_filter': False
                })
                continue

            orb = orb_data[orb_time]
            orb_size = orb['size']
            orb_size_norm = orb['size_norm']
            break_dir = orb['break_dir']

            # Check size filter
            passes_size_filter = True
            filter_reason = None

            if orb_size_filter is not None:
                if orb_size_norm is None:
                    passes_size_filter = False
                    filter_reason = "ATR not available (cannot calculate normalized size)"
                elif orb_size_norm <= orb_size_filter:
                    passes_size_filter = False
                    filter_reason = f"ORB too small ({orb_size_norm:.3f} <= {orb_size_filter:.3f})"

            # Check direction filter
            passes_direction_filter = True
            direction_reason = None

            if direction != 'BOTH':
                if break_dir is None or break_dir == 'NONE':
                    passes_direction_filter = False
                    direction_reason = "No breakout detected yet"
                elif direction == 'LONG' and break_dir != 'UP':
                    passes_direction_filter = False
                    direction_reason = f"Direction mismatch (edge wants LONG, ORB broke {break_dir})"
                elif direction == 'SHORT' and break_dir != 'DOWN':
                    passes_direction_filter = False
                    direction_reason = f"Direction mismatch (edge wants SHORT, ORB broke {break_dir})"

            # Determine overall status
            if passes_size_filter and passes_direction_filter:
                status = 'ACTIVE'
                reason = f"All filters passed! ORB size: {orb_size_norm:.3f}, Break: {break_dir}"
            elif not passes_size_filter:
                status = 'INVALID'
                reason = filter_reason
            elif not passes_direction_filter:
                status = 'WAITING'
                reason = direction_reason
            else:
                status = 'INVALID'
                reason = "Unknown filter failure"

            results.append({
                'edge_id': edge_id,
                'instrument': inst,
                'orb_time': orb_time,
                'direction': direction,
                'rr': rr,
                'sl_mode': sl_mode,
                'trigger_definition': trigger,
                'status': status,
                'reason': reason,
                'orb_size': orb_size,
                'orb_size_norm': orb_size_norm,
                'break_dir': break_dir,
                'filter_threshold': orb_size_filter,
                'passes_filter': passes_size_filter and passes_direction_filter
            })

        return results

    def get_active_setups(self, instrument: str = 'MGC') -> List[Dict]:
        """
        Get only ACTIVE setups (filters passed, ready to trade)

        Returns:
            List of active setups
        """
        all_setups = self.scan_current_market(instrument)
        return [s for s in all_setups if s['status'] == 'ACTIVE']

    def get_waiting_setups(self, instrument: str = 'MGC') -> List[Dict]:
        """
        Get WAITING setups (ORB completed but filters not met yet)

        Returns:
            List of waiting setups
        """
        all_setups = self.scan_current_market(instrument)
        return [s for s in all_setups if s['status'] == 'WAITING']

    def get_invalid_setups(self, instrument: str = 'MGC') -> List[Dict]:
        """
        Get INVALID setups (filters failed, not tradeable today)

        Returns:
            List of invalid setups
        """
        all_setups = self.scan_current_market(instrument)
        return [s for s in all_setups if s['status'] == 'INVALID']
