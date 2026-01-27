from __future__ import annotations

import os
import sys
import time as time_mod
import datetime as dt
import subprocess
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple

import duckdb
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

import databento as db
from databento.common.error import BentoClientError


# -----------------------------
# Config
# -----------------------------

@dataclass
class Cfg:
    db_path: str = "gold.db"
    symbol: str = "MPL"  # logical symbol stored in DB (your continuous)
    tz_local: str = "Australia/Brisbane"
    dataset: str = "GLBX.MDP3"
    schema: str = "ohlcv-1m"
    parent_symbol: str = "MPL.FUT"  # futures parent for Micro Platinum
    max_retries: int = 5
    retry_sleep_sec: float = 2.0


def env_cfg() -> Cfg:
    load_dotenv()
    db_path = os.getenv("DUCKDB_PATH", "gold.db").strip()
    symbol = os.getenv("SYMBOL", "MPL").strip() or "MPL"
    tz_local = os.getenv("TZ_LOCAL", "Australia/Brisbane").strip() or "Australia/Brisbane"
    dataset = os.getenv("DATABENTO_DATASET", "GLBX.MDP3").strip() or "GLBX.MDP3"
    schema = os.getenv("DATABENTO_SCHEMA", "ohlcv-1m").strip() or "ohlcv-1m"
    parent_symbol = os.getenv("DATABENTO_PARENT", "MPL.FUT").strip() or "MPL.FUT"
    return Cfg(db_path=db_path, symbol=symbol, tz_local=tz_local, dataset=dataset, schema=schema, parent_symbol=parent_symbol)


# -----------------------------
# Date helpers
# -----------------------------

def parse_date(s: str) -> dt.date:
    return dt.date.fromisoformat(s)

def daterange_inclusive(start: dt.date, end: dt.date):
    cur = start
    while cur <= end:
        yield cur
        cur += dt.timedelta(days=1)

def local_day_to_utc_window(d: dt.date, tz_name: str) -> Tuple[dt.datetime, dt.datetime]:
    """
    Trading day = 09:00 local -> next 09:00 local
    This aligns with ORB strategy (session starts at 09:00)
    """
    tz = ZoneInfo(tz_name)
    start_local = dt.datetime(d.year, d.month, d.day, 9, 0, 0, tzinfo=tz)
    end_local = start_local + dt.timedelta(days=1)
    return start_local.astimezone(dt.timezone.utc), end_local.astimezone(dt.timezone.utc)


# -----------------------------
# DuckDB writes
# -----------------------------

