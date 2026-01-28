"""
AUTONOMOUS STRATEGY VALIDATOR - WITH TCA GATE
==============================================

Implements TCA.txt "20% Friction Cap" validation.

Reports TWO expectancy values per strategy:
1. RAW Expectancy (all trades, ignoring friction ratio)
2. TCA-ADJUSTED Expectancy (only trades with friction < 20%)

HONESTY OVER OUTCOME. NO ASSUMPTIONS.
"""

import duckdb
import sys

sys.path.insert(0, 'C:/Users/sydne/OneDrive/Desktop/MPX3')
from pipeline.cost_model import COST_MODELS
from pipeline.load_validated_setups import load_validated_setups

DB_PATH = 'data/db/gold.db'

# CANONICAL COST MODEL (MANDATORY)
MGC_COSTS = COST_MODELS['MGC']
MGC_POINT_VALUE = MGC_COSTS['point_value']
MGC_FRICTION = MGC_COSTS['total_friction']  # $8.40 RT

# TCA GATE (from text.txt)
MAX_FRICTION_RATIO = 0.20  # 20% cap
MIN_RISK_DOLLARS = 50.00   # $50 minimum

print("=" * 80)
print("AUTONOMOUS STRATEGY VALIDATOR - WITH TCA GATE")
print("=" * 80)
print()
print(f"Canonical Cost Model: ${MGC_FRICTION:.2f} RT (MANDATORY)")
print(f"Point Value: ${MGC_POINT_VALUE:.2f}")
print(f"TCA Gate: {MAX_FRICTION_RATIO:.0%} Friction Cap (${MIN_RISK_DOLLARS:.0f} min risk)")
print(f"Approval Threshold: +0.15R at ${MGC_FRICTION:.2f}")
print()
print("Methodology: RAW vs TCA-ADJUSTED Expectancy")
print("=" * 80)
print()

conn = duckdb.connect(DB_PATH)

# Get all strategies
strategies = load_validated_setups(conn, instrument='MGC')

print(f"Found {len(strategies)} strategies to validate")
print()


def calculate_expectancy(trades):
    """Calculate expectancy using realized_rr."""
    realized_r_values = []

    for trade in trades:
        outcome, realized_rr = trade

        if outcome in ['NO_TRADE', 'OPEN', 'RISK_TOO_SMALL'] or realized_rr is None:
            continue

        realized_r_values.append(realized_rr)

    return sum(realized_r_values) / len(realized_r_values) if realized_r_values else 0.0


# Store validation results
all_results = []

