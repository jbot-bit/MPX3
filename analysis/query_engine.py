from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import duckdb
import numpy as np
import pandas as pd

# UI helper for Streamlit dashboards
# Keys are the internal IDs used in app_trading_hub.py dropdowns.
ENTRY_MODELS = {
    "1m_close_break": {
        "label": "1m close break",
        "desc": "Enter on 1m close beyond ORB high/low",
    },
    "5m_close_break": {
        "label": "5m close break",
        "desc": "Enter on 5m close beyond ORB high/low",
    },
    "retest_reject": {
        "label": "Retest + reject",
        "desc": "Break -> retest -> rejection confirmation",
    },
}

ORB_TIMES: Tuple[str, ...] = ("0900", "1000", "1100", "1800", "2300", "0030")
OUTCOME_OPTIONS: Tuple[str, ...] = ("WIN", "LOSS", "NO_TRADE")
BREAK_DIR_OPTIONS: Tuple[str, ...] = ("ANY", "UP", "DOWN")


@dataclass(frozen=True)
class Filters:
    start_date: Optional[str]
    end_date: Optional[str]
    orb_times: Tuple[str, ...]
    break_dir: str
    outcomes: Tuple[str, ...]
    asia_type_code: Optional[str]
    include_null_asia: bool
    london_type_code: Optional[str]
    include_null_london: bool
    pre_ny_type_code: Optional[str]
    include_null_pre_ny: bool
    enable_atr_filter: bool
    atr_min: Optional[float]
    atr_max: Optional[float]
    enable_asia_range_filter: bool
    asia_range_min: Optional[float]
    asia_range_max: Optional[float]


@dataclass(frozen=True)
class StrategyConfig:
    level_basis: str  # "orb_boundary" | "orb_half"
    entry_model: str  # "1m_close_break" | "1m_close_break_confirmed" | "5m_close_break" | "break_retest_reject"
    confirm_closes: int
    retest_required: bool
    retest_rule: str  # "touch" | "pierce_by_ticks"
    pierce_ticks: Optional[int]
    rejection_tf: str  # "1m" | "5m"
    stop_rule: str  # "ORB_opposite_boundary"
    max_stop_ticks: Optional[int]
    cutoff_minutes: Optional[int]
    one_trade_per_orb: bool


PRESETS: Dict[str, StrategyConfig] = {
    "Boundary | 1m Break (1 close)": StrategyConfig(
        level_basis="orb_boundary",
        entry_model="1m_close_break",
        confirm_closes=1,
        retest_required=False,
        retest_rule="touch",
        pierce_ticks=None,
        rejection_tf="1m",
        stop_rule="ORB_opposite_boundary",
        max_stop_ticks=None,
        cutoff_minutes=None,
        one_trade_per_orb=True,
    ),
    "Boundary | 1m Break (2 closes)": StrategyConfig(
        level_basis="orb_boundary",
        entry_model="1m_close_break_confirmed",
        confirm_closes=2,
        retest_required=False,
        retest_rule="touch",
        pierce_ticks=None,
        rejection_tf="1m",
        stop_rule="ORB_opposite_boundary",
        max_stop_ticks=None,
        cutoff_minutes=None,
        one_trade_per_orb=True,
    ),
    "Boundary | 5m Break (1 close)": StrategyConfig(
        level_basis="orb_boundary",
        entry_model="5m_close_break",
        confirm_closes=1,
        retest_required=False,
        retest_rule="touch",
        pierce_ticks=None,
        rejection_tf="1m",
        stop_rule="ORB_opposite_boundary",
        max_stop_ticks=None,
        cutoff_minutes=None,
        one_trade_per_orb=True,
    ),
    "Boundary | Break + Retest + 1m Reject": StrategyConfig(
        level_basis="orb_boundary",
        entry_model="break_retest_reject",
        confirm_closes=1,
        retest_required=True,
        retest_rule="touch",
        pierce_ticks=None,
        rejection_tf="1m",
        stop_rule="ORB_opposite_boundary",
        max_stop_ticks=None,
        cutoff_minutes=None,
        one_trade_per_orb=True,
    ),
    "Half ORB | 1m Break (1 close)": StrategyConfig(
        level_basis="orb_half",
        entry_model="1m_close_break",
        confirm_closes=1,
        retest_required=False,
        retest_rule="touch",
        pierce_ticks=None,
        rejection_tf="1m",
        stop_rule="ORB_opposite_boundary",
        max_stop_ticks=None,
        cutoff_minutes=None,
        one_trade_per_orb=True,
    ),
    "Half ORB | 1m Break (2 closes)": StrategyConfig(
        level_basis="orb_half",
        entry_model="1m_close_break_confirmed",
        confirm_closes=2,
        retest_required=False,
        retest_rule="touch",
        pierce_ticks=None,
        rejection_tf="1m",
        stop_rule="ORB_opposite_boundary",
        max_stop_ticks=None,
        cutoff_minutes=None,
        one_trade_per_orb=True,
    ),
    "Half ORB | Break + Retest + 1m Reject": StrategyConfig(
        level_basis="orb_half",
        entry_model="break_retest_reject",
        confirm_closes=1,
        retest_required=True,
        retest_rule="touch",
        pierce_ticks=None,
        rejection_tf="1m",
        stop_rule="ORB_opposite_boundary",
        max_stop_ticks=None,
        cutoff_minutes=None,
        one_trade_per_orb=True,
    ),
}


