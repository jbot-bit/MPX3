"""
Filter Optimizer - Systematically find best filters for trading edges

PROBLEM:
- You have 35 new edges from edge discovery
- Need to find filters that improve performance (win rate, expected R, annual R)
- Manual testing is slow and prone to overfitting

SOLUTION:
- Test hundreds of filter combinations systematically
- Use train/test split to prevent overfitting (60% train, 40% test)
- Measure improvement on BOTH train and test sets
- Reject filters that overfit (work on train but not test)
- Output ranked recommendations with statistical confidence

FILTERS TESTED:
1. ORB size filters (0.05, 0.10, 0.15, 0.20, 0.25)
2. Asia travel filters (1.0, 1.5, 2.0, 2.5, 3.0)
3. London range filters (0.5, 1.0, 1.5, 2.0)
4. Pre-NY travel filters (0.5, 1.0, 1.5, 2.0)
5. RSI filters (< 30, < 40, > 60, > 70)
6. ATR filters (< 0.5x ATR, > 1.5x ATR)
7. Day of week filters (exclude Mon/Tue/Wed/Thu/Fri)
8. Asia type filters (TIGHT, NORMAL, EXPANDED)
9. London type filters (SWEEP_HIGH, SWEEP_LOW, EXPANSION, CONSOLIDATION)
10. Combinations (e.g., ORB size + Asia travel)

USAGE:
    # Optimize filters for specific edge:
    python filter_optimizer.py --orb 0900 --rr 1.5 --sl-mode half

    # Optimize all edges at once:
    python filter_optimizer.py --optimize-all

    # Export results to CSV:
    python filter_optimizer.py --orb 0900 --rr 1.5 --export results.csv

OUTPUT:
    Filter Optimization Report
    ==========================
    Edge: 0900 ORB (RR=1.5, SL=HALF)
    Baseline: 58% WR, +0.25R avg, 120 trades, +30R/year

    TOP FILTERS (Ranked by Improvement):

    1. ORB size >= 0.10 AND Asia travel > 1.5
       Train: 68% WR, +0.40R avg, 65 trades, +50R/year (+10% WR, +0.15R)
       Test:  66% WR, +0.38R avg, 28 trades, +48R/year (+8% WR, +0.13R)
       ✅ VALIDATED (test performance within 5% of train)
       Confidence: HIGH (65 train, 28 test trades)

    2. ORB size >= 0.10
       Train: 62% WR, +0.30R avg, 95 trades, +40R/year (+4% WR, +0.05R)
       Test:  60% WR, +0.28R avg, 40 trades, +38R/year (+2% WR, +0.03R)
       ✅ VALIDATED
       Confidence: HIGH

    3. Asia travel > 1.5
       Train: 70% WR, +0.45R avg, 50 trades, +55R/year (+12% WR, +0.20R)
       Test:  58% WR, +0.22R avg, 22 trades, +28R/year (+0% WR, -0.03R)
       ❌ OVERFIT (train +12% WR, test +0% WR)
       Confidence: LOW (overfit detected)
"""

import duckdb
import numpy as np
import pandas as pd
from datetime import date, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from scipy import stats
import argparse

from trading_app.config import DB_PATH, TZ_LOCAL


@dataclass
class FilterResult:
    """Result of testing a single filter"""
    filter_name: str
    filter_condition: str

    # Train set results
    train_trades: int
    train_win_rate: float
    train_avg_r: float
    train_annual_r: float

    # Test set results
    test_trades: int
    test_win_rate: float
    test_avg_r: float
    test_annual_r: float

    # Improvement over baseline
    train_wr_improvement: float
    test_wr_improvement: float
    train_r_improvement: float
    test_r_improvement: float

    # Validation
    is_validated: bool  # True if test performance matches train (not overfit)
    confidence: str  # HIGH, MEDIUM, LOW based on sample size and validation
    overfit_score: float  # Difference between train and test improvement


@dataclass
class EdgeBaseline:
    """Baseline performance of an edge (no filters)"""
    orb_time: str
    rr: float
    sl_mode: str

    # Train set baseline
    train_trades: int
    train_win_rate: float
    train_avg_r: float
    train_annual_r: float

    # Test set baseline
    test_trades: int
    test_win_rate: float
    test_avg_r: float
    test_annual_r: float


