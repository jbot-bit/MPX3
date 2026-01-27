#!/usr/bin/env python3
"""
Reproduce 365-day backtest for Asia ORB candidates 45-49
Compare computed metrics vs target metrics from test16.txt
"""

import sys
from pathlib import Path
from datetime import date

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Asia backtest engine
from research.quick_asia.asia_backtest_core import compute_orb_levels, simulate_orb_breakout, compute_metrics

import duckdb

# Database path (local gold.db for bar data)
root = Path(__file__).parent.parent
db_path = root / "data" / "db" / "gold.db"

# Target metrics from asia_results_365d.csv (corrected)
TARGET_METRICS = {
    45: {"trades": 254, "win_rate": 0.378, "avg_r": 0.099, "total_r": 25.2},
    46: {"trades": 254, "win_rate": 0.299, "avg_r": 0.097, "total_r": 24.6},
    47: {"trades": 257, "win_rate": 0.529, "avg_r": 0.055, "total_r": 14.2},
    48: {"trades": 257, "win_rate": 0.354, "avg_r": 0.054, "total_r": 13.8},
    49: {"trades": 257, "win_rate": 0.444, "avg_r": 0.084, "total_r": 21.5},
}

# Tolerance (from test16.txt)
TOLERANCE = {
    "trades": 0,  # Must match exactly
    "win_rate": 0.005,  # ± 0.005 absolute
    "avg_r": 0.01,  # ± 0.01
    "total_r": 1.0,  # ± 1.0
}

# Candidate configurations
CANDIDATE_CONFIGS = {
    45: {"orb_time": "0900", "rr": 2.0, "sl_mode": "HALF", "scan_end": ("11", "00")},
    46: {"orb_time": "0900", "rr": 3.0, "sl_mode": "HALF", "scan_end": ("11", "00")},
    47: {"orb_time": "1000", "rr": 1.0, "sl_mode": "FULL", "scan_end": ("12", "00")},
    48: {"orb_time": "1000", "rr": 2.0, "sl_mode": "HALF", "scan_end": ("12", "00")},
    49: {"orb_time": "1000", "rr": 1.5, "sl_mode": "FULL", "scan_end": ("12", "00")},
}


def get_all_trading_days(conn, instrument, min_days=365):
    """Get maximum available trading days (up to min_days)."""
    query = """
        SELECT DISTINCT date_local
        FROM daily_features
        WHERE instrument = ?
        AND date_local >= '2024-01-02'
        ORDER BY date_local DESC
        LIMIT ?
    """
    result = conn.execute(query, [instrument, min_days]).fetchall()
    dates = [row[0] for row in result]
    return sorted(dates)


def run_candidate_backtest(conn, candidate_id, config, trading_days):
    """Run backtest for a single candidate."""
    orb_time = config["orb_time"]
    rr = config["rr"]
    sl_mode = config["sl_mode"]
    scan_end_hour, scan_end_min = config["scan_end"]

    # Parse ORB time
    orb_hour = int(orb_time[:2])
    orb_min = int(orb_time[2:])
    scan_end_hour = int(scan_end_hour)
    scan_end_min = int(scan_end_min)

    all_trades = []

    for trading_date in trading_days:
        # Convert date_local string to date object
        if isinstance(trading_date, str):
            trading_date = date.fromisoformat(trading_date)

        # Compute ORB
        orb_result = compute_orb_levels(conn, trading_date, orb_hour, orb_min, orb_duration_min=5)

        if orb_result is None:
            continue

        # Simulate trade
        trade_result = simulate_orb_breakout(
            conn,
            trading_date,
            orb_result,
            orb_hour,
            orb_min,
            scan_end_hour,
            scan_end_min,
            rr,
            sl_mode,
            mode="ISOLATION"
        )

        if trade_result:
            all_trades.append(trade_result)

    # Compute metrics
    metrics = compute_metrics(all_trades)

    return {
        "candidate_id": candidate_id,
        "trades": metrics["trades"],
        "win_rate": metrics["win_rate"],
        "avg_r": metrics["avg_r"],
        "total_r": metrics["total_r"],
        "trades_list": all_trades,
    }


def check_metric(name, computed, target, tolerance):
    """Check if metric is within tolerance."""
    if tolerance == 0:
        return computed == target
    else:
        return abs(computed - target) <= tolerance


