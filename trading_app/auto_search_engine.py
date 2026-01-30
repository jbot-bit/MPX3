"""
Auto Search Engine - Deterministic Edge Discovery

Generates edge candidates without bias using systematic parameter search.
Stores search memory to prevent repeats. Fast scoring using daily_features.

Hard constraints:
- Deterministic (no LLM)
- 300 second timeout
- No Streamlit freezing (periodic yield)
- Uses daily_features (NOT daily_features_v2)

Usage:
    from auto_search_engine import AutoSearchEngine

    engine = AutoSearchEngine(db_connection)
    results = engine.run_search(
        instrument='MGC',
        settings={'family': 'ORB_L4', 'rr_range': [1.5, 2.0, 2.5]},
        max_seconds=300
    )
"""

import duckdb
import hashlib
import json
import time
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from dataclasses import dataclass
import logging
import math

# Import audit3 modules
from trading_app.result_classifier import classify_result, RULESET_VERSION
from trading_app.priority_engine import PriorityEngine, PRIORITY_VERSION
from trading_app.provenance import create_provenance_dict

logger = logging.getLogger(__name__)


@dataclass
class SearchSettings:
    """Search configuration"""
    instrument: str = 'MGC'
    setup_family: str = 'ORB_BASELINE'  # ORB_BASELINE, ORB_L4, ORB_RSI, etc.
    orb_times: List[str] = None  # ['0900', '1000', '1100']
    rr_targets: List[float] = None  # [1.5, 2.0, 2.5, 3.0]
    filter_types: List[str] = None  # ['SIZE', 'TRAVEL', 'SESSION_TYPE']
    filter_ranges: Dict[str, List[float]] = None  # {'orb_size': [0.05, 0.10, 0.15]}
    min_sample_size: int = 30
    min_expected_r: float = 0.15
    date_start: Optional[date] = None
    date_end: Optional[date] = None

    def __post_init__(self):
        # Defaults
        if self.orb_times is None:
            self.orb_times = ['0900', '1000', '1100']
        if self.rr_targets is None:
            self.rr_targets = [1.5, 2.0]
        if self.filter_types is None:
            self.filter_types = []
        if self.filter_ranges is None:
            self.filter_ranges = {}


@dataclass
class SearchCandidate:
    """Promising candidate found by search"""
    instrument: str
    setup_family: str
    orb_time: str
    rr_target: float
    filters: Dict[str, Any]
    param_hash: str
    score_proxy: float
    sample_size: int
    win_rate_proxy: Optional[float] = None  # DEPRECATED: Use profitable_trade_rate or target_hit_rate
    expected_r_proxy: Optional[float] = None
    notes: Optional[str] = None
    # New clarified metrics (replaces ambiguous win_rate_proxy)
    profitable_trade_rate: Optional[float] = None  # Trades with realized_rr > 0
    target_hit_rate: Optional[float] = None  # Trades that hit profit target (outcome='WIN')


def compute_param_hash(params: Dict) -> str:
    """
    Compute stable hash of parameters for deduplication

    Hash key = instrument + setup_family + orb_time + rr_target + filters_json

    Args:
        params: Dict with instrument, setup_family, orb_time, rr_target, filters

    Returns:
        SHA256 hash (first 16 chars)
    """
    # Sort keys for deterministic JSON
    sorted_params = {
        'instrument': params.get('instrument', ''),
        'setup_family': params.get('setup_family', ''),
        'orb_time': params.get('orb_time', ''),
        'rr_target': params.get('rr_target', 0.0),
        'filters': params.get('filters', {})
    }

    # Create stable JSON string
    json_str = json.dumps(sorted_params, sort_keys=True, separators=(',', ':'))

    # Compute hash
    hash_obj = hashlib.sha256(json_str.encode('utf-8'))
    return hash_obj.hexdigest()[:16]


def _sort_dict_recursive(d: Dict) -> List:
    """
    Recursively sort dictionary for canonical serialization

    Returns list of tuples for stable ordering
    """
    if not isinstance(d, dict):
        return d

    sorted_items = []
    for key in sorted(d.keys()):
        value = d[key]
        if isinstance(value, dict):
            sorted_items.append((key, _sort_dict_recursive(value)))
        elif isinstance(value, list):
            sorted_items.append((key, [_sort_dict_recursive(item) if isinstance(item, dict) else item for item in value]))
        else:
            sorted_items.append((key, value))

    return sorted_items


