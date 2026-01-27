from trading_app.cloud_mode import get_database_connection

con = get_database_connection()
rows = con.execute("""
SELECT
  setup_id,
  orb_time,
  rr,
  sl_mode,
  tier,
  win_rate,
  avg_r,
  annual_trades
FROM validated_setups
WHERE instrument = 'MGC'
  AND orb_time IN ('2300','0030')
ORDER BY orb_time;
""").fetchall()

print("Rows:", len(rows))
for r in rows:
    print(r)

con.close()