def main():
    conn = duckdb.connect(str(db_path), read_only=True)

    print("="*80)
    print("VERIFY ASIA CANDIDATES 45-49: 365-DAY BACKTEST")
    print("="*80)
    print()

    # Get all trading days
    all_days = get_all_trading_days(conn, "MGC", 365)
    print(f"Total trading days: {len(all_days)}")
    print(f"Date range: {min(all_days)} to {max(all_days)}")
    print()

    # Run backtests for all candidates
    results = []
    verification_results = []

    for candidate_id, config in CANDIDATE_CONFIGS.items():
        print(f"Running backtest for candidate {candidate_id}...")
        print(f"  Config: {config['orb_time']} ORB, RR={config['rr']}, SL={config['sl_mode']}")

        result = run_candidate_backtest(conn, candidate_id, config, all_days)
        results.append(result)

        # Verify metrics
        target = TARGET_METRICS[candidate_id]

        trades_ok = check_metric("trades", result["trades"], target["trades"], TOLERANCE["trades"])
        win_rate_ok = check_metric("win_rate", result["win_rate"], target["win_rate"], TOLERANCE["win_rate"])
        avg_r_ok = check_metric("avg_r", result["avg_r"], target["avg_r"], TOLERANCE["avg_r"])
        total_r_ok = check_metric("total_r", result["total_r"], target["total_r"], TOLERANCE["total_r"])

        all_pass = trades_ok and win_rate_ok and avg_r_ok and total_r_ok

        verification_results.append({
            "candidate_id": candidate_id,
            "config": config,
            "computed": result,
            "target": target,
            "trades_ok": trades_ok,
            "win_rate_ok": win_rate_ok,
            "avg_r_ok": avg_r_ok,
            "total_r_ok": total_r_ok,
            "all_pass": all_pass,
        })

        status = "PASS" if all_pass else "FAIL"
        print(f"  Status: {status}")
        print(f"  Computed: trades={result['trades']}, win_rate={result['win_rate']:.3f}, avg_r={result['avg_r']:.3f}, total_r={result['total_r']:.1f}")
        print(f"  Target:   trades={target['trades']}, win_rate={target['win_rate']:.3f}, avg_r={target['avg_r']:.3f}, total_r={target['total_r']:.1f}")
        print()

    conn.close()

    # Generate verification report
    lines = []
    lines.append("# VERIFY ASIA CANDIDATES 45-49: 365-DAY BACKTEST")
    lines.append("")
    lines.append(f"**Date**: {date.today().isoformat()}")
    lines.append(f"**Trading Days**: {len(all_days)}")
    lines.append(f"**Date Range**: {min(all_days)} to {max(all_days)}")
    lines.append("")
    lines.append("## Verification Results")
    lines.append("")

    # Summary table
    lines.append("| Candidate | Config | Trades | Win Rate | Avg R | Total R | Status |")
    lines.append("|-----------|--------|--------|----------|-------|---------|--------|")

    all_passed = True
    for vr in verification_results:
        cid = vr["candidate_id"]
        cfg = vr["config"]
        comp = vr["computed"]
        tgt = vr["target"]
        status = "PASS" if vr["all_pass"] else "FAIL"

        if not vr["all_pass"]:
            all_passed = False

        config_str = f"{cfg['orb_time']} RR{cfg['rr']} {cfg['sl_mode']}"

        # Mark metrics that failed
        trades_str = str(comp["trades"])
        if not vr["trades_ok"]:
            trades_str += f" (exp {tgt['trades']})"

        wr_str = f"{comp['win_rate']:.3f}"
        if not vr["win_rate_ok"]:
            wr_str += f" (exp {tgt['win_rate']:.3f})"

        avgr_str = f"{comp['avg_r']:.3f}"
        if not vr["avg_r_ok"]:
            avgr_str += f" (exp {tgt['avg_r']:.3f})"

        totalr_str = f"{comp['total_r']:.1f}"
        if not vr["total_r_ok"]:
            totalr_str += f" (exp {tgt['total_r']:.1f})"

        lines.append(f"| {cid} | {config_str} | {trades_str} | {wr_str} | {avgr_str} | {totalr_str} | {status} |")

    lines.append("")

    # Overall result
    if all_passed:
        lines.append("## Overall Result: PASS")
        lines.append("")
        lines.append("All candidates passed verification. Metrics match target within tolerance.")
    else:
        lines.append("## Overall Result: FAIL")
        lines.append("")
        lines.append("One or more candidates failed verification. Metrics do not match target within tolerance.")

    lines.append("")

    # Detailed results
    lines.append("## Detailed Results")
    lines.append("")

    for vr in verification_results:
        cid = vr["candidate_id"]
        cfg = vr["config"]
        comp = vr["computed"]
        tgt = vr["target"]

        lines.append(f"### Candidate {cid}: {cfg['orb_time']} ORB RR={cfg['rr']} {cfg['sl_mode']}")
        lines.append("")
        lines.append("**Computed Metrics**:")
        lines.append(f"- Trades: {comp['trades']}")
        lines.append(f"- Win Rate: {comp['win_rate']:.3f}")
        lines.append(f"- Avg R: {comp['avg_r']:.3f}")
        lines.append(f"- Total R: {comp['total_r']:.1f}")
        lines.append("")
        lines.append("**Target Metrics**:")
        lines.append(f"- Trades: {tgt['trades']}")
        lines.append(f"- Win Rate: {tgt['win_rate']:.3f}")
        lines.append(f"- Avg R: {tgt['avg_r']:.3f}")
        lines.append(f"- Total R: {tgt['total_r']:.1f}")
        lines.append("")
        lines.append("**Verification**:")
        lines.append(f"- Trades: {'PASS' if vr['trades_ok'] else 'FAIL'}")
        lines.append(f"- Win Rate: {'PASS' if vr['win_rate_ok'] else 'FAIL'}")
        lines.append(f"- Avg R: {'PASS' if vr['avg_r_ok'] else 'FAIL'}")
        lines.append(f"- Total R: {'PASS' if vr['total_r_ok'] else 'FAIL'}")
        lines.append("")
        lines.append(f"**Overall: {'PASS' if vr['all_pass'] else 'FAIL'}**")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Save report
    output_path = root / "research" / "quick_asia" / "VERIFY_ASIA_45_49.md"
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))

    print("="*80)
    print("VERIFICATION COMPLETE")
    print("="*80)
    print()
    print(f"Overall result: {'PASS' if all_passed else 'FAIL'}")
    print(f"Report saved to: {output_path}")
    print()

    if not all_passed:
        print("WARNING: One or more candidates failed verification!")
        print("Review the report for details.")
        sys.exit(1)
    else:
        print("All candidates passed verification!")
        sys.exit(0)


if __name__ == "__main__":
    main()
