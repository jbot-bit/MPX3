"""
What-If Analyzer Engine - Deterministic Query System
====================================================

Evaluates condition sets against historical data to answer:
"What if I only traded when X condition was true?"

Features:
- Deterministic (same inputs = same outputs)
- Caches results (keyed by setup + condition hash)
- Reuses execution_engine.py and cost_model.py
- No UI dependency (pure backend logic)

Usage:
    from what_if_engine import WhatIfEngine

    engine = WhatIfEngine(db_connection)

    result = engine.analyze_conditions(
        instrument='MGC',
        orb_time='1000',
        direction='BOTH',
        rr=2.0,
        sl_mode='FULL',
        conditions={
            'orb_size_min': 0.5,  # ORB >= 0.5 ATR
            'asia_travel_max': 2.5,  # Asia travel < 2.5 ATR
            'session_types': ['QUIET']  # Only QUIET Asia
        },
        date_start='2024-01-01',
        date_end='2025-12-31'
    )

    print(f"Baseline: {result['baseline']['win_rate']:.1%}")
    print(f"With conditions: {result['conditional']['win_rate']:.1%}")
    print(f"Delta: {result['delta']['win_rate_pct']:+.1%}")
"""

import duckdb
import hashlib
import json
import sys
import os
from typing import Dict, List, Optional, Any
from datetime import date, datetime
from dataclasses import dataclass, asdict
import numpy as np

# Add paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.execution_engine import simulate_orb_trade
from pipeline.cost_model import calculate_expectancy, get_cost_model


@dataclass
class ConditionSet:
    """Represents a set of filter conditions"""
    # ORB size filters (normalized by ATR)
    orb_size_min: Optional[float] = None  # ORB >= X ATR
    orb_size_max: Optional[float] = None  # ORB <= X ATR

    # Pre-session travel filters (normalized by ATR)
    asia_travel_max: Optional[float] = None  # Asia travel < X ATR
    pre_orb_travel_max: Optional[float] = None  # Pre-ORB travel < X ATR

    # Session type filters (use actual database values)
    # Asia: 'NO_DATA', 'EXPANDED'
    # London: 'EXPANSION', 'SWEEP_HIGH', 'SWEEP_LOW', 'NO_DATA', 'CONSOLIDATION'
    # NY: (similar patterns)
    asia_types: Optional[List[str]] = None  # ['EXPANDED']
    london_types: Optional[List[str]] = None  # ['CONSOLIDATION', 'EXPANSION']

    # Range percentile filters
    orb_size_percentile_min: Optional[float] = None  # Bottom X%
    orb_size_percentile_max: Optional[float] = None  # Top X%
    percentile_window_days: int = 20  # Rolling window for percentile

    def to_dict(self) -> Dict:
        """Convert to dict for hashing and storage"""
        return asdict(self)

    def to_hash(self) -> str:
        """Generate unique hash for caching"""
        # Sort keys for deterministic hash
        json_str = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.md5(json_str.encode()).hexdigest()[:12]


@dataclass
class MetricsResult:
    """Trade metrics for a dataset"""
    sample_size: int
    win_rate: float
    expected_r: float
    avg_win: float
    avg_loss: float
    max_dd: float
    sharpe_ratio: float
    total_r: float

    # Stress tests
    stress_25_exp_r: float
    stress_50_exp_r: float
    stress_25_pass: bool
    stress_50_pass: bool

    # Raw trades
    trades: List[Dict]

    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if k != 'trades'}


