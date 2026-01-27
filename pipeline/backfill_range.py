from __future__ import annotations

import os
import sys
import datetime as dt
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import httpx
from dotenv import load_dotenv
from zoneinfo import ZoneInfo


# -----------------------------
# Config
# -----------------------------

@dataclass
class Cfg:
    base_url: str
    username: str
    api_key: str
    db_path: str = "gold.db"
    symbol: str = "MGC"         # logical symbol stored in DB
    live: bool = False          # ProjectX "live" flag (historical = False)
    tz_local: str = "Australia/Brisbane"


def env_cfg() -> Cfg:
    load_dotenv()
    base = os.getenv("PROJECTX_BASE_URL", "").strip()
    user = os.getenv("PROJECTX_USERNAME", "").strip()
    key = os.getenv("PROJECTX_API_KEY", "").strip()

    if not base.startswith("http"):
        raise RuntimeError("PROJECTX_BASE_URL must include https:// (e.g. https://api.topstepx.com)")
    if not user:
        raise RuntimeError("Missing PROJECTX_USERNAME in .env")
    if not key:
        raise RuntimeError("Missing PROJECTX_API_KEY in .env")

    db_path = os.getenv("DUCKDB_PATH", "gold.db").strip()
    symbol = os.getenv("SYMBOL", "MGC").strip()

    live_str = os.getenv("PROJECTX_LIVE", "false").strip().lower()
    live = live_str in ("1", "true", "yes", "y")

    tz_local = os.getenv("TZ_LOCAL", "Australia/Brisbane").strip() or "Australia/Brisbane"

    return Cfg(base_url=base, username=user, api_key=key, db_path=db_path, symbol=symbol, live=live, tz_local=tz_local)


# -----------------------------
# ProjectX minimal client
# -----------------------------

