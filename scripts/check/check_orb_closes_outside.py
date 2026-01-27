from trading_app.cloud_mode import get_database_connection

con = get_database_connection()

# Brisbane is UTC+10 (no DST). We'll convert "local Brisbane timestamps" -> UTC by subtracting 10 hours.
UTC_OFFSET_HOURS = 10

def to_utc_expr(local_ts_str):
    # local_ts_str like "2026-01-10 23:05:00"
    # return a duckdb expression result string in UTC
    return con.execute(
        "SELECT (CAST(? AS TIMESTAMP) - INTERVAL " + str(UTC_OFFSET_HOURS) + " HOUR)::VARCHAR",
        [local_ts_str]
    ).fetchone()[0]

def scan_orb(orb_time, orb_end_hhmm, scan_end_hhmm, instrument="MGC", limit_days=120):
    hi_col = f"orb_{orb_time}_high"
    lo_col = f"orb_{orb_time}_low"

    # confirm columns exist
    feat_cols = [r[1] for r in con.execute("PRAGMA table_info('daily_features')").fetchall()]
    if hi_col not in feat_cols or lo_col not in feat_cols:
        raise Exception(f"Missing ORB cols for {orb_time}: need {hi_col}, {lo_col}")

    # pick date col name
    date_col = "date_local" if "date_local" in feat_cols else ("date" if "date" in feat_cols else None)
    inst_col = "instrument" if "instrument" in feat_cols else ("symbol" if "symbol" in feat_cols else None)
    if not date_col or not inst_col:
        raise Exception(f"daily_features missing date/instrument cols. Found: {feat_cols}")

    days = con.execute(f"""
        SELECT {date_col} AS d, {hi_col} AS hi, {lo_col} AS lo
        FROM daily_features
        WHERE {inst_col} = ?
          AND {hi_col} IS NOT NULL
          AND {lo_col} IS NOT NULL
        ORDER BY {date_col} DESC
        LIMIT ?
    """, [instrument, limit_days]).fetchall()

    days = list(reversed(days))  # oldest->newest
    day_stats = []

    for d, hi, lo in days:
        d = str(d)

        # local Brisbane window
        start_local = f"{d} {orb_end_hhmm}:00"
        end_local   = f"{d} {scan_end_hhmm}:00"

        # if end earlier than start, end is next day
        if scan_end_hhmm < orb_end_hhmm:
            end_local = con.execute(
                "SELECT (CAST(? AS TIMESTAMP) + INTERVAL 1 DAY)::VARCHAR",
                [end_local]
            ).fetchone()[0]

        # convert to UTC strings
        start_utc = to_utc_expr(start_local)
        end_utc   = to_utc_expr(end_local)

        total_outside = con.execute("""
            SELECT COUNT(*)
            FROM bars_1m
            WHERE symbol = ?
              AND ts_utc >= CAST(? AS TIMESTAMP)
              AND ts_utc <= CAST(? AS TIMESTAMP)
              AND (close > ? OR close < ?)
        """, [instrument, start_utc, end_utc, hi, lo]).fetchone()[0]

        any_outside = 1 if total_outside > 0 else 0
        day_stats.append((d, float(hi), float(lo), int(any_outside), int(total_outside)))

    days_with = sum(x[3] for x in day_stats)
    total_closes = sum(x[4] for x in day_stats)
    n = len(day_stats)
    pct = (days_with / n * 100.0) if n else 0.0
    avg = (total_closes / n) if n else 0.0

    print(f"\nORB {orb_time} instrument={instrument} days={n}")
    print(f"Days w/ >=1 close outside: {days_with}/{n} = {pct:.1f}%")
    print(f"Total closes outside: {total_closes}")
    print(f"Avg closes outside per day: {avg:.2f}")

    print("\nLast 10 days sample (date, hi, lo, any_outside, closes_outside):")
    for row in day_stats[-10:]:
        print(row)

# 2300: ORB ends 23:05, scan to 09:00 next day (Brisbane local)
scan_orb("2300", "23:05", "09:00", instrument="MGC", limit_days=120)

# 0030: ORB ends 00:35, scan to 09:00 same day (Brisbane local)
scan_orb("0030", "00:35", "09:00", instrument="MGC", limit_days=120)

con.close()
print("\nDONE")