def compute_param_hash_v2(params: Dict) -> str:
    """
    Canonical param serialization for deterministic hashing

    Version: 2.0 (audit3 - explicit field order, no dict assumptions)
    Algorithm: SHA256
    Encoding: UTF-8

    Field order (fixed):
    1. instrument (str)
    2. setup_family (str)
    3. orb_time (str)
    4. rr_target (float, 2 decimals)
    5. filters (sorted dict, recursive)

    FUTURE EXTENSIBILITY: When adding new dimensions (direction, entry_rule,
    stop_mode, etc.), append to canonical list and increment PARAM_HASH_VERSION
    to "3.0". This ensures old hashes remain valid for comparison.

    Args:
        params: Dict with instrument, setup_family, orb_time, rr_target, filters
                Optional future: direction, entry_rule, stop_mode

    Returns:
        SHA256 hash (first 16 chars)
    """
    # Explicit field order (no Python dict order assumptions)
    # Fields MUST be in fixed order for deterministic hashing
    canonical = [
        ('instrument', params.get('instrument', '')),
        ('setup_family', params.get('setup_family', '')),
        ('orb_time', params.get('orb_time', '')),
        ('rr_target', round(float(params.get('rr_target', 0.0)), 2)),
        ('filters', _sort_dict_recursive(params.get('filters', {})))
    ]

    # Create stable JSON string (no whitespace variability)
    json_str = json.dumps(canonical, ensure_ascii=True, separators=(',', ':'))

    # Compute hash
    hash_obj = hashlib.sha256(json_str.encode('utf-8'))
    return hash_obj.hexdigest()[:16]


# Version constants (audit3)
PARAM_HASH_VERSION = "2.0"
RULESET_VERSION = "1.0"
PRIORITY_VERSION = "1.0"
EPSILON = 0.15  # Exploration budget (15% of each chunk)


