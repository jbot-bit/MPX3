#!/usr/bin/env python3
"""
Populate Realized Metrics from Phase 1 Analysis Results

Uses pre-calculated results from theoretical_vs_realized_analysis.py
instead of deriving from daily_features (which only has RR=1.0 data).

Data source: Phase 1 validation results
Target: validated_setups table
"""

import duckdb

DB_PATH = "gold.db"

# Phase 1 Analysis Results (from theoretical_vs_realized_analysis.py)
# These were calculated by running execution_engine with specific RR values
PHASE1_RESULTS = {
    # (instrument, orb_time, rr): {realized_rr, realized_expectancy, win_rate, ...}
    ('MGC', '0900', 1.5): {
        'win_rate': 62.3,
        'theoretical_rr': 1.5,
        'realized_rr': 0.998,
        'theoretical_expectancy': 0.120,
        'realized_expectancy': 0.245,
        'sample_size': 53
    },
    ('MGC', '1000', 1.5): {
        'win_rate': 69.1,
        'theoretical_rr': 1.5,
        'realized_rr': 0.981,
        'theoretical_expectancy': 0.257,
        'realized_expectancy': 0.369,
        'sample_size': 55
    },
    ('MGC', '1000', 2.0): {
        'win_rate': 69.1,
        'theoretical_rr': 2.0,
        'realized_rr': 1.377,
        'theoretical_expectancy': 0.215,
        'realized_expectancy': 0.643,
        'sample_size': 55
    },
    ('MGC', '1000', 2.5): {
        'win_rate': 69.1,
        'theoretical_rr': 2.5,
        'realized_rr': 1.773,
        'theoretical_expectancy': 0.132,
        'realized_expectancy': 0.916,
        'sample_size': 55
    },
    ('MGC', '1000', 3.0): {
        'win_rate': 69.1,
        'theoretical_rr': 3.0,
        'realized_rr': 2.169,
        'theoretical_expectancy': 0.132,
        'realized_expectancy': 1.190,
        'sample_size': 55
    },
    ('MGC', '1800', 1.5): {
        'win_rate': 62.5,
        'theoretical_rr': 1.5,
        'realized_rr': 1.010,
        'theoretical_expectancy': 0.125,
        'realized_expectancy': 0.256,
        'sample_size': 32
    },
}


def populate_from_phase1():
    """
    Populate validated_setups with Phase 1 analysis results.

    This is more reliable than deriving from daily_features because:
    - Phase 1 ran execution_engine with specific RR values
    - daily_features only has RR=1.0 outcomes (MFE stops at 1.0R target)
    - Can't extrapolate RR>1.0 from RR=1.0 data (ordering assumption)
    """
    con = duckdb.connect(DB_PATH)

    print("=" * 70)
    print("POPULATE REALIZED METRICS FROM PHASE 1 RESULTS")
    print("=" * 70)
    print()

    # Check schema
    schema = con.execute("PRAGMA table_info(validated_setups)").fetchall()
    columns = [col[1] for col in schema]

    if 'realized_expectancy' not in columns:
        print("Adding columns to validated_setups...")
        con.execute("ALTER TABLE validated_setups ADD COLUMN realized_expectancy DOUBLE")
        con.execute("ALTER TABLE validated_setups ADD COLUMN avg_win_r DOUBLE")
        con.execute("ALTER TABLE validated_setups ADD COLUMN avg_loss_r DOUBLE")
        print("[OK] Columns added")
        print()

    # Get all MGC setups
    setups = con.execute("""
        SELECT id, instrument, orb_time, rr
        FROM validated_setups
        WHERE instrument = 'MGC'
        ORDER BY orb_time, rr
    """).fetchall()

    print(f"Found {len(setups)} MGC setups in validated_setups")
    print()

    updated = 0
    skipped = 0

    for setup_id, instrument, orb_time, rr in setups:
        key = (instrument, orb_time, rr)

        if key in PHASE1_RESULTS:
            result = PHASE1_RESULTS[key]

            # Calculate avg_win_r and avg_loss_r
            # Expectancy = (win_rate × avg_win) - (loss_rate × avg_loss)
            # Given: win_rate, realized_expectancy
            # Assume: avg_loss = -1.0R (full stop)
            win_rate_decimal = result['win_rate'] / 100.0
            loss_rate = 1.0 - win_rate_decimal

            # Solve for avg_win:
            # realized_expectancy = (win_rate × avg_win) + (loss_rate × -1.0)
            # avg_win = (realized_expectancy + loss_rate) / win_rate
            if win_rate_decimal > 0:
                avg_win_r = (result['realized_expectancy'] + loss_rate) / win_rate_decimal
            else:
                avg_win_r = 0.0

            avg_loss_r = -1.0

            # Update validated_setups
            con.execute("""
                UPDATE validated_setups
                SET realized_expectancy = ?,
                    avg_win_r = ?,
                    avg_loss_r = ?,
                    sample_size = ?,
                    win_rate = ?
                WHERE id = ?
            """, [
                result['realized_expectancy'],
                avg_win_r,
                avg_loss_r,
                result['sample_size'],
                result['win_rate'],
                setup_id
            ])

            print(f"[OK] {instrument} {orb_time} RR={rr}")
            print(f"     Realized Expectancy: {result['realized_expectancy']:+.3f}R")
            print(f"     Win Rate: {result['win_rate']:.1f}%")
            print(f"     Sample: {result['sample_size']} trades")
            print()

            updated += 1
        else:
            print(f"[SKIP] {instrument} {orb_time} RR={rr} (no Phase 1 data)")
            print()
            skipped += 1

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    print(f"Updated: {updated} setups")
    print(f"Skipped: {skipped} setups (no Phase 1 data)")
    print()

    # Show comparison
    results = con.execute("""
        SELECT
            instrument,
            orb_time,
            rr,
            expected_r as theoretical_expectancy,
            realized_expectancy,
            (realized_expectancy - expected_r) as delta,
            win_rate,
            sample_size
        FROM validated_setups
        WHERE instrument = 'MGC'
        AND realized_expectancy IS NOT NULL
        ORDER BY orb_time, rr
    """).fetchall()

    print("Theoretical vs Realized Expectancy:")
    print()
    for row in results:
        inst, orb, rr, theo, real, delta, wr, n = row
        status = "SURVIVES" if real >= 0.15 else ("MARGINAL" if real >= 0.05 else "FAILS")
        print(f"{inst} {orb} RR={rr:.1f}: {theo:+.3f}R -> {real:+.3f}R (delta: {delta:+.3f}R) [{status}]")
        print(f"          Win Rate: {wr:.1f}%, Sample: {n} trades")

    print()
    print("[OK] Populated realized metrics from Phase 1 analysis")
    print()

    con.close()


if __name__ == "__main__":
    populate_from_phase1()
