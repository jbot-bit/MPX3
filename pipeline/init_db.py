import duckdb
from pathlib import Path

DB_PATH = Path("gold.db")
SCHEMA_PATH = Path("schema.sql")

def main() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    con = duckdb.connect(str(DB_PATH))
    try:
        con.execute(schema_sql)
        print("OK: DB initialized:", DB_PATH.resolve())
    finally:
        con.close()

if __name__ == "__main__":
    main()
