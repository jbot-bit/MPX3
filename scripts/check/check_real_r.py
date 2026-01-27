import duckdb
con = duckdb.connect('data/db/gold.db', read_only=True)
rows = con.execute("SELECT orb_time, rr, expected_r, real_expected_r FROM validated_setups WHERE instrument='MGC' ORDER BY orb_time, rr").fetchall()
print("MGC setups in data/db/gold.db:")
for r in rows:
    real_str = f"{r[3]:+.3f}" if r[3] is not None else "None"
    print(f"  {r[0]} RR={r[1]}: canonical={r[2]:+.3f}, real={real_str}")
con.close()
