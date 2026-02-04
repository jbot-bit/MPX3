import duckdb
from pipeline.paths import GOLD_DB_PATH

con = duckdb.connect(GOLD_DB_PATH)

con.execute("DELETE FROM bars_1m_mpl WHERE symbol = 'MPL'")
con.execute("DELETE FROM bars_5m_mpl WHERE symbol = 'MPL'")
con.execute("DELETE FROM daily_features_mpl WHERE instrument = 'MPL'")

con.close()
print("OK: wiped all MPL data (bars_1m_mpl, bars_5m_mpl, daily_features_mpl)")
