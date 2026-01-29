"""
Priority Engine - Deterministic Parameter Space Exploration

Scores parameter combinations based on past results to prioritize testing.
Uses only deterministic metrics from search_knowledge table.

Priority Version: 1.0 (audit3)
"""

import duckdb
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Priority version (audit3)
PRIORITY_VERSION = "1.0"

# Axis weights for combined scoring
WEIGHT_ORB = 0.40  # 40% weight on ORB time performance
WEIGHT_RR = 0.30   # 30% weight on RR target performance
WEIGHT_FILTER = 0.30  # 30% weight on filter type performance


class PriorityEngine:
    """
    Deterministic priority scoring engine

    Calculates priority scores for parameter combinations based on
    past performance (GOOD/NEUTRAL/BAD counts from search_knowledge).

    Version: 1.0 (audit3)
    """

    def __init__(self, db_conn: duckdb.DuckDBPyConnection):
        """
        Initialize priority engine

        Args:
            db_conn: DuckDB connection to database with search_knowledge table
        """
        self.conn = db_conn
        self.priorities = {}
        self.version = PRIORITY_VERSION

        # Calculate priorities on initialization
        self._calculate_all_priorities()

    def _calculate_all_priorities(self):
        """
        Calculate priority scores for all axes

        Populates self.priorities with:
        - orb_times: {orb_time: score}
        - rr_targets: {rr_target: score}
        - filter_types: {filter_type: score}
        """
        self.priorities = {
            'orb_times': self._calculate_orb_priorities(),
            'rr_targets': self._calculate_rr_priorities(),
            'filter_types': self._calculate_filter_priorities()
        }

        logger.info(f"Priority engine initialized (version {self.version})")
        logger.info(f"  ORB priorities: {len(self.priorities['orb_times'])} values")
        logger.info(f"  RR priorities: {len(self.priorities['rr_targets'])} values")
        logger.info(f"  Filter priorities: {len(self.priorities['filter_types'])} values")

    def _calculate_orb_priorities(self) -> Dict[str, float]:
        """
        Calculate priority scores for each ORB time

        Score = (GOOD_count * 1.0 + NEUTRAL_count * 0.5) / total_count
        Untested ORBs get 0.5 (neutral priority)

        Returns:
            Dictionary {orb_time: priority_score}
        """
        priorities = {}

        try:
            # Get result counts per ORB time
            results = self.conn.execute("""
                SELECT
                    orb_time,
                    SUM(CASE WHEN result_class = 'GOOD' THEN 1 ELSE 0 END) as good_count,
                    SUM(CASE WHEN result_class = 'NEUTRAL' THEN 1 ELSE 0 END) as neutral_count,
                    COUNT(*) as total_count
                FROM search_knowledge
                GROUP BY orb_time
            """).fetchall()

            for orb_time, good, neutral, total in results:
                if total > 0:
                    priority = (good * 1.0 + neutral * 0.5) / total
                else:
                    priority = 0.5  # Neutral for untested

                priorities[orb_time] = priority

        except Exception as e:
            logger.warning(f"Error calculating ORB priorities: {e}")
            # Return empty dict if search_knowledge doesn't have data yet

        return priorities

    def _calculate_rr_priorities(self) -> Dict[float, float]:
        """
        Calculate priority scores for each RR target

        Score = (GOOD_count * 1.0 + NEUTRAL_count * 0.5) / total_count
        Untested RRs get 0.5 (neutral priority)

        Returns:
            Dictionary {rr_target: priority_score}
        """
        priorities = {}

        try:
            # Get result counts per RR target
            results = self.conn.execute("""
                SELECT
                    rr_target,
                    SUM(CASE WHEN result_class = 'GOOD' THEN 1 ELSE 0 END) as good_count,
                    SUM(CASE WHEN result_class = 'NEUTRAL' THEN 1 ELSE 0 END) as neutral_count,
                    COUNT(*) as total_count
                FROM search_knowledge
                GROUP BY rr_target
            """).fetchall()

            for rr_target, good, neutral, total in results:
                if total > 0:
                    priority = (good * 1.0 + neutral * 0.5) / total
                else:
                    priority = 0.5  # Neutral for untested

                priorities[float(rr_target)] = priority

        except Exception as e:
            logger.warning(f"Error calculating RR priorities: {e}")
            # Return empty dict if search_knowledge doesn't have data yet

        return priorities

    def _calculate_filter_priorities(self) -> Dict[str, float]:
        """
        Calculate priority scores for each filter type

        Extracts filter types from filters_json and scores each family
        (SIZE, TRAVEL, SESSION_TYPE, etc.)

        Score = (GOOD_count * 1.0 + NEUTRAL_count * 0.5) / total_count
        Untested filters get 0.5 (neutral priority)

        Returns:
            Dictionary {filter_type: priority_score}
        """
        priorities = {}

        try:
            # Get all filters_json from search_knowledge
            results = self.conn.execute("""
                SELECT filters_json, result_class
                FROM search_knowledge
            """).fetchall()

            # Count results per filter type
            filter_counts = {}  # {filter_type: {'good': N, 'neutral': N, 'total': N}}

            for filters_json, result_class in results:
                if filters_json:
                    # Extract filter types (keys in JSON)
                    import json
                    try:
                        filters = json.loads(filters_json) if isinstance(filters_json, str) else filters_json

                        for filter_type in filters.keys():
                            if filter_type not in filter_counts:
                                filter_counts[filter_type] = {'good': 0, 'neutral': 0, 'total': 0}

                            filter_counts[filter_type]['total'] += 1

                            if result_class == 'GOOD':
                                filter_counts[filter_type]['good'] += 1
                            elif result_class == 'NEUTRAL':
                                filter_counts[filter_type]['neutral'] += 1

                    except Exception:
                        pass  # Skip malformed JSON

            # Calculate priorities
            for filter_type, counts in filter_counts.items():
                if counts['total'] > 0:
                    priority = (counts['good'] * 1.0 + counts['neutral'] * 0.5) / counts['total']
                else:
                    priority = 0.5

                priorities[filter_type] = priority

        except Exception as e:
            logger.warning(f"Error calculating filter priorities: {e}")
            # Return empty dict if search_knowledge doesn't have data yet

        return priorities

    def score_combination(self, combo: Dict) -> float:
        """
        Score a parameter combination using priority weights

        Combined score = (ORB_priority * 0.4 + RR_priority * 0.3 + Filter_priority * 0.3)

        Args:
            combo: Dictionary with orb_time, rr_target, filters

        Returns:
            Priority score (0.0 to 1.0)
        """
        # Get ORB priority (default 0.5 for untested)
        orb_time = combo.get('orb_time', '')
        orb_priority = self.priorities['orb_times'].get(orb_time, 0.5)

        # Get RR priority (default 0.5 for untested)
        rr_target = float(combo.get('rr_target', 0.0))
        rr_priority = self.priorities['rr_targets'].get(rr_target, 0.5)

        # Get filter priority (average across all filter types)
        filters = combo.get('filters', {})
        if filters:
            filter_priorities = []
            for filter_type in filters.keys():
                filter_priorities.append(self.priorities['filter_types'].get(filter_type, 0.5))

            filter_priority = sum(filter_priorities) / len(filter_priorities) if filter_priorities else 0.5
        else:
            filter_priority = 0.5  # No filters = neutral

        # Combined score (weighted average)
        combined_score = (
            orb_priority * WEIGHT_ORB +
            rr_priority * WEIGHT_RR +
            filter_priority * WEIGHT_FILTER
        )

        return combined_score

    def get_axis_priorities(self) -> Dict:
        """
        Get calculated priority scores for all axes

        Returns:
            Dictionary with orb_times, rr_targets, filter_types priorities
        """
        return self.priorities

    def get_version(self) -> str:
        """Get priority engine version"""
        return self.version


