#!/usr/bin/env python3
"""
Promote candidates 47-48 directly to validated_setups
(Simplified version that matches actual schema)
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trading_app.cloud_mode import get_database_connection

def promote_candidate(conn, candidate_id, actor="claude_approve_txt"):
    """
    Promote a single APPROVED candidate to validated_setups.
    """
    # Fetch candidate
    query = """
        SELECT candidate_id, name, instrument, hypothesis_text,
               filter_spec_json, test_config_json, metrics_json,
               code_version, data_version, status, approved_at, approved_by
        FROM edge_candidates
        WHERE candidate_id = ?
    """

    result = conn.execute(query, [candidate_id]).fetchone()

    if result is None:
        raise ValueError(f"Candidate {candidate_id} not found")

    (cid, name, instrument, hypothesis_text,
     filter_spec_json, test_config_json, metrics_json,
     code_version, data_version, status, approved_at, approved_by) = result

    if status != 'APPROVED':
        raise ValueError(f"Cannot promote candidate {cid}: status is '{status}', must be 'APPROVED'")

    # Parse JSON
    filter_spec = json.loads(filter_spec_json)
    test_config = json.loads(test_config_json)
    metrics = json.loads(metrics_json)

    # Extract required fields
    orb_time = str(metrics.get("orb_time"))
    rr = metrics.get("rr")
    sl_mode = filter_spec.get("sl_mode")
    win_rate = metrics.get("win_rate")
    avg_r = metrics.get("avg_r")
    annual_trades = metrics.get("annual_trades")
    tier = metrics.get("tier")
    orb_size_filter = filter_spec.get("orb_size_filter")

    # Generate setup_id
    setup_id = f"{instrument}_{orb_time}_{candidate_id:03d}"

    # Build notes
    notes_metadata = {
        "name": name,
        "hypothesis_text": hypothesis_text,
        "code_version": code_version,
        "data_version": data_version,
        "test_window_start": filter_spec.get("test_window_start"),
        "test_window_end": filter_spec.get("test_window_end"),
        "promoted_from_candidate_id": candidate_id,
        "promoted_by": actor,
        "promoted_at": datetime.utcnow().isoformat()
    }
    notes_json = json.dumps(notes_metadata)

    # Insert into validated_setups
    insert_query = """
        INSERT INTO validated_setups (
            setup_id, instrument, orb_time, rr, sl_mode,
            close_confirmations, buffer_ticks, orb_size_filter,
            atr_filter, min_gap_filter,
            trades, win_rate, avg_r, annual_trades, tier,
            notes, validated_date, data_source
        ) VALUES (
            ?, ?, ?, ?, ?,
            1, 0.0, ?,
            NULL, NULL,
            ?, ?, ?, ?, ?,
            ?, CURRENT_DATE, 'edge_candidates'
        )
    """

    conn.execute(insert_query, [
        setup_id,
        instrument,
        orb_time,
        rr,
        sl_mode,
        orb_size_filter,
        annual_trades,  # Use annual_trades as proxy for trades
        win_rate,
        avg_r,
        annual_trades,
        tier,
        notes_json
    ])

    return setup_id


def main():
    conn = get_database_connection(read_only=False)

    print("="*80)
    print("PROMOTE CANDIDATES 47-48 TO VALIDATED_SETUPS")
    print("="*80)
    print()

    setup_ids = []

    for candidate_id in [47, 48]:
        print(f"Promoting candidate {candidate_id}...")
        try:
            setup_id = promote_candidate(conn, candidate_id)
            print(f"  SUCCESS: Created setup_id={setup_id}")
            setup_ids.append(setup_id)
        except Exception as e:
            print(f"  FAILED: {e}")
            conn.close()
            sys.exit(1)

        print()

    # Commit
    conn.commit()

    print("="*80)
    print("PROMOTION COMPLETE")
    print("="*80)
    print()

    # Verify
    print("Verifying promotion in validated_setups...")
    query = """
        SELECT setup_id, instrument, orb_time, rr, sl_mode, win_rate, avg_r, tier
        FROM validated_setups
        WHERE setup_id IN (?, ?)
        ORDER BY setup_id
    """

    results = conn.execute(query, setup_ids).fetchall()

    print(f"Found {len(results)} promoted setups:")
    for row in results:
        setup_id, instrument, orb_time, rr, sl_mode, win_rate, avg_r, tier = row
        print(f"  {setup_id}: {instrument} {orb_time} RR={rr} {sl_mode} (WR={win_rate:.3f}, AvgR={avg_r:.3f}, Tier={tier})")

    print()

    if len(results) != 2:
        print(f"ERROR: Expected 2 setups, found {len(results)}")
        conn.close()
        sys.exit(1)

    print("OK Promotion verified - exactly 2 new setups created")

    conn.close()

if __name__ == "__main__":
    main()