for strategy in strategies:
    setup_id = strategy['id']
    orb_time = strategy['orb_time']
    rr = strategy['rr']
    sl_mode = strategy['sl_mode']
    filter_val = strategy['filter']

    print("=" * 80)
    print(f"VALIDATING: ID {setup_id} | {orb_time} ORB RR={rr} {sl_mode}")
    if filter_val:
        print(f"Filter: ORB size >= {filter_val}")
    print("=" * 80)
    print()

    # Query ALL trades (RAW)
    raw_trades = conn.execute("""
        SELECT outcome, realized_rr
        FROM validated_trades
        WHERE setup_id = ?
          AND outcome IS NOT NULL
          AND outcome NOT IN ('NO_TRADE', 'RISK_TOO_SMALL')
        ORDER BY date_local
    """, [setup_id]).fetchall()

    # Query TCA-ADJUSTED trades (friction < 20%)
    tca_trades = conn.execute("""
        SELECT outcome, realized_rr
        FROM validated_trades
        WHERE setup_id = ?
          AND outcome IS NOT NULL
          AND outcome NOT IN ('NO_TRADE', 'RISK_TOO_SMALL')
          AND (friction_ratio IS NULL OR friction_ratio <= ?)
        ORDER BY date_local
    """, [setup_id, MAX_FRICTION_RATIO]).fetchall()

    print("=" * 80)
    print("TRADE COUNTS")
    print("=" * 80)
    print(f"RAW (all trades):        {len(raw_trades)} trades")
    print(f"TCA-ADJUSTED (<=20%):    {len(tca_trades)} trades")

    if len(raw_trades) > 0:
        filter_pct = ((len(raw_trades) - len(tca_trades)) / len(raw_trades)) * 100
        print(f"Filtered out:            {len(raw_trades) - len(tca_trades)} trades ({filter_pct:.1f}%)")
    print()

    # RAW EXPECTANCY
    print("=" * 80)
    print("RAW EXPECTANCY (All Trades)")
    print("=" * 80)

    raw_wins = sum(1 for t in raw_trades if t[0] == 'WIN')
    raw_losses = sum(1 for t in raw_trades if t[0] == 'LOSS')
    raw_open = sum(1 for t in raw_trades if t[0] == 'OPEN')
    raw_resolved = raw_wins + raw_losses

    print(f"Total: {len(raw_trades)} | WIN: {raw_wins} | LOSS: {raw_losses} | OPEN: {raw_open}")
    print(f"Resolved: {raw_resolved}")

    if raw_resolved >= 30:
        raw_exp = calculate_expectancy(raw_trades)
        print(f"Expectancy: {raw_exp:+.3f}R")
        raw_status = "PASS" if raw_exp >= 0.15 else "FAIL"
        print(f"Status: {raw_status} ({'+0.15R threshold'})")
    else:
        raw_exp = None
        print(f"Status: INSUFFICIENT SAMPLE (< 30 trades)")
    print()

    # TCA-ADJUSTED EXPECTANCY
    print("=" * 80)
    print(f"TCA-ADJUSTED EXPECTANCY (Friction <= {MAX_FRICTION_RATIO:.0%})")
    print("=" * 80)

    tca_wins = sum(1 for t in tca_trades if t[0] == 'WIN')
    tca_losses = sum(1 for t in tca_trades if t[0] == 'LOSS')
    tca_open = sum(1 for t in tca_trades if t[0] == 'OPEN')
    tca_resolved = tca_wins + tca_losses

    print(f"Total: {len(tca_trades)} | WIN: {tca_wins} | LOSS: {tca_losses} | OPEN: {tca_open}")
    print(f"Resolved: {tca_resolved}")

    if tca_resolved >= 30:
        tca_exp = calculate_expectancy(tca_trades)
        print(f"Expectancy: {tca_exp:+.3f}R")
        tca_status = "APPROVED" if tca_exp >= 0.15 else "REJECTED"
        print(f"Status: {tca_status} ({'+0.15R threshold'})")
    else:
        tca_exp = None
        tca_status = "INSUFFICIENT_SAMPLE"
        print(f"Status: INSUFFICIENT SAMPLE (< 30 trades after TCA filter)")
    print()

    # VERDICT
    print("=" * 80)
    print("VERDICT")
    print("=" * 80)

    if tca_status == "APPROVED":
        print(f"[APPROVED] Passes +0.15R with TCA gate: {tca_exp:+.3f}R")
        verdict = "APPROVED"
    elif tca_status == "INSUFFICIENT_SAMPLE":
        print(f"[REJECTED] Insufficient sample after TCA filter (< 30 trades)")
        verdict = "REJECTED"
    else:
        print(f"[REJECTED] Below +0.15R threshold: {tca_exp:+.3f}R")
        verdict = "REJECTED"

    print()

    all_results.append({
        'id': setup_id,
        'orb_time': orb_time,
        'rr': rr,
        'raw_trades': len(raw_trades),
        'tca_trades': len(tca_trades),
        'filter_pct': filter_pct if len(raw_trades) > 0 else 0,
        'raw_exp': raw_exp,
        'raw_resolved': raw_resolved,
        'tca_exp': tca_exp,
        'tca_resolved': tca_resolved,
        'tca_wins': tca_wins,
        'tca_losses': tca_losses,
        'verdict': verdict
    })

conn.close()

# =============================================================================
# SUMMARY
# =============================================================================
print()
print("=" * 80)
print("VALIDATION SUMMARY")
print("=" * 80)
print()

approved = [r for r in all_results if r['verdict'] == 'APPROVED']
rejected = [r for r in all_results if r['verdict'] == 'REJECTED']

print(f"APPROVED (pass +0.15R with TCA gate): {len(approved)}")
for r in approved:
    print(f"  ID {r['id']}: {r['orb_time']} RR={r['rr']}")
    print(f"    RAW: {r['raw_exp']:+.3f}R ({r['raw_resolved']} trades)")
    print(f"    TCA: {r['tca_exp']:+.3f}R ({r['tca_resolved']} trades, {r['filter_pct']:.1f}% filtered)")

print()
print(f"REJECTED (fail +0.15R or insufficient sample): {len(rejected)}")
for r in rejected:
    raw_str = f"{r['raw_exp']:+.3f}R" if r['raw_exp'] is not None else "N/A"
    tca_str = f"{r['tca_exp']:+.3f}R" if r['tca_exp'] is not None else "N/A"
    print(f"  ID {r['id']}: {r['orb_time']} RR={r['rr']}")
    print(f"    RAW: {raw_str} ({r['raw_resolved']} trades)")
    print(f"    TCA: {tca_str} ({r['tca_resolved']} trades, {r['filter_pct']:.1f}% filtered)")

print()
print("=" * 80)
print("KEY INSIGHTS")
print("=" * 80)
print()
print("TCA.txt Principle: 'Cost impact must be measured relative to stop distance'")
print()
print("If strategies still FAIL after TCA gate:")
print("  - ORB breakouts may not have edge on MGC")
print("  - Need different approach (filters, timing, or strategy type)")
print("  - NOT a cost model issue - professional risk management in action")
print()
print("HONESTY OVER OUTCOME.")
print()