class AutoSearchEngine:
    """Deterministic edge discovery engine"""

    def __init__(self, db_connection: duckdb.DuckDBPyConnection):
        self.conn = db_connection
        self.start_time = None
        self.max_seconds = 300
        self.stats = {
            'tested': 0,
            'skipped': 0,
            'promising': 0,
            'time_elapsed': 0.0
        }

    def run_search(
        self,
        instrument: str = 'MGC',
        settings: Optional[Dict] = None,
        max_seconds: int = 300
    ) -> Dict:
        """
        Run automated edge discovery search

        Args:
            instrument: Trading instrument
            settings: Search settings dict (or use defaults)
            max_seconds: Timeout (hard stop)

        Returns:
            Dict with run_id, stats, candidates
        """
        self.start_time = time.time()
        self.max_seconds = max_seconds

        # Parse settings
        if settings is None:
            settings = {}

        search_settings = SearchSettings(
            instrument=instrument,
            setup_family=settings.get('family', 'ORB_BASELINE'),
            orb_times=settings.get('orb_times'),
            rr_targets=settings.get('rr_targets'),
            filter_types=settings.get('filter_types'),
            filter_ranges=settings.get('filter_ranges'),
            min_sample_size=settings.get('min_sample_size', 30),
            min_expected_r=settings.get('min_expected_r', 0.15),
            date_start=settings.get('date_start'),
            date_end=settings.get('date_end')
        )

        # Create run record
        run_id = str(uuid.uuid4())
        self._create_run_record(run_id, instrument, settings)

        # Generate candidates
        candidates = []
        try:
            candidates = self._generate_candidates(run_id, search_settings)

            # Update run record (COMPLETED)
            self._update_run_record(
                run_id,
                status='COMPLETED',
                duration=time.time() - self.start_time,
                candidates_found=self.stats['promising'],
                candidates_skipped=self.stats['skipped'],
                total_tested=self.stats['tested']
            )

        except TimeoutError as e:
            logger.warning(f"Search timeout: {e}")
            self._update_run_record(
                run_id,
                status='TIMEOUT',
                duration=time.time() - self.start_time,
                candidates_found=self.stats['promising'],
                candidates_skipped=self.stats['skipped'],
                total_tested=self.stats['tested'],
                error_message=str(e)
            )

        except Exception as e:
            logger.error(f"Search failed: {e}")
            self._update_run_record(
                run_id,
                status='FAILED',
                duration=time.time() - self.start_time,
                error_message=str(e)
            )
            raise

        return {
            'run_id': run_id,
            'status': 'COMPLETED',
            'stats': self.stats,
            'candidates': candidates
        }

    def _create_run_record(self, run_id: str, instrument: str, settings: Dict):
        """Create search_runs record"""
        self.conn.execute("""
            INSERT INTO search_runs (
                run_id, created_at, instrument, settings_json, status
            ) VALUES (?, CURRENT_TIMESTAMP, ?, ?, 'RUNNING')
        """, [run_id, instrument, json.dumps(settings)])

    def _update_run_record(
        self,
        run_id: str,
        status: str,
        duration: float,
        candidates_found: int = 0,
        candidates_skipped: int = 0,
        total_tested: int = 0,
        error_message: Optional[str] = None
    ):
        """Update search_runs record"""
        self.conn.execute("""
            UPDATE search_runs
            SET status = ?,
                duration_seconds = ?,
                candidates_found = ?,
                candidates_skipped = ?,
                total_tested = ?,
                error_message = ?
            WHERE run_id = ?
        """, [status, duration, candidates_found, candidates_skipped, total_tested, error_message, run_id])

    def _generate_candidates(
        self,
        run_id: str,
        settings: SearchSettings
    ) -> List[SearchCandidate]:
        """
        Generate candidate combinations and evaluate

        Strategy:
        1. Generate all parameter combinations (ORB × RR × filters)
        2. Check search_memory (skip if already tested)
        3. Score using daily_features (fast proxy)
        4. If promising: save to search_candidates and search_memory
        """
        candidates = []

        # Generate combinations
        combinations = self._generate_combinations(settings)
        logger.info(f"Generated {len(combinations)} combinations to test")

        for combo in combinations:
            # Check timeout
            if time.time() - self.start_time > self.max_seconds:
                raise TimeoutError(f"Search exceeded {self.max_seconds} seconds")

            # Check if already tested (search_memory)
            param_hash = compute_param_hash(combo)

            if self._is_in_memory(param_hash):
                self.stats['skipped'] += 1
                continue

            # Score candidate (fast proxy using daily_features)
            score = self._score_candidate(combo, settings)

            self.stats['tested'] += 1

            # If promising: save and add to memory
            if score and score['score_proxy'] >= settings.min_expected_r:
                candidate = SearchCandidate(
                    instrument=settings.instrument,
                    setup_family=settings.setup_family,
                    orb_time=combo['orb_time'],
                    rr_target=combo['rr_target'],
                    filters=combo.get('filters', {}),
                    param_hash=param_hash,
                    score_proxy=score['score_proxy'],
                    sample_size=score['sample_size'],
                    win_rate_proxy=None,  # DEPRECATED - use specific rates below
                    expected_r_proxy=score.get('expected_r'),
                    notes=f"Auto-discovered: {score['sample_size']}N, {score.get('score_proxy', 0):.3f}R proxy",
                    profitable_trade_rate=score.get('profitable_trade_rate'),  # Profitable trades (RR > 0)
                    target_hit_rate=score.get('target_hit_rate')  # Trades that hit target
                )

                # Save to search_candidates
                self._save_candidate(run_id, candidate)

                # Add to search_memory
                self._add_to_memory(candidate)

                candidates.append(candidate)
                self.stats['promising'] += 1

        return candidates

    def _generate_combinations(self, settings: SearchSettings) -> List[Dict]:
        """Generate all parameter combinations to test"""
        combinations = []

        # Simple baseline: ORB × RR (no filters)
        # PROXY MODE: No RR-specific data, use stored model from daily_features
        for orb_time in settings.orb_times:
            for rr_target in settings.rr_targets:
                # Accept None (proxy mode) or skip non-None values
                if rr_target is not None and rr_target != 1.0:
                    logger.warning(f"Skipping RR={rr_target} for {orb_time} (proxy mode only, no RR-specific data)")
                    continue

                # Generate baseline (no filters)
                combinations.append({
                    'instrument': settings.instrument,
                    'setup_family': settings.setup_family,
                    'orb_time': orb_time,
                    'rr_target': rr_target,  # None = proxy mode
                    'filters': {}
                })

                # Generate filter combinations
                if settings.filter_types and settings.filter_ranges:
                    # Generate all filter combinations for this ORB + RR pair
                    for filter_type in settings.filter_types:
                        if filter_type not in settings.filter_ranges:
                            continue

                        filter_values = settings.filter_ranges[filter_type]

                        for filter_value in filter_values:
                            # Map filter_type to actual filter key
                            # SIZE -> orb_size, TRAVEL -> pre_orb_travel, SESSION_TYPE -> session_type
                            if filter_type == 'SIZE':
                                filter_key = 'orb_size'
                            elif filter_type == 'TRAVEL':
                                filter_key = 'pre_orb_travel'
                            elif filter_type == 'SESSION_TYPE':
                                filter_key = 'session_type'
                            else:
                                filter_key = filter_type.lower()

                            combinations.append({
                                'instrument': settings.instrument,
                                'setup_family': settings.setup_family,
                                'orb_time': orb_time,
                                'rr_target': rr_target,
                                'filters': {filter_key: filter_value}
                            })

        return combinations

    def _is_in_memory(self, param_hash: str) -> bool:
        """Check if combination already tested (in search_memory)"""
        result = self.conn.execute("""
            SELECT 1 FROM search_memory
            WHERE param_hash = ?
            LIMIT 1
        """, [param_hash]).fetchone()

        return result is not None

    def _score_candidate(
        self,
        combo: Dict,
        settings: SearchSettings
    ) -> Optional[Dict]:
        """
        Fast scoring proxy using daily_features

        Uses tradeable_realized_rr and tradeable_outcome columns (baseline RR=1.0 only)
        For other RR targets, scales the baseline data
        """
        orb_time = combo['orb_time']
        rr_target = combo['rr_target']
        instrument = settings.instrument

        try:
            # CRITICAL: Use tradeable_* columns (1st close outside ORB, not limit order)
            realized_rr_col = f"orb_{orb_time}_tradeable_realized_rr"
            outcome_col = f"orb_{orb_time}_tradeable_outcome"

            query = f"""
                SELECT
                    COUNT(*) as sample_size,
                    AVG(CASE WHEN {realized_rr_col} > 0 THEN 1.0 ELSE 0.0 END) as profitable_trade_rate,
                    AVG(CASE WHEN {outcome_col} = 'WIN' THEN 1.0 ELSE 0.0 END) as target_hit_rate,
                    AVG({realized_rr_col}) as avg_realized_rr
                FROM daily_features
                WHERE instrument = ?
                  AND {realized_rr_col} IS NOT NULL
                  AND {outcome_col} IS NOT NULL
            """

            result = self.conn.execute(query, [instrument]).fetchone()

            if result and result[0] >= settings.min_sample_size:
                sample_size = result[0]
                profitable_trade_rate = result[1]
                target_hit_rate = result[2]
                avg_realized_rr = result[3]

                # Stored Model Proxy (single RR target per ORB in daily_features)
                # No RR-specific data available - use average realized RR as proxy
                expected_r = avg_realized_rr

                return {
                    'sample_size': sample_size,
                    'profitable_trade_rate': profitable_trade_rate,
                    'target_hit_rate': target_hit_rate,
                    'expected_r': expected_r,
                    'score_proxy': expected_r
                }

        except Exception as e:
            logger.warning(f"Failed to score {orb_time} RR={rr_target}: {e}")
            return None

        return None

    def _save_candidate(self, run_id: str, candidate: SearchCandidate):
        """Save promising candidate to search_candidates"""
        # Generate candidate id from hash + timestamp (for determinism + uniqueness)
        import time
        timestamp_component = int(time.time() * 1000000) % 1000000  # Microseconds for uniqueness
        hash_component = int(candidate.param_hash[:8], 16) % 1000000  # Keep hash for determinism
        candidate_id = (hash_component * 1000000 + timestamp_component) % (2**31 - 1)

        self.conn.execute("""
            INSERT OR IGNORE INTO search_candidates (
                id, run_id, created_at, instrument, setup_family,
                orb_time, rr_target, filters_json, param_hash,
                score_proxy, sample_size, win_rate_proxy, expected_r_proxy, notes,
                profitable_trade_rate, target_hit_rate
            ) VALUES (
                ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, [
            candidate_id,
            run_id,
            candidate.instrument,
            candidate.setup_family,
            candidate.orb_time,
            candidate.rr_target,
            json.dumps(candidate.filters),
            candidate.param_hash,
            candidate.score_proxy,
            candidate.sample_size,
            candidate.win_rate_proxy,
            candidate.expected_r_proxy,
            candidate.notes,
            candidate.profitable_trade_rate,
            candidate.target_hit_rate
        ])

        # Also save to search_knowledge with result classification
        expectancy_r = candidate.expected_r_proxy if candidate.expected_r_proxy else 0.0
        sample_size = candidate.sample_size if candidate.sample_size else 0

        # Calculate robust_flags (bitmask for extensibility)
        # Uses bit flags so future concerns (OOS stability, cost stress, regime slices,
        # drawdown/tail checks) can be added without changing existing semantics.
        #
        # Current concerns (v1.0):
        # Bit 0 (0x01): Marginal sample size (30-49 trades)
        # Bit 1 (0x02): Marginal expectancy (0.15R-0.20R)
        # Bit 2 (0x04): Very low sample size (< 30)
        # Bit 3 (0x08): Weak/negative expectancy (< 0.15R)
        #
        # Future extensibility (reserve bits 4-7 for additional gates):
        # Bit 4 (0x10): OOS stability concern (not implemented)
        # Bit 5 (0x20): Cost stress failure (not implemented)
        # Bit 6 (0x40): Regime instability (not implemented)
        # Bit 7 (0x80): Tail risk / drawdown concern (not implemented)
        #
        robust_flags = 0

        # Bit 0: Marginal sample size (30-49 trades)
        if 30 <= sample_size < 50:
            robust_flags |= 0x01

        # Bit 1: Marginal expectancy (0.15R-0.20R)
        if 0.15 <= expectancy_r < 0.20:
            robust_flags |= 0x02

        # Bit 2: Very low sample size (< 30)
        if sample_size < 30:
            robust_flags |= 0x04

        # Bit 3: Weak/negative expectancy (< 0.15R)
        if expectancy_r < 0.15:
            robust_flags |= 0x08

        self._save_to_search_knowledge(
            candidate=candidate,
            expectancy_r=expectancy_r,
            sample_size=sample_size,
            robust_flags=robust_flags
        )

    def _add_to_memory(self, candidate: SearchCandidate):
        """Add candidate to search_memory (deduplication registry)"""
        from datetime import datetime

        # Generate memory_id from hash (for determinism)
        memory_id = int(candidate.param_hash[:8], 16) % (2**31 - 1)
        now = datetime.now()

        self.conn.execute("""
            INSERT INTO search_memory (
                memory_id, param_hash, instrument, setup_family, filters_json,
                first_seen_at, last_seen_at, test_count, best_score, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, '')
            ON CONFLICT (param_hash) DO UPDATE SET
                last_seen_at = ?,
                test_count = search_memory.test_count + 1,
                best_score = CASE
                    WHEN ? > search_memory.best_score THEN ?
                    ELSE search_memory.best_score
                END
        """, [
            memory_id,                          # ? for memory_id
            candidate.param_hash,               # ? for param_hash
            candidate.instrument,               # ? for instrument
            candidate.setup_family,             # ? for setup_family
            json.dumps(candidate.filters),      # ? for filters_json
            now,                                # ? for first_seen_at
            now,                                # ? for last_seen_at
            candidate.score_proxy,              # ? for best_score
            now,                                # ? for last_seen_at UPDATE
            candidate.score_proxy,              # ? for CASE WHEN comparison
            candidate.score_proxy               # ? for CASE WHEN THEN value
        ])

    def get_recent_candidates(self, run_id: str, limit: int = 20) -> List[Dict]:
        """Get candidates from specific run"""
        results = self.conn.execute("""
            SELECT
                id, orb_time, rr_target, score_proxy, sample_size,
                win_rate_proxy, expected_r_proxy, notes,
                profitable_trade_rate, target_hit_rate
            FROM search_candidates
            WHERE run_id = ?
            ORDER BY score_proxy DESC
            LIMIT ?
        """, [run_id, limit]).fetchall()

        candidates = []
        for row in results:
            candidates.append({
                'id': row[0],
                'orb_time': row[1],
                'rr_target': row[2],
                'score_proxy': row[3],
                'sample_size': row[4],
                'win_rate_proxy': row[5],  # DEPRECATED
                'profitable_trade_rate': row[8],  # New clarified metric
                'target_hit_rate': row[9],  # New clarified metric
                'expected_r_proxy': row[6],
                'notes': row[7]
            })

        return candidates

    def _save_to_search_knowledge(
        self,
        candidate: SearchCandidate,
        expectancy_r: float,
        sample_size: int,
        robust_flags: int = 0
    ):
        """
        Save candidate to search_knowledge with result classification

        Args:
            candidate: SearchCandidate to save
            expectancy_r: Expected R from scoring
            sample_size: Number of trades
            robust_flags: Number of robustness concerns (default 0)
        """
        # Classify result
        result_class = classify_result(expectancy_r, sample_size, robust_flags)

        # Get provenance
        prov = create_provenance_dict(
            ruleset_version=RULESET_VERSION,
            priority_version=PRIORITY_VERSION,
            param_hash_version=PARAM_HASH_VERSION
        )

        # Generate knowledge_id from param_hash (deterministic)
        knowledge_id = int(candidate.param_hash[:8], 16) % (2**31 - 1)

        # Insert or update
        self.conn.execute("""
            INSERT INTO search_knowledge (
                knowledge_id, param_hash, param_hash_version,
                instrument, setup_family, orb_time, rr_target, filters_json,
                result_class, expectancy_r, sample_size, robust_flags,
                ruleset_version, priority_version,
                git_commit, db_path, created_at, last_seen_at, notes
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT (param_hash) DO UPDATE SET
                result_class = EXCLUDED.result_class,
                expectancy_r = EXCLUDED.expectancy_r,
                sample_size = EXCLUDED.sample_size,
                robust_flags = EXCLUDED.robust_flags,
                last_seen_at = CURRENT_TIMESTAMP
        """, [
            knowledge_id,
            candidate.param_hash,
            PARAM_HASH_VERSION,
            candidate.instrument,
            candidate.setup_family,
            candidate.orb_time,
            candidate.rr_target,
            json.dumps(candidate.filters),
            result_class,
            expectancy_r,
            sample_size,
            robust_flags,
            RULESET_VERSION,
            PRIORITY_VERSION,
            prov['git_commit'],
            prov['db_path'],
            datetime.now(),
            datetime.now(),
            candidate.notes
        ])

    def _get_untested_combinations(
        self,
        settings: SearchSettings,
        max_count: int = 1000
    ) -> List[Dict]:
        """
        Get untested parameter combinations (not in search_memory)

        Args:
            settings: Search settings
            max_count: Maximum combinations to return

        Returns:
            List of untested combinations (sorted by param_hash for determinism)
        """
        # Generate all combinations
        all_combinations = self._generate_combinations(settings)

        # Filter to untested only
        untested = []
        for combo in all_combinations:
            param_hash = compute_param_hash_v2(combo)
            if not self._is_in_memory(param_hash):
                combo['param_hash'] = param_hash
                untested.append(combo)

        # Sort by param_hash for deterministic ordering
        untested_sorted = sorted(untested, key=lambda x: x['param_hash'])

        # Limit count
        return untested_sorted[:max_count]

    def _apply_epsilon_exploration(
        self,
        settings: SearchSettings,
        total_budget: int,
        epsilon: float = EPSILON
    ) -> tuple[List[Dict], List[Dict]]:
        """
        Split combinations into exploitation and exploration sets

        Exploitation: Top (1-ε) of total_budget by priority score
        Exploration: ε of total_budget from UNTESTED pool (hash-sorted for determinism)

        CRITICAL: Exploration MUST draw from untested pool, NOT from low-priority
        combinations in current batch. This ensures systematic parameter space coverage.

        Args:
            settings: Search settings
            total_budget: Total number of combinations to test
            epsilon: Exploration fraction (default 0.15 = 15%)

        Returns:
            (exploitation_list, exploration_list)
        """
        # Calculate split
        exploit_count = int(total_budget * (1 - epsilon))
        explore_count = total_budget - exploit_count

        # Initialize priority engine
        priority_engine = PriorityEngine(self.conn)

        # Generate ALL combinations (tested + untested)
        all_combinations = self._generate_combinations(settings)

        # Score all combinations (includes already-tested ones for priority learning)
        scored = []
        for combo in all_combinations:
            param_hash = compute_param_hash_v2(combo)
            combo['param_hash'] = param_hash

            # Skip if already tested (memory deduplication)
            if self._is_in_memory(param_hash):
                continue

            priority_score = priority_engine.score_combination(combo)
            combo['priority_score'] = priority_score
            scored.append(combo)

        # Sort by priority (descending)
        scored_sorted = sorted(scored, key=lambda x: x['priority_score'], reverse=True)

        # EXPLOITATION: Top (1-ε) by priority
        exploitation = scored_sorted[:exploit_count]

        # EXPLORATION: ε from UNTESTED pool (deterministic hash-sorted)
        # Get untested combinations (already hash-sorted by _get_untested_combinations)
        untested_pool = self._get_untested_combinations(settings, max_count=explore_count * 2)

        # Take first explore_count from hash-sorted untested pool (deterministic)
        exploration = untested_pool[:explore_count]

        logger.info(f"ε-exploration split: {exploit_count} exploit + {explore_count} explore (ε={epsilon})")
        logger.info(f"  Exploitation: Top {exploit_count} by priority score")
        logger.info(f"  Exploration: First {explore_count} from {len(untested_pool)} untested (hash-sorted)")

        return exploitation, exploration


def test_engine():
    """Test auto search engine"""
    import os
    from pathlib import Path

    db_path = Path(__file__).parent.parent / "data" / "db" / "gold.db"
    conn = duckdb.connect(str(db_path))

    engine = AutoSearchEngine(conn)

    print("="*80)
    print("AUTO SEARCH ENGINE TEST")
    print("="*80)

    # Test hash computation
    params1 = {
        'instrument': 'MGC',
        'setup_family': 'ORB_BASELINE',
        'orb_time': '0900',
        'rr_target': 1.5,
        'filters': {}
    }

    hash1 = compute_param_hash(params1)
    hash2 = compute_param_hash(params1)  # Should be same

    print(f"Hash determinism: {hash1 == hash2} (hash: {hash1})")

    # Run quick search
    print("\nRunning quick search (max 30 seconds)...")

    results = engine.run_search(
        instrument='MGC',
        settings={
            'family': 'ORB_BASELINE',
            'orb_times': ['0900', '1000'],
            'rr_targets': [1.5, 2.0],
            'min_sample_size': 30,
            'min_expected_r': 0.15
        },
        max_seconds=30
    )

    print(f"\nSearch complete: run_id={results['run_id'][:8]}...")
    print(f"  Tested: {results['stats']['tested']}")
    print(f"  Skipped: {results['stats']['skipped']}")
    print(f"  Promising: {results['stats']['promising']}")
    print(f"  Time: {results['stats']['time_elapsed']:.1f}s")

    # Show candidates
    if results['candidates']:
        print(f"\nTop candidates:")
        for c in results['candidates'][:5]:
            print(f"  {c.orb_time} RR={c.rr_target}: {c.score_proxy:.3f}R ({c.sample_size}N)")

    conn.close()


if __name__ == "__main__":
    test_engine()
