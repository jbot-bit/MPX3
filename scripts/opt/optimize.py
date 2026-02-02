"""
OPTUNA CLI OPTIMIZATION ORCHESTRATOR

Deterministic, fail-closed optimization using Optuna.
Consumes ONLY BacktestResult fields: avg_r, win_rate, max_dd_R, survives_stress.
NO derived metrics. NO peeking into trades. NO logic changes.

Usage:
    python -m scripts.opt.optimize --dry-run --study test1 --instrument MGC --orb 1000
    python -m scripts.opt.optimize --run 50 --seed 123 --study test1 --instrument MGC --orb 1000
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

# Optuna import (fail-closed if missing)
try:
    import optuna
    from optuna.samplers import TPESampler
except ImportError:
    print("ERROR: optuna not installed. Run: pip install optuna")
    sys.exit(1)

# Add project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "trading_app"))

from strategy_discovery import StrategyDiscovery, DiscoveryConfig, BacktestResult

# Paths
OPTUNA_DIR = PROJECT_ROOT / "artifacts" / "optuna"
OPTUNA_DIR.mkdir(parents=True, exist_ok=True)


def compute_config_hash(instrument: str, orb_times: list, rr_range: tuple, filter_range: tuple, seed: int) -> str:
    """Compute deterministic hash for study configuration."""
    config_str = f"{instrument}|{sorted(orb_times)}|{rr_range}|{filter_range}|{seed}"
    return hashlib.sha256(config_str.encode()).hexdigest()[:16]


def get_study_paths(study_name: str):
    """Get paths for study artifacts."""
    return {
        "db": OPTUNA_DIR / f"{study_name}.db",
        "trials": OPTUNA_DIR / f"{study_name}_trials.jsonl",
        "meta": OPTUNA_DIR / f"{study_name}_meta.json",
        "summary": OPTUNA_DIR / f"{study_name}_summary.json"
    }


def log_trial(paths: dict, trial_num: int, config: DiscoveryConfig, result: BacktestResult,
              pruned: bool = False, prune_reason: str = None):
    """Append trial to JSONL log (fail-silent)."""
    try:
        entry = {
            "trial": trial_num,
            "logged_at": datetime.utcnow().isoformat() + "Z",
            "config": {
                "instrument": config.instrument,
                "orb_time": config.orb_time,
                "rr": config.rr,
                "sl_mode": config.sl_mode,
                "orb_size_filter": config.orb_size_filter
            },
            # ONLY BacktestResult fields - no derived metrics
            "avg_r": result.avg_r if result else None,
            "win_rate": result.win_rate if result else None,
            "max_dd_R": result.max_dd_R if result else None,
            "survives_stress": result.survives_stress if result else None,
            "total_trades": result.total_trades if result else 0,
            "pruned": pruned,
            "prune_reason": prune_reason
        }
        with open(paths["trials"], "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # Fail-silent logging


def create_objective(discovery: StrategyDiscovery, instrument: str, orb_time: str, paths: dict):
    """
    Create Optuna objective function.

    CONSTRAINT: Uses ONLY BacktestResult fields:
    - avg_r
    - win_rate
    - max_dd_R
    - survives_stress

    NO derived metrics. NO peeking into trades.
    """
    def objective(trial: optuna.Trial) -> float:
        # Sample parameters
        rr = trial.suggest_float("rr", 1.0, 8.0, step=0.5)
        sl_mode = trial.suggest_categorical("sl_mode", ["FULL", "HALF"])
        use_filter = trial.suggest_categorical("use_filter", [True, False])
        orb_size_filter = trial.suggest_float("orb_size_filter", 0.05, 0.20, step=0.01) if use_filter else None

        config = DiscoveryConfig(
            instrument=instrument,
            orb_time=orb_time,
            rr=rr,
            sl_mode=sl_mode,
            orb_size_filter=orb_size_filter
        )

        try:
            result = discovery.backtest_configuration(config)
        except Exception as e:
            log_trial(paths, trial.number, config, None, pruned=True, prune_reason=f"error:{str(e)[:50]}")
            return -999.0  # Penalize errors

        # PRUNE: insufficient trades
        if result.total_trades < 30:
            log_trial(paths, trial.number, config, result, pruned=True, prune_reason="insufficient_trades")
            raise optuna.TrialPruned()

        # PRUNE: strong negative avg_r early
        if result.avg_r < -0.1:
            log_trial(paths, trial.number, config, result, pruned=True, prune_reason="negative_avg_r")
            raise optuna.TrialPruned()

        # Log successful trial
        log_trial(paths, trial.number, config, result)

        # OBJECTIVE: avg_r (ONLY from BacktestResult, no derivation)
        return result.avg_r

    return objective


def run_optimization(args):
    """Run Optuna optimization."""
    paths = get_study_paths(args.study)
    config_hash = compute_config_hash(args.instrument, [args.orb], (1.0, 8.0), (0.05, 0.20), args.seed)

    # Check for existing study with mismatched config
    if paths["meta"].exists():
        with open(paths["meta"]) as f:
            meta = json.load(f)
        if meta.get("config_hash") != config_hash:
            print(f"FAIL-CLOSED: Study '{args.study}' exists with different config.")
            print(f"  Existing hash: {meta.get('config_hash')}")
            print(f"  New hash: {config_hash}")
            print("Delete existing study files or use a different study name.")
            sys.exit(1)
        print(f"Resuming study '{args.study}' (hash: {config_hash})")
    else:
        # Save meta for new study
        meta = {
            "study_name": args.study,
            "config_hash": config_hash,
            "instrument": args.instrument,
            "orb_time": args.orb,
            "seed": args.seed,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        with open(paths["meta"], "w") as f:
            json.dump(meta, f, indent=2)
        print(f"Created new study '{args.study}' (hash: {config_hash})")

    # Create/load Optuna study
    storage = f"sqlite:///{paths['db']}"
    sampler = TPESampler(seed=args.seed)

    study = optuna.create_study(
        study_name=args.study,
        storage=storage,
        sampler=sampler,
        direction="maximize",
        load_if_exists=True
    )

    # Initialize discovery engine
    discovery = StrategyDiscovery()
    objective = create_objective(discovery, args.instrument, args.orb, paths)

    print(f"\nRunning {args.run} trials for {args.instrument} ORB {args.orb}...")
    print(f"Storage: {paths['db']}")
    print(f"Trials log: {paths['trials']}")
    print()

    # Run optimization
    study.optimize(objective, n_trials=args.run, show_progress_bar=True)

    # Print summary
    print(f"\n{'='*60}")
    print(f"OPTIMIZATION COMPLETE")
    print(f"{'='*60}")
    print(f"Best avg_r: {study.best_value:.4f}")
    print(f"Best params: {study.best_params}")
    print(f"Total trials: {len(study.trials)}")

    # Save summary
    summary = {
        "study_name": args.study,
        "completed_at": datetime.utcnow().isoformat() + "Z",
        "total_trials": len(study.trials),
        "best_value": study.best_value,
        "best_params": study.best_params
    }
    with open(paths["summary"], "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved to: {paths['summary']}")


def dry_run(args):
    """Print planned trials without execution."""
    paths = get_study_paths(args.study)
    config_hash = compute_config_hash(args.instrument, [args.orb], (1.0, 8.0), (0.05, 0.20), args.seed)

    print(f"{'='*60}")
    print(f"DRY RUN - Optuna Optimization Plan")
    print(f"{'='*60}")
    print(f"Study name: {args.study}")
    print(f"Config hash: {config_hash}")
    print(f"Instrument: {args.instrument}")
    print(f"ORB time: {args.orb}")
    print(f"Seed: {args.seed}")
    print()
    print("Search space:")
    print("  rr: [1.0, 8.0] step=0.5")
    print("  sl_mode: [FULL, HALF]")
    print("  orb_size_filter: None or [0.05, 0.20] step=0.01")
    print()
    print("Pruning rules:")
    print("  - Prune if total_trades < 30")
    print("  - Prune if avg_r < -0.1")
    print()
    print("Objective: maximize avg_r (BacktestResult field only)")
    print()
    print(f"Output paths:")
    print(f"  DB: {paths['db']}")
    print(f"  Trials: {paths['trials']}")
    print(f"  Meta: {paths['meta']}")
    print(f"  Summary: {paths['summary']}")
    print()
    print("To execute, run:")
    print(f"  python -m scripts.opt.optimize --run N --seed {args.seed} --study {args.study} --instrument {args.instrument} --orb {args.orb}")


def main():
    parser = argparse.ArgumentParser(description="Optuna CLI Optimization Orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without execution")
    parser.add_argument("--run", type=int, default=0, help="Number of trials to run")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--study", type=str, required=True, help="Study name")
    parser.add_argument("--instrument", type=str, default="MGC", help="Instrument (MGC, NQ, MPL)")
    parser.add_argument("--orb", type=str, default="1000", help="ORB time (0900, 1000, etc.)")

    args = parser.parse_args()

    if args.dry_run:
        dry_run(args)
    elif args.run > 0:
        run_optimization(args)
    else:
        parser.print_help()
        print("\nError: Must specify --dry-run or --run N")
        sys.exit(1)


if __name__ == "__main__":
    main()