def upsert_bars_1m(
    con: duckdb.DuckDBPyConnection,
    cfg: Cfg,
    source_symbol: str,
    rows_1m: List[Tuple[str, str, str, float, float, float, float, int]],
) -> int:
    if not rows_1m:
        return 0

    con.executemany(
        """
        INSERT OR REPLACE INTO bars_1m_mpl
        (ts_utc, symbol, source_symbol, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows_1m,
    )
    return len(rows_1m)


def rebuild_5m_from_1m(con: duckdb.DuckDBPyConnection, cfg: Cfg, start_utc: dt.datetime, end_utc: dt.datetime) -> None:
    con.execute(
        """
        DELETE FROM bars_5m_mpl
        WHERE symbol = ?
          AND ts_utc >= CAST(? AS TIMESTAMPTZ)
          AND ts_utc <  CAST(? AS TIMESTAMPTZ)
        """,
        [cfg.symbol, start_utc, end_utc],
    )

    con.execute(
        """
        INSERT INTO bars_5m_mpl (ts_utc, symbol, source_symbol, open, high, low, close, volume)
        SELECT
            CAST(to_timestamp(floor(epoch(ts_utc) / 300) * 300) AS TIMESTAMPTZ) AS ts_5m,
            symbol,
            NULL AS source_symbol,
            arg_min(open, ts_utc)  AS open,
            max(high)              AS high,
            min(low)               AS low,
            arg_max(close, ts_utc) AS close,
            sum(volume)            AS volume
        FROM bars_1m_mpl
        WHERE symbol = ?
          AND ts_utc >= CAST(? AS TIMESTAMPTZ)
          AND ts_utc <  CAST(? AS TIMESTAMPTZ)
        GROUP BY 1, 2
        ORDER BY 1
        """,
        [cfg.symbol, start_utc, end_utc],
    )


# -----------------------------
# Databento helpers
# -----------------------------

def safe_get_range_with_retries(
    client: db.Historical,
    *,
    dataset: str,
    schema: str,
    parent_symbol: str,
    start_utc: dt.datetime,
    end_utc: dt.datetime,
    max_retries: int,
    retry_sleep_sec: float,
):
    last_err: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            return client.timeseries.get_range(
                dataset=dataset,
                schema=schema,
                stype_in="parent",
                symbols=[parent_symbol],
                start=start_utc.isoformat(),
                end=end_utc.isoformat(),
            )
        except Exception as e:
            last_err = e
            # 422 should be handled by clamping; if it still happens, break fast.
            if isinstance(e, BentoClientError) and "data_end_after_available_end" in str(e):
                raise
            time_mod.sleep(retry_sleep_sec * attempt)
    raise RuntimeError(f"Databento get_range failed after {max_retries} retries: {last_err}") from last_err


def choose_front_symbol(df) -> Optional[str]:
    # pick the most active outright contract (ignore spreads with '-')
    if df is None or len(df) == 0:
        return None
    tmp = df.copy()
    tmp = tmp[tmp["symbol"].astype(str).str.contains("-") == False]  # outrights only
    if len(tmp) == 0:
        return None
    vols = tmp.groupby("symbol")["volume"].sum().sort_values(ascending=False)
    return str(vols.index[0]) if len(vols) else None


# -----------------------------
# Initialize MPL tables
# -----------------------------

def init_mpl_tables(con: duckdb.DuckDBPyConnection):
    """Create MPL-specific tables if they don't exist"""
    con.execute("""
        CREATE TABLE IF NOT EXISTS bars_1m_mpl (
          ts_utc        TIMESTAMPTZ NOT NULL,
          symbol        TEXT NOT NULL,
          source_symbol TEXT,
          open          DOUBLE NOT NULL,
          high          DOUBLE NOT NULL,
          low           DOUBLE NOT NULL,
          close         DOUBLE NOT NULL,
          volume        BIGINT NOT NULL,
          PRIMARY KEY (symbol, ts_utc)
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS bars_5m_mpl (
          ts_utc        TIMESTAMPTZ NOT NULL,
          symbol        TEXT NOT NULL,
          source_symbol TEXT,
          open          DOUBLE NOT NULL,
          high          DOUBLE NOT NULL,
          low           DOUBLE NOT NULL,
          close         DOUBLE NOT NULL,
          volume        BIGINT NOT NULL,
          PRIMARY KEY (symbol, ts_utc)
        );
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS daily_features_mpl (
          date_local     DATE,
          instrument     TEXT,

          -- Session stats
          asia_high      DOUBLE,
          asia_low       DOUBLE,
          asia_range     DOUBLE,
          london_high    DOUBLE,
          london_low     DOUBLE,
          ny_high        DOUBLE,
          ny_low         DOUBLE,

          -- Pre-move travel
          pre_ny_travel  DOUBLE,
          pre_orb_travel DOUBLE,

          -- ATR
          atr_20         DOUBLE,

          -- ORB 09:00
          orb_0900_high        DOUBLE,
          orb_0900_low         DOUBLE,
          orb_0900_size        DOUBLE,
          orb_0900_break_dir   TEXT,
          orb_0900_outcome     TEXT,
          orb_0900_r_multiple  DOUBLE,
          orb_0900_mae         DOUBLE,
          orb_0900_mfe         DOUBLE,

          -- ORB 10:00
          orb_1000_high        DOUBLE,
          orb_1000_low         DOUBLE,
          orb_1000_size        DOUBLE,
          orb_1000_break_dir   TEXT,
          orb_1000_outcome     TEXT,
          orb_1000_r_multiple  DOUBLE,
          orb_1000_mae         DOUBLE,
          orb_1000_mfe         DOUBLE,

          -- ORB 11:00
          orb_1100_high        DOUBLE,
          orb_1100_low         DOUBLE,
          orb_1100_size        DOUBLE,
          orb_1100_break_dir   TEXT,
          orb_1100_outcome     TEXT,
          orb_1100_r_multiple  DOUBLE,
          orb_1100_mae         DOUBLE,
          orb_1100_mfe         DOUBLE,

          -- ORB 18:00
          orb_1800_high        DOUBLE,
          orb_1800_low         DOUBLE,
          orb_1800_size        DOUBLE,
          orb_1800_break_dir   TEXT,
          orb_1800_outcome     TEXT,
          orb_1800_r_multiple  DOUBLE,
          orb_1800_mae         DOUBLE,
          orb_1800_mfe         DOUBLE,

          -- ORB 23:00
          orb_2300_high        DOUBLE,
          orb_2300_low         DOUBLE,
          orb_2300_size        DOUBLE,
          orb_2300_break_dir   TEXT,
          orb_2300_outcome     TEXT,
          orb_2300_r_multiple  DOUBLE,
          orb_2300_mae         DOUBLE,
          orb_2300_mfe         DOUBLE,

          -- ORB 00:30
          orb_0030_high        DOUBLE,
          orb_0030_low         DOUBLE,
          orb_0030_size        DOUBLE,
          orb_0030_break_dir   TEXT,
          orb_0030_outcome     TEXT,
          orb_0030_r_multiple  DOUBLE,
          orb_0030_mae         DOUBLE,
          orb_0030_mfe         DOUBLE,

          PRIMARY KEY (date_local, instrument)
        );
    """)


# -----------------------------
# Main
# -----------------------------

def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python backfill_databento_continuous_mpl.py YYYY-MM-DD YYYY-MM-DD")

    cfg = env_cfg()
    api_key = os.getenv("DATABENTO_API_KEY")
    if not api_key:
        raise RuntimeError("Missing DATABENTO_API_KEY (set it in your environment or .env)")

    start_day = parse_date(sys.argv[1])
    end_day = parse_date(sys.argv[2])

    # IMPORTANT: clamp for Databento availability end to prevent 422.
    # You can update this when Databento extends the dataset.
    AVAILABLE_END_UTC = dt.datetime(2026, 1, 10, 0, 0, 0, tzinfo=dt.timezone.utc)

    client = db.Historical(api_key)
    con = duckdb.connect(cfg.db_path)

    total = 0
    try:
        # Initialize MPL tables
        init_mpl_tables(con)

        days = list(daterange_inclusive(start_day, end_day))
        days = list(reversed(days))  # newest -> oldest

        for d in days:
            start_utc, end_utc = local_day_to_utc_window(d, cfg.tz_local)

            # clamp end to available end
            if end_utc > AVAILABLE_END_UTC:
                end_utc = AVAILABLE_END_UTC

            if start_utc >= end_utc:
                print(f"{d} (local) [{start_utc.isoformat()} -> {end_utc.isoformat()}] -> inserted/replaced 0 rows (no data; past available_end)")
                continue

            store = safe_get_range_with_retries(
                client,
                dataset=cfg.dataset,
                schema=cfg.schema,
                parent_symbol=cfg.parent_symbol,
                start_utc=start_utc,
                end_utc=end_utc,
                max_retries=cfg.max_retries,
                retry_sleep_sec=cfg.retry_sleep_sec,
            )

            df = store.to_df()
            if df is None or len(df) == 0:
                print(f"{d} (local) [{start_utc.isoformat()} -> {end_utc.isoformat()}] -> inserted/replaced 0 rows (no data)")
                continue

            front = choose_front_symbol(df)
            if not front:
                print(f"{d} (local) [{start_utc.isoformat()} -> {end_utc.isoformat()}] -> inserted/replaced 0 rows (no outright front)")
                continue

            df_front = df[df["symbol"].astype(str) == front].copy()
            if len(df_front) == 0:
                print(f"{d} (local) [{start_utc.isoformat()} -> {end_utc.isoformat()}] -> front={front} -> inserted/replaced 0 rows")
                continue

            # Databento index is ts_event (tz-aware UTC)
            rows_1m: List[Tuple[str, str, str, float, float, float, float, int]] = []
            for ts_event, row in df_front.iterrows():
                # ensure ISO with offset
                ts_iso = ts_event.isoformat()
                rows_1m.append((
                    ts_iso,             # ts_utc
                    cfg.symbol,         # logical symbol (continuous)
                    front,              # source_symbol (actual contract)
                    float(row["open"]),
                    float(row["high"]),
                    float(row["low"]),
                    float(row["close"]),
                    int(row["volume"]),
                ))

            inserted = upsert_bars_1m(con, cfg, front, rows_1m)
            total += inserted

            print(
                f"{d} (local) [{start_utc.isoformat()} -> {end_utc.isoformat()}] -> front={front} -> inserted/replaced {inserted} rows"
            )

        # rebuild 5m for the full requested LOCAL range (also clamp to available end)
        range_start_utc, _ = local_day_to_utc_window(start_day, cfg.tz_local)
        _, range_end_utc = local_day_to_utc_window(end_day, cfg.tz_local)
        if range_end_utc > AVAILABLE_END_UTC:
            range_end_utc = AVAILABLE_END_UTC

        if range_start_utc < range_end_utc:
            rebuild_5m_from_1m(con, cfg, range_start_utc, range_end_utc)
            print("OK: rebuilt 5m bars for range")

        print(f"OK: bars_1m_mpl upsert total = {total}")

    finally:
        con.close()

    # build daily_features_mpl
    for d in reversed(list(daterange_inclusive(start_day, end_day))):
        cmd = [sys.executable, "scripts/build_daily_features_mpl.py", d.isoformat()]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"FAIL daily_features_mpl {d}:")
            print(r.stdout)
            print(r.stderr)
            sys.exit(r.returncode)
        else:
            print(f"OK: daily_features_mpl built for {d}")

    print("DONE")


if __name__ == "__main__":
    main()
