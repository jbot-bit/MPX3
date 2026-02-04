#!/usr/bin/env python3
"""
Restore candidate 48 to validated_setups
(It was incorrectly deleted due to architectural misunderstanding)
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trading_app.cloud_mode import get_database_connection

def promote_candidate(conn, candidate_id, actor="claude_architecture_fix"):
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
        "promoted_at": datetime.utcnow().isoformat(),
        "restored": True,
        "restore_reason": "Incorrectly deleted due to architectural misunderstanding"
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
    print("RESTORE CANDIDATE 48 TO validated_setups")
    print("="*80)
    print()

    print("Promoting candidate 48...")
    try:
        setup_id = promote_candidate(conn, 48)
        print(f"  SUCCESS: Created setup_id={setup_id}")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback
        traceback.print_exc()
        conn.close()
        sys.exit(1)

    print()

    # Commit
    conn.commit()

    print("="*80)
    print("RESTORATION COMPLETE")
    print("="*80)
    print()

    # Verify both 47 and 48 now exist
    print("Verifying both candidates 47 and 48 in validated_setups...")
    query = """
        SELECT setup_id, instrument, orb_time, rr, sl_mode, win_rate, avg_r, tier
        FROM validated_setups
        WHERE setup_id LIKE 'MGC_1000_04%'
        ORDER BY setup_id
    """

    results = conn.execute(query).fetchall()

    print(f"Found {len(results)} MGC 1000 setups:")
    for row in results:
        setup_id, instrument, orb_time, rr, sl_mode, win_rate, avg_r, tier = row
        print(f"  {setup_id}: {instrument} {orb_time} RR={rr} {sl_mode} (WR={win_rate:.3f}, AvgR={avg_r:.3f}, Tier={tier})")

    print()

    if len(results) != 2:
        print(f"ERROR: Expected 2 setups, found {len(results)}")
        conn.close()
        sys.exit(1)

    print("OK Both candidates 47 and 48 now exist in validated_setups")

    conn.close()

if __name__ == "__main__":
    main()
