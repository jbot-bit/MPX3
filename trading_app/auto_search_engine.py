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
        for orb_time in settings.orb_times:
            for rr_target in settings.rr_targets:
                combinations.append({
                    'instrument': settings.instrument,
                    'setup_family': settings.setup_family,
                    'orb_time': orb_time,
                    'rr_target': rr_target,
                    'filters': {}
                })

        # TODO: Add filter combinations (size, travel, session type)
        # For now, keep it simple with baseline only

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

        Prefers existing ORB columns if available:
        - orb_*_tradeable_realized_rr (if RR matches)
        - orb_*_outcome (for win rate)

        Fallback: Average r_multiple from outcomes
        """
        orb_time = combo['orb_time']
        rr_target = combo['rr_target']
        instrument = settings.instrument

        try:
            # Check if tradeable_realized_rr column exists for this RR
            # Format: orb_0900_tradeable_realized_rr_1_5 (for RR=1.5)
            rr_str = str(rr_target).replace('.', '_')
            realized_rr_col = f"orb_{orb_time}_tradeable_realized_rr_{rr_str}"

            # Try to use existing column
            query = f"""
                SELECT
                    COUNT(*) as sample_size,
                    AVG(CASE WHEN {realized_rr_col} > 0 THEN 1.0 ELSE 0.0 END) as profitable_trade_rate,
                    AVG({realized_rr_col}) as expected_r
                FROM daily_features
                WHERE instrument = ?
                  AND {realized_rr_col} IS NOT NULL
            """

            result = self.conn.execute(query, [instrument]).fetchone()

            if result and result[0] >= settings.min_sample_size:
                return {
                    'sample_size': result[0],
                    'profitable_trade_rate': result[1],  # Profitable trades (realized_rr > 0)
                    'target_hit_rate': None,  # Not available in this path
                    'expected_r': result[2],
                    'score_proxy': result[2]  # Use expected_r as proxy
                }

        except Exception:
            # Column doesn't exist, use fallback
            pass

        # Fallback: Use r_multiple from baseline outcomes
        try:
            outcome_col = f"orb_{orb_time}_outcome"
            r_multiple_col = f"orb_{orb_time}_r_multiple"

            query = f"""
                SELECT
                    COUNT(*) as sample_size,
                    AVG(CASE WHEN {outcome_col} = 'WIN' THEN 1.0 ELSE 0.0 END) as target_hit_rate,
                    AVG({r_multiple_col}) as avg_r
                FROM daily_features
                WHERE instrument = ?
                  AND {outcome_col} IS NOT NULL
                  AND {r_multiple_col} IS NOT NULL
            """

            result = self.conn.execute(query, [instrument]).fetchone()

            if result and result[0] >= settings.min_sample_size:
                return {
                    'sample_size': result[0],
                    'profitable_trade_rate': None,  # Not available in this path
                    'target_hit_rate': result[1],  # Trades that hit profit target
                    'expected_r': result[2],
                    'score_proxy': result[2]
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
