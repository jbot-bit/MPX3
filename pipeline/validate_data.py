"""
Data Validation System
======================
Comprehensive checks for data quality, gaps, anomalies, and integrity.

Usage:
  python validate_data.py                    # Run all checks
  python validate_data.py --check gaps       # Run specific check
  python validate_data.py --fix              # Attempt to fix issues
  python validate_data.py --report           # Generate detailed report

Checks:
- Date gaps in bars_1m and daily_features
- Duplicate timestamps
- Volume anomalies (zeros, spikes)
- Price anomalies (impossible moves, zero prices)
- Contract roll verification
- ORB calculation integrity
- Session boundary correctness
"""

import duckdb
import argparse
from datetime import date, datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import json


@dataclass
class ValidationIssue:
    """Represents a data quality issue"""
    severity: str  # CRITICAL, WARNING, INFO
    check: str
    date_local: Optional[date]
    description: str
    affected_rows: int
    suggestion: str


class DataValidator:
    """Validate MGC data quality"""

    def __init__(self, db_path: str = "gold.db"):
        self.db_path = db_path
        self.issues: List[ValidationIssue] = []

    def add_issue(self, severity: str, check: str, description: str,
                  affected_rows: int = 0, date_local: Optional[date] = None,
                  suggestion: str = ""):
        """Add a validation issue to the list"""
        self.issues.append(ValidationIssue(
            severity=severity,
            check=check,
            date_local=date_local,
            description=description,
            affected_rows=affected_rows,
            suggestion=suggestion,
        ))

    def check_date_gaps(self) -> None:
        """Check for missing days in daily_features"""
        con = duckdb.connect(self.db_path, read_only=True)

        try:
            # Get date range
            result = con.execute("""
                SELECT MIN(date_local), MAX(date_local)
                FROM daily_features
            """).fetchone()

            if not result or not result[0]:
                self.add_issue("CRITICAL", "date_gaps",
                              "No data found in daily_features table",
                              suggestion="Run backfill: python backfill_databento_continuous.py 2024-01-01 2026-01-10")
                return

            start_date, end_date = result

            # Get all dates present
            existing_dates = set(
                row[0] for row in con.execute("""
                    SELECT DISTINCT date_local
                    FROM daily_features
                    ORDER BY date_local
                """).fetchall()
            )

            # Check for gaps (skip weekends)
            current = start_date
            gaps = []
            while current <= end_date:
                # Skip Saturdays (5) and Sundays (6)
                if current.weekday() < 5 and current not in existing_dates:
                    gaps.append(current)
                current += timedelta(days=1)

            if gaps:
                gap_count = len(gaps)
                if gap_count > 10:
                    # Show first and last few gaps
                    gap_str = f"{gaps[0]} to {gaps[-1]} ({gap_count} days total)"
                else:
                    gap_str = ", ".join(str(d) for d in gaps[:5])
                    if gap_count > 5:
                        gap_str += f" ... ({gap_count} total)"

                self.add_issue(
                    "WARNING", "date_gaps",
                    f"Missing weekday data for {gap_count} days: {gap_str}",
                    affected_rows=gap_count,
                    suggestion=f"Run: python daily_update.py --days {(end_date - gaps[0]).days + 5}"
                )
            else:
                self.add_issue("INFO", "date_gaps",
                              f"No gaps found. Continuous data from {start_date} to {end_date}",
                              affected_rows=0)

        finally:
            con.close()

    def check_duplicates(self) -> None:
        """Check for duplicate rows"""
        con = duckdb.connect(self.db_path, read_only=True)

        try:
            # Check bars_1m duplicates
            dupes_1m = con.execute("""
                SELECT symbol, ts_utc, COUNT(*) as cnt
                FROM bars_1m
                GROUP BY symbol, ts_utc
                HAVING COUNT(*) > 1
                LIMIT 10
            """).fetchall()

            if dupes_1m:
                self.add_issue(
                    "CRITICAL", "duplicates",
                    f"Found {len(dupes_1m)} duplicate timestamps in bars_1m",
                    affected_rows=len(dupes_1m),
                    suggestion="This should never happen. Check backfill scripts."
                )

            # Check daily_features duplicates
            dupes_df = con.execute("""
                SELECT date_local, instrument, COUNT(*) as cnt
                FROM daily_features
                GROUP BY date_local, instrument
                HAVING COUNT(*) > 1
                LIMIT 10
            """).fetchall()

            if dupes_df:
                self.add_issue(
                    "CRITICAL", "duplicates",
                    f"Found {len(dupes_df)} duplicate dates in daily_features",
                    affected_rows=len(dupes_df),
                    suggestion="Rebuild features: python build_daily_features.py <date>"
                )

            if not dupes_1m and not dupes_df:
                self.add_issue("INFO", "duplicates",
                              "No duplicate rows found", affected_rows=0)

        finally:
            con.close()

    def check_volume_anomalies(self) -> None:
        """Check for zero or abnormally high volume"""
        con = duckdb.connect(self.db_path, read_only=True)

        try:
            # Check for zero volume bars
            zero_vol = con.execute("""
                SELECT COUNT(*)
                FROM bars_1m
                WHERE volume = 0 OR volume IS NULL
            """).fetchone()[0]

            if zero_vol > 0:
                self.add_issue(
                    "WARNING", "volume_anomalies",
                    f"Found {zero_vol} bars with zero or null volume",
                    affected_rows=zero_vol,
                    suggestion="Zero volume bars may be valid during low liquidity periods"
                )

            # Check for volume spikes (>100x median)
            result = con.execute("""
                WITH vol_stats AS (
                    SELECT MEDIAN(volume) as med_vol
                    FROM bars_1m
                    WHERE volume > 0
                )
                SELECT COUNT(*)
                FROM bars_1m, vol_stats
                WHERE bars_1m.volume > vol_stats.med_vol * 100
            """).fetchone()[0]

            if result > 0:
                self.add_issue(
                    "WARNING", "volume_anomalies",
                    f"Found {result} bars with extreme volume spikes (>100x median)",
                    affected_rows=result,
                    suggestion="May indicate contract rolls or news events - review manually"
                )

            if zero_vol == 0 and result == 0:
                self.add_issue("INFO", "volume_anomalies",
                              "No significant volume anomalies detected", affected_rows=0)

        finally:
            con.close()

    def check_price_anomalies(self) -> None:
        """Check for impossible price moves or zero prices"""
        con = duckdb.connect(self.db_path, read_only=True)

        try:
            # Check for zero or negative prices
            zero_prices = con.execute("""
                SELECT COUNT(*)
                FROM bars_1m
                WHERE open <= 0 OR high <= 0 OR low <= 0 OR close <= 0
            """).fetchone()[0]

            if zero_prices > 0:
                self.add_issue(
                    "CRITICAL", "price_anomalies",
                    f"Found {zero_prices} bars with zero or negative prices",
                    affected_rows=zero_prices,
                    suggestion="Critical data corruption - re-backfill affected dates"
                )

            # Check for bars where low > high
            invalid_bars = con.execute("""
                SELECT COUNT(*)
                FROM bars_1m
                WHERE low > high
            """).fetchone()[0]

            if invalid_bars > 0:
                self.add_issue(
                    "CRITICAL", "price_anomalies",
                    f"Found {invalid_bars} bars where low > high (impossible)",
                    affected_rows=invalid_bars,
                    suggestion="Critical data corruption - re-backfill affected dates"
                )

            # Check for extreme 1-bar moves (>10% in 1 minute)
            extreme_moves = con.execute("""
                WITH bar_moves AS (
                    SELECT
                        ts_utc,
                        close,
                        LAG(close) OVER (ORDER BY ts_utc) as prev_close,
                        ABS(close - LAG(close) OVER (ORDER BY ts_utc)) /
                            LAG(close) OVER (ORDER BY ts_utc) as pct_move
                    FROM bars_1m
                    WHERE symbol = 'MGC'
                )
                SELECT COUNT(*)
                FROM bar_moves
                WHERE pct_move > 0.10
            """).fetchone()[0]

            if extreme_moves > 0:
                self.add_issue(
                    "WARNING", "price_anomalies",
                    f"Found {extreme_moves} bars with >10% moves in 1 minute",
                    affected_rows=extreme_moves,
                    suggestion="May indicate contract rolls or flash crashes - review manually"
                )

            if zero_prices == 0 and invalid_bars == 0 and extreme_moves == 0:
                self.add_issue("INFO", "price_anomalies",
                              "No price anomalies detected", affected_rows=0)

        finally:
            con.close()

    def check_contract_continuity(self) -> None:
        """Check for proper contract roll handling"""
        con = duckdb.connect(self.db_path, read_only=True)

        try:
            # Check for days with multiple source symbols (roll days)
            rolls = con.execute("""
                SELECT
                    DATE(ts_utc AT TIME ZONE 'Australia/Brisbane') as date_local,
                    COUNT(DISTINCT source_symbol) as num_contracts
                FROM bars_1m
                WHERE symbol = 'MGC'
                GROUP BY DATE(ts_utc AT TIME ZONE 'Australia/Brisbane')
                HAVING COUNT(DISTINCT source_symbol) > 1
                ORDER BY date_local DESC
                LIMIT 20
            """).fetchall()

            if rolls:
                roll_count = len(rolls)
                latest_roll = rolls[0][0] if rolls else None

                self.add_issue(
                    "INFO", "contract_continuity",
                    f"Found {roll_count} contract roll days (expected). Latest: {latest_roll}",
                    affected_rows=roll_count,
                    suggestion="Contract rolls are normal - ensure continuity is maintained"
                )

            # Check for orphan contracts (single day appearances)
            orphans = con.execute("""
                WITH contract_days AS (
                    SELECT
                        source_symbol,
                        COUNT(DISTINCT DATE(ts_utc AT TIME ZONE 'Australia/Brisbane')) as days
                    FROM bars_1m
                    WHERE symbol = 'MGC'
                    GROUP BY source_symbol
                )
                SELECT COUNT(*)
                FROM contract_days
                WHERE days = 1
            """).fetchone()[0]

            if orphans > 0:
                self.add_issue(
                    "WARNING", "contract_continuity",
                    f"Found {orphans} contracts appearing only on single days",
                    affected_rows=orphans,
                    suggestion="Review contract selection logic in backfill script"
                )

        finally:
            con.close()

    def check_orb_integrity(self) -> None:
        """Verify ORB calculations are correct"""
        con = duckdb.connect(self.db_path, read_only=True)

        try:
            # Sample check: verify ORB size = high - low for recent data
            invalid_orbs = con.execute("""
                SELECT COUNT(*)
                FROM daily_features
                WHERE (
                    (orb_0900_size IS NOT NULL AND
                     ABS(orb_0900_size - (orb_0900_high - orb_0900_low)) > 0.01)
                    OR
                    (orb_1000_size IS NOT NULL AND
                     ABS(orb_1000_size - (orb_1000_high - orb_1000_low)) > 0.01)
                    OR
                    (orb_1100_size IS NOT NULL AND
                     ABS(orb_1100_size - (orb_1100_high - orb_1100_low)) > 0.01)
                )
                AND date_local >= CURRENT_DATE - INTERVAL '30 days'
            """).fetchone()[0]

            if invalid_orbs > 0:
                self.add_issue(
                    "WARNING", "orb_integrity",
                    f"Found {invalid_orbs} ORBs with size != (high - low) in last 30 days",
                    affected_rows=invalid_orbs,
                    suggestion="Rebuild features: python build_daily_features.py <date>"
                )

            # Check for ORBs with outcome but no direction
            orphan_outcomes = con.execute("""
                SELECT COUNT(*)
                FROM daily_features
                WHERE (
                    (orb_0900_outcome IS NOT NULL AND orb_0900_break_dir IS NULL)
                    OR
                    (orb_1000_outcome IS NOT NULL AND orb_1000_break_dir IS NULL)
                )
            """).fetchone()[0]

            if orphan_outcomes > 0:
                self.add_issue(
                    "WARNING", "orb_integrity",
                    f"Found {orphan_outcomes} ORBs with outcome but no break direction",
                    affected_rows=orphan_outcomes,
                    suggestion="Rebuild features for affected dates"
                )

            if invalid_orbs == 0 and orphan_outcomes == 0:
                self.add_issue("INFO", "orb_integrity",
                              "ORB calculations appear correct", affected_rows=0)

        finally:
            con.close()

    def check_session_boundaries(self) -> None:
        """Verify session time windows are correct"""
        con = duckdb.connect(self.db_path, read_only=True)

        try:
            # Check that Asia session stats use correct time windows
            # Sample: verify we have data during expected Asia hours
            result = con.execute("""
                SELECT date_local
                FROM daily_features
                WHERE asia_high IS NOT NULL
                  AND NOT EXISTS (
                    SELECT 1
                    FROM bars_1m
                    WHERE DATE(ts_utc AT TIME ZONE 'Australia/Brisbane') = daily_features.date_local
                      AND EXTRACT(HOUR FROM ts_utc AT TIME ZONE 'Australia/Brisbane') BETWEEN 9 AND 16
                  )
                LIMIT 5
            """).fetchall()

            if result:
                self.add_issue(
                    "WARNING", "session_boundaries",
                    f"Found {len(result)} days with Asia stats but no data during Asia hours",
                    affected_rows=len(result),
                    date_local=result[0][0] if result else None,
                    suggestion="Check session time window definitions in build_daily_features.py"
                )
            else:
                self.add_issue("INFO", "session_boundaries",
                              "Session time boundaries appear correct", affected_rows=0)

        finally:
            con.close()

    def check_5m_aggregation(self) -> None:
        """Verify 5m bars are correctly aggregated from 1m bars"""
        con = duckdb.connect(self.db_path, read_only=True)

        try:
            # Check row count ratio (should be ~5:1)
            counts = con.execute("""
                SELECT
                    (SELECT COUNT(*) FROM bars_1m) as cnt_1m,
                    (SELECT COUNT(*) FROM bars_5m) as cnt_5m
            """).fetchone()

            cnt_1m, cnt_5m = counts
            ratio = cnt_1m / cnt_5m if cnt_5m > 0 else 0

            if ratio < 4.5 or ratio > 5.5:
                self.add_issue(
                    "WARNING", "5m_aggregation",
                    f"Unexpected 1m:5m ratio: {ratio:.2f} (expected ~5.0)",
                    affected_rows=0,
                    suggestion="Rebuild 5m bars for recent dates"
                )
            else:
                self.add_issue("INFO", "5m_aggregation",
                              f"5-minute aggregation ratio looks good ({ratio:.2f})",
                              affected_rows=0)

        finally:
            con.close()

    def run_all_checks(self) -> None:
        """Run all validation checks"""
        print("\n" + "="*80)
        print("DATA VALIDATION - Running all checks...")
        print("="*80)

        checks = [
            ("Date Gaps", self.check_date_gaps),
            ("Duplicates", self.check_duplicates),
            ("Volume Anomalies", self.check_volume_anomalies),
            ("Price Anomalies", self.check_price_anomalies),
            ("Contract Continuity", self.check_contract_continuity),
            ("ORB Integrity", self.check_orb_integrity),
            ("Session Boundaries", self.check_session_boundaries),
            ("5m Aggregation", self.check_5m_aggregation),
        ]

        for name, check_func in checks:
            print(f"\n[{name}]", end=" ")
            try:
                check_func()
                print("[OK]")
            except Exception as e:
                print(f"[ERROR]: {str(e)}")
                self.add_issue("CRITICAL", name.lower().replace(" ", "_"),
                             f"Check failed with error: {str(e)}",
                             suggestion="Review validation script")

    def print_report(self) -> None:
        """Print validation report"""
        print("\n" + "="*80)
        print("VALIDATION REPORT")
        print("="*80)

        # Group by severity
        critical = [i for i in self.issues if i.severity == "CRITICAL"]
        warnings = [i for i in self.issues if i.severity == "WARNING"]
        info = [i for i in self.issues if i.severity == "INFO"]

        # Print summary
        print(f"\nSummary:")
        print(f"  CRITICAL: {len(critical)}")
        print(f"  WARNING:  {len(warnings)}")
        print(f"  INFO:     {len(info)}")

        # Print critical issues
        if critical:
            print("\n" + "="*80)
            print("CRITICAL ISSUES (require immediate attention)")
            print("="*80)
            for issue in critical:
                print(f"\n[{issue.check.upper()}]")
                print(f"  {issue.description}")
                if issue.affected_rows > 0:
                    print(f"  Affected rows: {issue.affected_rows}")
                if issue.date_local:
                    print(f"  Date: {issue.date_local}")
                if issue.suggestion:
                    print(f"  => {issue.suggestion}")

        # Print warnings
        if warnings:
            print("\n" + "="*80)
            print("WARNINGS (review recommended)")
            print("="*80)
            for issue in warnings:
                print(f"\n[{issue.check.upper()}]")
                print(f"  {issue.description}")
                if issue.affected_rows > 0:
                    print(f"  Affected rows: {issue.affected_rows}")
                if issue.suggestion:
                    print(f"  => {issue.suggestion}")

        # Print info (collapsed)
        if info:
            print("\n" + "="*80)
            print("INFO (all checks passed)")
            print("="*80)
            for issue in info:
                print(f"  [OK] {issue.check}: {issue.description}")

        # Overall status
        print("\n" + "="*80)
        if critical:
            print("STATUS: CRITICAL - Data has serious issues that need fixing")
        elif warnings:
            print("STATUS: WARNING - Data is usable but has some quality issues")
        else:
            print("STATUS: HEALTHY - All validation checks passed")
        print("="*80 + "\n")

    def save_report_json(self, filename: str = "validation_report.json") -> None:
        """Save validation report as JSON"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "critical": len([i for i in self.issues if i.severity == "CRITICAL"]),
                "warnings": len([i for i in self.issues if i.severity == "WARNING"]),
                "info": len([i for i in self.issues if i.severity == "INFO"]),
            },
            "issues": [
                {
                    "severity": i.severity,
                    "check": i.check,
                    "date": i.date_local.isoformat() if i.date_local else None,
                    "description": i.description,
                    "affected_rows": i.affected_rows,
                    "suggestion": i.suggestion,
                }
                for i in self.issues
            ]
        }

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\nReport saved to: {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Validate MGC data quality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--check",
        choices=["gaps", "duplicates", "volume", "price", "contracts", "orb", "sessions", "5m"],
        help="Run specific check only",
    )

    parser.add_argument(
        "--report",
        action="store_true",
        help="Save detailed report as JSON",
    )

    args = parser.parse_args()

    validator = DataValidator()

    if args.check:
        # Run specific check
        check_map = {
            "gaps": validator.check_date_gaps,
            "duplicates": validator.check_duplicates,
            "volume": validator.check_volume_anomalies,
            "price": validator.check_price_anomalies,
            "contracts": validator.check_contract_continuity,
            "orb": validator.check_orb_integrity,
            "sessions": validator.check_session_boundaries,
            "5m": validator.check_5m_aggregation,
        }
        check_map[args.check]()
    else:
        # Run all checks
        validator.run_all_checks()

    # Print report
    validator.print_report()

    # Save JSON report if requested
    if args.report:
        validator.save_report_json()


if __name__ == "__main__":
    main()
