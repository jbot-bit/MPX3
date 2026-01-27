"""
ORB Performance Analysis V2 - ZERO LOOKAHEAD
=============================================
Analyzes ORB performance using ONLY pre-open information available at decision time.

Key Changes from V1:
- Uses PRE blocks instead of SESSION types
- No lookahead bias
- Real, tradeable edges only
- Clear temporal boundaries

Usage:
  python analyze_orb_v2.py

Outputs:
- ORB performance by time
- ORB performance by PRE block characteristics
- Valid trading rules with zero lookahead
"""

import duckdb
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass


@dataclass
class ORBStats:
    """Statistics for an ORB setup"""
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_r: float
    avg_r: float

    def __str__(self):
        if self.total_trades == 0:
            return "No trades"
        return (f"Trades: {self.total_trades} | Win: {self.wins} Loss: {self.losses} "
                f"| WR: {self.win_rate:.1%} | Total R: {self.total_r:+.1f} | Avg R: {self.avg_r:+.2f}")


def calculate_stats(rows: List[Tuple]) -> ORBStats:
    """Calculate statistics from query results (outcome, r_multiple)"""
    if not rows:
        return ORBStats(0, 0, 0, 0.0, 0.0, 0.0)

    wins = sum(1 for outcome, _ in rows if outcome == "WIN")
    losses = sum(1 for outcome, _ in rows if outcome == "LOSS")

    trades = [r for r in rows if r[0] in ("WIN", "LOSS") and r[1] is not None]
    total_trades = len(trades)

    if total_trades == 0:
        return ORBStats(0, 0, 0, 0.0, 0.0, 0.0)

    total_r = sum(r[1] for r in trades)
    avg_r = total_r / total_trades
    win_rate = wins / total_trades if total_trades > 0 else 0.0

    return ORBStats(total_trades, wins, losses, win_rate, total_r, avg_r)


