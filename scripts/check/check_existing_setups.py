#!/usr/bin/env python3
import sys
sys.path.insert(0, 'trading_app')
from cloud_mode import get_database_connection

conn = get_database_connection()

# Get existing 2300/0030 setups
setups = conn.execute("""
    SELECT *
    FROM validated_setups
    WHERE instrument='MGC' AND orb_time IN ('2300', '0030')
    ORDER BY orb_time
""").fetchdf()

print("EXISTING 2300/0030 SETUPS IN validated_setups:")
print("="*80)

for idx, row in setups.iterrows():
    print(f"\nSETUP: {row['setup_id']}")
    print(f"  ORB Time: {row['orb_time']}")
    print(f"  RR: {row['rr']}")
    print(f"  SL Mode: {row['sl_mode']}")
    print(f"  ORB Size Filter: {row['orb_size_filter']}")
    print(f"  Trades: {row['trades']}")
    print(f"  Win Rate: {row['win_rate']}%")
    print(f"  Avg R: {row['avg_r']}")
    print(f"  Annual Trades: {row['annual_trades']}")
    print(f"  Tier: {row['tier']}")
    print(f"  Validated Date: {row['validated_date']}")
    print(f"  Data Source: {row['data_source']}")
    print(f"  Notes: {row['notes'][:150] if row['notes'] else 'NULL'}...")

conn.close()

print("\n" + "="*80)
print("\nCONCLUSION:")
print("These setups ALREADY EXIST in validated_setups with Phase 2 metrics.")
print("They appear to be the extended-window edges based on the metrics match.")
print("\nAction needed: Verify if these are truly extended-window or if new ones needed.")
