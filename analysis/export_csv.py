"""
CSV Export Tool
===============
Export MGC data and analysis results to CSV files for Excel, Python notebooks, etc.

Usage:
  python export_csv.py daily_features              # Export all daily features
  python export_csv.py daily_features --days 30    # Export last 30 days
  python export_csv.py orb_performance             # Export ORB win/loss by setup
  python export_csv.py session_stats               # Export session type statistics
  python export_csv.py bars_1m 2026-01-09          # Export 1-minute bars for specific date
  python export_csv.py bars_5m 2026-01-09          # Export 5-minute bars for specific date

All exports go to ./exports/ directory
"""

import duckdb
import argparse
import os
from datetime import date, timedelta
from typing import Optional


class CSVExporter:
    """Export MGC data to CSV files"""

    def __init__(self, db_path: str = "gold.db", output_dir: str = "exports"):
        self.db_path = db_path
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def export_daily_features(self, days: Optional[int] = None, output_file: Optional[str] = None) -> str:
        """Export daily_features table to CSV"""
        con = duckdb.connect(self.db_path, read_only=True)

        try:
            # Build query
            where_clause = ""
            if days:
                cutoff_date = date.today() - timedelta(days=days)
                where_clause = f"WHERE date_local >= '{cutoff_date.isoformat()}'"

            query = f"""
                SELECT
                    date_local,
                    instrument,
                    asia_high,
                    asia_low,
                    asia_range,
                    (asia_range / 0.1) AS asia_range_ticks,
                    asia_type,
                    london_high,
                    london_low,
                    london_type,
                    ny_high,
                    ny_low,
                    ny_type,
                    pre_ny_travel,
                    pre_orb_travel,
                    atr_20,
                    -- ORB 09:00
                    orb_0900_high,
                    orb_0900_low,
                    orb_0900_size,
                    (orb_0900_size / 0.1) AS orb_0900_size_ticks,
                    orb_0900_break_dir,
                    orb_0900_outcome,
                    orb_0900_r_multiple,
                    orb_0900_mae,
                    orb_0900_mfe,
                    -- ORB 10:00
                    orb_1000_high,
                    orb_1000_low,
                    orb_1000_size,
                    (orb_1000_size / 0.1) AS orb_1000_size_ticks,
                    orb_1000_break_dir,
                    orb_1000_outcome,
                    orb_1000_r_multiple,
                    orb_1000_mae,
                    orb_1000_mfe,
                    -- ORB 11:00
                    orb_1100_high,
                    orb_1100_low,
                    orb_1100_size,
                    (orb_1100_size / 0.1) AS orb_1100_size_ticks,
                    orb_1100_break_dir,
                    orb_1100_outcome,
                    orb_1100_r_multiple,
                    orb_1100_mae,
                    orb_1100_mfe,
                    -- ORB 18:00
                    orb_1800_high,
                    orb_1800_low,
                    orb_1800_size,
                    (orb_1800_size / 0.1) AS orb_1800_size_ticks,
                    orb_1800_break_dir,
                    orb_1800_outcome,
                    orb_1800_r_multiple,
                    orb_1800_mae,
                    orb_1800_mfe,
                    -- ORB 23:00
                    orb_2300_high,
                    orb_2300_low,
                    orb_2300_size,
                    (orb_2300_size / 0.1) AS orb_2300_size_ticks,
                    orb_2300_break_dir,
                    orb_2300_outcome,
                    orb_2300_r_multiple,
                    orb_2300_mae,
                    orb_2300_mfe,
                    -- ORB 00:30
                    orb_0030_high,
                    orb_0030_low,
                    orb_0030_size,
                    (orb_0030_size / 0.1) AS orb_0030_size_ticks,
                    orb_0030_break_dir,
                    orb_0030_outcome,
                    orb_0030_r_multiple,
                    orb_0030_mae,
                    orb_0030_mfe,
                    rsi_at_orb
                FROM daily_features
                {where_clause}
                ORDER BY date_local
            """

            # Generate output filename
            if not output_file:
                suffix = f"_last_{days}d" if days else "_all"
                output_file = f"daily_features{suffix}.csv"

            output_path = os.path.join(self.output_dir, output_file)

            # Export to CSV
            con.execute(f"""
                COPY ({query})
                TO '{output_path}' (HEADER, DELIMITER ',')
            """)

            # Get row count
            row_count = con.execute(f"SELECT COUNT(*) FROM ({query})").fetchone()[0]

            return output_path, row_count

        finally:
            con.close()

    def export_orb_performance(self, output_file: Optional[str] = None) -> str:
        """Export ORB performance summary by time, direction, and session types"""
        con = duckdb.connect(self.db_path, read_only=True)

        try:
            # This creates a performance summary for each ORB time x direction x session type
            query = """
                WITH orb_stats AS (
                    -- Unpack all 6 ORBs into rows
                    SELECT 'ORB_0900' AS orb_time, orb_0900_break_dir AS direction, orb_0900_outcome AS outcome,
                           orb_0900_r_multiple AS r_multiple, asia_type, london_type, ny_type
                    FROM daily_features WHERE orb_0900_outcome IS NOT NULL
                    UNION ALL
                    SELECT 'ORB_1000', orb_1000_break_dir, orb_1000_outcome, orb_1000_r_multiple, asia_type, london_type, ny_type
                    FROM daily_features WHERE orb_1000_outcome IS NOT NULL
                    UNION ALL
                    SELECT 'ORB_1100', orb_1100_break_dir, orb_1100_outcome, orb_1100_r_multiple, asia_type, london_type, ny_type
                    FROM daily_features WHERE orb_1100_outcome IS NOT NULL
                    UNION ALL
                    SELECT 'ORB_1800', orb_1800_break_dir, orb_1800_outcome, orb_1800_r_multiple, asia_type, london_type, ny_type
                    FROM daily_features WHERE orb_1800_outcome IS NOT NULL
                    UNION ALL
                    SELECT 'ORB_2300', orb_2300_break_dir, orb_2300_outcome, orb_2300_r_multiple, asia_type, london_type, ny_type
                    FROM daily_features WHERE orb_2300_outcome IS NOT NULL
                    UNION ALL
                    SELECT 'ORB_0030', orb_0030_break_dir, orb_0030_outcome, orb_0030_r_multiple, asia_type, london_type, ny_type
                    FROM daily_features WHERE orb_0030_outcome IS NOT NULL
                )
                SELECT
                    orb_time,
                    direction,
                    asia_type,
                    london_type,
                    ny_type,
                    COUNT(*) AS total_trades,
                    SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) AS losses,
                    SUM(CASE WHEN outcome = 'NO_TRADE' THEN 1 ELSE 0 END) AS no_trades,
                    ROUND(SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END)::DOUBLE /
                          COUNT(*)::DOUBLE, 4) AS win_rate,
                    ROUND(AVG(r_multiple), 4) AS avg_r,
                    ROUND(SUM(r_multiple), 2) AS total_r,
                    ROUND(MIN(r_multiple), 2) AS worst_r,
                    ROUND(MAX(r_multiple), 2) AS best_r
                FROM orb_stats
                WHERE outcome IN ('WIN', 'LOSS')
                GROUP BY orb_time, direction, asia_type, london_type, ny_type
                HAVING COUNT(*) >= 5
                ORDER BY orb_time, direction, avg_r DESC
            """

            if not output_file:
                output_file = "orb_performance_summary.csv"

            output_path = os.path.join(self.output_dir, output_file)

            con.execute(f"""
                COPY ({query})
                TO '{output_path}' (HEADER, DELIMITER ',')
            """)

            row_count = con.execute(f"SELECT COUNT(*) FROM ({query})").fetchone()[0]

            return output_path, row_count

        finally:
            con.close()

    def export_session_stats(self, output_file: Optional[str] = None) -> str:
        """Export session type distribution and statistics"""
        con = duckdb.connect(self.db_path, read_only=True)

        try:
            query = """
                SELECT
                    asia_type,
                    london_type,
                    ny_type,
                    COUNT(*) AS occurrences,
                    ROUND(AVG(asia_range / 0.1), 1) AS avg_asia_range_ticks,
                    ROUND(AVG(atr_20), 2) AS avg_atr_20,
                    -- Average win rates across all ORBs for this session combo
                    ROUND(AVG(CASE WHEN orb_0900_outcome = 'WIN' THEN 1.0
                                   WHEN orb_0900_outcome = 'LOSS' THEN 0.0 END), 3) AS orb_0900_wr,
                    ROUND(AVG(CASE WHEN orb_1000_outcome = 'WIN' THEN 1.0
                                   WHEN orb_1000_outcome = 'LOSS' THEN 0.0 END), 3) AS orb_1000_wr,
                    ROUND(AVG(CASE WHEN orb_1100_outcome = 'WIN' THEN 1.0
                                   WHEN orb_1100_outcome = 'LOSS' THEN 0.0 END), 3) AS orb_1100_wr,
                    ROUND(AVG(CASE WHEN orb_1800_outcome = 'WIN' THEN 1.0
                                   WHEN orb_1800_outcome = 'LOSS' THEN 0.0 END), 3) AS orb_1800_wr,
                    ROUND(AVG(CASE WHEN orb_2300_outcome = 'WIN' THEN 1.0
                                   WHEN orb_2300_outcome = 'LOSS' THEN 0.0 END), 3) AS orb_2300_wr,
                    ROUND(AVG(CASE WHEN orb_0030_outcome = 'WIN' THEN 1.0
                                   WHEN orb_0030_outcome = 'LOSS' THEN 0.0 END), 3) AS orb_0030_wr
                FROM daily_features
                GROUP BY asia_type, london_type, ny_type
                HAVING COUNT(*) >= 3
                ORDER BY occurrences DESC
            """

            if not output_file:
                output_file = "session_type_stats.csv"

            output_path = os.path.join(self.output_dir, output_file)

            con.execute(f"""
                COPY ({query})
                TO '{output_path}' (HEADER, DELIMITER ',')
            """)

            row_count = con.execute(f"SELECT COUNT(*) FROM ({query})").fetchone()[0]

            return output_path, row_count

        finally:
            con.close()

    def export_bars(self, table: str, target_date: date, output_file: Optional[str] = None) -> str:
        """Export 1-minute or 5-minute bars for a specific date"""
        con = duckdb.connect(self.db_path, read_only=True)

        try:
            # Validate table name
            if table not in ['bars_1m', 'bars_5m']:
                raise ValueError(f"Invalid table: {table}. Must be 'bars_1m' or 'bars_5m'")

            # Convert target date to local trading day boundaries
            query = f"""
                SELECT
                    ts_utc AT TIME ZONE 'Australia/Brisbane' AS ts_local,
                    ts_utc,
                    symbol,
                    source_symbol,
                    open,
                    high,
                    low,
                    close,
                    volume
                FROM {table}
                WHERE DATE(ts_utc AT TIME ZONE 'Australia/Brisbane') = ?
                ORDER BY ts_utc
            """

            if not output_file:
                output_file = f"{table}_{target_date.isoformat()}.csv"

            output_path = os.path.join(self.output_dir, output_file)

            con.execute(f"""
                COPY ({query})
                TO '{output_path}' (HEADER, DELIMITER ',')
            """, [target_date])

            row_count = con.execute(query, [target_date]).fetchall()
            row_count = len(row_count)

            return output_path, row_count

        finally:
            con.close()


