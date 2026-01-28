"""
Drift Monitor - System Health Monitoring

Detects:
1. Schema drift (database vs code expectations)
2. Performance decay (edge degradation over time)
3. Data quality issues (missing data, outliers)
4. Config/database synchronization issues

Usage:
    from drift_monitor import DriftMonitor

    monitor = DriftMonitor(db_connection)
    health = monitor.check_system_health()

    if health['status'] == 'CRITICAL':
        # Handle critical issues
        pass
"""

import duckdb
from typing import Dict, List, Optional
from datetime import datetime, timedelta, date
import json


class DriftMonitor:
    """System health monitoring and drift detection"""

    def __init__(self, db_connection: duckdb.DuckDBPyConnection):
        self.conn = db_connection

    def check_system_health(self) -> Dict:
        """
        Run all health checks and return system status

        Returns:
            Dict with:
            - status: 'OK' | 'WARNING' | 'CRITICAL'
            - checks: List of individual check results
            - critical_issues: List of critical problems
            - warnings: List of warnings
        """
        checks = []
        critical_issues = []
        warnings = []

        # Check 1: Schema sync
        schema_check = self.check_schema_sync()
        checks.append(schema_check)
        if schema_check['status'] == 'CRITICAL':
            critical_issues.extend(schema_check.get('issues', []))
        elif schema_check['status'] == 'WARNING':
            warnings.extend(schema_check.get('issues', []))

        # Check 2: Data quality
        data_check = self.check_data_quality()
        checks.append(data_check)
        if data_check['status'] == 'CRITICAL':
            critical_issues.extend(data_check.get('issues', []))
        elif data_check['status'] == 'WARNING':
            warnings.extend(data_check.get('issues', []))

        # Check 3: Performance decay
        perf_check = self.check_performance_decay()
        checks.append(perf_check)
        if perf_check['status'] == 'CRITICAL':
            critical_issues.extend(perf_check.get('issues', []))
        elif perf_check['status'] == 'WARNING':
            warnings.extend(perf_check.get('issues', []))

        # Check 4: Database/config sync
        config_check = self.check_config_sync()
        checks.append(config_check)
        if config_check['status'] == 'CRITICAL':
            critical_issues.extend(config_check.get('issues', []))
        elif config_check['status'] == 'WARNING':
            warnings.extend(config_check.get('issues', []))

        # Determine overall status
        if critical_issues:
            overall_status = 'CRITICAL'
        elif warnings:
            overall_status = 'WARNING'
        else:
            overall_status = 'OK'

        return {
            'status': overall_status,
            'checks': checks,
            'critical_issues': critical_issues,
            'warnings': warnings,
            'checked_at': datetime.now().isoformat()
        }

    def check_schema_sync(self) -> Dict:
        """
        Check if database schema matches code expectations

        Returns:
            Dict with status and issues
        """
        issues = []

        # Check if required tables exist
        required_tables = ['edge_registry', 'experiment_run', 'validated_setups', 'daily_features']

        for table in required_tables:
            try:
                self.conn.execute(f"SELECT 1 FROM {table} LIMIT 1")
            except Exception as e:
                issues.append(f"Table '{table}' missing or inaccessible: {e}")

        # Check if required columns exist in daily_features
        required_cols = [
            'date_local', 'instrument', 'atr_20',
            'orb_0900_size', 'orb_1000_size', 'orb_1100_size', 'orb_1800_size'
        ]

        try:
            schema = self.conn.execute("DESCRIBE daily_features").fetchdf()
            existing_cols = set(schema['column_name'].tolist())

            for col in required_cols:
                if col not in existing_cols:
                    issues.append(f"Required column '{col}' missing from daily_features")
        except Exception as e:
            issues.append(f"Failed to check daily_features schema: {e}")

        # Check if experiment_run has control_run_id column (T7 requirement)
        try:
            schema = self.conn.execute("DESCRIBE experiment_run").fetchdf()
            if 'control_run_id' not in schema['column_name'].tolist():
                issues.append("Column 'control_run_id' missing from experiment_run (T7 requirement)")
        except Exception as e:
            issues.append(f"Failed to check experiment_run schema: {e}")

        return {
            'check': 'schema_sync',
            'status': 'CRITICAL' if issues else 'OK',
            'issues': issues,
            'description': 'Database schema validation'
        }

    def check_data_quality(self) -> Dict:
        """
        Check for data quality issues

        Returns:
            Dict with status and issues
        """
        issues = []
        warnings = []

        # Check for recent data (last 7 days)
        try:
            cutoff = date.today() - timedelta(days=7)
            recent_count = self.conn.execute("""
                SELECT COUNT(*) FROM daily_features
                WHERE date_local >= ?
            """, [cutoff]).fetchone()[0]

            if recent_count == 0:
                issues.append(f"No data in last 7 days (last data: check manually)")
            elif recent_count < 5:
                warnings.append(f"Only {recent_count} days of data in last 7 days (expected 5-7)")
        except Exception as e:
            issues.append(f"Failed to check recent data: {e}")

        # Check for NULL values in critical columns
        try:
            null_checks = [
                ('date_local', 'daily_features'),
                ('instrument', 'daily_features'),
                ('edge_id', 'edge_registry'),
                ('run_id', 'experiment_run')
            ]

            for col, table in null_checks:
                null_count = self.conn.execute(f"""
                    SELECT COUNT(*) FROM {table} WHERE {col} IS NULL
                """).fetchone()[0]

                if null_count > 0:
                    issues.append(f"Found {null_count} NULL values in {table}.{col}")
        except Exception as e:
            warnings.append(f"Failed to check NULL values: {e}")

        # Check for missing ORB data
        try:
            total_days = self.conn.execute("SELECT COUNT(*) FROM daily_features WHERE instrument = 'MGC'").fetchone()[0]
            missing_orb = self.conn.execute("""
                SELECT COUNT(*) FROM daily_features
                WHERE instrument = 'MGC'
                AND (orb_0900_outcome IS NULL AND orb_1000_outcome IS NULL AND orb_1100_outcome IS NULL)
            """).fetchone()[0]

            if missing_orb > 0:
                pct = (missing_orb / total_days * 100) if total_days > 0 else 0
                if pct > 10:
                    warnings.append(f"{missing_orb} days ({pct:.1f}%) have no ORB outcomes")
        except Exception as e:
            warnings.append(f"Failed to check ORB data: {e}")

        return {
            'check': 'data_quality',
            'status': 'CRITICAL' if issues else 'WARNING' if warnings else 'OK',
            'issues': issues + warnings,
            'description': 'Data quality validation'
        }

    def check_performance_decay(self) -> Dict:
        """
        Check if any promoted edges are degrading

        Returns:
            Dict with status and issues
        """
        issues = []
        warnings = []

        # Get all PROMOTED edges
        try:
            promoted = self.conn.execute("""
                SELECT edge_id FROM edge_registry WHERE status = 'PROMOTED'
            """).fetchall()

            if not promoted:
                # No promoted edges to check
                return {
                    'check': 'performance_decay',
                    'status': 'OK',
                    'issues': [],
                    'description': 'No promoted edges to monitor'
                }

            # For each promoted edge, check recent performance vs baseline
            for (edge_id,) in promoted:
                # Get original validation metrics
                original_run = self.conn.execute("""
                    SELECT metrics FROM experiment_run
                    WHERE edge_id = ? AND run_type = 'VALIDATION' AND status = 'COMPLETED'
                    ORDER BY started_at
                    LIMIT 1
                """, [edge_id]).fetchone()

                if not original_run:
                    warnings.append(f"Edge {edge_id[:16]}... has no validation baseline")
                    continue

                original_metrics = json.loads(original_run[0]) if isinstance(original_run[0], str) else original_run[0]
                original_wr = original_metrics.get('win_rate', 0)

                # TODO: Check recent actual performance
                # For now, we can't check actual trading performance without live tracking
                # This would require a separate trade_history table
                warnings.append(f"Edge {edge_id[:16]}... - live tracking not implemented")

        except Exception as e:
            warnings.append(f"Failed to check performance decay: {e}")

        return {
            'check': 'performance_decay',
            'status': 'WARNING' if warnings else 'OK',
            'issues': warnings,
            'description': 'Edge performance monitoring (requires live tracking)'
        }

    def check_config_sync(self) -> Dict:
        """
        Check if config.py matches validated_setups database

        Returns:
            Dict with status and issues
        """
        issues = []
        warnings = []

        try:
            # Count setups in database
            db_count = self.conn.execute("SELECT COUNT(*) FROM validated_setups").fetchone()[0]

            # Check by instrument
            mgc_count = self.conn.execute("SELECT COUNT(*) FROM validated_setups WHERE instrument = 'MGC'").fetchone()[0]

            # We can't easily check config.py from here, so we rely on test_app_sync.py
            # Instead, we check for inconsistencies in the database itself

            # Check for duplicate setups (same instrument, orb_time, rr, sl_mode)
            duplicates = self.conn.execute("""
                SELECT instrument, orb_time, rr, sl_mode, COUNT(*) as count
                FROM validated_setups
                GROUP BY instrument, orb_time, rr, sl_mode
                HAVING COUNT(*) > 1
            """).fetchall()

            if duplicates:
                for dup in duplicates:
                    warnings.append(f"Duplicate setup: {dup[0]} {dup[1]} RR={dup[2]} SL={dup[3]} ({dup[4]} copies)")

        except Exception as e:
            issues.append(f"Failed to check config sync: {e}")

        return {
            'check': 'config_sync',
            'status': 'CRITICAL' if issues else 'WARNING' if warnings else 'OK',
            'issues': issues + warnings,
            'description': 'Database/config synchronization (run test_app_sync.py for full check)'
        }


def get_system_health_summary(db_connection: duckdb.DuckDBPyConnection) -> str:
    """
    Get a quick summary of system health

    Returns:
        String like "OK" or "WARNING (2 issues)" or "CRITICAL (1 critical, 3 warnings)"
    """
    monitor = DriftMonitor(db_connection)
    health = monitor.check_system_health()

    status = health['status']
    critical_count = len(health['critical_issues'])
    warning_count = len(health['warnings'])

    if status == 'OK':
        return "OK"
    elif status == 'WARNING':
        return f"WARNING ({warning_count} issue{'s' if warning_count != 1 else ''})"
    else:
        return f"CRITICAL ({critical_count} critical, {warning_count} warning{'s' if warning_count != 1 else ''})"
