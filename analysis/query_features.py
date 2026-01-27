import duckdb

con = duckdb.connect("gold.db")

print("daily_features count:", con.execute("SELECT COUNT(*) FROM daily_features").fetchone())

# Query with new schema (v5) showing all 6 ORBs and session types
q = """
SELECT date_local,
       ((asia_high-asia_low)/0.10) AS asia_ticks,
       atr_20,
       asia_type,
       london_type,
       ny_type,
       orb_0900_break_dir,
       orb_0900_outcome,
       orb_0900_r_multiple,
       orb_1000_break_dir,
       orb_1000_outcome,
       orb_1000_r_multiple,
       orb_0030_break_dir,
       orb_0030_outcome,
       orb_0030_r_multiple
FROM daily_features
ORDER BY date_local DESC
LIMIT 20;
"""

rows = con.execute(q).fetchall()
for row in rows:
    print(f"\nDate: {row[0]}")
    asia_ticks = f"{row[1]:.0f}" if row[1] is not None else "N/A"
    atr_20 = f"{row[2]:.2f}" if row[2] is not None else "N/A"
    print(f"  Asia: {asia_ticks} ticks, ATR_20: {atr_20}, Type: {row[3]}")
    print(f"  London: {row[4]}, NY: {row[5]}")
    print(f"  ORB 09:00: {row[6]} -> {row[7]} (R={row[8]})")
    print(f"  ORB 10:00: {row[9]} -> {row[10]} (R={row[11]})")
    print(f"  ORB 00:30: {row[12]} -> {row[13]} (R={row[14]})")

con.close()
