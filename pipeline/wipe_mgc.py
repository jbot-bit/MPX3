import duckdb
from pipeline.paths import GOLD_DB_PATH

con = duckdb.connect(GOLD_DB_PATH)

con.execute("DELETE FROM bars_1m WHERE symbol = 'MGC'")
con.execute("DELETE FROM bars_5m WHERE symbol = 'MGC'")
con.execute("DELETE FROM daily_features WHERE instrument = 'MGC'")

con.close()
print("OK: wiped all MGC data (bars_1m, bars_5m, daily_features)")