class FilterOptimizer:
    """Systematically optimize filters for trading edges"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn = duckdb.connect(db_path, read_only=True)

        # Validation parameters
        self.MIN_TRAIN_TRADES = 30  # Minimum trades in train set
        self.MIN_TEST_TRADES = 15   # Minimum trades in test set
        self.TRAIN_RATIO = 0.60     # 60% train, 40% test
        self.OVERFIT_THRESHOLD = 0.10  # Max 10% difference between train/test WR improvement

        # Filter definitions
        self.orb_size_thresholds = [0.05, 0.10, 0.15, 0.20, 0.25]
        self.asia_travel_thresholds = [1.0, 1.5, 2.0, 2.5, 3.0]
        self.london_range_thresholds = [0.5, 1.0, 1.5, 2.0]
        self.pre_ny_travel_thresholds = [0.5, 1.0, 1.5, 2.0]
        self.rsi_thresholds = [(None, 30), (None, 40), (60, None), (70, None)]
        self.atr_multipliers = [0.5, 1.5]
        self.days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    def get_edge_data(
        self,
        orb_time: str,
        instrument: str = 'MGC',
        min_date: Optional[date] = None,
        max_date: Optional[date] = None
    ) -> pd.DataFrame:
        """
        Get all data for an edge from daily_features.

        Returns DataFrame with columns:
        - date_local
        - orb_size (orb_{time}_size)
        - outcome (orb_{time}_outcome)
        - r_multiple (orb_{time}_r_multiple)
        - asia_travel (asia_high - asia_low)
        - london_range (london_high - london_low)
        - pre_ny_travel (pre-computed in daily_features)
        - rsi (rsi_at_orb)
        - atr (atr_20)
        - day_of_week
        - asia_type
        - london_type
        """
        outcome_col = f"orb_{orb_time}_outcome"
        r_col = f"orb_{orb_time}_r_multiple"
        size_col = f"orb_{orb_time}_size"

        query = f"""
            SELECT
                date_local,
                {size_col} as orb_size,
                {outcome_col} as outcome,
                {r_col} as r_multiple,
                asia_range as asia_travel,
                london_high - london_low as london_range,
                pre_ny_travel,
                rsi_at_orb as rsi,
                atr_20 as atr,
                DAYNAME(date_local) as day_of_week,
                asia_type,
                london_type
            FROM daily_features
            WHERE instrument = ?
              AND {outcome_col} IN ('WIN', 'LOSS')
              AND {r_col} IS NOT NULL
        """

        params = [instrument]

        if min_date:
            query += " AND date_local >= ?"
            params.append(min_date)

        if max_date:
            query += " AND date_local <= ?"
            params.append(max_date)

        query += " ORDER BY date_local"

        df = self.conn.execute(query, params).df()
        return df

    def split_train_test(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Split data into train and test sets chronologically.

        Train = first 60% of data
        Test = last 40% of data
        """
        split_idx = int(len(df) * self.TRAIN_RATIO)
        train = df.iloc[:split_idx].copy()
        test = df.iloc[split_idx:].copy()
        return train, test

    def calculate_baseline(
        self,
        orb_time: str,
        rr: float,
        sl_mode: str,
        instrument: str = 'MGC'
    ) -> EdgeBaseline:
        """Calculate baseline performance (no filters)"""
        df = self.get_edge_data(orb_time, instrument)

        if len(df) == 0:
            raise ValueError(f"No data found for {orb_time} ORB")

        train, test = self.split_train_test(df)

        # Train baseline
        train_wins = (train['outcome'] == 'WIN').sum()
        train_total = len(train)
        train_wr = (train_wins / train_total) * 100 if train_total > 0 else 0
        train_avg_r = train['r_multiple'].mean() if train_total > 0 else 0
        train_annual_r = self._calculate_annual_r(train_avg_r, train_total)

        # Test baseline
        test_wins = (test['outcome'] == 'WIN').sum()
        test_total = len(test)
        test_wr = (test_wins / test_total) * 100 if test_total > 0 else 0
        test_avg_r = test['r_multiple'].mean() if test_total > 0 else 0
        test_annual_r = self._calculate_annual_r(test_avg_r, test_total)

        return EdgeBaseline(
            orb_time=orb_time,
            rr=rr,
            sl_mode=sl_mode,
            train_trades=train_total,
            train_win_rate=train_wr,
            train_avg_r=train_avg_r,
            train_annual_r=train_annual_r,
            test_trades=test_total,
            test_win_rate=test_wr,
            test_avg_r=test_avg_r,
            test_annual_r=test_annual_r
        )

    def _calculate_annual_r(self, avg_r: float, trades: int) -> float:
        """Calculate estimated annual R"""
        if trades == 0:
            return 0.0
        # Assume 740 trading days with data, 260 trading days per year
        trades_per_year = (trades / 740) * 260
        return avg_r * trades_per_year

    def test_filter(
        self,
        train: pd.DataFrame,
        test: pd.DataFrame,
        filter_condition: str,
        filter_name: str,
        baseline: EdgeBaseline
    ) -> Optional[FilterResult]:
        """
        Test a single filter on train and test sets.

        Args:
            train: Training data
            test: Test data
            filter_condition: Pandas query string (e.g., "orb_size >= 0.10")
            filter_name: Human-readable name
            baseline: Baseline performance

        Returns:
            FilterResult if filter has sufficient data, None otherwise
        """
        # Apply filter to train set
        try:
            train_filtered = train.query(filter_condition)
        except Exception as e:
            print(f"  [WARN] Filter '{filter_name}' failed on train: {e}")
            return None

        # Apply filter to test set
        try:
            test_filtered = test.query(filter_condition)
        except Exception as e:
            print(f"  [WARN] Filter '{filter_name}' failed on test: {e}")
            return None

        # Check minimum sample size
        if len(train_filtered) < self.MIN_TRAIN_TRADES or len(test_filtered) < self.MIN_TEST_TRADES:
            return None

        # Calculate train performance
        train_wins = (train_filtered['outcome'] == 'WIN').sum()
        train_total = len(train_filtered)
        train_wr = (train_wins / train_total) * 100
        train_avg_r = train_filtered['r_multiple'].mean()
        train_annual_r = self._calculate_annual_r(train_avg_r, train_total)

        # Calculate test performance
        test_wins = (test_filtered['outcome'] == 'WIN').sum()
        test_total = len(test_filtered)
        test_wr = (test_wins / test_total) * 100
        test_avg_r = test_filtered['r_multiple'].mean()
        test_annual_r = self._calculate_annual_r(test_avg_r, test_total)

        # Calculate improvements
        train_wr_improvement = train_wr - baseline.train_win_rate
        test_wr_improvement = test_wr - baseline.test_win_rate
        train_r_improvement = train_avg_r - baseline.train_avg_r
        test_r_improvement = test_avg_r - baseline.test_avg_r

        # Check for overfitting
        overfit_score = abs(train_wr_improvement - test_wr_improvement)
        is_validated = overfit_score <= (self.OVERFIT_THRESHOLD * 100)  # Convert to percentage

        # Determine confidence
        if train_total >= 50 and test_total >= 25 and is_validated:
            confidence = 'HIGH'
        elif train_total >= 30 and test_total >= 15 and is_validated:
            confidence = 'MEDIUM'
        else:
            confidence = 'LOW'

        if not is_validated:
            confidence = 'LOW'  # Overfit = low confidence

        return FilterResult(
            filter_name=filter_name,
            filter_condition=filter_condition,
            train_trades=train_total,
            train_win_rate=train_wr,
            train_avg_r=train_avg_r,
            train_annual_r=train_annual_r,
            test_trades=test_total,
            test_win_rate=test_wr,
            test_avg_r=test_avg_r,
            test_annual_r=test_annual_r,
            train_wr_improvement=train_wr_improvement,
            test_wr_improvement=test_wr_improvement,
            train_r_improvement=train_r_improvement,
            test_r_improvement=test_r_improvement,
            is_validated=is_validated,
            confidence=confidence,
            overfit_score=overfit_score
        )

    def generate_all_filters(self) -> List[Tuple[str, str]]:
        """
        Generate all filter combinations to test.

        Returns:
            List of (filter_name, filter_condition) tuples
        """
        filters = []

        # 1. ORB size filters
        for threshold in self.orb_size_thresholds:
            filters.append((
                f"ORB size >= {threshold}",
                f"orb_size >= {threshold}"
            ))

        # 2. Asia travel filters
        for threshold in self.asia_travel_thresholds:
            filters.append((
                f"Asia travel > {threshold}",
                f"asia_travel > {threshold}"
            ))

        # 3. London range filters
        for threshold in self.london_range_thresholds:
            filters.append((
                f"London range > {threshold}",
                f"london_range > {threshold}"
            ))

        # 4. Pre-NY travel filters
        for threshold in self.pre_ny_travel_thresholds:
            filters.append((
                f"Pre-NY travel > {threshold}",
                f"pre_ny_travel > {threshold}"
            ))

        # 5. RSI filters
        for low, high in self.rsi_thresholds:
            if low is None:
                filters.append((
                    f"RSI < {high}",
                    f"rsi < {high}"
                ))
            else:
                filters.append((
                    f"RSI > {low}",
                    f"rsi > {low}"
                ))

        # 6. ATR filters
        for multiplier in self.atr_multipliers:
            if multiplier < 1.0:
                filters.append((
                    f"ORB size < {multiplier}x ATR",
                    f"orb_size < (atr * {multiplier})"
                ))
            else:
                filters.append((
                    f"ORB size > {multiplier}x ATR",
                    f"orb_size > (atr * {multiplier})"
                ))

        # 7. Day of week filters (exclude each day)
        for day in self.days_of_week:
            filters.append((
                f"Exclude {day}",
                f"day_of_week != '{day}'"
            ))

        # 8. Asia type filters
        for asia_type in ['A1_TIGHT', 'A0_NORMAL', 'A2_EXPANDED']:
            filters.append((
                f"Asia type = {asia_type}",
                f"asia_type == '{asia_type}'"
            ))

        # 9. London type filters
        for london_type in ['L1_SWEEP_HIGH', 'L2_SWEEP_LOW', 'L3_EXPANSION', 'L4_CONSOLIDATION']:
            filters.append((
                f"London type = {london_type}",
                f"london_type == '{london_type}'"
            ))

        # 10. Combinations (ORB size + Asia travel)
        for orb_threshold in [0.10, 0.15]:
            for asia_threshold in [1.5, 2.0]:
                filters.append((
                    f"ORB >= {orb_threshold} AND Asia > {asia_threshold}",
                    f"orb_size >= {orb_threshold} and asia_travel > {asia_threshold}"
                ))

        # 11. Combinations (ORB size + London range)
        for orb_threshold in [0.10, 0.15]:
            for london_threshold in [1.0, 1.5]:
                filters.append((
                    f"ORB >= {orb_threshold} AND London > {london_threshold}",
                    f"orb_size >= {orb_threshold} and london_range > {london_threshold}"
                ))

        return filters

    def optimize_edge(
        self,
        orb_time: str,
        rr: float,
        sl_mode: str,
        instrument: str = 'MGC',
        top_n: int = 10
    ) -> Tuple[EdgeBaseline, List[FilterResult]]:
        """
        Optimize filters for a single edge.

        Args:
            orb_time: ORB time (0900, 1000, etc.)
            rr: Risk/reward ratio
            sl_mode: Stop loss mode (full, half)
            instrument: Instrument (MGC, NQ, MPL)
            top_n: Number of top filters to return

        Returns:
            (baseline, top_filters)
        """
        print(f"\n{'='*70}")
        print(f"OPTIMIZING FILTERS: {orb_time} ORB (RR={rr}, SL={sl_mode})")
        print(f"{'='*70}\n")

        # Get data and calculate baseline
        df = self.get_edge_data(orb_time, instrument)
        print(f"Total data points: {len(df)}")

        train, test = self.split_train_test(df)
        print(f"Train set: {len(train)} trades ({len(train)/len(df)*100:.0f}%)")
        print(f"Test set: {len(test)} trades ({len(test)/len(df)*100:.0f}%)\n")

        baseline = self.calculate_baseline(orb_time, rr, sl_mode, instrument)

        print("BASELINE PERFORMANCE:")
        print(f"  Train: {baseline.train_win_rate:.1f}% WR, {baseline.train_avg_r:+.2f}R avg, {baseline.train_trades} trades, {baseline.train_annual_r:+.0f}R/year")
        print(f"  Test:  {baseline.test_win_rate:.1f}% WR, {baseline.test_avg_r:+.2f}R avg, {baseline.test_trades} trades, {baseline.test_annual_r:+.0f}R/year\n")

        # Generate and test all filters
        all_filters = self.generate_all_filters()
        print(f"Testing {len(all_filters)} filter combinations...\n")

        results = []
        for filter_name, filter_condition in all_filters:
            result = self.test_filter(train, test, filter_condition, filter_name, baseline)
            if result:
                results.append(result)

        print(f"Valid filters: {len(results)} (with sufficient sample size)\n")

        # Sort by test set improvement (to avoid overfitting bias)
        # Primary: test WR improvement
        # Secondary: test avg R improvement
        results.sort(key=lambda x: (x.test_wr_improvement, x.test_r_improvement), reverse=True)

        return baseline, results[:top_n]

    def print_results(self, baseline: EdgeBaseline, results: List[FilterResult]):
        """Print optimization results in human-readable format"""
        print(f"\n{'='*70}")
        print("FILTER OPTIMIZATION RESULTS")
        print(f"{'='*70}\n")

        print(f"Edge: {baseline.orb_time} ORB (RR={baseline.rr}, SL={baseline.sl_mode})")
        print(f"Baseline: {baseline.train_win_rate:.1f}% WR, {baseline.train_avg_r:+.2f}R avg, {baseline.train_trades} train trades, {baseline.train_annual_r:+.0f}R/year\n")

        print("TOP FILTERS (Ranked by Test Set Improvement):\n")

        for i, result in enumerate(results, 1):
            print(f"{i}. {result.filter_name}")
            print(f"   Train: {result.train_win_rate:.1f}% WR, {result.train_avg_r:+.2f}R avg, {result.train_trades} trades, {result.train_annual_r:+.0f}R/year ({result.train_wr_improvement:+.1f}% WR, {result.train_r_improvement:+.2f}R)")
            print(f"   Test:  {result.test_win_rate:.1f}% WR, {result.test_avg_r:+.2f}R avg, {result.test_trades} trades, {result.test_annual_r:+.0f}R/year ({result.test_wr_improvement:+.1f}% WR, {result.test_r_improvement:+.2f}R)")

            if result.is_validated:
                print(f"   [OK] VALIDATED (test performance within {self.OVERFIT_THRESHOLD*100:.0f}% of train)")
            else:
                print(f"   [OVERFIT] (train {result.train_wr_improvement:+.1f}% WR, test {result.test_wr_improvement:+.1f}% WR, diff={result.overfit_score:.1f}%)")

            print(f"   Confidence: {result.confidence}")
            print()

    def export_results(
        self,
        baseline: EdgeBaseline,
        results: List[FilterResult],
        output_file: str
    ):
        """Export results to CSV"""
        rows = []
        for result in results:
            rows.append({
                'orb_time': baseline.orb_time,
                'rr': baseline.rr,
                'sl_mode': baseline.sl_mode,
                'filter_name': result.filter_name,
                'filter_condition': result.filter_condition,
                'train_trades': result.train_trades,
                'train_wr': result.train_win_rate,
                'train_avg_r': result.train_avg_r,
                'train_annual_r': result.train_annual_r,
                'test_trades': result.test_trades,
                'test_wr': result.test_win_rate,
                'test_avg_r': result.test_avg_r,
                'test_annual_r': result.test_annual_r,
                'train_wr_improvement': result.train_wr_improvement,
                'test_wr_improvement': result.test_wr_improvement,
                'train_r_improvement': result.train_r_improvement,
                'test_r_improvement': result.test_r_improvement,
                'is_validated': result.is_validated,
                'confidence': result.confidence,
                'overfit_score': result.overfit_score
            })

        df = pd.DataFrame(rows)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n[OK] Results exported to {output_file}")

    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    parser = argparse.ArgumentParser(description='Optimize filters for trading edges')
    parser.add_argument('--orb', type=str, help='ORB time (0900, 1000, 1100, 1800, 2300, 0030)')
    parser.add_argument('--rr', type=float, default=1.0, help='Risk/reward ratio')
    parser.add_argument('--sl-mode', type=str, default='full', choices=['full', 'half'], help='Stop loss mode')
    parser.add_argument('--instrument', type=str, default='MGC', help='Instrument (MGC, NQ, MPL)')
    parser.add_argument('--top-n', type=int, default=10, help='Number of top filters to show')
    parser.add_argument('--export', type=str, help='Export results to CSV file')
    parser.add_argument('--optimize-all', action='store_true', help='Optimize all ORBs (0900, 1000, 1100, 1800, 2300, 0030)')

    args = parser.parse_args()

    optimizer = FilterOptimizer()

    if args.optimize_all:
        # Optimize all 6 ORBs
        orb_times = ['0900', '1000', '1100', '1800', '2300', '0030']

        for orb_time in orb_times:
            try:
                baseline, results = optimizer.optimize_edge(
                    orb_time=orb_time,
                    rr=args.rr,
                    sl_mode=args.sl_mode,
                    instrument=args.instrument,
                    top_n=args.top_n
                )

                optimizer.print_results(baseline, results)

                if args.export:
                    export_file = f"{orb_time}_{args.export}"
                    optimizer.export_results(baseline, results, export_file)

            except Exception as e:
                print(f"\n[ERROR] Failed to optimize {orb_time}: {e}\n")
                continue

    elif args.orb:
        # Optimize single ORB
        baseline, results = optimizer.optimize_edge(
            orb_time=args.orb,
            rr=args.rr,
            sl_mode=args.sl_mode,
            instrument=args.instrument,
            top_n=args.top_n
        )

        optimizer.print_results(baseline, results)

        if args.export:
            optimizer.export_results(baseline, results, args.export)

    else:
        print("Error: Must specify --orb or --optimize-all")
        parser.print_help()
        return

    optimizer.close()

    print(f"\n{'='*70}")
    print("FILTER OPTIMIZATION COMPLETE")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
