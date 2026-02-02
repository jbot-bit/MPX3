"""
OPTUNA STUDY SUMMARIZER

Read study artifacts and produce summary report.

Usage:
    python -m scripts.opt.summarize --study test1
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
OPTUNA_DIR = PROJECT_ROOT / "artifacts" / "optuna"


def summarize_study(study_name: str):
    """Summarize an Optuna study from its artifacts."""
    paths = {
        "db": OPTUNA_DIR / f"{study_name}.db",
        "trials": OPTUNA_DIR / f"{study_name}_trials.jsonl",
        "meta": OPTUNA_DIR / f"{study_name}_meta.json",
        "summary": OPTUNA_DIR / f"{study_name}_summary.json"
    }

    # Check study exists
    if not paths["meta"].exists():
        print(f"ERROR: Study '{study_name}' not found.")
        print(f"Expected meta file: {paths['meta']}")
        sys.exit(1)

    # Load meta
    with open(paths["meta"]) as f:
        meta = json.load(f)

    print(f"{'='*60}")
    print(f"STUDY SUMMARY: {study_name}")
    print(f"{'='*60}")
    print(f"Config hash: {meta.get('config_hash')}")
    print(f"Instrument: {meta.get('instrument')}")
    print(f"ORB time: {meta.get('orb_time')}")
    print(f"Seed: {meta.get('seed')}")
    print(f"Created: {meta.get('created_at')}")
    print()

    # Load trials
    if paths["trials"].exists():
        trials = []
        with open(paths["trials"]) as f:
            for line in f:
                trials.append(json.loads(line))

        completed = [t for t in trials if not t.get("pruned")]
        pruned = [t for t in trials if t.get("pruned")]

        print(f"Total trials: {len(trials)}")
        print(f"  Completed: {len(completed)}")
        print(f"  Pruned: {len(pruned)}")
        print()

        if completed:
            # Sort by avg_r
            completed.sort(key=lambda x: x.get("avg_r", -999), reverse=True)

            print("TOP 5 TRIALS (by avg_r):")
            print("-" * 60)
            for i, t in enumerate(completed[:5], 1):
                cfg = t.get("config", {})
                print(f"{i}. avg_r={t.get('avg_r', 0):+.4f} | "
                      f"RR={cfg.get('rr')} SL={cfg.get('sl_mode')} "
                      f"Filter={cfg.get('orb_size_filter')} | "
                      f"Trades={t.get('total_trades')}")
            print()

        if pruned:
            # Count prune reasons
            reasons = {}
            for t in pruned:
                reason = t.get("prune_reason", "unknown")
                reasons[reason] = reasons.get(reason, 0) + 1

            print("PRUNE REASONS:")
            for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
                print(f"  {reason}: {count}")
            print()

    # Load final summary if exists
    if paths["summary"].exists():
        with open(paths["summary"]) as f:
            summary = json.load(f)
        print("BEST RESULT:")
        print(f"  avg_r: {summary.get('best_value', 'N/A')}")
        print(f"  params: {summary.get('best_params', {})}")
    else:
        print("(No final summary yet - study may still be running)")


def main():
    parser = argparse.ArgumentParser(description="Summarize Optuna study")
    parser.add_argument("--study", type=str, required=True, help="Study name")

    args = parser.parse_args()
    summarize_study(args.study)


if __name__ == "__main__":
    main()
