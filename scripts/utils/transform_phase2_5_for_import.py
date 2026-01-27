#!/usr/bin/env python3
"""
Transform Phase 2.5 candidates into edge_import.py compatible format.
"""

import json
from pathlib import Path

def transform_candidates():
    """Transform phase2_5_top50_candidates.json to edge_import format."""

    # Load source file
    source = Path("research/phase2_5_top50_candidates.json")
    with open(source, 'r') as f:
        data = json.load(f)

    # Extract candidates array from wrapper
    candidates = data.get("candidates", [])

    transformed = []

    for c in candidates:
        # Extract session from name or use provided session field
        session = c.get("session", "UNKNOWN")

        # Parse scan window to extract start/end times
        scan_parts = c.get("scan_window", "").split("→")
        scan_start = scan_parts[0].strip() if len(scan_parts) > 0 else "N/A"
        scan_end = scan_parts[1].strip() if len(scan_parts) > 1 else "N/A"

        # Build filter_spec
        filter_spec = {
            "type": c.get("structure", "unknown"),
            "description": c.get("filter", "No filter specified"),
            "scan_window_start": scan_start,
            "scan_window_end": scan_end
        }

        # Build test_config
        test_config = {
            "orb_time": session,
            "entry_rule": c.get("entry", "First 1m close outside ORB"),
            "stop_rule": c.get("stop", "ORB midpoint (HALF mode)"),
            "target_rule": c.get("target", "N/A"),
            "scan_window": c.get("scan_window", "N/A")
        }

        # Build metrics (expected performance)
        metrics = {
            "expected_win_rate": c.get("expected_wr", 0.0),
            "expected_avg_r": c.get("expected_avg_r", 0.0),
            "status": "UNTESTED",
            "note": "Systematically generated in Phase 2.5 MGC discovery"
        }

        # Build slippage assumptions (defaults)
        slippage = {
            "entry_slippage_ticks": 1,
            "exit_slippage_ticks": 1,
            "commission_per_side": 2.50,
            "note": "Standard MGC assumptions"
        }

        # Build transformed candidate
        transformed_candidate = {
            "research_id": f"PHASE2.5_MGC_{c['id']:03d}",
            "name": c["name"],
            "instrument": c["instrument"],
            "hypothesis_text": c.get("hypothesis", "No hypothesis provided"),
            "filter_spec": filter_spec,
            "test_config": test_config,
            "metrics": metrics,
            "slippage_assumptions": slippage,
            "code_version": "phase2.5_systematic_discovery",
            "data_version": "2020-12-20_to_2026-01-10",
            "survival_score": None,
            "confidence_level": "UNTESTED"
        }

        transformed.append(transformed_candidate)

    # Write transformed file
    output = Path("research/phase2_5_for_import.json")
    with open(output, 'w') as f:
        json.dump(transformed, f, indent=2)

    print(f"[OK] Transformed {len(transformed)} candidates")
    print(f"     Input: {source}")
    print(f"     Output: {output}")
    print()
    print("Next: python trading_app/edge_import.py --input research/phase2_5_for_import.json --actor Phase2.5_Discovery")

if __name__ == "__main__":
    transform_candidates()