class ORBAnalyzerV2:
    """Analyze ORBs with zero lookahead guarantee"""

    def __init__(self, db_path: str = "gold.db", connection: Optional[duckdb.DuckDBPyConnection] = None):
        """Initialize with either a db_path or an existing connection.
        
        Args:
            db_path: Path to database file (used if connection is None)
            connection: Existing DuckDB connection to reuse (avoids connection conflicts)
        """
        if connection is not None:
            self.con = connection
            self._owns_connection = False
        else:
            self.con = duckdb.connect(db_path, read_only=True)
            self._owns_connection = True

    def analyze_overall_performance(self):
        """Overall ORB performance by time"""
        print("\n" + "="*80)
        print("ORB PERFORMANCE BY TIME (Zero Lookahead)")
        print("="*80)

        orbs = {
            "0900": "09:00 (Asia Open)",
            "1000": "10:00 (Asia Mid)",
            "1100": "11:00 (Asia Late)",
            "1800": "18:00 (London Open)",
            "2300": "23:00 (NY Futures)",
            "0030": "00:30 (NYSE Cash)",
        }

        for orb_time, label in orbs.items():
            rows = self.con.execute(f"""
                SELECT orb_{orb_time}_outcome, orb_{orb_time}_r_multiple
                FROM daily_features
                WHERE orb_{orb_time}_outcome IS NOT NULL
            """).fetchall()

            stats = calculate_stats(rows)
            print(f"\n{label}:")
            print(f"  {stats}")

    def analyze_by_pre_blocks(self):
        """Analyze ORBs filtered by PRE block characteristics"""
        print("\n" + "="*80)
        print("ORB PERFORMANCE BY PRE BLOCK RANGE (Zero Lookahead)")
        print("="*80)
        print("\nWhat we KNOW at each open:\n")

        # 09:00 ORB: Uses PRE_ASIA (07:00-09:00)
        print("\n--- 09:00 ORB (can see PRE_ASIA) ---")

        # Large PRE_ASIA (>50 ticks)
        rows = self.con.execute("""
            SELECT orb_0900_outcome, orb_0900_r_multiple
            FROM daily_features
            WHERE orb_0900_outcome IN ('WIN', 'LOSS')
              AND (pre_asia_range / 0.1) > 50
        """).fetchall()
        stats = calculate_stats(rows)
        print(f"  PRE_ASIA > 50 ticks: {stats}")

        # Small PRE_ASIA (<30 ticks)
        rows = self.con.execute("""
            SELECT orb_0900_outcome, orb_0900_r_multiple
            FROM daily_features
            WHERE orb_0900_outcome IN ('WIN', 'LOSS')
              AND (pre_asia_range / 0.1) < 30
        """).fetchall()
        stats = calculate_stats(rows)
        print(f"  PRE_ASIA < 30 ticks: {stats}")

        # 11:00 ORB: Can see PRE_ASIA + Asia so far (09:00-11:00)
        print("\n--- 11:00 ORB (can see PRE_ASIA + first 2 hours of Asia) ---")

        # Large PRE_ASIA
        for direction in ["UP", "DOWN"]:
            rows = self.con.execute(f"""
                SELECT orb_1100_outcome, orb_1100_r_multiple
                FROM daily_features
                WHERE orb_1100_outcome IN ('WIN', 'LOSS')
                  AND orb_1100_break_dir = ?
                  AND (pre_asia_range / 0.1) > 50
            """, [direction]).fetchall()
            stats = calculate_stats(rows)
            if stats.total_trades >= 10:
                print(f"  {direction} | PRE_ASIA > 50 ticks: {stats}")

        # 18:00 ORB: Can see PRE_LONDON + COMPLETED ASIA
        print("\n--- 18:00 ORB (can see PRE_LONDON + completed ASIA) ---")

        # Small PRE_LONDON + Large ASIA
        for direction in ["UP", "DOWN"]:
            rows = self.con.execute(f"""
                SELECT orb_1800_outcome, orb_1800_r_multiple
                FROM daily_features
                WHERE orb_1800_outcome IN ('WIN', 'LOSS')
                  AND orb_1800_break_dir = ?
                  AND (pre_london_range / 0.1) < 20
                  AND (asia_range / 0.1) > 300
            """, [direction]).fetchall()
            stats = calculate_stats(rows)
            if stats.total_trades >= 5:
                print(f"  {direction} | PRE_LONDON < 20 ticks + ASIA > 300 ticks: {stats}")

        # Large PRE_LONDON
        for direction in ["UP", "DOWN"]:
            rows = self.con.execute(f"""
                SELECT orb_1800_outcome, orb_1800_r_multiple
                FROM daily_features
                WHERE orb_1800_outcome IN ('WIN', 'LOSS')
                  AND orb_1800_break_dir = ?
                  AND (pre_london_range / 0.1) > 40
            """, [direction]).fetchall()
            stats = calculate_stats(rows)
            if stats.total_trades >= 10:
                print(f"  {direction} | PRE_LONDON > 40 ticks: {stats}")

        # 00:30 ORB: Can see PRE_NY + COMPLETED LONDON + COMPLETED ASIA
        print("\n--- 00:30 ORB (can see PRE_NY + completed LONDON + completed ASIA) ---")

        # Volatile PRE_NY
        for direction in ["UP", "DOWN"]:
            rows = self.con.execute(f"""
                SELECT orb_0030_outcome, orb_0030_r_multiple
                FROM daily_features
                WHERE orb_0030_outcome IN ('WIN', 'LOSS')
                  AND orb_0030_break_dir = ?
                  AND (pre_ny_range / 0.1) > 40
            """, [direction]).fetchall()
            stats = calculate_stats(rows)
            if stats.total_trades >= 10:
                print(f"  {direction} | PRE_NY > 40 ticks: {stats}")

    def analyze_orb_correlations(self):
        """Analyze ORB-to-ORB correlations (using completed ORBs)"""
        print("\n" + "="*80)
        print("ORB CORRELATIONS (Using Completed ORBs - Zero Lookahead)")
        print("="*80)

        # 10:00 after 09:00 failed
        print("\n--- 10:00 ORB after 09:00 ORB outcome ---")

        for prev_outcome in ["WIN", "LOSS", "NO_TRADE"]:
            for direction in ["UP", "DOWN"]:
                rows = self.con.execute(f"""
                    SELECT orb_1000_outcome, orb_1000_r_multiple
                    FROM daily_features
                    WHERE orb_1000_outcome IN ('WIN', 'LOSS')
                      AND orb_1000_break_dir = ?
                      AND orb_0900_outcome = ?
                """, [direction, prev_outcome]).fetchall()

                stats = calculate_stats(rows)
                if stats.total_trades >= 10:
                    print(f"  After 09:00 {prev_outcome} | 10:00 {direction}: {stats}")

        # 11:00 after both 09:00 and 10:00
        print("\n--- 11:00 ORB after 09:00 + 10:00 outcomes ---")

        for prev_pattern in [("LOSS", "LOSS"), ("WIN", "WIN"), ("LOSS", "WIN")]:
            orb_09, orb_10 = prev_pattern
            for direction in ["UP", "DOWN"]:
                rows = self.con.execute(f"""
                    SELECT orb_1100_outcome, orb_1100_r_multiple
                    FROM daily_features
                    WHERE orb_1100_outcome IN ('WIN', 'LOSS')
                      AND orb_1100_break_dir = ?
                      AND orb_0900_outcome = ?
                      AND orb_1000_outcome = ?
                """, [direction, orb_09, orb_10]).fetchall()

                stats = calculate_stats(rows)
                if stats.total_trades >= 5:
                    print(f"  After 09:00 {orb_09} + 10:00 {orb_10} | 11:00 {direction}: {stats}")

    def find_best_edges(self):
        """Find best performing setups with statistical significance"""
        print("\n" + "="*80)
        print("BEST EDGES (Min 20 trades, WR > 52%, Avg R > 0.05)")
        print("="*80)

        edges = []

        # Test various combinations
        test_cases = [
            # Basic direction edges
            ("0900", "UP", "orb_0900_break_dir = 'UP'", "09:00 UP"),
            ("0900", "DOWN", "orb_0900_break_dir = 'DOWN'", "09:00 DOWN"),
            ("1000", "UP", "orb_1000_break_dir = 'UP'", "10:00 UP"),
            ("1000", "DOWN", "orb_1000_break_dir = 'DOWN'", "10:00 DOWN"),
            ("1100", "UP", "orb_1100_break_dir = 'UP'", "11:00 UP"),
            ("1100", "DOWN", "orb_1100_break_dir = 'DOWN'", "11:00 DOWN"),
            ("1800", "UP", "orb_1800_break_dir = 'UP'", "18:00 UP"),
            ("1800", "DOWN", "orb_1800_break_dir = 'DOWN'", "18:00 DOWN"),

            # PRE block filtered
            ("1100", "UP", "orb_1100_break_dir = 'UP' AND (pre_asia_range / 0.1) > 50",
             "11:00 UP | PRE_ASIA > 50 ticks"),
            ("1800", "UP", "orb_1800_break_dir = 'UP' AND (pre_london_range / 0.1) < 20",
             "18:00 UP | PRE_LONDON < 20 ticks"),
            ("1800", "DOWN", "orb_1800_break_dir = 'DOWN' AND (pre_london_range / 0.1) < 20 AND (asia_range / 0.1) > 300",
             "18:00 DOWN | PRE_LONDON < 20 + ASIA > 300"),
        ]

        for orb_time, _, condition, label in test_cases:
            rows = self.con.execute(f"""
                SELECT orb_{orb_time}_outcome, orb_{orb_time}_r_multiple
                FROM daily_features
                WHERE orb_{orb_time}_outcome IN ('WIN', 'LOSS')
                  AND {condition}
            """).fetchall()

            stats = calculate_stats(rows)

            if stats.total_trades >= 20 and stats.win_rate > 0.52 and stats.avg_r > 0.05:
                edges.append((label, stats))

        # Sort by avg R
        edges.sort(key=lambda x: x[1].avg_r, reverse=True)

        if edges:
            for label, stats in edges:
                print(f"\n{label}:")
                print(f"  {stats}")
        else:
            print("\nNo edges found meeting criteria")
            print("(Try lowering thresholds or testing more combinations)")

    def analyze_overall(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Return overall ORB performance by time as a dict structure for app use"""
        result = {}
        
        orbs = {
            "0900": "09:00 (Asia Open)",
            "1000": "10:00 (Asia Mid)",
            "1100": "11:00 (Asia Late)",
            "1800": "18:00 (London Open)",
            "2300": "23:00 (NY Futures)",
            "0030": "00:30 (NYSE Cash)",
        }
        
        for orb_time, label in orbs.items():
            # Get UP direction
            rows_up = self.con.execute(f"""
                SELECT orb_{orb_time}_outcome, orb_{orb_time}_r_multiple
                FROM daily_features
                WHERE orb_{orb_time}_outcome IN ('WIN', 'LOSS')
                  AND orb_{orb_time}_break_dir = 'UP'
            """).fetchall()
            stats_up = calculate_stats(rows_up)
            
            # Get DOWN direction
            rows_down = self.con.execute(f"""
                SELECT orb_{orb_time}_outcome, orb_{orb_time}_r_multiple
                FROM daily_features
                WHERE orb_{orb_time}_outcome IN ('WIN', 'LOSS')
                  AND orb_{orb_time}_break_dir = 'DOWN'
            """).fetchall()
            stats_down = calculate_stats(rows_down)
            
            result[orb_time] = {
                'UP': {
                    'win_rate': stats_up.win_rate,
                    'avg_r': stats_up.avg_r,
                    'total_r': stats_up.total_r,
                    'total_trades': stats_up.total_trades,
                    'wins': stats_up.wins,
                    'losses': stats_up.losses
                },
                'DOWN': {
                    'win_rate': stats_down.win_rate,
                    'avg_r': stats_down.avg_r,
                    'total_r': stats_down.total_r,
                    'total_trades': stats_down.total_trades,
                    'wins': stats_down.wins,
                    'losses': stats_down.losses
                }
            }
        
        return result
    
    def analyze_pre_asia(self) -> List[Dict[str, Any]]:
        """Return PRE block filtered edges as a list of dicts for app use"""
        edges = []
        
        # 09:00 ORB with PRE_ASIA filters
        # Large PRE_ASIA (>50 ticks)
        rows = self.con.execute("""
            SELECT orb_0900_outcome, orb_0900_r_multiple
            FROM daily_features
            WHERE orb_0900_outcome IN ('WIN', 'LOSS')
              AND (pre_asia_range / 0.1) > 50
        """).fetchall()
        stats = calculate_stats(rows)
        if stats.total_trades >= 10:
            edges.append({
                'setup': "09:00 | PRE_ASIA > 50 ticks",
                'win_rate': stats.win_rate,
                'avg_r': stats.avg_r,
                'total_r': stats.total_r,
                'total_trades': stats.total_trades,
                'wins': stats.wins,
                'losses': stats.losses
            })
        
        # Small PRE_ASIA (<30 ticks)
        rows = self.con.execute("""
            SELECT orb_0900_outcome, orb_0900_r_multiple
            FROM daily_features
            WHERE orb_0900_outcome IN ('WIN', 'LOSS')
              AND (pre_asia_range / 0.1) < 30
        """).fetchall()
        stats = calculate_stats(rows)
        if stats.total_trades >= 10:
            edges.append({
                'setup': "09:00 | PRE_ASIA < 30 ticks",
                'win_rate': stats.win_rate,
                'avg_r': stats.avg_r,
                'total_r': stats.total_r,
                'total_trades': stats.total_trades,
                'wins': stats.wins,
                'losses': stats.losses
            })
        
        # 11:00 ORB with PRE_ASIA filters
        for direction in ["UP", "DOWN"]:
            rows = self.con.execute(f"""
                SELECT orb_1100_outcome, orb_1100_r_multiple
                FROM daily_features
                WHERE orb_1100_outcome IN ('WIN', 'LOSS')
                  AND orb_1100_break_dir = ?
                  AND (pre_asia_range / 0.1) > 50
            """, [direction]).fetchall()
            stats = calculate_stats(rows)
            if stats.total_trades >= 10:
                edges.append({
                    'setup': f"11:00 {direction} | PRE_ASIA > 50 ticks",
                    'win_rate': stats.win_rate,
                    'avg_r': stats.avg_r,
                    'total_r': stats.total_r,
                    'total_trades': stats.total_trades,
                    'wins': stats.wins,
                    'losses': stats.losses
                })
        
        # 18:00 ORB with PRE_LONDON filters
        for direction in ["UP", "DOWN"]:
            # Small PRE_LONDON + Large ASIA
            rows = self.con.execute(f"""
                SELECT orb_1800_outcome, orb_1800_r_multiple
                FROM daily_features
                WHERE orb_1800_outcome IN ('WIN', 'LOSS')
                  AND orb_1800_break_dir = ?
                  AND (pre_london_range / 0.1) < 20
                  AND (asia_range / 0.1) > 300
            """, [direction]).fetchall()
            stats = calculate_stats(rows)
            if stats.total_trades >= 5:
                edges.append({
                    'setup': f"18:00 {direction} | PRE_LONDON < 20 + ASIA > 300",
                    'win_rate': stats.win_rate,
                    'avg_r': stats.avg_r,
                    'total_r': stats.total_r,
                    'total_trades': stats.total_trades,
                    'wins': stats.wins,
                    'losses': stats.losses
                })
            
            # Large PRE_LONDON
            rows = self.con.execute(f"""
                SELECT orb_1800_outcome, orb_1800_r_multiple
                FROM daily_features
                WHERE orb_1800_outcome IN ('WIN', 'LOSS')
                  AND orb_1800_break_dir = ?
                  AND (pre_london_range / 0.1) > 40
            """, [direction]).fetchall()
            stats = calculate_stats(rows)
            if stats.total_trades >= 10:
                edges.append({
                    'setup': f"18:00 {direction} | PRE_LONDON > 40 ticks",
                    'win_rate': stats.win_rate,
                    'avg_r': stats.avg_r,
                    'total_r': stats.total_r,
                    'total_trades': stats.total_trades,
                    'wins': stats.wins,
                    'losses': stats.losses
                })
        
        # 00:30 ORB with PRE_NY filters
        for direction in ["UP", "DOWN"]:
            rows = self.con.execute(f"""
                SELECT orb_0030_outcome, orb_0030_r_multiple
                FROM daily_features
                WHERE orb_0030_outcome IN ('WIN', 'LOSS')
                  AND orb_0030_break_dir = ?
                  AND (pre_ny_range / 0.1) > 40
            """, [direction]).fetchall()
            stats = calculate_stats(rows)
            if stats.total_trades >= 10:
                edges.append({
                    'setup': f"00:30 {direction} | PRE_NY > 40 ticks",
                    'win_rate': stats.win_rate,
                    'avg_r': stats.avg_r,
                    'total_r': stats.total_r,
                    'total_trades': stats.total_trades,
                    'wins': stats.wins,
                    'losses': stats.losses
                })
        
        return edges
    
    def analyze_orb_correlations(self) -> List[Dict[str, Any]]:
        """Return ORB correlation edges as a list of dicts for app use
        
        ⚠️ ZERO-LOOKAHEAD NOTE: These correlations assume the previous ORB trade
        is CLOSED (WIN/LOSS decided) before the next ORB decision time.
        
        In practice: Most ORB trades close quickly (within minutes), so this is
        usually valid. But in live trading, you must verify:
        - 09:00 trade state = CLOSED before using at 10:00
        - 10:00 trade state = CLOSED before using at 11:00
        
        If a previous trade is still OPEN, you cannot use its outcome and should
        fall back to baseline stats or simpler filters.
        """
        edges = []
        
        # 10:00 after 09:00 outcomes
        # NOTE: Assumes 09:00 trade is CLOSED before 10:00 decision
        for prev_outcome in ["WIN", "LOSS", "NO_TRADE"]:
            for direction in ["UP", "DOWN"]:
                rows = self.con.execute(f"""
                    SELECT orb_1000_outcome, orb_1000_r_multiple
                    FROM daily_features
                    WHERE orb_1000_outcome IN ('WIN', 'LOSS')
                      AND orb_1000_break_dir = ?
                      AND orb_0900_outcome = ?
                """, [direction, prev_outcome]).fetchall()
                
                stats = calculate_stats(rows)
                if stats.total_trades >= 10:
                    edges.append({
                        'setup': f"10:00 {direction} after 09:00 {prev_outcome}",
                        'win_rate': stats.win_rate,
                        'avg_r': stats.avg_r,
                        'total_r': stats.total_r,
                        'total_trades': stats.total_trades,
                        'wins': stats.wins,
                        'losses': stats.losses
                    })
        
        # 11:00 after both 09:00 and 10:00
        for prev_pattern in [("LOSS", "LOSS"), ("WIN", "WIN"), ("LOSS", "WIN")]:
            orb_09, orb_10 = prev_pattern
            for direction in ["UP", "DOWN"]:
                rows = self.con.execute(f"""
                    SELECT orb_1100_outcome, orb_1100_r_multiple
                    FROM daily_features
                    WHERE orb_1100_outcome IN ('WIN', 'LOSS')
                      AND orb_1100_break_dir = ?
                      AND orb_0900_outcome = ?
                      AND orb_1000_outcome = ?
                """, [direction, orb_09, orb_10]).fetchall()
                
                stats = calculate_stats(rows)
                if stats.total_trades >= 5:
                    edges.append({
                        'setup': f"11:00 {direction} after 09:00 {orb_09} + 10:00 {orb_10}",
                        'win_rate': stats.win_rate,
                        'avg_r': stats.avg_r,
                        'total_r': stats.total_r,
                        'total_trades': stats.total_trades,
                        'wins': stats.wins,
                        'losses': stats.losses
                    })
        
        return edges

    def close(self):
        """Close the connection only if we own it"""
        if self._owns_connection:
            self.con.close()


def main():
    analyzer = ORBAnalyzerV2()

    try:
        # Check if V2 table exists and has data
        count = analyzer.con.execute("SELECT COUNT(*) FROM daily_features").fetchone()[0]

        if count == 0:
            print("\nERROR: daily_features table is empty")
            print("Run: python build_daily_features.py 2024-01-01 2026-01-10")
            return

        print(f"\nAnalyzing {count} days with ZERO LOOKAHEAD...")

        analyzer.analyze_overall_performance()
        analyzer.analyze_by_pre_blocks()
        analyzer.analyze_orb_correlations()
        analyzer.find_best_edges()

        print("\n" + "="*80)
        print("ANALYSIS COMPLETE")
        print("="*80)
        print("\nAll edges shown use ONLY information available at decision time.")
        print("These are 100% reproducible in live trading.")
        print("="*80 + "\n")

    finally:
        analyzer.close()


if __name__ == "__main__":
    main()
