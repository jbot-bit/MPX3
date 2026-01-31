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
import logging
from trading_app.time_spec import ORBS, ORB_FORMATION  # TSOT: Canonical ORB time source

# Phase 3A: Explicit logging for fail-closed visibility
logger = logging.getLogger(__name__)


class LiveScanner:
    """Real-time market scanner for validated edges"""

    def __init__(self, db_connection: duckdb.DuckDBPyConnection):
        self.conn = db_connection
        self._condition_cache = {}  # Cache promoted conditions

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

        # Check which ORBs have completed (use canonical ORB_FORMATION end times)
        orb_end_times = {orb: ORB_FORMATION[orb]['end'] for orb in ORBS}

        available_orbs = []
        for orb_name, orb_end_time in orb_end_times.items():
            if current_time >= orb_end_time:
                available_orbs.append(orb_name)

        # Get ORB data from daily_features
        orb_data = {}
        try:
            row = self.conn.execute("""
                SELECT
                    date_local, atr_20,
                    orb_0900_high, orb_0900_low, orb_0900_size, orb_0900_break_dir,
                    orb_0900_tradeable_entry_price, orb_0900_tradeable_stop_price, orb_0900_tradeable_target_price,
                    orb_1000_high, orb_1000_low, orb_1000_size, orb_1000_break_dir,
                    orb_1000_tradeable_entry_price, orb_1000_tradeable_stop_price, orb_1000_tradeable_target_price,
                    orb_1100_high, orb_1100_low, orb_1100_size, orb_1100_break_dir,
                    orb_1100_tradeable_entry_price, orb_1100_tradeable_stop_price, orb_1100_tradeable_target_price,
                    orb_1800_high, orb_1800_low, orb_1800_size, orb_1800_break_dir,
                    orb_1800_tradeable_entry_price, orb_1800_tradeable_stop_price, orb_1800_tradeable_target_price,
                    orb_2300_high, orb_2300_low, orb_2300_size, orb_2300_break_dir,
                    orb_2300_tradeable_entry_price, orb_2300_tradeable_stop_price, orb_2300_tradeable_target_price,
                    orb_0030_high, orb_0030_low, orb_0030_size, orb_0030_break_dir,
                    orb_0030_tradeable_entry_price, orb_0030_tradeable_stop_price, orb_0030_tradeable_target_price
                FROM daily_features
                WHERE date_local = ? AND instrument = ?
            """, [today_date, instrument]).fetchone()

            if row:
                atr = row[1]
                orb_data['atr_20'] = atr

                # Build orb_columns dynamically using canonical ORBS
                # Row structure: [date_local, atr_20, then 7 cols per ORB]
                orb_columns = []
                for i, orb_name in enumerate(ORBS):
                    base_idx = 2 + (i * 7)
                    orb_columns.append((
                        orb_name,
                        row[base_idx], row[base_idx+1], row[base_idx+2], row[base_idx+3],
                        row[base_idx+4], row[base_idx+5], row[base_idx+6]
                    ))

                for orb_name, high, low, orb_size, break_dir, entry, stop, target in orb_columns:
                    if orb_name in available_orbs and orb_size is not None:
                        orb_size_norm = orb_size / atr if atr and atr > 0 else None
                        orb_data[orb_name] = {
                            'high': high,
                            'low': low,
                            'size': orb_size,
                            'size_norm': orb_size_norm,
                            'break_dir': break_dir,
                            'atr': atr,
                            'entry_price': entry,
                            'stop_price': stop,
                            'target_price': target
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

    def _load_promoted_conditions(self, edge_id: str) -> Optional[Dict]:
        """
        Load promoted condition rules for an edge

        Checks if edge was created from a What-If snapshot with conditions.

        Returns:
            Dict of conditions or None
        """
        if edge_id in self._condition_cache:
            return self._condition_cache[edge_id]

        try:
            # Check what_if_snapshots for promoted snapshot linked to this edge
            row = self.conn.execute("""
                SELECT conditions
                FROM what_if_snapshots
                WHERE candidate_edge_id = ?
                AND promoted_to_candidate = TRUE
                LIMIT 1
            """, [edge_id]).fetchone()

            if row:
                conditions = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                self._condition_cache[edge_id] = conditions
                return conditions
            else:
                self._condition_cache[edge_id] = None
                return None

        except Exception as e:
            # Phase 3A: Explicit logging for fail-closed visibility
            logger.error(f"DEGRADED: Failed to load promoted conditions for edge {edge_id}: {e}")
            # Return None with degraded flag - caller should treat as "conditions unknown"
            # NOT as "no conditions exist"
            self._condition_cache[edge_id] = {'_load_error': str(e), '_degraded': True}
            return None

    def _evaluate_conditions(
        self,
        conditions: Dict,
        market_state: Dict,
        orb_time: str
    ) -> tuple:
        """
        Evaluate promoted conditions against current market state

        Args:
            conditions: Condition dict from snapshot
            market_state: Current market state
            orb_time: ORB time being evaluated

        Returns:
            (passes: bool, reason: str)
        """
        orb_data = market_state.get('orb_data', {})
        orb_info = orb_data.get(orb_time, {})

        if not orb_info:
            return False, "ORB data not available"

        orb_size_norm = orb_info.get('size_norm')
        atr = orb_info.get('atr')

        # Check ORB size conditions
        if 'orb_size_min' in conditions and conditions['orb_size_min'] is not None:
            if orb_size_norm is None or orb_size_norm < conditions['orb_size_min']:
                return False, f"ORB size {orb_size_norm:.2f} < {conditions['orb_size_min']:.2f} ATR"

        if 'orb_size_max' in conditions and conditions['orb_size_max'] is not None:
            if orb_size_norm is None or orb_size_norm > conditions['orb_size_max']:
                return False, f"ORB size {orb_size_norm:.2f} > {conditions['orb_size_max']:.2f} ATR"

        # Check pre-travel conditions
        if 'pre_orb_travel_max' in conditions and conditions['pre_orb_travel_max'] is not None:
            # Would need to query daily_features for pre_orb_travel
            # For V1, skip this check in live mode (requires additional query)
            pass

        # Check session type conditions
        if 'asia_types' in conditions and conditions['asia_types'] is not None:
            # Would need to query daily_features for asia_type
            # For V1, skip this check in live mode
            pass

        # All checks passed
        return True, "All conditions met"

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

            # Check promoted conditions (What-If validated filters)
            passes_promoted_conditions = True
            promoted_reason = None
            is_degraded = False

            promoted_conditions = self._load_promoted_conditions(edge_id)

            # Phase 3A: Check for degraded state (condition load failure)
            cached_state = self._condition_cache.get(edge_id)
            if cached_state and isinstance(cached_state, dict) and cached_state.get('_degraded'):
                is_degraded = True
                promoted_reason = f"DEGRADED: {cached_state.get('_load_error', 'condition load failed')}"
                logger.warning(f"Edge {edge_id[:16]}... in degraded state - conditions could not be loaded")
            elif promoted_conditions:
                passes_promoted_conditions, promoted_reason = self._evaluate_conditions(
                    promoted_conditions, market_state, orb_time
                )

            # Determine overall status
            # Phase 3A: DEGRADED status takes priority - fail-closed with visibility
            if is_degraded:
                status = 'DEGRADED'
                reason = promoted_reason
            elif passes_size_filter and passes_direction_filter and passes_promoted_conditions:
                status = 'ACTIVE'
                reason = f"All filters passed! ORB size: {orb_size_norm:.3f}, Break: {break_dir}"
            elif not passes_size_filter:
                status = 'INVALID'
                reason = filter_reason
            elif not passes_direction_filter:
                status = 'WAITING'
                reason = direction_reason
            elif not passes_promoted_conditions:
                status = 'INVALID'
                reason = f"Promoted condition failed: {promoted_reason}"
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
                'passes_filter': passes_size_filter and passes_direction_filter,
                'is_degraded': is_degraded  # Phase 3A: Surface degraded state
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

    def get_latest_price(self, instrument: str = 'MGC') -> Optional[Dict]:
        """
        Get latest bar/price with freshness information

        Returns:
            Dict with:
            - price: Latest close price
            - timestamp: Bar timestamp
            - seconds_ago: Seconds since bar timestamp
            - is_stale: True if > 60 seconds old
            - warning: Optional warning message if stale
        """
        try:
            # Get most recent bar from bars_1m
            row = self.conn.execute("""
                SELECT ts_utc, close
                FROM bars_1m
                WHERE symbol = ?
                ORDER BY ts_utc DESC
                LIMIT 1
            """, [instrument]).fetchone()

            if not row:
                return None

            from zoneinfo import ZoneInfo
            import datetime as dt

            bar_ts_utc = row[0]
            close_price = row[1]

            # Convert to local time
            tz_local = ZoneInfo("Australia/Brisbane")
            bar_ts_local = bar_ts_utc.astimezone(tz_local)

            # Calculate seconds ago
            now_utc = dt.datetime.now(dt.timezone.utc)
            seconds_ago = (now_utc - bar_ts_utc).total_seconds()

            is_stale = seconds_ago > 60
            warning = None

            if is_stale:
                if seconds_ago > 86400:  # > 1 day
                    warning = f"Last bar is {int(seconds_ago/3600)} hours old (weekend/holiday)"
                else:
                    warning = f"Data may be stale ({int(seconds_ago)} seconds old)"

            return {
                'price': float(close_price),
                'timestamp': bar_ts_local,
                'seconds_ago': int(seconds_ago),
                'is_stale': is_stale,
                'warning': warning
            }

        except Exception as e:
            return {'error': str(e)}

    def get_current_market_state_with_fallback(self, instrument: str = 'MGC') -> Dict:
        """
        Get current market state with weekend fallback

        If today has no data (weekend/holiday), falls back to most recent trading day

        Returns:
            Same as get_current_market_state() plus:
            - is_fallback: True if using historical data
            - fallback_date: The date being used (if different from today)
        """
        import datetime as dt

        now_local = datetime.now()
        today_date = now_local.date()

        # Try today first
        market_state = self.get_current_market_state(instrument)

        # Check if we have data
        has_data = bool(market_state['orb_data'] and not market_state['orb_data'].get('error'))

        if has_data:
            market_state['is_fallback'] = False
            market_state['fallback_date'] = None
            return market_state

        # No data for today - find most recent trading day
        try:
            row = self.conn.execute("""
                SELECT date_local, atr_20,
                    orb_0900_high, orb_0900_low, orb_0900_size, orb_0900_break_dir,
                    orb_0900_tradeable_entry_price, orb_0900_tradeable_stop_price, orb_0900_tradeable_target_price,
                    orb_1000_high, orb_1000_low, orb_1000_size, orb_1000_break_dir,
                    orb_1000_tradeable_entry_price, orb_1000_tradeable_stop_price, orb_1000_tradeable_target_price,
                    orb_1100_high, orb_1100_low, orb_1100_size, orb_1100_break_dir,
                    orb_1100_tradeable_entry_price, orb_1100_tradeable_stop_price, orb_1100_tradeable_target_price,
                    orb_1800_high, orb_1800_low, orb_1800_size, orb_1800_break_dir,
                    orb_1800_tradeable_entry_price, orb_1800_tradeable_stop_price, orb_1800_tradeable_target_price,
                    orb_2300_high, orb_2300_low, orb_2300_size, orb_2300_break_dir,
                    orb_2300_tradeable_entry_price, orb_2300_tradeable_stop_price, orb_2300_tradeable_target_price,
                    orb_0030_high, orb_0030_low, orb_0030_size, orb_0030_break_dir,
                    orb_0030_tradeable_entry_price, orb_0030_tradeable_stop_price, orb_0030_tradeable_target_price
                FROM daily_features
                WHERE date_local < ? AND instrument = ?
                ORDER BY date_local DESC
                LIMIT 1
            """, [today_date, instrument]).fetchone()

            if not row:
                # No historical data either
                market_state['is_fallback'] = False
                market_state['fallback_date'] = None
                return market_state

            fallback_date = row[0]
            atr = row[1]

            orb_data = {'atr_20': atr}

            # Build orb_columns dynamically using canonical ORBS
            # Row structure: [date_local, atr_20, then 7 cols per ORB]
            orb_columns = []
            for i, orb_name in enumerate(ORBS):
                base_idx = 2 + (i * 7)
                orb_columns.append((
                    orb_name,
                    row[base_idx], row[base_idx+1], row[base_idx+2], row[base_idx+3],
                    row[base_idx+4], row[base_idx+5], row[base_idx+6]
                ))

            for orb_name, high, low, orb_size, break_dir, entry, stop, target in orb_columns:
                if orb_size is not None:
                    orb_size_norm = orb_size / atr if atr and atr > 0 else None
                    orb_data[orb_name] = {
                        'high': high,
                        'low': low,
                        'size': orb_size,
                        'size_norm': orb_size_norm,
                        'break_dir': break_dir,
                        'atr': atr,
                        'entry_price': entry,
                        'stop_price': stop,
                        'target_price': target
                    }

            # All ORBs are "available" for fallback date
            available_orbs = list(orb_data.keys())
            if 'atr_20' in available_orbs:
                available_orbs.remove('atr_20')

            return {
                'date_local': fallback_date,
                'current_time_local': now_local.time(),
                'available_orbs': available_orbs,
                'orb_data': orb_data,
                'instrument': instrument,
                'is_fallback': True,
                'fallback_date': fallback_date
            }

        except Exception as e:
            market_state['is_fallback'] = False
            market_state['fallback_date'] = None
            market_state['fallback_error'] = str(e)
            return market_state
