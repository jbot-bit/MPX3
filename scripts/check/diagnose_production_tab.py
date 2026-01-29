"""
Diagnose what Production tab should show
Run with app CLOSED to avoid database lock
"""
import duckdb

print("="*70)
print("PRODUCTION TAB DIAGNOSTIC")
print("="*70)

try:
    conn = duckdb.connect('data/db/gold.db', read_only=True)

    # This is the EXACT query from app_canonical.py Production tab
    query = """
    SELECT
        vs.id,
        vs.instrument,
        vs.orb_time,
        vs.rr,
        vs.sl_mode,
        vs.orb_size_filter,
        vs.win_rate,
        vs.expected_r,
        vs.real_expected_r,
        vs.sample_size,
        vs.notes,
        COUNT(vt.date_local) as trade_count,
        SUM(CASE WHEN vt.outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN vt.outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
        AVG(vt.realized_rr) as avg_realized_rr,
        SUM(CASE WHEN vt.realized_rr >= 0.15 THEN 1 ELSE 0 END) as friction_pass_count
    FROM validated_setups vs
    LEFT JOIN validated_trades vt ON vs.id = vt.setup_id
    WHERE vs.instrument = 'MGC'
    GROUP BY vs.id, vs.instrument, vs.orb_time, vs.rr, vs.sl_mode,
             vs.orb_size_filter, vs.win_rate, vs.expected_r, vs.real_expected_r,
             vs.sample_size, vs.notes
    ORDER BY vs.orb_time, vs.expected_r DESC
    """

    result = conn.execute(query).fetchdf()

    print(f"\nQuery returned: {len(result)} rows")
    print(f"\nORB breakdown:")
    orb_counts = result.groupby('orb_time').size()
    for orb_time, count in orb_counts.items():
        print(f"  {orb_time}: {count} variants")

    print(f"\nFirst 10 setups (what app should show):")
    print("-"*70)

    for idx, row in result.head(10).iterrows():
        print(f"\n{row['orb_time']} - RR={row['rr']:.1f} {row['sl_mode']}")
        print(f"  ExpR: {row['expected_r']:+.3f}R")
        print(f"  Win Rate: {row['win_rate']:.1%}")
        print(f"  Sample: {row['sample_size']} trades")
        print(f"  Trades in validated_trades: {int(row['trade_count'])}")
        if row['orb_size_filter']:
            print(f"  Filter: ORB > {row['orb_size_filter']:.3f} ATR")

    conn.close()

    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    print(f"The Production tab SHOULD show {len(result)} MGC setups.")
    print("If you don't see them in the app, possible issues:")
    print("1. Looking at wrong tab (check 'Production' tab, not 'Research Lab')")
    print("2. Groups are collapsed (click expand arrows)")
    print("3. Instrument filter wrong (should be 'MGC')")
    print("4. App error (check browser console or app_errors.txt)")

except Exception as e:
    print(f"\nERROR: {e}")
    print("\nIs the app still running? Close it first (Ctrl+C in terminal)")
    print("Then run: python diagnose_production_tab.py")
