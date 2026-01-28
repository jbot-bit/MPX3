"""
UPDATE VALIDATED_SETUPS FROM VALIDATED_TRADES (TCA-ADJUSTED)
=============================================================

validated_setups is a CACHED SUMMARY derived from validated_trades.

This script:
1. Aggregates validated_trades (post-TCA, friction <= 20%)
2. Updates realized_expectancy, win_rate, sample_size in validated_setups
3. Enforces PRODUCTION phase gate (>= 0.15R)
4. Sets status='ACTIVE' or 'RETIRED' (does NOT delete rows)

SINGLE SOURCE OF TRUTH: validated_trades table
"""

import duckdb
from datetime import datetime

DB_PATH = 'data/db/gold.db'

def update_validated_setups_from_tca():
    """Update validated_setups with aggregated TCA-adjusted metrics from validated_trades."""

    conn = duckdb.connect(DB_PATH)

    print("=" * 80)
    print("UPDATE VALIDATED_SETUPS FROM VALIDATED_TRADES (TCA-ADJUSTED)")
    print("=" * 80)
    print()
    print("Single Source of Truth: validated_trades table")
    print("Phase Gate: PRODUCTION (>= 0.15R)")
    print()

    # Check if status column exists, add if not
    columns = conn.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'validated_setups'
    """).fetchall()

    column_names = [c[0] for c in columns]

    if 'status' not in column_names:
        print("[INFO] Adding status column to validated_setups...")
        conn.execute("""
            ALTER TABLE validated_setups
            ADD COLUMN status VARCHAR DEFAULT 'ACTIVE'
        """)
        print("[OK] Status column added\n")

    # Aggregate TCA-adjusted metrics from validated_trades
    print("=" * 80)
    print("AGGREGATING TCA-ADJUSTED METRICS")
    print("=" * 80)
    print()

    agg_query = """
        SELECT
            vt.setup_id,
            vs.instrument,
            vs.orb_time,
            vs.rr,
            vs.sl_mode,
            vs.orb_size_filter,

            -- Sample size (only trades that passed TCA gate)
            COUNT(*) as total_signals,
            SUM(CASE WHEN vt.outcome NOT IN ('NO_TRADE', 'RISK_TOO_SMALL')
                     AND (vt.friction_ratio IS NULL OR vt.friction_ratio <= 0.20)
                THEN 1 ELSE 0 END) as tca_trades,

            -- Win/Loss counts
            SUM(CASE WHEN vt.outcome = 'WIN'
                     AND (vt.friction_ratio IS NULL OR vt.friction_ratio <= 0.20)
                THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN vt.outcome = 'LOSS'
                     AND (vt.friction_ratio IS NULL OR vt.friction_ratio <= 0.20)
                THEN 1 ELSE 0 END) as losses,

            -- Realized expectancy (TCA-adjusted)
            AVG(CASE WHEN vt.outcome IN ('WIN', 'LOSS')
                     AND (vt.friction_ratio IS NULL OR vt.friction_ratio <= 0.20)
                THEN vt.realized_rr ELSE NULL END) as realized_expectancy,

            -- Avg win/loss R
            AVG(CASE WHEN vt.outcome = 'WIN'
                     AND (vt.friction_ratio IS NULL OR vt.friction_ratio <= 0.20)
                THEN vt.realized_rr ELSE NULL END) as avg_win_r,
            AVG(CASE WHEN vt.outcome = 'LOSS'
                     AND (vt.friction_ratio IS NULL OR vt.friction_ratio <= 0.20)
                THEN vt.realized_rr ELSE NULL END) as avg_loss_r

        FROM validated_trades vt
        JOIN validated_setups vs ON vt.setup_id = vs.id
        WHERE vs.instrument = 'MGC'
        GROUP BY vt.setup_id, vs.instrument, vs.orb_time, vs.rr, vs.sl_mode, vs.orb_size_filter
        ORDER BY vs.orb_time, vs.rr
    """

    results = conn.execute(agg_query).fetchall()

    print(f"Found {len(results)} strategies to update\n")

    print("=" * 80)
    print("UPDATING VALIDATED_SETUPS")
    print("=" * 80)
    print()
    print(f"{'ID':<4} {'ORB':<6} {'RR':<5} {'Expectancy':<12} {'Sample':<8} {'WR':<8} {'Status':<10} {'Phase':<10}")
    print("-" * 80)

    updates_applied = 0
    retired_count = 0
    active_count = 0

    for row in results:
        (setup_id, instrument, orb_time, rr, sl_mode, orb_filter,
         total_signals, tca_trades, wins, losses,
         realized_exp, avg_win_r, avg_loss_r) = row

        # Calculate metrics
        resolved = wins + losses
        win_rate = (wins / resolved) if resolved > 0 else 0.0

        # Enforce PRODUCTION phase gate (>= 0.15R)
        if realized_exp is not None and realized_exp >= 0.15 and resolved >= 30:
            status = 'ACTIVE'
            phase = 'PROD'
            active_count += 1
        else:
            status = 'RETIRED'
            phase = 'REJECTED'
            retired_count += 1

        # Update database
        conn.execute("""
            UPDATE validated_setups
            SET
                realized_expectancy = ?,
                win_rate = ?,
                sample_size = ?,
                avg_win_r = ?,
                avg_loss_r = ?,
                status = ?,
                updated_at = ?
            WHERE id = ?
        """, [
            realized_exp if realized_exp is not None else 0.0,
            win_rate,
            resolved,
            avg_win_r if avg_win_r is not None else 0.0,
            avg_loss_r if avg_loss_r is not None else 0.0,
            status,
            datetime.now(),
            setup_id
        ])

        # Print summary
        exp_str = f"{realized_exp:+.3f}R" if realized_exp is not None else "N/A"
        print(f"{setup_id:<4} {orb_time:<6} {rr:<5.1f} {exp_str:<12} {resolved:<8} {win_rate:<8.1%} {status:<10} {phase:<10}")

        updates_applied += 1

    print("-" * 80)
    print(f"Total updates: {updates_applied}")
    print(f"ACTIVE (PROD >= 0.15R): {active_count}")
    print(f"RETIRED (< 0.15R): {retired_count}")
    print()

    # Summary of active strategies
    print("=" * 80)
    print("ACTIVE STRATEGIES (PRODUCTION)")
    print("=" * 80)
    print()

    active_strategies = conn.execute("""
        SELECT id, orb_time, rr, realized_expectancy, sample_size, win_rate
        FROM validated_setups
        WHERE instrument = 'MGC' AND status = 'ACTIVE'
        ORDER BY realized_expectancy DESC
    """).fetchall()

    if active_strategies:
        print(f"{'ID':<4} {'ORB':<6} {'RR':<5} {'Expectancy':<12} {'Sample':<8} {'Win Rate':<10}")
        print("-" * 50)
        for strategy in active_strategies:
            sid, orb, rr_val, exp, sample, wr = strategy
            print(f"{sid:<4} {orb:<6} {rr_val:<5.1f} {exp:+.3f}R{'':<7} {sample:<8} {wr:<10.1%}")
        print()
    else:
        print("[WARNING] No strategies passed PRODUCTION gate (>= 0.15R)")
        print()

    conn.close()

    print("=" * 80)
    print("UPDATE COMPLETE")
    print("=" * 80)
    print()
    print("validated_setups is now synchronized with validated_trades (TCA-adjusted)")
    print()


if __name__ == "__main__":
    update_validated_setups_from_tca()