def main():
    parser = argparse.ArgumentParser(
        description="Export MGC data to CSV files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "export_type",
        choices=["daily_features", "orb_performance", "session_stats", "bars_1m", "bars_5m"],
        help="Type of data to export",
    )

    parser.add_argument(
        "date",
        nargs="?",
        type=str,
        help="Date for bars export (YYYY-MM-DD). Required for bars_1m and bars_5m",
    )

    parser.add_argument(
        "--days",
        type=int,
        metavar="N",
        help="For daily_features: export last N days only",
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        metavar="FILE",
        help="Output filename (default: auto-generated)",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="exports",
        help="Output directory (default: ./exports/)",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.export_type in ["bars_1m", "bars_5m"] and not args.date:
        parser.error(f"{args.export_type} requires a date argument (YYYY-MM-DD)")

    exporter = CSVExporter(output_dir=args.output_dir)

    print(f"\nExporting {args.export_type}...")

    try:
        if args.export_type == "daily_features":
            output_path, row_count = exporter.export_daily_features(
                days=args.days,
                output_file=args.output,
            )
        elif args.export_type == "orb_performance":
            output_path, row_count = exporter.export_orb_performance(
                output_file=args.output,
            )
        elif args.export_type == "session_stats":
            output_path, row_count = exporter.export_session_stats(
                output_file=args.output,
            )
        elif args.export_type in ["bars_1m", "bars_5m"]:
            target_date = date.fromisoformat(args.date)
            output_path, row_count = exporter.export_bars(
                table=args.export_type,
                target_date=target_date,
                output_file=args.output,
            )

        print(f"\nSuccess! Exported {row_count:,} rows to:")
        print(f"  {output_path}")

    except Exception as e:
        print(f"\nERROR: Export failed")
        print(f"  {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
