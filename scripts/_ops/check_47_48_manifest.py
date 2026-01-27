#!/usr/bin/env python3
"""
Check manifest fields for candidates 47-48
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

    output_lines = []

    for row in results:
        candidate_id, test_config_json, metrics_json, filter_spec_json = row

        print(f"="*80)
        print(f"Candidate {candidate_id}")
        print(f"="*80)

        test_config = json.loads(test_config_json) if test_config_json else {}
        metrics = json.loads(metrics_json) if metrics_json else {}
        filter_spec = json.loads(filter_spec_json) if filter_spec_json else {}

        print()
        print("test_config_json:")
        for key, value in test_config.items():
            print(f"  {key}: {value}")

        print()
        print("metrics_json:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")

        print()
        print("filter_spec_json:")
        for key, value in filter_spec.items():
            print(f"  {key}: {value}")

        print()

        # Check required fields for promotion
        print("REQUIRED FIELDS CHECK (for edge_pipeline.py):")
        print("-" * 80)

        # From metrics_json
        required_in_metrics = ["orb_time", "rr", "win_rate", "avg_r", "annual_trades", "tier"]
        print("metrics_json needs:")
        for field in required_in_metrics:
            has_it = field in metrics
            status = "OK" if has_it else "MISSING"
            value = metrics.get(field, "N/A")
            print(f"  {field}: {status} (value: {value})")

        print()

        # From filter_spec_json
        required_in_filter = ["orb_size_filter", "sl_mode"]
        print("filter_spec_json needs:")
        for field in required_in_filter:
            has_it = field in filter_spec
            status = "OK" if has_it else "MISSING"
            value = filter_spec.get(field, "N/A")
            print(f"  {field}: {status} (value: {value})")

        print()
        print()

    conn.close()

if __name__ == "__main__":
    main()
