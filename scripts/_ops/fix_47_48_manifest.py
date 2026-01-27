#!/usr/bin/env python3
"""
Fix manifest JSON fields for candidates 47-48 to match edge_pipeline.py requirements
"""

import sys
import json
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trading_app.cloud_mode import get_database_connection

def main():
    conn = get_database_connection(read_only=False)

    print("="*80)
    print("FIX MANIFEST FOR CANDIDATES 47-48")
    print("="*80)
    print()

    query = """
        SELECT candidate_id, test_config_json, metrics_json, filter_spec_json
        FROM edge_candidates
        WHERE candidate_id IN (47, 48)
        ORDER BY candidate_id
    """

    results = conn.execute(query).fetchall()

    for row in results:
        candidate_id, test_config_json, metrics_json, filter_spec_json = row

        print(f"Candidate {candidate_id}:")

        test_config = json.loads(test_config_json)
        metrics = json.loads(metrics_json)
        filter_spec = json.loads(filter_spec_json)

        # Extract values from test_config and metrics.365d
        orb_time = str(test_config.get("orb_time"))  # Convert to string
        rr = test_config.get("rr")
        sl_mode = test_config.get("sl_mode")

        metrics_365d = metrics.get("365d", {})
        win_rate = metrics_365d.get("win_rate")
        avg_r = metrics_365d.get("avg_r")
        trades = metrics_365d.get("trades", 0)

        # Calculate annual_trades (trades over 365 days)
        annual_trades = trades  # Already for 365 days

        # Assign tier based on avg_r
        if avg_r >= 0.08:
            tier = "A"
        elif avg_r >= 0.05:
            tier = "B"
        else:
            tier = "C"

        print(f"  Extracted values:")
        print(f"    orb_time: {orb_time}")
        print(f"    rr: {rr}")
        print(f"    sl_mode: {sl_mode}")
        print(f"    win_rate: {win_rate}")
        print(f"    avg_r: {avg_r}")
        print(f"    annual_trades: {annual_trades}")
        print(f"    tier: {tier}")

        # Update metrics_json to include required fields at top level
        updated_metrics = metrics.copy()
        updated_metrics["orb_time"] = orb_time
        updated_metrics["rr"] = rr
        updated_metrics["win_rate"] = win_rate
        updated_metrics["avg_r"] = avg_r
        updated_metrics["annual_trades"] = annual_trades
        updated_metrics["tier"] = tier

        # Update filter_spec_json to include sl_mode and orb_size_filter
        updated_filter_spec = filter_spec.copy()
        updated_filter_spec["sl_mode"] = sl_mode
        updated_filter_spec["orb_size_filter"] = None  # No filter for these candidates

        # Also add test_window_start and test_window_end for edge_pipeline
        updated_filter_spec["test_window_start"] = "2025-01-11"
        updated_filter_spec["test_window_end"] = "2026-01-10"

        # Convert to JSON
        updated_metrics_json = json.dumps(updated_metrics)
        updated_filter_spec_json = json.dumps(updated_filter_spec)

        # Update database
        update_query = """
            UPDATE edge_candidates
            SET metrics_json = ?::JSON,
                filter_spec_json = ?::JSON
            WHERE candidate_id = ?
        """

        conn.execute(update_query, [updated_metrics_json, updated_filter_spec_json, candidate_id])

        print(f"  UPDATED")
        print()

    conn.commit()

    print("="*80)
    print("MANIFEST FIX COMPLETE")
    print("="*80)

    conn.close()

if __name__ == "__main__":
    main()
