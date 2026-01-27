"""
Edge Evolution Tracker - Monitor Edge Health Over Time

Tracks validated_setups performance, detects degradation, discovers new patterns.

Core functions:
1. Edge health monitoring - Track performance over rolling windows (30/60/90 days)
2. Degradation detection - Early warning when edges stop working
3. Regime change detection - Identify market condition shifts
4. Pattern discovery - Find new edges in recent data

Usage:
    from trading_app.edge_tracker import EdgeTracker

    tracker = EdgeTracker()

    # Check edge health
    health = tracker.check_edge_health('0900', 'MGC')

    # Detect regime changes
    regime = tracker.detect_regime()

    # Get system-wide status
    status = tracker.get_system_status()
"""

import duckdb
import numpy as np
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from scipy import stats

from trading_app.config import DB_PATH, TZ_LOCAL, MGC_ORB_CONFIGS


class EdgeTracker:
    """Monitors edge performance and evolution over time"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.tz_local = TZ_LOCAL

        # Performance thresholds
        self.DEGRADATION_WR_THRESHOLD = 10.0  # % drop in win rate
        self.DEGRADATION_ER_THRESHOLD = 20.0  # % drop in expected R
        self.MIN_SAMPLE_SIZE = 10  # Minimum trades to validate

    def get_baseline_performance(
        self,
        orb_time: str,
        instrument: str = 'MGC'
    ) -> Optional[Dict]:
        """
        Get baseline performance from validated_setups table.

        Args:
            orb_time: ORB time (0900, 1000, etc.)
            instrument: Instrument

        Returns:
            Baseline metrics or None if not found
        """
        conn = duckdb.connect(self.db_path, read_only=True)

        result = conn.execute("""
            SELECT
                win_rate,
                expected_r,
                sample_size,
                rr,
                sl_mode
            FROM validated_setups
            WHERE instrument = ?
              AND orb_time = ?
        """, [instrument, orb_time]).fetchone()
        conn.close()

        if result:
            return {
                'win_rate': result[0],
                'expected_r': result[1],
                'sample_size': result[2],
                'rr': result[3],
                'sl_mode': result[4]
            }
        return None

    def get_recent_performance(
        self,
        orb_time: str,
        instrument: str = 'MGC',
        days_back: int = 30
    ) -> Dict:
        """
        Get recent performance from daily_features.

        This calculates performance from actual backtest data.

        Args:
            orb_time: ORB time
            instrument: Instrument
            days_back: Look back N days

        Returns:
            Recent performance metrics
        """
        conn = duckdb.connect(self.db_path, read_only=True)

        # Column names based on ORB time
        outcome_col = f"orb_{orb_time}_outcome"
        r_col = f"orb_{orb_time}_r_multiple"

        query = f"""
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN {outcome_col} = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN {outcome_col} = 'LOSS' THEN 1 ELSE 0 END) as losses,
                AVG({r_col}) as avg_r,
                SUM({r_col}) as total_r,
                MAX(date_local) as last_date
            FROM daily_features
            WHERE instrument = ?
              AND date_local >= CURRENT_DATE - INTERVAL '{days_back} days'
              AND {outcome_col} IN ('WIN', 'LOSS')
              AND {r_col} IS NOT NULL
        """

        result = conn.execute(query, [instrument]).fetchone()
        conn.close()

        if result and result[0] > 0:
            total, wins, losses, avg_r, total_r, last_date = result
            win_rate = (wins / total) * 100 if total > 0 else 0

            return {
                'total_trades': total,
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate,
                'avg_r': avg_r if avg_r else 0.0,
                'total_r': total_r if total_r else 0.0,
                'last_date': last_date,
                'has_data': True
            }

        return {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'avg_r': 0.0,
            'total_r': 0.0,
            'last_date': None,
            'has_data': False
        }

    def check_edge_health(
        self,
        orb_time: str,
        instrument: str = 'MGC'
    ) -> Dict:
        """
        Check edge health across multiple time windows.

        Args:
            orb_time: ORB time
            instrument: Instrument

        Returns:
            Edge health report with status and recommendations
        """
        # Get baseline
        baseline = self.get_baseline_performance(orb_time, instrument)
        if not baseline:
            return {
                'status': 'NO_DATA',
                'message': f'Setup {orb_time} not found in validated_setups',
                'has_baseline': False,
                'orb_time': orb_time
            }

        # Get recent performance across multiple windows
        perf_30d = self.get_recent_performance(orb_time, instrument, 30)
        perf_60d = self.get_recent_performance(orb_time, instrument, 60)
        perf_90d = self.get_recent_performance(orb_time, instrument, 90)

        # Check if we have enough data
        if perf_30d['total_trades'] < self.MIN_SAMPLE_SIZE:
            return {
                'status': 'INSUFFICIENT_DATA',
                'message': f'Only {perf_30d["total_trades"]} trades in last 30 days (need {self.MIN_SAMPLE_SIZE})',
                'baseline': baseline,
                'recent': perf_30d,
                'has_baseline': True,
                'orb_time': orb_time
            }

        # Calculate performance changes
        wr_change_30d = perf_30d['win_rate'] - baseline['win_rate']
        wr_change_60d = perf_60d['win_rate'] - baseline['win_rate'] if perf_60d['has_data'] else 0
        wr_change_90d = perf_90d['win_rate'] - baseline['win_rate'] if perf_90d['has_data'] else 0

        er_change_30d = ((perf_30d['avg_r'] - baseline['expected_r']) / baseline['expected_r'] * 100) if baseline['expected_r'] != 0 else 0
        er_change_60d = ((perf_60d['avg_r'] - baseline['expected_r']) / baseline['expected_r'] * 100) if perf_60d['has_data'] and baseline['expected_r'] != 0 else 0
        er_change_90d = ((perf_90d['avg_r'] - baseline['expected_r']) / baseline['expected_r'] * 100) if perf_90d['has_data'] and baseline['expected_r'] != 0 else 0

        # Determine status
        status = 'HEALTHY'
        severity = 'low'
        recommendations = []

        # Check for degradation
        if wr_change_30d < -self.DEGRADATION_WR_THRESHOLD or er_change_30d < -self.DEGRADATION_ER_THRESHOLD:
            status = 'DEGRADED'
            severity = 'high'
            recommendations.append('REDUCE POSITION SIZE: Use 50% size until edge stabilizes')
            recommendations.append(f'INVESTIGATE: Recent WR={perf_30d["win_rate"]:.1f}% vs baseline {baseline["win_rate"]:.1f}%')

        elif wr_change_30d < -5.0 or er_change_30d < -10.0:
            status = 'WATCH'
            severity = 'medium'
            recommendations.append('MONITOR CLOSELY: Performance declining but not critical yet')
            recommendations.append('Check next 7-14 days for further degradation')

        else:
            recommendations.append(f'Edge performing well ({perf_30d["win_rate"]:.1f}% WR)')
            recommendations.append('Continue trading as normal')

        # Performance improving
        if wr_change_30d > 5.0 and er_change_30d > 10.0:
            status = 'EXCELLENT'
            recommendations.insert(0, 'EDGE PERFORMING ABOVE BASELINE - Consider increasing focus')

        return {
            'status': status,
            'severity': severity,
            'orb_time': orb_time,
            'instrument': instrument,
            'baseline': baseline,
            'performance': {
                '30d': perf_30d,
                '60d': perf_60d,
                '90d': perf_90d
            },
            'changes': {
                'wr_30d': wr_change_30d,
                'wr_60d': wr_change_60d,
                'wr_90d': wr_change_90d,
                'er_30d': er_change_30d,
                'er_60d': er_change_60d,
                'er_90d': er_change_90d
            },
            'recommendations': recommendations,
            'has_baseline': True
        }

    def get_system_status(self, instrument: str = 'MGC') -> Dict:
        """
        Get system-wide edge health status.

        Checks all validated setups and returns overall health.

        Args:
            instrument: Instrument

        Returns:
            System status summary
        """
        conn = duckdb.connect(self.db_path, read_only=True)

        # Get all validated setups for this instrument
        # Filter to only real ORB times (exclude CASCADE, SINGLE_LIQ, etc.)
        valid_orb_times = ('0030', '0900', '1000', '1100', '1800', '2300')
        setups = conn.execute("""
            SELECT orb_time, rr, win_rate, expected_r
            FROM validated_setups
            WHERE instrument = ?
              AND orb_time IN ('0030', '0900', '1000', '1100', '1800', '2300')
            ORDER BY expected_r DESC
        """, [instrument]).fetchall()
        conn.close()

        if not setups:
            return {
                'status': 'NO_DATA',
                'message': f'No validated setups found for {instrument}',
                'total_edges': 0
            }

        # Check health of each setup
        edge_health = []
        degraded = []
        watch = []
        healthy = []
        excellent = []

        for setup in setups:
            orb_time = setup[0]
            health = self.check_edge_health(orb_time, instrument)

            edge_health.append({
                'orb_time': orb_time,
                'status': health['status'],
                'severity': health.get('severity', 'low'),
                'baseline_wr': setup[2],
                'baseline_er': setup[3]
            })

            if health['status'] == 'DEGRADED':
                degraded.append(orb_time)
            elif health['status'] == 'WATCH':
                watch.append(orb_time)
            elif health['status'] == 'EXCELLENT':
                excellent.append(orb_time)
            elif health['status'] == 'HEALTHY':
                healthy.append(orb_time)

        # Overall system status
        if len(degraded) > 0:
            system_status = 'DEGRADED'
            message = f'{len(degraded)} edge(s) degraded - immediate attention required'
        elif len(watch) > len(healthy):
            system_status = 'CAUTION'
            message = f'{len(watch)} edge(s) on watch list - monitor closely'
        elif len(excellent) > 0:
            system_status = 'EXCELLENT'
            message = f'{len(excellent)} edge(s) performing above baseline'
        else:
            system_status = 'HEALTHY'
            message = 'All edges performing normally'

        return {
            'status': system_status,
            'message': message,
            'instrument': instrument,
            'total_edges': len(setups),
            'degraded': degraded,
            'watch': watch,
            'healthy': healthy,
            'excellent': excellent,
            'edge_health': edge_health,
            'timestamp': datetime.now(self.tz_local)
        }

    def detect_regime(self, days_back: int = 90, instrument: str = 'MGC') -> Dict:
        """
        Detect current market regime based on recent behavior.

        Regime types:
        - TRENDING: Sustained directional moves
        - RANGE_BOUND: Mean reversion dominates
        - VOLATILE: Large swings
        - QUIET: Compressed ranges

        Args:
            days_back: Look back N days
            instrument: Instrument

        Returns:
            Regime classification
        """
        conn = duckdb.connect(self.db_path, read_only=True)

        # Get recent session data
        query = f"""
            SELECT
                date_local,
                asia_high - asia_low as asia_travel,
                london_high - london_low as london_range,
                ny_high - ny_low as ny_range
            FROM daily_features
            WHERE instrument = ?
              AND date_local >= CURRENT_DATE - INTERVAL '{days_back} days'
              AND asia_high IS NOT NULL
              AND asia_low IS NOT NULL
            ORDER BY date_local DESC
        """

        results = conn.execute(query, [instrument]).fetchall()
        conn.close()

        if len(results) < 20:
            return {
                'regime': 'UNKNOWN',
                'confidence': 0.0,
                'message': 'Insufficient data to determine regime'
            }

        # Calculate metrics
        asia_travels = [r[1] for r in results if r[1]]
        london_ranges = [r[2] for r in results if r[2]]
        ny_ranges = [r[3] for r in results if r[3]]

        avg_asia = np.mean(asia_travels)
        std_asia = np.std(asia_travels)
        avg_london = np.mean(london_ranges)
        avg_ny = np.mean(ny_ranges)

        # Classify regime
        if std_asia > 1.5 and avg_ny > 2.5:
            regime = 'VOLATILE'
            confidence = 0.75
            message = 'Large swings and high volatility - adjust position sizing'

        elif avg_asia > 2.0 and avg_ny > 2.0:
            regime = 'TRENDING'
            confidence = 0.80
            message = 'Sustained directional moves - breakouts working well'

        elif avg_asia < 1.0 and avg_ny < 1.5:
            regime = 'QUIET'
            confidence = 0.70
            message = 'Compressed ranges - low probability setups'

        else:
            regime = 'RANGE_BOUND'
            confidence = 0.65
            message = 'Mean reversion environment - breakouts may fail'

        return {
            'regime': regime,
            'confidence': confidence,
            'message': message,
            'metrics': {
                'avg_asia_travel': avg_asia,
                'std_asia_travel': std_asia,
                'avg_london_range': avg_london,
                'avg_ny_range': avg_ny
            },
            'sample_size': len(results),
            'lookback_days': days_back
        }


def main():
    """Demo usage"""
    tracker = EdgeTracker()

    print("\n" + "="*70)
    print("EDGE EVOLUTION TRACKER - Demo")
    print("="*70 + "\n")

    # Check system-wide status
    print("[1] Checking system-wide edge health...")
    status = tracker.get_system_status()
    print(f"  System status: {status['status']}")
    print(f"  {status['message']}")
    print(f"  Total edges: {status['total_edges']}")
    print(f"  Degraded: {len(status['degraded'])}")
    print(f"  Watch: {len(status['watch'])}")
    print(f"  Healthy: {len(status['healthy'])}")
    print(f"  Excellent: {len(status['excellent'])}\n")

    # Check individual edge
    print("[2] Checking 0900 ORB health...")
    health = tracker.check_edge_health('0900')
    if health['has_baseline']:
        print(f"  Status: {health['status']}")
        print(f"  Baseline WR: {health['baseline']['win_rate']:.1f}%")
        if health['performance']['30d']['has_data']:
            print(f"  Recent WR (30d): {health['performance']['30d']['win_rate']:.1f}%")
            print(f"  Change: {health['changes']['wr_30d']:+.1f}%")
        print(f"\n  Recommendations:")
        for rec in health['recommendations']:
            print(f"    - {rec}")
    print()

    # Detect regime
    print("[3] Detecting market regime...")
    regime = tracker.detect_regime()
    print(f"  Regime: {regime['regime']}")
    print(f"  Confidence: {regime['confidence']:.0%}")
    print(f"  {regime['message']}\n")

    print("="*70)
    print("Demo complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
