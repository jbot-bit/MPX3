from pathlib import Path
import duckdb

DB_PATH = Path("gold.db")
SYMBOL = "MGC"

def main() -> None:
    con = duckdb.connect(str(DB_PATH))
    try:
        con.execute(
            """
            INSERT OR REPLACE INTO bars_5m
            (ts_utc, symbol, source_symbol, open, high, low, close, volume)
            SELECT
              to_timestamp(floor(epoch(ts_utc) / 300) * 300) AS ts_5m,
              symbol,
              arg_max(source_symbol, ts_utc) AS source_symbol,
              arg_min(open, ts_utc)  AS open,
              max(high)              AS high,
              min(low)               AS low,
              arg_max(close, ts_utc) AS close,
              sum(volume)            AS volume
            FROM bars_1m
            WHERE symbol = ?
            GROUP BY 1, 2
            """,
            [SYMBOL],
        )

        n5 = con.execute(
            "SELECT count(*) FROM bars_5m WHERE symbol = ?",
            [SYMBOL],
        ).fetchone()[0]

        print(f"OK: bars_5m built. total_5m_rows={n5}")
    finally:
        con.close()

if __name__ == "__main__":
    main()
