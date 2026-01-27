#!/usr/bin/env python3
"""
Check required manifest fields for candidates 47-48
"""

import sys
import json
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trading_app.cloud_mode import get_database_connection

def main():
    conn = get_database_connection(read_only=True)

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

        test_config = json.loads(test_config_json) if test_config_json else {}
        metrics = json.loads(metrics_json) if metrics_json else {}
        filter_spec = json.loads(filter_spec_json) if filter_spec_json else {}

        # Check required fields for edge_pipeline.py promotion
        required_in_metrics = ["orb_time", "rr", "win_rate", "avg_r", "annual_trades", "tier"]
        required_in_filter = ["orb_size_filter", "sl_mode"]

        print(f"  Checking metrics_json:")
        for field in required_in_metrics:
            has_it = field in metrics
            if has_it:
                print(f"    {field}: FOUND")
            else:
                print(f"    {field}: MISSING")

        print(f"  Checking filter_spec_json:")
        for field in required_in_filter:
            has_it = field in filter_spec
            if has_it:
                print(f"    {field}: FOUND")
            else:
                print(f"    {field}: MISSING")

        # Check if test_config has fields that should be in metrics
        if "orb_time" in test_config:
            print(f"  NOTE: orb_time found in test_config_json: {test_config['orb_time']}")
        if "rr" in test_config:
            print(f"  NOTE: rr found in test_config_json: {test_config['rr']}")
        if "sl_mode" in test_config:
            print(f"  NOTE: sl_mode found in test_config_json: {test_config['sl_mode']}")

        # Check metrics.365d section
        if "365d" in metrics:
            print(f"  NOTE: Found metrics.365d section with keys: {list(metrics['365d'].keys())}")

        print()

    conn.close()

if __name__ == "__main__":
    main()