class WhatIfEngine:
    """
    What-If Analyzer Engine

    Evaluates condition sets against historical data with full determinism
    and caching.
    """

    def __init__(self, db_connection: duckdb.DuckDBPyConnection):
        self.conn = db_connection
        self.cache = {}  # In-memory cache (could be replaced with disk cache)

    def analyze_conditions(
        self,
        instrument: str,
        orb_time: str,
        direction: str,  # 'UP', 'DOWN', 'BOTH'
        rr: float,
        sl_mode: str,  # 'FULL' or 'HALF'
        conditions: Optional[Dict] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict:
        """
        Analyze setup with optional conditions

        Returns:
            {
                'baseline': MetricsResult (all trades),
                'conditional': MetricsResult (condition-matched only),
                'non_matched': MetricsResult (condition-excluded),
                'delta': {
                    'sample_size': int (conditional - baseline),
                    'win_rate_pct': float (conditional - baseline in pct points),
                    'expected_r': float (conditional - baseline),
                    ...
                },
                'condition_set': ConditionSet,
                'cache_key': str
            }
        """
        # Parse conditions
        if conditions is None:
            conditions = {}

        condition_set = ConditionSet(**conditions)

        # Generate cache key
        cache_key = self._generate_cache_key(
            instrument, orb_time, direction, rr, sl_mode,
            condition_set, date_start, date_end
        )

        # Check cache
        if use_cache and cache_key in self.cache:
            return self.cache[cache_key]

        # Query daily_features
        dates_and_features = self._query_daily_features(
            instrument, orb_time, date_start, date_end
        )

        if len(dates_and_features) == 0:
            return {
                'error': 'No data found for date range',
                'baseline': None,
                'conditional': None,
                'non_matched': None,
                'delta': None
            }

        # Apply conditions and split into matched/non-matched
        matched_dates, non_matched_dates = self._apply_conditions(
            dates_and_features, orb_time, condition_set
        )

        # Simulate trades for all three sets
        baseline_trades = self._simulate_trades(
            dates_and_features, instrument, orb_time, direction, rr, sl_mode
        )

        conditional_trades = self._simulate_trades(
            matched_dates, instrument, orb_time, direction, rr, sl_mode
        )

        non_matched_trades = self._simulate_trades(
            non_matched_dates, instrument, orb_time, direction, rr, sl_mode
        )

        # Calculate metrics
        baseline_metrics = self._calculate_metrics(baseline_trades, instrument)
        conditional_metrics = self._calculate_metrics(conditional_trades, instrument)
        non_matched_metrics = self._calculate_metrics(non_matched_trades, instrument)

        # Calculate deltas
        delta = self._calculate_delta(baseline_metrics, conditional_metrics)

        result = {
            'baseline': baseline_metrics,
            'conditional': conditional_metrics,
            'non_matched': non_matched_metrics,
            'delta': delta,
            'condition_set': condition_set.to_dict(),
            'cache_key': cache_key,
            'timestamp': datetime.now().isoformat()
        }

        # Cache result
        if use_cache:
            self.cache[cache_key] = result

        return result

    def _generate_cache_key(
        self,
        instrument: str,
        orb_time: str,
        direction: str,
        rr: float,
        sl_mode: str,
        condition_set: ConditionSet,
        date_start: Optional[str],
        date_end: Optional[str]
    ) -> str:
        """Generate deterministic cache key"""
        # Convert dates to strings if they're date objects
        start_str = str(date_start) if date_start else 'all'
        end_str = str(date_end) if date_end else 'all'

        key_parts = [
            instrument,
            orb_time,
            direction,
            f"rr{rr}",
            sl_mode.lower(),
            condition_set.to_hash(),
            start_str,
            end_str,
            'v1'  # Version number for cache invalidation
        ]
        return '_'.join(key_parts)

    def _query_daily_features(
        self,
        instrument: str,
        orb_time: str,
        date_start: Optional[str],
        date_end: Optional[str]
    ) -> List[Dict]:
        """Query daily_features with optional date range"""

        # Build WHERE clause
        where_parts = [
            f"instrument = '{instrument}'",
            f"orb_{orb_time}_size IS NOT NULL"
        ]

        if date_start:
            where_parts.append(f"date_local >= '{date_start}'")
        if date_end:
            where_parts.append(f"date_local <= '{date_end}'")

        where_clause = " AND ".join(where_parts)

        query = f"""
            SELECT
                date_local,
                atr_20,
                orb_{orb_time}_size,
                orb_{orb_time}_break_dir,
                pre_orb_travel,
                asia_type,
                london_type,
                ny_type
            FROM daily_features
            WHERE {where_clause}
            ORDER BY date_local
        """

        rows = self.conn.execute(query).fetchall()

        # Convert to dicts
        results = []
        for row in rows:
            results.append({
                'date_local': row[0],
                'atr_20': row[1],
                'orb_size': row[2],
                'orb_break_dir': row[3],
                'pre_orb_travel': row[4],
                'asia_type': row[5],
                'london_type': row[6],
                'ny_type': row[7]
            })

        return results

    def _apply_conditions(
        self,
        dates_and_features: List[Dict],
        orb_time: str,
        conditions: ConditionSet
    ) -> tuple:
        """
        Apply conditions and split into matched/non-matched

        Returns:
            (matched_dates, non_matched_dates)
        """
        matched = []
        non_matched = []

        # Calculate percentiles if needed
        if conditions.orb_size_percentile_min is not None or conditions.orb_size_percentile_max is not None:
            # Calculate rolling percentiles
            for i, d in enumerate(dates_and_features):
                # Get window of recent ORB sizes
                window = conditions.percentile_window_days
                start_idx = max(0, i - window)
                window_sizes = [dates_and_features[j]['orb_size']
                               for j in range(start_idx, i)
                               if dates_and_features[j]['orb_size'] is not None]

                if len(window_sizes) > 0 and d['orb_size'] is not None:
                    # Calculate percentile rank of current ORB size
                    percentile = (sum(x < d['orb_size'] for x in window_sizes) / len(window_sizes)) * 100
                    d['orb_size_percentile'] = percentile
                else:
                    d['orb_size_percentile'] = None

        # Apply filters
        for d in dates_and_features:
            passes = True

            # ORB size filters (normalized)
            if d['atr_20'] and d['atr_20'] > 0:
                orb_size_norm = d['orb_size'] / d['atr_20']

                if conditions.orb_size_min is not None:
                    if orb_size_norm < conditions.orb_size_min:
                        passes = False

                if conditions.orb_size_max is not None:
                    if orb_size_norm > conditions.orb_size_max:
                        passes = False

            # Travel filters (normalized)
            if d['atr_20'] and d['atr_20'] > 0 and d['pre_orb_travel'] is not None:
                travel_norm = d['pre_orb_travel'] / d['atr_20']

                if conditions.pre_orb_travel_max is not None:
                    if travel_norm >= conditions.pre_orb_travel_max:
                        passes = False

            # Session type filters
            if conditions.asia_types is not None:
                if d['asia_type'] not in conditions.asia_types:
                    passes = False

            if conditions.london_types is not None:
                if d['london_type'] not in conditions.london_types:
                    passes = False

            # Percentile filters
            if 'orb_size_percentile' in d and d['orb_size_percentile'] is not None:
                if conditions.orb_size_percentile_min is not None:
                    if d['orb_size_percentile'] < conditions.orb_size_percentile_min:
                        passes = False

                if conditions.orb_size_percentile_max is not None:
                    if d['orb_size_percentile'] > conditions.orb_size_percentile_max:
                        passes = False

            # Append to appropriate list
            if passes:
                matched.append(d)
            else:
                non_matched.append(d)

        return matched, non_matched

    def _simulate_trades(
        self,
        dates: List[Dict],
        instrument: str,
        orb_time: str,
        direction: str,
        rr: float,
        sl_mode: str
    ) -> List[Dict]:
        """Simulate trades using execution_engine.py"""
        trades = []

        for d in dates:
            date_local = d['date_local']
            orb_break_dir = d.get('orb_break_dir')

            # Skip if no break or direction doesn't match
            if orb_break_dir is None or orb_break_dir == 'NONE':
                continue

            if direction != 'BOTH':
                if direction != orb_break_dir:
                    continue

            # Simulate trade
            result = simulate_orb_trade(
                con=self.conn,
                date_local=date_local,
                orb=orb_time,
                mode='1m',
                confirm_bars=1,
                rr=rr,
                sl_mode=sl_mode.lower(),
                buffer_ticks=0,
                entry_delay_bars=0
            )

            # Convert to dict
            trade_dict = asdict(result)
            trade_dict['date_local'] = date_local
            trade_dict['instrument'] = instrument
            trade_dict['orb_time'] = orb_time

            trades.append(trade_dict)

        return trades

    def _calculate_metrics(
        self,
        trades: List[Dict],
        instrument: str
    ) -> MetricsResult:
        """Calculate comprehensive metrics from trades"""

        if len(trades) == 0:
            return MetricsResult(
                sample_size=0,
                win_rate=0.0,
                expected_r=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                max_dd=0.0,
                sharpe_ratio=0.0,
                total_r=0.0,
                stress_25_exp_r=0.0,
                stress_50_exp_r=0.0,
                stress_25_pass=False,
                stress_50_pass=False,
                trades=[]
            )

        # Filter to completed trades only
        completed = [t for t in trades if t['outcome'] in ['WIN', 'LOSS']]

        if len(completed) == 0:
            return MetricsResult(
                sample_size=0,
                win_rate=0.0,
                expected_r=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                max_dd=0.0,
                sharpe_ratio=0.0,
                total_r=0.0,
                stress_25_exp_r=0.0,
                stress_50_exp_r=0.0,
                stress_25_pass=False,
                stress_50_pass=False,
                trades=completed
            )

        # Win rate
        wins = [t for t in completed if t['outcome'] == 'WIN']
        losses = [t for t in completed if t['outcome'] == 'LOSS']
        win_rate = len(wins) / len(completed) if len(completed) > 0 else 0.0

        # Expected R (subtract costs)
        r_multiples = [t['r_multiple'] - t['cost_r'] for t in completed]
        expected_r = np.mean(r_multiples)
        total_r = np.sum(r_multiples)

        # Avg win/loss
        avg_win = np.mean([t['r_multiple'] for t in wins]) if len(wins) > 0 else 0.0
        avg_loss = np.mean([t['r_multiple'] for t in losses]) if len(losses) > 0 else 0.0

        # Max drawdown
        cumulative_r = np.cumsum(r_multiples)
        running_max = np.maximum.accumulate(cumulative_r)
        drawdowns = cumulative_r - running_max
        max_dd = np.min(drawdowns)

        # Sharpe ratio (assuming 0 risk-free rate)
        sharpe = np.mean(r_multiples) / np.std(r_multiples) if np.std(r_multiples) > 0 else 0.0

        # Stress tests (+25% and +50% costs)
        stress_25_r = [t['r_multiple'] - (t['cost_r'] * 1.25) for t in completed]
        stress_50_r = [t['r_multiple'] - (t['cost_r'] * 1.50) for t in completed]

        stress_25_exp_r = np.mean(stress_25_r)
        stress_50_exp_r = np.mean(stress_50_r)

        stress_25_pass = stress_25_exp_r >= 0.15
        stress_50_pass = stress_50_exp_r >= 0.15

        return MetricsResult(
            sample_size=len(completed),
            win_rate=win_rate,
            expected_r=expected_r,
            avg_win=avg_win,
            avg_loss=avg_loss,
            max_dd=max_dd,
            sharpe_ratio=sharpe,
            total_r=total_r,
            stress_25_exp_r=stress_25_exp_r,
            stress_50_exp_r=stress_50_exp_r,
            stress_25_pass=stress_25_pass,
            stress_50_pass=stress_50_pass,
            trades=completed
        )

    def _calculate_delta(
        self,
        baseline: MetricsResult,
        conditional: MetricsResult
    ) -> Dict:
        """Calculate delta between baseline and conditional"""
        return {
            'sample_size': conditional.sample_size - baseline.sample_size,
            'win_rate_pct': (conditional.win_rate - baseline.win_rate) * 100,  # Percentage points
            'expected_r': conditional.expected_r - baseline.expected_r,
            'avg_win': conditional.avg_win - baseline.avg_win,
            'avg_loss': conditional.avg_loss - baseline.avg_loss,
            'max_dd': conditional.max_dd - baseline.max_dd,
            'sharpe_ratio': conditional.sharpe_ratio - baseline.sharpe_ratio,
            'total_r': conditional.total_r - baseline.total_r,
        }

    def clear_cache(self):
        """Clear all cached results"""
        self.cache = {}

    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            'cache_size': len(self.cache),
            'cache_keys': list(self.cache.keys())
        }


