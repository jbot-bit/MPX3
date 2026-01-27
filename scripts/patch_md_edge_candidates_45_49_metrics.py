#!/usr/bin/env python3
"""
Patch MotherDuck edge_candidates 45-49 with correct win_rate values
from asia_results_365d.csv

DATA INTEGRITY PATCH ONLY - Does not change strategy logic or backtest logic.
"""

import sys
import json
import pandas as pd
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trading_app.cloud_mode import get_database_connection

# Source of truth
root = Path(__file__).parent.parent
csv_path = root / "research" / "quick_asia" / "research" / "quick_asia" / "asia_results_365d.csv"

# Candidate mapping (orb_time as int to match CSV)
CANDIDATE_CONFIGS = {
    45: {"orb_time": 900, "rr": 2.0, "sl_mode": "HALF"},
    46: {"orb_time": 900, "rr": 3.0, "sl_mode": "HALF"},
    47: {"orb_time": 1000, "rr": 1.0, "sl_mode": "FULL"},
    48: {"orb_time": 1000, "rr": 2.0, "sl_mode": "HALF"},
    49: {"orb_time": 1000, "rr": 1.5, "sl_mode": "FULL"},
}


def load_correct_metrics_from_csv():
    """Load correct metrics from asia_results_365d.csv."""
    df = pd.read_csv(csv_path)

    # Filter for ISOLATION mode only
    df = df[df['mode'] == 'ISOLATION']

    correct_metrics = {}

    for candidate_id, config in CANDIDATE_CONFIGS.items():
        # Find matching row
        match = df[
            (df['orb_time'] == config['orb_time']) &
            (df['rr'] == config['rr']) &
            (df['sl_mode'] == config['sl_mode'])
        ]

        if len(match) == 0:
            print(f"ERROR: No match found in CSV for candidate {candidate_id}")
            print(f"  Config: {config}")
            sys.exit(1)

        if len(match) > 1:
            print(f"ERROR: Multiple matches found in CSV for candidate {candidate_id}")
            sys.exit(1)

        row = match.iloc[0]

        correct_metrics[candidate_id] = {
            "trades": int(row['trades']),
            "win_rate": float(row['win_rate']),
            "avg_r": float(row['avg_r']),
            "total_r": float(row['total_r']),
        }

    return correct_metrics


def main():
    print("="*80)
    print("PATCH MOTHERDUCK EDGE_CANDIDATES 45-49 METRICS")
    print("="*80)
    print()

    # Load correct metrics from CSV
    print("Loading correct metrics from asia_results_365d.csv...")
    correct_metrics = load_correct_metrics_from_csv()

    print("Correct metrics (from CSV):")
    for cid, metrics in correct_metrics.items():
        print(f"  Candidate {cid}: trades={metrics['trades']}, win_rate={metrics['win_rate']:.6f}, avg_r={metrics['avg_r']:.6f}, total_r={metrics['total_r']:.2f}")
    print()

    # Connect to MotherDuck
    print("Connecting to MotherDuck...")
    conn = get_database_connection(read_only=False)

    # Fetch current state
    query = """
        SELECT candidate_id, name, metrics_json
        FROM edge_candidates
        WHERE candidate_id BETWEEN 45 AND 49
        ORDER BY candidate_id
    """

    current_rows = conn.execute(query).fetchall()

    if len(current_rows) != 5:
        print(f"ERROR: Expected 5 rows, found {len(current_rows)}")
        print("STOP: Schema ambiguity or missing candidates")
        sys.exit(1)

    print("="*80)
    print("BEFORE STATE (MotherDuck)")
    print("="*80)
    print()

    before_state = []

    for row in current_rows:
        candidate_id, name, metrics_json_str = row

        if metrics_json_str:
            metrics = json.loads(metrics_json_str)
            current_365d = metrics.get('365d', {})

            print(f"Candidate {candidate_id}: {name}")
            print(f"  Current 365d metrics:")
            print(f"    trades: {current_365d.get('trades', 'N/A')}")
            print(f"    win_rate: {current_365d.get('win_rate', 'N/A')}")
            print(f"    avg_r: {current_365d.get('avg_r', 'N/A')}")
            print(f"    total_r: {current_365d.get('total_r', 'N/A')}")
            print()

            before_state.append({
                "candidate_id": candidate_id,
                "name": name,
                "current_365d": current_365d.copy(),
                "metrics": metrics,
            })
        else:
            print(f"Candidate {candidate_id}: {name}")
            print(f"  ERROR: No metrics_json found")
            print("STOP: Missing metrics")
            sys.exit(1)

    # Patch metrics
    print("="*80)
    print("PATCHING METRICS")
    print("="*80)
    print()

    updated_count = 0

    for state in before_state:
        candidate_id = state['candidate_id']
        correct = correct_metrics[candidate_id]
        current_365d = state['current_365d']

        print(f"Candidate {candidate_id}:")
        print(f"  BEFORE: win_rate={current_365d.get('win_rate', 'N/A')}")
        print(f"  AFTER:  win_rate={correct['win_rate']:.6f}")

        # Update metrics_json
        updated_metrics = state['metrics'].copy()

        # Update 365d section
        updated_metrics['365d'] = {
            "trades": correct['trades'],
            "win_rate": correct['win_rate'],
            "avg_r": correct['avg_r'],
            "total_r": correct['total_r'],
        }

        # Add provenance note to source_notes if it exists
        if 'source_notes' in updated_metrics:
            if 'metrics patched' not in updated_metrics['source_notes']:
                updated_metrics['source_notes'] += ' | metrics patched to match asia_results_365d.csv (365d)'

        # Convert to JSON
        updated_metrics_json = json.dumps(updated_metrics)

        # Update in database
        update_query = """
            UPDATE edge_candidates
            SET metrics_json = ?::JSON
            WHERE candidate_id = ?
        """

        conn.execute(update_query, [updated_metrics_json, candidate_id])
        updated_count += 1

        print(f"  OK Updated")
        print()

    # Commit changes
    conn.commit()

    # Assert exactly 5 rows updated
    if updated_count != 5:
        print(f"ERROR: Expected to update 5 rows, but updated {updated_count}")
        print("STOP: Update count mismatch")
        sys.exit(1)

    print(f"OK Successfully updated {updated_count} rows")
    print()

    # Fetch AFTER state
    print("="*80)
    print("AFTER STATE (MotherDuck)")
    print("="*80)
    print()

    after_rows = conn.execute(query).fetchall()

    for row in after_rows:
        candidate_id, name, metrics_json_str = row

        metrics = json.loads(metrics_json_str)
        updated_365d = metrics.get('365d', {})

        print(f"Candidate {candidate_id}: {name}")
        print(f"  Updated 365d metrics:")
        print(f"    trades: {updated_365d.get('trades', 'N/A')}")
        print(f"    win_rate: {updated_365d.get('win_rate', 'N/A')}")
        print(f"    avg_r: {updated_365d.get('avg_r', 'N/A')}")
        print(f"    total_r: {updated_365d.get('total_r', 'N/A')}")
        print()

    conn.close()

    print("="*80)
    print("PATCH COMPLETE")
    print("="*80)
    print()
    print("OK 5 candidates updated with correct metrics from CSV")
    print("OK All win_rate values now match asia_results_365d.csv")
    print()
    print("Next step: Re-run verification")
    print("  python scripts/verify_asia_candidates_45_49_backtest.py")
    print()


if __name__ == "__main__":
    main()
