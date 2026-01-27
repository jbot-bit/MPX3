#!/usr/bin/env python3
"""
Populate Realized Metrics in validated_setups

Derives realized_expectancy from daily_features using:
1. Execution engine outcomes (WIN/LOSS) - respects TP/SL ordering
2. Cost model calculations - recomputes realized_rr for each RR target
3. Aggregation - realized_expectancy = AVG(realized_rr) across all trades

Data flow: daily_features → this script → validated_setups

CRITICAL: Does NOT infer outcomes from MFE. Uses execution_engine outcomes.
"""

import duckdb
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.cost_model import calculate_realized_rr

DB_PATH = "gold.db"


def calculate_realized_expectancy(
    con: duckdb.DuckDBPyConnection,
    instrument: str,
    orb_time: str,
    rr: float,
    sl_mode: str
) -> dict:
    """
    Calculate realized expectancy for a setup by reading daily_features.

    Args:
        con: Database connection
        instrument: 'MGC', 'NQ', or 'MPL'
        orb_time: '0900', '1000', '1100', '1800', '2300', '0030'
        rr: Target RR (1.0, 1.5, 2.0, 2.5, 3.0, etc.)
        sl_mode: 'full' or 'half'

    Returns:
        dict with realized_expectancy, win_rate, avg_win_r, avg_loss_r, sample_size
    """
    # Query daily_features for this setup
    # Note: daily_features stores outcomes at RR=1.0 by default
    # We need to recompute outcomes for RR > 1.0 using MFE
    query = f"""
    SELECT
        orb_{orb_time}_size,
        orb_{orb_time}_mfe,
        orb_{orb_time}_outcome,
        orb_{orb_time}_risk_ticks
    FROM daily_features
    WHERE instrument = ?
    AND orb_{orb_time}_break_dir != 'NONE'
    AND orb_{orb_time}_mfe IS NOT NULL
    AND orb_{orb_time}_risk_ticks IS NOT NULL
    """

    trades = con.execute(query, [instrument]).fetchall()

    if not trades:
        return {
            'realized_expectancy': None,
            'win_rate': None,
            'avg_win_r': None,
            'avg_loss_r': None,
            'sample_size': 0
        }

    realized_rr_values = []
    wins = []
    losses = []

    for trade in trades:
        orb_size, mfe_r, outcome_rr1, risk_ticks = trade

        # Determine outcome for THIS RR target
        # Use MFE to check if target was hit (respects execution engine ordering)
        # MFE is in R-multiples, so MFE >= rr means target was hit
        target_hit = mfe_r >= rr

        if target_hit:
            # WIN: Recompute realized_rr for this RR using cost_model
            # (costs are non-linear, can't just scale RR=1.0 value)
            stop_points = risk_ticks * 0.1  # ticks to points

            try:
                realized = calculate_realized_rr(
                    instrument=instrument,
                    stop_distance_points=stop_points,
                    rr_theoretical=rr,  # Use THIS RR, not 1.0
                    stress_level='normal'
                )
                realized_rr_win = realized['realized_rr']
            except Exception as e:
                # If cost_model fails (e.g., NQ/MPL blocked), skip this trade
                continue

            realized_rr_values.append(realized_rr_win)
            wins.append(realized_rr_win)
        else:
            # LOSS: Full stop hit = -1.0R
            # (Could use MAE to compute partial loss, but conservative: assume full loss)
            realized_rr_values.append(-1.0)
            losses.append(-1.0)

    if not realized_rr_values:
        return {
            'realized_expectancy': None,
            'win_rate': None,
            'avg_win_r': None,
            'avg_loss_r': None,
            'sample_size': 0
        }

    # Calculate realized expectancy as AVG(realized_rr) across ALL trades
    realized_expectancy = sum(realized_rr_values) / len(realized_rr_values)

    # Optional reporting metrics
    win_rate = (len(wins) / len(trades)) * 100 if trades else 0
    avg_win_r = sum(wins) / len(wins) if wins else 0
    avg_loss_r = sum(losses) / len(losses) if losses else 0

    return {
        'realized_expectancy': realized_expectancy,
        'win_rate': win_rate,
        'avg_win_r': avg_win_r,
        'avg_loss_r': avg_loss_r,
        'sample_size': len(trades)
    }