if __name__ == "__main__":
    # Test the engine
    import duckdb
    from pathlib import Path

    # Connect to database
    db_path = Path(__file__).parent.parent / "data" / "db" / "gold.db"
    conn = duckdb.connect(str(db_path))

    # Create engine
    engine = WhatIfEngine(conn)

    # Test analysis
    print("Testing What-If Analyzer Engine...")
    print()

    result = engine.analyze_conditions(
        instrument='MGC',
        orb_time='1000',
        direction='BOTH',
        rr=2.0,
        sl_mode='FULL',
        conditions={
            'orb_size_min': 0.5,  # ORB >= 0.5 ATR
            'asia_travel_max': 2.5  # Asia travel < 2.5 ATR
        },
        date_start='2024-01-01',
        date_end='2025-12-31'
    )

    print(f"Baseline:")
    print(f"  Trades: {result['baseline'].sample_size}")
    print(f"  Win Rate: {result['baseline'].win_rate*100:.1f}%")
    print(f"  Expected R: {result['baseline'].expected_r:.3f}R")
    print()

    print(f"With Conditions:")
    print(f"  Trades: {result['conditional'].sample_size}")
    print(f"  Win Rate: {result['conditional'].win_rate*100:.1f}%")
    print(f"  Expected R: {result['conditional'].expected_r:.3f}R")
    print()

    print(f"Delta:")
    print(f"  Trades: {result['delta']['sample_size']:+d}")
    print(f"  Win Rate: {result['delta']['win_rate_pct']:+.1f} pct points")
    print(f"  Expected R: {result['delta']['expected_r']:+.3f}R")
    print()

    print(f"Cache key: {result['cache_key']}")

    conn.close()