def default_strategy() -> StrategyConfig:
    return PRESETS["Boundary | 1m Break (1 close)"]


def get_connection(db_path: str = "gold.db") -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection to the gold database."""
    return duckdb.connect(db_path)


def fetch_filter_metadata(con: duckdb.DuckDBPyConnection) -> Dict[str, Any]:
    """Collect filter metadata (date bounds, numeric ranges, and type codes)."""
    min_max_row = con.execute(
        """
        SELECT
          MIN(v.date_local) AS min_date,
          MAX(v.date_local) AS max_date,
          MIN(df.atr_20) AS min_atr,
          MAX(df.atr_20) AS max_atr,
          MIN(df.asia_range) AS min_asia_range,
          MAX(df.asia_range) AS max_asia_range
        FROM v_orb_trades v
        JOIN daily_features df
          ON df.date_local = v.date_local AND df.instrument = v.instrument
        """
    ).fetchone()

    # Default fallbacks if table is empty
    min_date, max_date, min_atr, max_atr, min_asia_range, max_asia_range = (
        min_max_row if min_max_row is not None else (None, None, None, None, None, None)
    )

    def _list_codes(column: str) -> List[str]:
        # Query daily_features_half directly for type codes
        rows = con.execute(
            f"""
            SELECT DISTINCT {column}
            FROM daily_features_half
            WHERE {column} IS NOT NULL
            AND instrument = 'MGC'
            ORDER BY {column}
            """
        ).fetchall()
        return [r[0] for r in rows]

    return {
        "min_date": min_date,
        "max_date": max_date,
        "min_atr": min_atr,
        "max_atr": max_atr,
        "min_asia_range": min_asia_range,
        "max_asia_range": max_asia_range,
        "asia_type_codes": _list_codes("asia_type_code"),
        "london_type_codes": _list_codes("london_type_code"),
        "pre_ny_type_codes": _list_codes("pre_ny_type_code"),
    }


def filters_key(filters: Filters) -> Tuple[Any, ...]:
    """Tuple key for caching."""
    return (
        filters.start_date,
        filters.end_date,
        filters.orb_times,
        filters.break_dir,
        filters.outcomes,
        filters.asia_type_code,
        filters.include_null_asia,
        filters.london_type_code,
        filters.include_null_london,
        filters.pre_ny_type_code,
        filters.include_null_pre_ny,
        filters.enable_atr_filter,
        filters.atr_min,
        filters.atr_max,
        filters.enable_asia_range_filter,
        filters.asia_range_min,
        filters.asia_range_max,
    )


def strategy_key(strategy: StrategyConfig) -> Tuple[Any, ...]:
    """Tuple key for caching strategy-specific results."""
    return (
        strategy.level_basis,
        strategy.entry_model,
        strategy.confirm_closes,
        strategy.retest_required,
        strategy.retest_rule,
        strategy.pierce_ticks,
        strategy.rejection_tf,
        strategy.stop_rule,
        strategy.max_stop_ticks,
        strategy.cutoff_minutes,
        strategy.one_trade_per_orb,
    )


def serialize_filters(filters: Filters) -> Dict[str, Any]:
    """Convert Filters to a JSON-serializable dict."""
    data = asdict(filters)
    # Tuples become lists for JSON friendliness
    data["orb_times"] = list(filters.orb_times)
    data["outcomes"] = list(filters.outcomes)
    return data


def filters_from_dict(payload: Dict[str, Any]) -> Filters:
    """Reconstruct Filters from serialized dict."""
    return Filters(
        start_date=payload.get("start_date"),
        end_date=payload.get("end_date"),
        orb_times=tuple(payload.get("orb_times", [])),
        break_dir=payload.get("break_dir", "ANY"),
        outcomes=tuple(payload.get("outcomes", [])),
        asia_type_code=payload.get("asia_type_code"),
        include_null_asia=payload.get("include_null_asia", True),
        london_type_code=payload.get("london_type_code"),
        include_null_london=payload.get("include_null_london", True),
        pre_ny_type_code=payload.get("pre_ny_type_code"),
        include_null_pre_ny=payload.get("include_null_pre_ny", True),
        enable_atr_filter=payload.get("enable_atr_filter", False),
        atr_min=payload.get("atr_min"),
        atr_max=payload.get("atr_max"),
        enable_asia_range_filter=payload.get("enable_asia_range_filter", False),
        asia_range_min=payload.get("asia_range_min"),
        asia_range_max=payload.get("asia_range_max"),
    )


def serialize_strategy(strategy: StrategyConfig) -> Dict[str, Any]:
    data = asdict(strategy)
    return data


def strategy_from_dict(payload: Dict[str, Any]) -> StrategyConfig:
    return StrategyConfig(
        level_basis=payload.get("level_basis", "orb_boundary"),
        entry_model=payload.get("entry_model", "1m_close_break"),
        confirm_closes=int(payload.get("confirm_closes", 1)),
        retest_required=bool(payload.get("retest_required", False)),
        retest_rule=payload.get("retest_rule", "touch"),
        pierce_ticks=payload.get("pierce_ticks"),
        rejection_tf=payload.get("rejection_tf", "1m"),
        stop_rule=payload.get("stop_rule", "ORB_opposite_boundary"),
        max_stop_ticks=payload.get("max_stop_ticks"),
        cutoff_minutes=payload.get("cutoff_minutes"),
        one_trade_per_orb=bool(payload.get("one_trade_per_orb", True)),
    )


def _build_where_clause(
    filters: Filters,
    *,
    include_outcome_filter: bool = True,
    trades_only: bool = False,
    table_alias: Optional[str] = None,
) -> Tuple[str, List[Any]]:
    """Construct WHERE clause and parameter list based on the provided filters."""
    alias = f"{table_alias}." if table_alias else ""
    conditions: List[str] = []
    params: List[Any] = []

    if filters.start_date:
        conditions.append(f"{alias}date_local >= ?")
        params.append(filters.start_date)
    if filters.end_date:
        conditions.append(f"{alias}date_local <= ?")
        params.append(filters.end_date)

    if filters.orb_times:
        placeholders = ",".join(["?"] * len(filters.orb_times))
        conditions.append(f"{alias}orb_time IN ({placeholders})")
        params.extend(filters.orb_times)

    if filters.break_dir and filters.break_dir != "ANY":
        conditions.append(f"{alias}break_dir = ?")
        params.append(filters.break_dir)

    if include_outcome_filter and filters.outcomes:
        placeholders = ",".join(["?"] * len(filters.outcomes))
        conditions.append(f"{alias}outcome IN ({placeholders})")
        params.extend(filters.outcomes)

    if trades_only:
        conditions.append(f"{alias}outcome IN ('WIN','LOSS')")

    if filters.asia_type_code:
        if filters.include_null_asia:
            conditions.append(f"({alias}asia_type_code = ? OR {alias}asia_type_code IS NULL)")
        else:
            conditions.append(f"{alias}asia_type_code = ?")
        params.append(filters.asia_type_code)
    if filters.london_type_code:
        if filters.include_null_london:
            conditions.append(f"({alias}london_type_code = ? OR {alias}london_type_code IS NULL)")
        else:
            conditions.append(f"{alias}london_type_code = ?")
        params.append(filters.london_type_code)
    if filters.pre_ny_type_code:
        if filters.include_null_pre_ny:
            conditions.append(f"({alias}pre_ny_type_code = ? OR {alias}pre_ny_type_code IS NULL)")
        else:
            conditions.append(f"{alias}pre_ny_type_code = ?")
        params.append(filters.pre_ny_type_code)

    if filters.enable_atr_filter:
        if filters.atr_min is not None:
            conditions.append(f"{alias}atr_20 >= ?")
            params.append(filters.atr_min)
        if filters.atr_max is not None:
            conditions.append(f"{alias}atr_20 <= ?")
            params.append(filters.atr_max)

    if filters.enable_asia_range_filter:
        if filters.asia_range_min is not None:
            conditions.append(f"{alias}asia_range >= ?")
            params.append(filters.asia_range_min)
        if filters.asia_range_max is not None:
            conditions.append(f"{alias}asia_range <= ?")
            params.append(filters.asia_range_max)

    where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    return where_sql, params


def _sanitize(df: pd.DataFrame) -> pd.DataFrame:
    """Replace inf/NaN with None for JSON safety."""
    return df.replace([np.inf, -np.inf], np.nan).where(pd.notnull(df), None)


def _fetch_base_frame(con: duckdb.DuckDBPyConnection, filters: Filters) -> pd.DataFrame:
    """Base frame with ORB prices and optional close confirmations."""
    where_sql, params = _build_where_clause(filters, include_outcome_filter=True, trades_only=False, table_alias="v")
    sql = f"""
    WITH execs AS (
      SELECT date_local, orb AS orb_time, MAX(close_confirmations) AS close_confirmations
      FROM orb_trades_1m_exec
      GROUP BY date_local, orb
    )
    SELECT
      v.date_local,
      v.instrument,
      v.orb_time,
      v.break_dir,
      v.outcome,
      v.r_multiple,
      df.asia_type_code,
      df.london_type_code,
      df.pre_ny_type_code,
      df.asia_range,
      df.london_range,
      df.pre_ny_range,
      df.atr_20,
      CASE v.orb_time
        WHEN '0900' THEN df.orb_0900_high
        WHEN '1000' THEN df.orb_1000_high
        WHEN '1100' THEN df.orb_1100_high
        WHEN '1800' THEN df.orb_1800_high
        WHEN '2300' THEN df.orb_2300_high
        WHEN '0030' THEN df.orb_0030_high
      END AS orb_high,
      CASE v.orb_time
        WHEN '0900' THEN df.orb_0900_low
        WHEN '1000' THEN df.orb_1000_low
        WHEN '1100' THEN df.orb_1100_low
        WHEN '1800' THEN df.orb_1800_low
        WHEN '2300' THEN df.orb_2300_low
        WHEN '0030' THEN df.orb_0030_low
      END AS orb_low,
      CASE v.orb_time
        WHEN '0900' THEN df.orb_0900_size
        WHEN '1000' THEN df.orb_1000_size
        WHEN '1100' THEN df.orb_1100_size
        WHEN '1800' THEN df.orb_1800_size
        WHEN '2300' THEN df.orb_2300_size
        WHEN '0030' THEN df.orb_0030_size
      END AS orb_size,
      ex.close_confirmations
    FROM v_orb_trades v
    JOIN daily_features df
      ON df.date_local = v.date_local AND df.instrument = v.instrument
    LEFT JOIN execs ex
      ON ex.date_local = v.date_local AND ex.orb_time = v.orb_time
    {where_sql}
    """
    try:
        df = con.execute(sql, params).fetchdf()
    except duckdb.Error:
        # Fallback if execs table missing
        sql_no_exec = f"""
        SELECT
          v.date_local,
          v.instrument,
          v.orb_time,
          v.break_dir,
          v.outcome,
          v.r_multiple,
          df.asia_type_code,
          df.london_type_code,
          df.pre_ny_type_code,
          df.asia_range,
          df.london_range,
          df.pre_ny_range,
          df.atr_20,
          CASE v.orb_time
            WHEN '0900' THEN df.orb_0900_high
            WHEN '1000' THEN df.orb_1000_high
            WHEN '1100' THEN df.orb_1100_high
            WHEN '1800' THEN df.orb_1800_high
            WHEN '2300' THEN df.orb_2300_high
            WHEN '0030' THEN df.orb_0030_high
          END AS orb_high,
          CASE v.orb_time
            WHEN '0900' THEN df.orb_0900_low
            WHEN '1000' THEN df.orb_1000_low
            WHEN '1100' THEN df.orb_1100_low
            WHEN '1800' THEN df.orb_1800_low
            WHEN '2300' THEN df.orb_2300_low
            WHEN '0030' THEN df.orb_0030_low
          END AS orb_low,
          CASE v.orb_time
            WHEN '0900' THEN df.orb_0900_size
            WHEN '1000' THEN df.orb_1000_size
            WHEN '1100' THEN df.orb_1100_size
            WHEN '1800' THEN df.orb_1800_size
            WHEN '2300' THEN df.orb_2300_size
            WHEN '0030' THEN df.orb_0030_size
          END AS orb_size,
          NULL AS close_confirmations
        FROM v_orb_trades v
        JOIN daily_features df
          ON df.date_local = v.date_local AND df.instrument = v.instrument
        {where_sql}
        """
        df = con.execute(sql_no_exec, params).fetchdf()
    return df


def _required_closes(strategy: StrategyConfig) -> int:
    if strategy.entry_model == "1m_close_break":
        return 1
    if strategy.entry_model == "1m_close_break_confirmed":
        return max(strategy.confirm_closes, 1)
    if strategy.entry_model == "5m_close_break":
        return 1
    return max(strategy.confirm_closes, 1)


def _apply_strategy(df: pd.DataFrame, strategy: StrategyConfig) -> pd.DataFrame:
    frame = df.copy()
    frame["orb_mid"] = (frame["orb_high"] + frame["orb_low"]) / 2
    frame["level_basis"] = strategy.level_basis
    frame["broke_side"] = frame["break_dir"]
    frame["level_price"] = np.where(
        strategy.level_basis == "orb_half",
        frame["orb_mid"],
        np.where(frame["break_dir"] == "UP", frame["orb_high"], frame["orb_low"]),
    )
    frame["stop_ticks"] = np.where(
        strategy.level_basis == "orb_half",
        frame["orb_size"] / 2 if "orb_size" in frame else np.nan,
        frame["orb_size"],
    )
    frame["break_occurred"] = frame["outcome"] != "NO_TRADE"
    if "close_confirmations" in frame:
        confirm_series = frame["close_confirmations"]
    else:
        confirm_series = pd.Series(np.nan, index=frame.index)
    default_confirms = pd.Series(np.where(frame["break_occurred"], 1, 0), index=frame.index)
    frame["confirm_closes_hit"] = confirm_series.fillna(default_confirms)
    required_closes = _required_closes(strategy)
    frame["confirm_required"] = required_closes
    frame["confirm_pass"] = frame["confirm_closes_hit"] >= required_closes

    # Retest / rejection flags (no tick-level data, assume pass if a break occurred)
    frame["retest_hit"] = np.where(frame["break_occurred"], True, False)
    frame["rejection_hit"] = np.where(frame["break_occurred"], True, False)

    def _fail_reason(row: pd.Series) -> Optional[str]:
        if not row.get("break_occurred", False):
            return "no_break"
        if not row.get("confirm_pass", False):
            return "confirm_not_met"
        if strategy.retest_required and not row.get("retest_hit", False):
            return "retest_not_met"
        if strategy.retest_required and strategy.entry_model == "break_retest_reject" and not row.get(
            "rejection_hit", False
        ):
            return "rejection_not_met"
        if (
            strategy.max_stop_ticks is not None
            and row.get("stop_ticks") is not None
            and pd.notnull(row.get("stop_ticks"))
            and row.get("stop_ticks") > strategy.max_stop_ticks
        ):
            return "stop_too_large"
        return None

    frame["filtered_out_reason"] = frame.apply(_fail_reason, axis=1)
    frame["eligible_trade"] = frame["filtered_out_reason"].isnull() & frame["outcome"].isin(["WIN", "LOSS"])
    return frame


def strategy_dataset(con: duckdb.DuckDBPyConnection, filters: Filters, strategy: StrategyConfig) -> pd.DataFrame:
    """Return strategy-aware dataset."""
    base = _fetch_base_frame(con, filters)
    df = _apply_strategy(base, strategy)
    return df


def headline_stats(con: duckdb.DuckDBPyConnection, filters: Filters) -> Dict[str, Any]:
    """Backward-compatible wrapper using default strategy."""
    return headline_stats_with_strategy(con, filters, default_strategy())


def equity_curve(con: duckdb.DuckDBPyConnection, filters: Filters) -> pd.DataFrame:
    """Return cumulative equity curve for trades (WIN/LOSS) ordered by date and ORB."""
    return equity_curve_with_strategy(con, filters, default_strategy())


def histogram(con: duckdb.DuckDBPyConnection, filters: Filters) -> pd.DataFrame:
    """Return r_multiple values for histogram plotting (WIN/LOSS only)."""
    return histogram_with_strategy(con, filters, default_strategy())


def heatmap(con: duckdb.DuckDBPyConnection, filters: Filters) -> pd.DataFrame:
    """Return heatmap data (Avg R and WR) grouped by Asia x London type codes."""
    return heatmap_with_strategy(con, filters, default_strategy())


def drilldown(
    con: duckdb.DuckDBPyConnection,
    filters: Filters,
    limit: Optional[int] = 500,
    order: str = "chronological",
) -> pd.DataFrame:
    """Return drilldown rows (date + ORB detail) with an optional limit."""
    return drilldown_with_strategy(con, filters, default_strategy(), limit=limit, order=order)


def drilldown_full(con: duckdb.DuckDBPyConnection, filters: Filters, order: str = "chronological") -> pd.DataFrame:
    """Return full filtered dataset (no limit) for CSV export."""
    return drilldown_full_with_strategy(con, filters, default_strategy(), order=order)


def headline_stats_with_strategy(
    con: duckdb.DuckDBPyConnection, filters: Filters, strategy: StrategyConfig
) -> Dict[str, Any]:
    df = strategy_dataset(con, filters, strategy)
    trades_df = df[df["eligible_trade"]]
    trades = len(trades_df)
    wins = len(trades_df[trades_df["outcome"] == "WIN"])
    avg_r = float(trades_df["r_multiple"].mean()) if not trades_df.empty else 0.0
    total_r = float(trades_df["r_multiple"].sum()) if not trades_df.empty else 0.0

    # Opportunities ignore the outcome filter so NO_TRADE rows are always counted.
    opportunities = len(df)

    # Baseline using date window only
    base_filters = Filters(
        start_date=filters.start_date,
        end_date=filters.end_date,
        orb_times=(),
        break_dir="ANY",
        outcomes=(),
        asia_type_code=None,
        include_null_asia=True,
        london_type_code=None,
        include_null_london=True,
        pre_ny_type_code=None,
        include_null_pre_ny=True,
        enable_atr_filter=False,
        atr_min=None,
        atr_max=None,
        enable_asia_range_filter=False,
        asia_range_min=None,
        asia_range_max=None,
    )
    base_df = strategy_dataset(con, base_filters, strategy)
    base_opportunities = len(base_df)
    base_trades = len(base_df[base_df["outcome"].isin(["WIN", "LOSS"])])

    return {
        "trades": trades,
        "wins": wins,
        "avg_r": avg_r,
        "total_r": total_r,
        "opportunities": opportunities,
        "base_opportunities": base_opportunities,
        "base_trades": base_trades,
    }


def equity_curve_with_strategy(
    con: duckdb.DuckDBPyConnection, filters: Filters, strategy: StrategyConfig
) -> pd.DataFrame:
    df = strategy_dataset(con, filters, strategy)
    trades = df[df["eligible_trade"]].copy()
    trades = trades.sort_values(["date_local", "orb_time"])
    trades["equity"] = trades["r_multiple"].cumsum()
    return trades[["date_local", "orb_time", "r_multiple", "equity"]]


def histogram_with_strategy(
    con: duckdb.DuckDBPyConnection, filters: Filters, strategy: StrategyConfig
) -> pd.DataFrame:
    df = strategy_dataset(con, filters, strategy)
    trades = df[df["eligible_trade"]].copy()
    return trades[["r_multiple"]].dropna()


def heatmap_with_strategy(
    con: duckdb.DuckDBPyConnection, filters: Filters, strategy: StrategyConfig
) -> pd.DataFrame:
    df = strategy_dataset(con, filters, strategy)
    trades = df[df["eligible_trade"]].copy()
    if trades.empty:
        return trades
    grouped = (
        trades.groupby(["asia_type_code", "london_type_code"])
        .agg(
            avg_r=("r_multiple", "mean"),
            win_rate=("outcome", lambda s: (s == "WIN").mean()),
            count_rows=("outcome", "count"),
        )
        .reset_index()
    )
    return _sanitize(grouped)


def drilldown_with_strategy(
    con: duckdb.DuckDBPyConnection,
    filters: Filters,
    strategy: StrategyConfig,
    limit: Optional[int] = 500,
    order: str = "chronological",
) -> pd.DataFrame:
    df = strategy_dataset(con, filters, strategy)
    if order == "r_multiple_desc":
        df = df.sort_values(["r_multiple"], ascending=False, na_position="last")
    else:
        df = df.sort_values(["date_local", "orb_time"])
    if limit is not None:
        df = df.head(limit)
    return _sanitize(df)


def drilldown_full_with_strategy(
    con: duckdb.DuckDBPyConnection, filters: Filters, strategy: StrategyConfig, order: str = "chronological"
) -> pd.DataFrame:
    return drilldown_with_strategy(con, filters, strategy, limit=None, order=order)


def entry_funnel(con: duckdb.DuckDBPyConnection, filters: Filters, strategy: StrategyConfig) -> Dict[str, int]:
    df = strategy_dataset(con, filters, strategy)
    total = len(df)
    break_occurred = int((df["break_occurred"]).sum())
    confirm_met = int((df["break_occurred"] & df["confirm_pass"]).sum())
    if strategy.retest_required:
        retest_met = int((df["break_occurred"] & df["confirm_pass"] & df["retest_hit"]).sum())
        rejection_met = int((df["break_occurred"] & df["confirm_pass"] & df["retest_hit"] & df["rejection_hit"]).sum())
    else:
        retest_met = confirm_met
        rejection_met = confirm_met
    trades = int(df["eligible_trade"].sum())
    wins = int(df[df["eligible_trade"] & (df["outcome"] == "WIN")].shape[0])
    losses = int(df[df["eligible_trade"] & (df["outcome"] == "LOSS")].shape[0])
    return {
        "total_orbs": total,
        "break_occurred": break_occurred,
        "confirm_met": confirm_met,
        "retest_met": retest_met,
        "rejection_met": rejection_met,
        "trades": trades,
        "wins": wins,
        "losses": losses,
    }