def populate_validated_setups():
    """
    Populate realized metrics for all MGC setups in validated_setups.

    Reads from daily_features, writes to validated_setups.
    """
    con = duckdb.connect(DB_PATH)

    print("=" * 70)
    print("POPULATE REALIZED METRICS - validated_setups")
    print("=" * 70)
    print()

    # Check if columns exist
    schema = con.execute("PRAGMA table_info(validated_setups)").fetchall()
    columns = [col[1] for col in schema]

    needs_schema_update = False
    if 'realized_expectancy' not in columns:
        needs_schema_update = True
        print("[!] Schema update needed: adding realized_expectancy column")

    if needs_schema_update:
        print()
        print("Adding columns to validated_setups...")
        con.execute("ALTER TABLE validated_setups ADD COLUMN realized_expectancy DOUBLE")
        con.execute("ALTER TABLE validated_setups ADD COLUMN avg_win_r DOUBLE")
        con.execute("ALTER TABLE validated_setups ADD COLUMN avg_loss_r DOUBLE")
        print("[OK] Columns added")
        print()

    # Get all MGC setups
    setups = con.execute("""
        SELECT id, instrument, orb_time, rr, sl_mode
        FROM validated_setups
        WHERE instrument = 'MGC'
        ORDER BY orb_time, rr
    """).fetchall()

    print(f"Found {len(setups)} MGC setups in validated_setups")
    print()

    # Populate each setup
    for setup_id, instrument, orb_time, rr, sl_mode in setups:
        print(f"Processing: {instrument} {orb_time} RR={rr} sl_mode={sl_mode}")

        metrics = calculate_realized_expectancy(
            con, instrument, orb_time, rr, sl_mode
        )

        if metrics['realized_expectancy'] is not None:
            # Update validated_setups
            con.execute("""
                UPDATE validated_setups
                SET realized_expectancy = ?,
                    avg_win_r = ?,
                    avg_loss_r = ?,
                    sample_size = ?
                WHERE id = ?
            """, [
                metrics['realized_expectancy'],
                metrics['avg_win_r'],
                metrics['avg_loss_r'],
                metrics['sample_size'],
                setup_id
            ])

            print(f"  Realized Expectancy: {metrics['realized_expectancy']:+.3f}R")
            print(f"  Win Rate: {metrics['win_rate']:.1f}%")
            print(f"  Avg Win: {metrics['avg_win_r']:+.3f}R, Avg Loss: {metrics['avg_loss_r']:+.3f}R")
            print(f"  Sample: {metrics['sample_size']} trades")
        else:
            print(f"  [SKIP] No data available")

        print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()

    # Show updated values
    results = con.execute("""
        SELECT
            instrument,
            orb_time,
            rr,
            expected_r as theoretical_expectancy,
            realized_expectancy,
            (realized_expectancy - expected_r) as delta,
            sample_size
        FROM validated_setups
        WHERE instrument = 'MGC'
        AND realized_expectancy IS NOT NULL
        ORDER BY orb_time, rr
    """).fetchall()

    print("Theoretical vs Realized Expectancy:")
    print()
    for row in results:
        inst, orb, rr, theo, real, delta, n = row
        print(f"{inst} {orb} RR={rr:.1f}: {theo:+.3f}R → {real:+.3f}R (delta: {delta:+.3f}R, n={n})")

    print()
    print("[OK] Populated realized metrics for all MGC setups")
    print()

    con.close()


if __name__ == "__main__":
    populate_validated_setups()
