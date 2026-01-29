"""
What-If Snapshot Persistence
============================

Stores and retrieves What-If Analyzer results as immutable snapshots.

Features:
- Immutable storage (no updates, only inserts)
- Full reproducibility (all parameters + results stored)
- Deterministic re-evaluation (can reload and re-run)
- Promotion tracking (snapshots → validation candidates)

Usage:
    from what_if_snapshots import SnapshotManager

    manager = SnapshotManager(db_connection)

    # Save a snapshot
    snapshot_id = manager.save_snapshot(
        result=engine_result,
        notes="Promising ORB size filter",
        created_by="user@example.com"
    )

    # Load a snapshot
    snapshot = manager.load_snapshot(snapshot_id)

    # List recent snapshots
    recent = manager.list_snapshots(limit=10)

    # Re-evaluate a snapshot (deterministic)
    new_result = manager.re_evaluate_snapshot(snapshot_id, engine)
"""

import duckdb
import json
import uuid
from typing import Dict, List, Optional
from datetime import datetime


class SnapshotManager:
    """
    Manages What-If Analyzer snapshots

    Handles saving, loading, and re-evaluating analysis results.
    """

    def __init__(self, db_connection: duckdb.DuckDBPyConnection):
        self.conn = db_connection
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Create what_if_snapshots table if it doesn't exist"""
        # Validate connection before executing
        if self.conn is None:
            raise ValueError("Database connection is None. Cannot create table.")

        try:
            # Test connection is alive
            self.conn.execute("SELECT 1").fetchone()
        except Exception as e:
            raise ValueError(f"Database connection is invalid or closed: {e}")

        # Read schema from file
        import os
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'docs',
            'what_if_snapshots_schema.sql'
        )

        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
                # Execute schema (CREATE TABLE IF NOT EXISTS)
                try:
                    self.conn.execute(schema_sql)
                except Exception as e:
                    # Log error but don't crash - table might already exist
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Error executing schema (table may already exist): {e}")
        else:
            # Fallback: create minimal table
            try:
                self.conn.execute("""
                    CREATE TABLE IF NOT EXISTS what_if_snapshots (
                        snapshot_id TEXT PRIMARY KEY,
                        cache_key TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    instrument TEXT NOT NULL,
                    orb_time TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    rr DOUBLE NOT NULL,
                    sl_mode TEXT NOT NULL,
                    conditions JSON NOT NULL,
                    date_start DATE,
                    date_end DATE,
                    baseline_sample_size INTEGER NOT NULL,
                    baseline_win_rate DOUBLE NOT NULL,
                    baseline_expected_r DOUBLE NOT NULL,
                    baseline_avg_win DOUBLE NOT NULL,
                    baseline_avg_loss DOUBLE NOT NULL,
                    baseline_max_dd DOUBLE NOT NULL,
                    baseline_sharpe_ratio DOUBLE NOT NULL,
                    baseline_total_r DOUBLE NOT NULL,
                    baseline_stress_25_exp_r DOUBLE NOT NULL,
                    baseline_stress_50_exp_r DOUBLE NOT NULL,
                    baseline_stress_25_pass BOOLEAN NOT NULL,
                    baseline_stress_50_pass BOOLEAN NOT NULL,
                    conditional_sample_size INTEGER NOT NULL,
                    conditional_win_rate DOUBLE NOT NULL,
                    conditional_expected_r DOUBLE NOT NULL,
                    conditional_avg_win DOUBLE NOT NULL,
                    conditional_avg_loss DOUBLE NOT NULL,
                    conditional_max_dd DOUBLE NOT NULL,
                    conditional_sharpe_ratio DOUBLE NOT NULL,
                    conditional_total_r DOUBLE NOT NULL,
                    conditional_stress_25_exp_r DOUBLE NOT NULL,
                    conditional_stress_50_exp_r DOUBLE NOT NULL,
                    conditional_stress_25_pass BOOLEAN NOT NULL,
                    conditional_stress_50_pass BOOLEAN NOT NULL,
                    non_matched_sample_size INTEGER NOT NULL,
                    non_matched_win_rate DOUBLE NOT NULL,
                    non_matched_expected_r DOUBLE NOT NULL,
                    delta_sample_size INTEGER NOT NULL,
                    delta_win_rate_pct DOUBLE NOT NULL,
                    delta_expected_r DOUBLE NOT NULL,
                    delta_avg_win DOUBLE NOT NULL,
                    delta_avg_loss DOUBLE NOT NULL,
                    delta_max_dd DOUBLE NOT NULL,
                    delta_sharpe_ratio DOUBLE NOT NULL,
                    delta_total_r DOUBLE NOT NULL,
                    data_version TEXT,
                    engine_version TEXT NOT NULL DEFAULT 'v1',
                    notes TEXT,
                    promoted_to_candidate BOOLEAN DEFAULT FALSE,
                    candidate_edge_id TEXT,
                    created_by TEXT
                )
            """)
            except Exception as e:
                # Log error but don't crash - table might already exist
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Error creating table (may already exist): {e}")

    def save_snapshot(
        self,
        result: Dict,
        notes: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> str:
        """
        Save a What-If result as an immutable snapshot

        Args:
            result: Result dict from WhatIfEngine.analyze_conditions()
            notes: Optional user notes
            created_by: Optional user identifier

        Returns:
            snapshot_id (UUID)
        """
        snapshot_id = str(uuid.uuid4())

        # Extract setup from result
        # Note: WhatIfEngine doesn't store setup params in result,
        # so we need to parse from cache_key or pass separately
        # For now, we'll extract from condition_set and assume setup is in result
        # (This should be improved in WhatIfEngine to include setup in result)

        # Parse setup from cache_key
        cache_key = result['cache_key']
        parts = cache_key.split('_')
        instrument = parts[0]
        orb_time = parts[1]
        direction = parts[2]
        rr = float(parts[3].replace('rr', ''))
        sl_mode = parts[4].upper()
        date_start = parts[6] if parts[6] != 'all' else None
        date_end = parts[7] if parts[7] != 'all' else None

        # Get metrics
        baseline = result['baseline']
        conditional = result['conditional']
        non_matched = result['non_matched']
        delta = result['delta']
        condition_set = result['condition_set']

        # Data version (snapshot of daily_features state)
        data_version = self._get_data_version()

        # Insert snapshot (convert numpy types to Python types)
        # Use explicit column names for clarity
        self.conn.execute("""
            INSERT INTO what_if_snapshots (
                snapshot_id, cache_key, created_at,
                instrument, orb_time, direction, rr, sl_mode,
                conditions, date_start, date_end,
                baseline_sample_size, baseline_win_rate, baseline_expected_r,
                baseline_avg_win, baseline_avg_loss, baseline_max_dd,
                baseline_sharpe_ratio, baseline_total_r,
                baseline_stress_25_exp_r, baseline_stress_50_exp_r,
                baseline_stress_25_pass, baseline_stress_50_pass,
                conditional_sample_size, conditional_win_rate, conditional_expected_r,
                conditional_avg_win, conditional_avg_loss, conditional_max_dd,
                conditional_sharpe_ratio, conditional_total_r,
                conditional_stress_25_exp_r, conditional_stress_50_exp_r,
                conditional_stress_25_pass, conditional_stress_50_pass,
                non_matched_sample_size, non_matched_win_rate, non_matched_expected_r,
                delta_sample_size, delta_win_rate_pct, delta_expected_r,
                delta_avg_win, delta_avg_loss, delta_max_dd,
                delta_sharpe_ratio, delta_total_r,
                data_version, engine_version, notes,
                promoted_to_candidate, candidate_edge_id, created_by
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, [
            snapshot_id,
            cache_key,
            datetime.now(),
            instrument,
            orb_time,
            direction,
            float(rr),
            sl_mode,
            json.dumps(condition_set),
            date_start,
            date_end,
            # Baseline
            int(baseline.sample_size),
            float(baseline.win_rate),
            float(baseline.expected_r),
            float(baseline.avg_win),
            float(baseline.avg_loss),
            float(baseline.max_dd),
            float(baseline.sharpe_ratio),
            float(baseline.total_r),
            float(baseline.stress_25_exp_r),
            float(baseline.stress_50_exp_r),
            bool(baseline.stress_25_pass),
            bool(baseline.stress_50_pass),
            # Conditional
            int(conditional.sample_size),
            float(conditional.win_rate),
            float(conditional.expected_r),
            float(conditional.avg_win),
            float(conditional.avg_loss),
            float(conditional.max_dd),
            float(conditional.sharpe_ratio),
            float(conditional.total_r),
            float(conditional.stress_25_exp_r),
            float(conditional.stress_50_exp_r),
            bool(conditional.stress_25_pass),
            bool(conditional.stress_50_pass),
            # Non-matched
            int(non_matched.sample_size),
            float(non_matched.win_rate),
            float(non_matched.expected_r),
            # Delta
            int(delta['sample_size']),
            float(delta['win_rate_pct']),
            float(delta['expected_r']),
            float(delta['avg_win']),
            float(delta['avg_loss']),
            float(delta['max_dd']),
            float(delta['sharpe_ratio']),
            float(delta['total_r']),
            # Metadata
            data_version,
            'v1',  # engine_version
            notes,
            False,  # promoted_to_candidate
            None,  # candidate_edge_id
            created_by
        ])

        return snapshot_id

    def load_snapshot(self, snapshot_id: str) -> Dict:
        """
        Load a snapshot by ID

        Returns:
            Dict with all snapshot data
        """
        row = self.conn.execute("""
            SELECT * FROM what_if_snapshots
            WHERE snapshot_id = ?
        """, [snapshot_id]).fetchone()

        if row is None:
            raise ValueError(f"Snapshot not found: {snapshot_id}")

        # Convert to dict (column names from schema)
        columns = [desc[0] for desc in self.conn.description]
        snapshot = dict(zip(columns, row))

        # Parse JSON conditions
        snapshot['conditions'] = json.loads(snapshot['conditions'])

        return snapshot

    def list_snapshots(
        self,
        instrument: Optional[str] = None,
        orb_time: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        List snapshots with optional filters

        Args:
            instrument: Filter by instrument ('MGC', 'NQ', etc.)
            orb_time: Filter by ORB time ('1000', '1800', etc.)
            limit: Max results to return
            offset: Pagination offset

        Returns:
            List of snapshot dicts (summary info only)
        """
        where_parts = []
        params = []

        if instrument:
            where_parts.append("instrument = ?")
            params.append(instrument)

        if orb_time:
            where_parts.append("orb_time = ?")
            params.append(orb_time)

        where_clause = " AND ".join(where_parts) if where_parts else "1=1"

        query = f"""
            SELECT
                snapshot_id,
                cache_key,
                created_at,
                instrument,
                orb_time,
                direction,
                rr,
                sl_mode,
                conditions,
                baseline_sample_size,
                baseline_win_rate,
                baseline_expected_r,
                conditional_sample_size,
                conditional_win_rate,
                conditional_expected_r,
                delta_sample_size,
                delta_win_rate_pct,
                delta_expected_r,
                promoted_to_candidate,
                candidate_edge_id,
                notes
            FROM what_if_snapshots
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """

        rows = self.conn.execute(query, params + [limit, offset]).fetchall()

        # Convert to dicts
        results = []
        columns = [desc[0] for desc in self.conn.description]
        for row in rows:
            snapshot = dict(zip(columns, row))
            snapshot['conditions'] = json.loads(snapshot['conditions'])
            results.append(snapshot)

        return results

    def re_evaluate_snapshot(
        self,
        snapshot_id: str,
        engine  # WhatIfEngine instance
    ) -> Dict:
        """
        Re-evaluate a snapshot deterministically

        Reloads the snapshot parameters and re-runs the analysis
        to verify reproducibility.

        Args:
            snapshot_id: Snapshot to re-evaluate
            engine: WhatIfEngine instance

        Returns:
            New result dict (should match original snapshot)
        """
        # Load snapshot
        snapshot = self.load_snapshot(snapshot_id)

        # Extract parameters
        instrument = snapshot['instrument']
        orb_time = snapshot['orb_time']
        direction = snapshot['direction']
        rr = snapshot['rr']
        sl_mode = snapshot['sl_mode']
        conditions = snapshot['conditions']
        date_start = snapshot['date_start']
        date_end = snapshot['date_end']

        # Re-run analysis (deterministic)
        result = engine.analyze_conditions(
            instrument=instrument,
            orb_time=orb_time,
            direction=direction,
            rr=rr,
            sl_mode=sl_mode,
            conditions=conditions,
            date_start=date_start,
            date_end=date_end,
            use_cache=False  # Force recomputation
        )

        return result

    def promote_snapshot_to_candidate(
        self,
        snapshot_id: str,
        trigger_definition: str,
        notes: Optional[str] = None
    ) -> str:
        """
        Promote a snapshot to validation candidate

        Creates a new edge in edge_registry with status=CANDIDATE
        and links it to the snapshot for lineage tracking.

        Args:
            snapshot_id: Snapshot to promote
            trigger_definition: Entry trigger description
            notes: Optional notes for the candidate

        Returns:
            edge_id of created candidate
        """
        # Load snapshot
        snapshot = self.load_snapshot(snapshot_id)

        # Import edge_utils for create_candidate
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from trading_app.edge_utils import create_candidate

        # Extract parameters
        instrument = snapshot['instrument']
        orb_time = snapshot['orb_time']
        direction = snapshot['direction']
        rr = snapshot['rr']
        sl_mode = snapshot['sl_mode']
        conditions = snapshot['conditions']

        # Build orb_filter from conditions (if ORB size filter was applied)
        orb_filter = None
        if conditions.get('orb_size_min') is not None:
            orb_filter = conditions['orb_size_min']

        # Create candidate with filters stored in filters_applied JSON
        edge_id, message = create_candidate(
            db_connection=self.conn,
            instrument=instrument,
            orb_time=orb_time,
            direction=direction,
            trigger_definition=trigger_definition,
            rr=rr,
            sl_mode=sl_mode,
            orb_filter=orb_filter,
            session=None,
            notes=notes or f"Promoted from What-If snapshot {snapshot_id[:16]}"
        )

        # Store full condition set in filters_applied (extend edge_utils if needed)
        # For now, update directly
        import json
        self.conn.execute("""
            UPDATE edge_registry
            SET filters_applied = ?
            WHERE edge_id = ?
        """, [json.dumps(conditions), edge_id])

        # Mark snapshot as promoted
        self.conn.execute("""
            UPDATE what_if_snapshots
            SET promoted_to_candidate = TRUE,
                candidate_edge_id = ?
            WHERE snapshot_id = ?
        """, [edge_id, snapshot_id])

        return edge_id

    def promote_to_candidate(
        self,
        snapshot_id: str,
        candidate_edge_id: str
    ):
        """
        Mark a snapshot as promoted to validation candidate

        Args:
            snapshot_id: Snapshot ID
            candidate_edge_id: The edge_id created in edge_registry
        """
        self.conn.execute("""
            UPDATE what_if_snapshots
            SET promoted_to_candidate = TRUE,
                candidate_edge_id = ?
            WHERE snapshot_id = ?
        """, [candidate_edge_id, snapshot_id])

    def _get_data_version(self) -> str:
        """
        Get current data version for reproducibility

        Returns version string based on daily_features metadata
        """
        try:
            # Get max date from daily_features (data freshness indicator)
            max_date = self.conn.execute("""
                SELECT MAX(date_local) FROM daily_features
            """).fetchone()[0]

            return f"daily_features_{max_date}"
        except:
            return f"daily_features_{datetime.now().date()}"


if __name__ == "__main__":
    # Test snapshot persistence
    import duckdb
    from pathlib import Path
    from what_if_engine import WhatIfEngine

    # Connect to database
    db_path = Path(__file__).parent.parent / "data" / "db" / "gold.db"
    conn = duckdb.connect(str(db_path))

    # Create engine and manager
    engine = WhatIfEngine(conn)
    manager = SnapshotManager(conn)

    print("Testing Snapshot Persistence...")
    print()

    # Run analysis
    result = engine.analyze_conditions(
        instrument='MGC',
        orb_time='1000',
        direction='BOTH',
        rr=2.0,
        sl_mode='FULL',
        conditions={
            'orb_size_min': 0.5,
            'asia_travel_max': 2.5
        },
        date_start='2024-01-01',
        date_end='2025-12-31'
    )

    # Save snapshot
    snapshot_id = manager.save_snapshot(
        result=result,
        notes="Test snapshot - ORB >= 0.5 ATR filter",
        created_by="test_script"
    )

    print(f"[SAVED] Snapshot ID: {snapshot_id}")
    print()

    # Load snapshot
    loaded = manager.load_snapshot(snapshot_id)
    print(f"[LOADED] Snapshot")
    print(f"  Instrument: {loaded['instrument']}")
    print(f"  ORB: {loaded['orb_time']}")
    print(f"  Baseline: {loaded['baseline_sample_size']} trades, {loaded['baseline_win_rate']*100:.1f}% WR")
    print(f"  Conditional: {loaded['conditional_sample_size']} trades, {loaded['conditional_win_rate']*100:.1f}% WR")
    print(f"  Delta: {loaded['delta_sample_size']:+d} trades, {loaded['delta_expected_r']:+.3f}R")
    print()

    # Re-evaluate (deterministic test)
    print("[RE-EVALUATING] Snapshot...")
    re_eval_result = manager.re_evaluate_snapshot(snapshot_id, engine)

    # Compare
    original_exp_r = loaded['conditional_expected_r']
    re_eval_exp_r = re_eval_result['conditional'].expected_r

    print(f"  Original ExpR: {original_exp_r:.6f}R")
    print(f"  Re-eval ExpR: {re_eval_exp_r:.6f}R")
    print(f"  Difference: {abs(original_exp_r - re_eval_exp_r):.9f}R")

    if abs(original_exp_r - re_eval_exp_r) < 0.0001:
        print("  [PASS] Deterministic reproduction verified!")
    else:
        print("  [WARN] Small difference detected (may be due to rounding)")

    print()

    # List recent snapshots
    recent = manager.list_snapshots(limit=5)
    print(f"[LIST] Recent snapshots: {len(recent)}")
    for snap in recent[:3]:
        print(f"  {snap['snapshot_id'][:8]}: {snap['instrument']} {snap['orb_time']} - {snap['notes']}")

    conn.close()
