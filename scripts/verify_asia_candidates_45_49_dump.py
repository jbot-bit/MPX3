#!/usr/bin/env python3
"""
Dump edge_candidates rows 45-49 for verification
"""

import sys
import json
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trading_app.cloud_mode import get_database_connection

# Database path
root = Path(__file__).parent.parent

def main():
    conn = get_database_connection(read_only=True)

    print("="*80)
    print("EDGE_CANDIDATES 45-49 RAW DUMP")
    print("="*80)
    print()

    # Query candidates 45-49
    query = """
        SELECT
            candidate_id,
            status,
            instrument,
            name,
            metrics_json,
            feature_spec_json,
            filter_spec_json,
            test_config_json
        FROM edge_candidates
        WHERE candidate_id BETWEEN 45 AND 49
        ORDER BY candidate_id
    """

    results = conn.execute(query).fetchall()

    if not results:
        print("ERROR: No candidates found in range 45-49")
        return

    print(f"Found {len(results)} candidates")
    print()

    lines = []
    lines.append("# EDGE_CANDIDATES 45-49 RAW DUMP")
    lines.append("")
    lines.append(f"**Total Candidates**: {len(results)}")
    lines.append("")

    for row in results:
        candidate_id, status, instrument, name, metrics_json, feature_spec_json, filter_spec_json, test_config_json = row

        print(f"{'='*80}")
        print(f"Candidate ID: {candidate_id}")
        print(f"{'='*80}")
        print(f"Status: {status}")
        print(f"Instrument: {instrument}")
        print(f"Name: {name}")
        print()

        lines.append(f"## Candidate {candidate_id}")
        lines.append("")
        lines.append(f"**Status**: {status}")
        lines.append(f"**Instrument**: {instrument}")
        lines.append(f"**Name**: {name}")
        lines.append("")

        # Parse and display metrics
        if metrics_json:
            metrics = json.loads(metrics_json)
            print("Metrics JSON:")

            if '365d' in metrics:
                print("  365d:")
                for k, v in metrics['365d'].items():
                    print(f"    {k}: {v}")

                lines.append("### Metrics - 365d")
                lines.append("")
                lines.append("```json")
                lines.append(json.dumps(metrics['365d'], indent=2))
                lines.append("```")
                lines.append("")

            if 'splits' in metrics:
                print("  splits:")
                for k, v in metrics['splits'].items():
                    print(f"    {k}: {v}")

                lines.append("### Metrics - Splits")
                lines.append("")
                lines.append("```json")
                lines.append(json.dumps(metrics['splits'], indent=2))
                lines.append("```")
                lines.append("")

        # Parse and display feature_spec
        if feature_spec_json:
            feature_spec = json.loads(feature_spec_json)
            print("Feature Spec JSON keys:")
            print(f"  {list(feature_spec.keys())}")
            lines.append("### Feature Spec Keys")
            lines.append("")
            lines.append(f"```\n{list(feature_spec.keys())}\n```")
            lines.append("")

        # Parse and display filter_spec
        if filter_spec_json:
            filter_spec = json.loads(filter_spec_json)
            print("Filter Spec JSON:")
            print(json.dumps(filter_spec, indent=2))
            lines.append("### Filter Spec")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(filter_spec, indent=2))
            lines.append("```")
            lines.append("")

        # Parse and display test_config
        if test_config_json:
            test_config = json.loads(test_config_json)
            print("Test Config JSON:")
            print(json.dumps(test_config, indent=2))
            lines.append("### Test Config")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(test_config, indent=2))
            lines.append("```")
            lines.append("")

        print()
        lines.append("---")
        lines.append("")

    # Save to markdown
    output_path = root / "research" / "quick_asia" / "VERIFY_ASIA_45_49_RAW_DUMP.md"
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))

    print(f"OK Saved dump to: {output_path}")

    conn.close()

if __name__ == "__main__":
    main()