class ProjectX:
    def __init__(self, cfg: Cfg):
        self.cfg = cfg
        self.token: Optional[str] = None

    def _headers(self) -> Dict[str, str]:
        h = {"accept": "text/plain", "Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def login_key(self) -> str:
        url = f"{self.cfg.base_url}/api/Auth/loginKey"
        payload = {"userName": self.cfg.username, "apiKey": self.cfg.api_key}
        with httpx.Client(timeout=30.0) as client:
            r = client.post(url, headers=self._headers(), json=payload)
            r.raise_for_status()
            data = r.json()
        if not data.get("success"):
            raise RuntimeError(f"Login failed: {data}")
        self.token = data["token"]
        return self.token

    def contract_search(self, search_text: str) -> Dict[str, Any]:
        url = f"{self.cfg.base_url}/api/Contract/search"
        payload = {"searchText": search_text, "live": self.cfg.live}
        with httpx.Client(timeout=30.0) as client:
            r = client.post(url, headers=self._headers(), json=payload)
            r.raise_for_status()
            data = r.json()
        if not data.get("success"):
            raise RuntimeError(f"Contract search failed: {data}")
        return data

    def list_available_contracts(self) -> Dict[str, Any]:
        url = f"{self.cfg.base_url}/api/Contract/available"
        payload = {"live": self.cfg.live}
        with httpx.Client(timeout=30.0) as client:
            r = client.post(url, headers=self._headers(), json=payload)
            r.raise_for_status()
            data = r.json()
        if not data.get("success"):
            raise RuntimeError(f"Contract available failed: {data}")
        return data

    def retrieve_bars(
        self,
        contract_id: str,
        start_iso_z: str,
        end_iso_z: str,
        unit: int = 2,          # 2 = minute
        unit_number: int = 1,   # 1-minute
        limit: int = 20000,
        include_partial: bool = False,
    ) -> List[Dict[str, Any]]:
        url = f"{self.cfg.base_url}/api/History/retrieveBars"
        payload = {
            "contractId": contract_id,
            "live": self.cfg.live,
            "startTime": start_iso_z,
            "endTime": end_iso_z,
            "unit": unit,
            "unitNumber": unit_number,
            "limit": limit,
            "includePartialBar": include_partial,
        }
        with httpx.Client(timeout=60.0) as client:
            r = client.post(url, headers=self._headers(), json=payload)
            r.raise_for_status()
            data = r.json()
        if not data.get("success"):
            raise RuntimeError(f"retrieveBars failed: {data}")
        return data.get("bars") or []


# -----------------------------
# DuckDB writes
# -----------------------------

def upsert_bars_1m(con: duckdb.DuckDBPyConnection, cfg: Cfg, source_symbol: str, bars: List[Dict[str, Any]]) -> int:
    """
    Upsert into bars_1m using INSERT OR REPLACE on (symbol, ts_utc).
    bars format: {t,o,h,l,c,v}
    """
    if not bars:
        return 0

    rows = []
    for b in bars:
        rows.append((
            b["t"],                 # ISO timestamp with tz offset (UTC)
            cfg.symbol,
            source_symbol or None,
            float(b["o"]),
            float(b["h"]),
            float(b["l"]),
            float(b["c"]),
            int(b["v"]),
        ))

    con.executemany(
        """
        INSERT OR REPLACE INTO bars_1m
        (ts_utc, symbol, source_symbol, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def rebuild_5m_from_1m(con: duckdb.DuckDBPyConnection, cfg: Cfg, start_utc: str, end_utc: str) -> None:
    """
    Deterministic 1m -> 5m:
    bucket = floor(epoch(ts)/300)*300
    open  = arg_min(open, ts)
    close = arg_max(close, ts)
    high  = max(high)
    low   = min(low)
    volume= sum(volume)
    """
    con.execute(
        """
        DELETE FROM bars_5m
        WHERE symbol = ?
          AND ts_utc >= CAST(? AS TIMESTAMPTZ)
          AND ts_utc <  CAST(? AS TIMESTAMPTZ)
        """,
        [cfg.symbol, start_utc, end_utc],
    )

    con.execute(
        """
        INSERT INTO bars_5m (ts_utc, symbol, source_symbol, open, high, low, close, volume)
        SELECT
            CAST(to_timestamp(floor(epoch(ts_utc) / 300) * 300) AS TIMESTAMPTZ) AS ts_5m,
            symbol,
            NULL AS source_symbol,
            arg_min(open, ts_utc)  AS open,
            max(high)              AS high,
            min(low)               AS low,
            arg_max(close, ts_utc) AS close,
            sum(volume)            AS volume
        FROM bars_1m
        WHERE symbol = ?
          AND ts_utc >= CAST(? AS TIMESTAMPTZ)
          AND ts_utc <  CAST(? AS TIMESTAMPTZ)
        GROUP BY 1, 2
        ORDER BY 1
        """,
        [cfg.symbol, start_utc, end_utc],
    )


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

def iso_utc_from_local_date(d: dt.date, hh: int, mm: int = 0, ss: int = 0, tz_name: str = "Australia/Brisbane") -> str:
    """
    Convert local date + time to UTC ISO string.
    NOTE: Trading day = 09:00 -> next 09:00, so use hh=9 for trading day start.
    """
    tz = ZoneInfo(tz_name)
    local_dt = dt.datetime(d.year, d.month, d.day, hh, mm, ss, tzinfo=tz)
    utc_dt = local_dt.astimezone(dt.timezone.utc)
    return utc_dt.isoformat().replace("+00:00", "Z")


# -----------------------------
# Contract selection (rollover-safe without relying on expiry fields)
# -----------------------------

def _is_mgc_contract(c: Dict[str, Any]) -> bool:
    # Defensive: some APIs expose symbolId, some only name/description
    sid = (c.get("symbolId") or "").upper()
    name = (c.get("name") or "").upper()
    desc = (c.get("description") or "").upper()
    return ("MGC" in sid) or name.startswith("MGC") or ("MICRO GOLD" in desc)

def _contracts_newest_first(contracts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # We don’t have expiry fields in your current output.
    # Best-effort ordering: activeContract first, then reverse lexicographic on name (often MGCG6 > MGCZ5 > ...)
    def key(c: Dict[str, Any]) -> Tuple[int, str]:
        active = 1 if c.get("activeContract") else 0
        name = (c.get("name") or "")
        return (active, name)
    return sorted(contracts, key=key, reverse=True)

def pick_contract_for_day(
    px: ProjectX,
    mgc_contracts: List[Dict[str, Any]],
    start_iso_z: str,
    end_iso_z: str,
    preferred: Optional[Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Try preferred contract first. If no bars returned, scan other MGC contracts (newest->oldest)
    until we get bars. If none return bars, return (preferred, []).
    """
    tried_ids = set()

    def try_one(c: Dict[str, Any]) -> List[Dict[str, Any]]:
        cid = c.get("id")
        if not cid or cid in tried_ids:
            return []
        tried_ids.add(cid)
        return px.retrieve_bars(
            contract_id=cid,
            start_iso_z=start_iso_z,
            end_iso_z=end_iso_z,
            unit=2,
            unit_number=1,
            limit=20000,
            include_partial=False,
        )

    if preferred:
        bars = try_one(preferred)
        if bars:
            return preferred, bars

    for c in mgc_contracts:
        if preferred and c.get("id") == preferred.get("id"):
            continue
        bars = try_one(c)
        if bars:
            return c, bars

    return preferred, []


# -----------------------------
# Main
# -----------------------------

def main():
    if len(sys.argv) < 3:
        print("Usage: python backfill_range.py YYYY-MM-DD YYYY-MM-DD")
        print("Example: python backfill_range.py 2025-12-01 2026-01-09")
        sys.exit(1)

    cfg = env_cfg()
    start_day = parse_date(sys.argv[1])
    end_day = parse_date(sys.argv[2])

    px = ProjectX(cfg)
    px.login_key()

    # Pull all available contracts once
    avail = px.list_available_contracts()
    all_contracts = avail.get("contracts") or []
    mgc_contracts = [c for c in all_contracts if _is_mgc_contract(c)]
    mgc_contracts = _contracts_newest_first(mgc_contracts)

    if not mgc_contracts:
        raise RuntimeError("No MGC contracts returned from /api/Contract/available. Cannot backfill older dates.")

    # Show a quick summary
    print(f"Available contracts: {len(all_contracts)} | MGC-like: {len(mgc_contracts)} | live={cfg.live}")
    print(f"DB={cfg.db_path} symbol={cfg.symbol} tz_local={cfg.tz_local}")

    con = duckdb.connect(cfg.db_path)

    total = 0
    current_contract: Optional[Dict[str, Any]] = None

    # Pull 1 LOCAL day at a time: [local 09:00 -> next local 09:00] converted to UTC
    for d in daterange_inclusive(start_day, end_day):
        start_utc = iso_utc_from_local_date(d, 9, 0, 0, cfg.tz_local)
        end_utc = iso_utc_from_local_date(d + dt.timedelta(days=1), 9, 0, 0, cfg.tz_local)

        picked, bars = pick_contract_for_day(px, mgc_contracts, start_utc, end_utc, current_contract)
        current_contract = picked

        source_symbol = (picked.get("name") if picked else None) or ""
        contract_id = (picked.get("id") if picked else None) or ""

        inserted = upsert_bars_1m(con, cfg, source_symbol, bars)
        total += inserted

        if inserted > 0:
            print(f"{d} -> {source_symbol} ({contract_id}) -> inserted/replaced {inserted} rows")
        else:
            # Keep visibility: could be closed day, outage, or wrong contract set
            print(f"{d} -> {source_symbol or 'NO_CONTRACT'} -> inserted/replaced 0 rows")

    # Build 5m for the whole LOCAL range in one shot
    range_start_utc = iso_utc_from_local_date(start_day, 9, 0, 0, cfg.tz_local)
    range_end_utc = iso_utc_from_local_date(end_day + dt.timedelta(days=1), 9, 0, 0, cfg.tz_local)

    rebuild_5m_from_1m(con, cfg, range_start_utc, range_end_utc)
    print("OK: rebuilt 5m bars for range")

    con.close()
    print(f"OK: bars_1m upsert total = {total}")

    # Build daily_features (calls your existing script)
    for d in daterange_inclusive(start_day, end_day):
        cmd = [sys.executable, "build_daily_features.py", d.isoformat()]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"FAIL daily_features {d}:")
            print(r.stdout)
            print(r.stderr)
            sys.exit(r.returncode)
        else:
            print(f"OK: daily_features built for {d}")

    print("DONE")


if __name__ == "__main__":
    main()
