import duckdb

con = duckdb.connect("gold.db")

print("=== bars_1m schema ===")
print(con.execute("PRAGMA table_info('bars_1m')").fetchall())

print("\n=== bars_1m row count ===")
print(con.execute("SELECT COUNT(*) FROM bars_1m").fetchone())

print("\n=== bars_1m duplicate check (symbol, ts_utc) ===")
dupes_1m = con.execute(
    """
    SELECT symbol, ts_utc, COUNT(*) AS c
    FROM bars_1m
    GROUP BY symbol, ts_utc
    HAVING c > 1
    LIMIT 20
    """
).fetchall()
print(dupes_1m if dupes_1m else "No duplicates found [OK]")

print("\n=== bars_5m schema ===")
print(con.execute("PRAGMA table_info('bars_5m')").fetchall())

print("\n=== bars_5m row count ===")
print(con.execute("SELECT COUNT(*) FROM bars_5m").fetchone())

print("\n=== daily_features schema ===")
print(con.execute("PRAGMA table_info('daily_features')").fetchall())

print("\n=== daily_features row count ===")
print(con.execute("SELECT COUNT(*) FROM daily_features").fetchone())

print("\n=== daily_features duplicate check (date_local, instrument) ===")
dupes_df = con.execute(
    """
    SELECT date_local, instrument, COUNT(*) AS c
    FROM daily_features
    GROUP BY date_local, instrument
    HAVING c > 1
    LIMIT 20
    """
).fetchall()
print(dupes_df if dupes_df else "No duplicates found [OK]")

print("\n=== date range in bars_1m ===")
print(con.execute("SELECT MIN(ts_utc), MAX(ts_utc) FROM bars_1m").fetchone())

print("\n=== date range in daily_features ===")
print(con.execute("SELECT MIN(date_local), MAX(date_local) FROM daily_features").fetchone())

con.close()