if __name__ == "__main__":
    # Test priority engine
    print("=" * 70)
    print(f"PRIORITY ENGINE TEST (Version {PRIORITY_VERSION})")
    print("=" * 70)
    print()

    # Connect to database
    import sys
    from pathlib import Path

    repo_root = Path(__file__).parent.parent
    db_path = repo_root / "data" / "db" / "gold.db"

    if not db_path.exists():
        print(f"[ERROR] Database not found: {db_path}")
        sys.exit(1)

    conn = duckdb.connect(str(db_path), read_only=True)

    # Initialize engine
    engine = PriorityEngine(conn)

    # Get priorities
    priorities = engine.get_axis_priorities()

    print("ORB Time Priorities:")
    if priorities['orb_times']:
        for orb, score in sorted(priorities['orb_times'].items()):
            print(f"  {orb}: {score:.3f}")
    else:
        print("  (no data yet)")

    print()
    print("RR Target Priorities:")
    if priorities['rr_targets']:
        for rr, score in sorted(priorities['rr_targets'].items()):
            print(f"  {rr}: {score:.3f}")
    else:
        print("  (no data yet)")

    print()
    print("Filter Type Priorities:")
    if priorities['filter_types']:
        for ft, score in sorted(priorities['filter_types'].items()):
            print(f"  {ft}: {score:.3f}")
    else:
        print("  (no data yet)")

    print()

    # Test combination scoring
    test_combo = {
        'orb_time': '1000',
        'rr_target': 2.0,
        'filters': {}
    }

    score = engine.score_combination(test_combo)
    print(f"Test combination score: {score:.3f}")
    print(f"  ORB: 1000, RR: 2.0, Filters: none")

    print()
    print("[OK] Priority engine initialized successfully")

    conn.close()
