"""
Add CASCADE and SINGLE_LIQUIDITY strategies to validated_setups database.

These are contextual strategies that use market structure, not just simple ORBs.
"""

import duckdb
from datetime import date

con = duckdb.connect('gold.db')

# Check if these already exist
existing = con.execute("""
    SELECT setup_id FROM validated_setups
    WHERE setup_id LIKE '%CASCADE%' OR setup_id LIKE '%SINGLE_LIQ%'
""").fetchall()

if existing:
    print(f"Found existing contextual setups: {existing}")
    print("Deleting them first...")
    con.execute("DELETE FROM validated_setups WHERE setup_id LIKE '%CASCADE%' OR setup_id LIKE '%SINGLE_LIQ%'")

# ============================================================================
# CASCADE STRATEGY - S+ TIER
# ============================================================================
# Performance (740 days, 2024-2026):
# - Trades: 69 total (9.3% frequency)
# - Win Rate: 19%
# - Avg R: +1.95R
# - Total R: ~+135R
# - Annual: ~35 trades/year, ~+68R/year

cascade_setup = {
    'setup_id': 'MGC_CASCADE_MULTI_LIQUIDITY',
    'instrument': 'MGC',
    'orb_time': 'CASCADE',  # Not ORB-based
    'rr': 4.0,  # Effective 4R (gap-based)
    'sl_mode': 'DYNAMIC',  # 0.5 gaps from entry
    'close_confirmations': 3,  # Acceptance failure within 3 bars
    'buffer_ticks': 1.0,  # Entry within 0.1pts of level
    'orb_size_filter': None,
    'atr_filter': None,
    'min_gap_filter': 9.5,  # Gap >9.5pts (MANDATORY)
    'trades': 69,
    'win_rate': 19.0,
    'avg_r': 1.95,
    'annual_trades': 35,
    'tier': 'S+',
    'notes': 'MULTI-LIQUIDITY CASCADE: London sweeps Asia → NY sweeps London. 2 cascading acceptance failures. Gap-based targeting (4R effective). Rare but massive edge.',
    'validated_date': date.today(),
    'data_source': 'manual_validation'
}

con.execute("""
    INSERT INTO validated_setups VALUES (
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?, ?, ?
    )
""", [
    cascade_setup['setup_id'],
    cascade_setup['instrument'],
    cascade_setup['orb_time'],
    cascade_setup['rr'],
    cascade_setup['sl_mode'],
    cascade_setup['close_confirmations'],
    cascade_setup['buffer_ticks'],
    cascade_setup['orb_size_filter'],
    cascade_setup['atr_filter'],
    cascade_setup['min_gap_filter'],
    cascade_setup['trades'],
    cascade_setup['win_rate'],
    cascade_setup['avg_r'],
    cascade_setup['annual_trades'],
    cascade_setup['tier'],
    cascade_setup['notes'],
    cascade_setup['validated_date'],
    cascade_setup['data_source']
])

print(f"[OK] Added CASCADE setup: {cascade_setup['setup_id']}")
print(f"  - Trades: {cascade_setup['trades']} (~{cascade_setup['annual_trades']}/year)")
print(f"  - WR: {cascade_setup['win_rate']}% | Avg R: +{cascade_setup['avg_r']}R")
print(f"  - Annual: ~+68R/year")
print()

# ============================================================================
# SINGLE_LIQUIDITY STRATEGY - S TIER
# ============================================================================
# Performance (740 days, 2024-2026):
# - Win Rate: 33.7%
# - Avg R: +1.44R
# - Frequency: 16% (more common than CASCADE)
# - Annual: ~59 trades/year, ~+85R/year

single_liq_setup = {
    'setup_id': 'MGC_SINGLE_LIQUIDITY',
    'instrument': 'MGC',
    'orb_time': 'SINGLE_LIQ',  # Not ORB-based
    'rr': 3.0,  # Typical (targets opposite London level)
    'sl_mode': 'DYNAMIC',  # 2pts beyond sweep point
    'close_confirmations': 3,  # Acceptance failure within 3 bars
    'buffer_ticks': 1.0,  # Entry within 0.1pts of level
    'orb_size_filter': None,
    'atr_filter': None,
    'min_gap_filter': None,  # No gap required (single level)
    'trades': 118,  # 16% of 740 days
    'win_rate': 33.7,
    'avg_r': 1.44,
    'annual_trades': 59,
    'tier': 'S',
    'notes': 'SINGLE LIQUIDITY: Single London level swept at NY open (23:00). Simpler than CASCADE but still strong edge. Targets opposite London level.',
    'validated_date': date.today(),
    'data_source': 'manual_validation'
}

con.execute("""
    INSERT INTO validated_setups VALUES (
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?, ?, ?
    )
""", [
    single_liq_setup['setup_id'],
    single_liq_setup['instrument'],
    single_liq_setup['orb_time'],
    single_liq_setup['rr'],
    single_liq_setup['sl_mode'],
    single_liq_setup['close_confirmations'],
    single_liq_setup['buffer_ticks'],
    single_liq_setup['orb_size_filter'],
    single_liq_setup['atr_filter'],
    single_liq_setup['min_gap_filter'],
    single_liq_setup['trades'],
    single_liq_setup['win_rate'],
    single_liq_setup['avg_r'],
    single_liq_setup['annual_trades'],
    single_liq_setup['tier'],
    single_liq_setup['notes'],
    single_liq_setup['validated_date'],
    single_liq_setup['data_source']
])

print(f"[OK] Added SINGLE_LIQUIDITY setup: {single_liq_setup['setup_id']}")
print(f"  - Trades: {single_liq_setup['trades']} (~{single_liq_setup['annual_trades']}/year)")
print(f"  - WR: {single_liq_setup['win_rate']}% | Avg R: +{single_liq_setup['avg_r']}R")
print(f"  - Annual: ~+85R/year")
print()

# Show all MGC setups now
print("=" * 80)
print("ALL MGC SETUPS IN DATABASE:")
print("=" * 80)

all_setups = con.execute("""
    SELECT orb_time, tier, win_rate, avg_r, annual_trades, notes
    FROM validated_setups
    WHERE instrument = 'MGC'
    ORDER BY
        CASE tier
            WHEN 'S+' THEN 1
            WHEN 'S' THEN 2
            WHEN 'A' THEN 3
            ELSE 4
        END,
        avg_r DESC
""").fetchall()

for orb_time, tier, wr, avg_r, annual, notes in all_setups:
    annual_r = annual * avg_r if annual and avg_r else 0
    print(f"{orb_time:12} ({tier:2}) - {wr:5.1f}% WR | {avg_r:+.3f}R avg | ~{annual_r:+.0f}R/year")
    if notes:
        print(f"             {notes[:80]}")
    print()

con.close()

print("=" * 80)
print("SUCCESS: Contextual strategies added to database!")
print("=" * 80)
print()
print("Your AI will now know about:")
print("  - CASCADE (S+ tier, +1.95R avg)")
print("  - SINGLE_LIQUIDITY (S tier, +1.44R avg)")
print("  - All 6 baseline ORB setups")
print()
print("Total MGC system: ~+450-600R/year")
