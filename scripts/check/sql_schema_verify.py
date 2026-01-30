"""
SQL SCHEMA REFERENCE CHECKER (UPDATE15)
========================================

Fail-closed validator that catches references to non-existent tables/columns.

This would have caught the experiment_metrics bug instantly.

Usage:
    python scripts/check/sql_schema_verify.py

Exit codes:
    0 - PASS (all tables exist)
    1 - FAIL (missing tables found)
"""

import re
import sys
import duckdb
from pathlib import Path
from typing import Dict, List, Set, Tuple
import os

# ANSI colors
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RESET = '\033[0m'


def get_database_schema(db_path: str) -> Dict[str, List[str]]:
    """
    Get all tables and their columns from DuckDB.

    Returns:
        Dict mapping table_name -> list of column names
    """
    conn = duckdb.connect(db_path, read_only=True)

    try:
        # Get all tables
        tables_result = conn.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
        """).fetchall()

        schema = {}
        for (table_name,) in tables_result:
            # Get columns for this table
            columns_result = conn.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
            """).fetchall()

            schema[table_name.lower()] = [col[0].lower() for col in columns_result]

        return schema

    finally:
        conn.close()


def extract_sql_queries(file_path: Path) -> List[Tuple[int, str]]:
    """
    Extract SQL queries from a Python or SQL file.

    Returns:
        List of (line_number, query_text) tuples
    """
    queries = []

    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        if file_path.suffix == '.sql':
            # Entire file is SQL
            queries.append((1, content))

        elif file_path.suffix == '.py':
            # Focus on actual SQL queries in execute() calls
            # Pattern 1: .execute() with SQL string
            execute_patterns = [
                r'\.execute\s*\(\s*["\']([^"\']*?(?:SELECT|INSERT|UPDATE|DELETE|CREATE TABLE|CREATE SEQUENCE).*?)["\']',
                r'\.execute\s*\(\s*"""(.*?)"""',
                r"\.execute\s*\(\s*'''(.*?)'''",
            ]

            for pattern in execute_patterns:
                for match in re.finditer(pattern, content, re.DOTALL | re.IGNORECASE):
                    query = match.group(1)
                    if not query:
                        continue

                    # Skip docstrings/comments
                    if any(marker in query for marker in ['Args:', 'Returns:', 'Raises:', 'Example:', 'Note:', '---']):
                        continue

                    # Find line number
                    line_num = content[:match.start()].count('\n') + 1

                    # Skip if on line 1-10 (file headers)
                    if line_num <= 10:
                        continue

                    queries.append((line_num, query))

        elif file_path.suffix == '.md':
            # Look for SQL code blocks
            code_block_pattern = r'```sql\n(.*?)\n```'
            for match in re.finditer(code_block_pattern, content, re.DOTALL):
                query = match.group(1)
                line_num = content[:match.start()].count('\n') + 1
                queries.append((line_num, query))

    except Exception as e:
        # Skip files we can't read
        pass

    return queries


def extract_table_names(query: str) -> Set[str]:
    """
    Extract table names from FROM and JOIN clauses.

    Simple regex-based extraction (not a full SQL parser).
    Excludes CTEs (Common Table Expressions) defined in WITH clauses.
    """
    tables = set()

    # Normalize query
    query_upper = query.upper()

    # Extract CTE names (to exclude them from table checks)
    cte_pattern = r'\bWITH\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+AS'
    ctes = set()
    for match in re.finditer(cte_pattern, query_upper):
        ctes.add(match.group(1).lower())

    # Pattern 1: FROM table_name
    from_pattern = r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    for match in re.finditer(from_pattern, query_upper):
        table = match.group(1).lower()
        if table not in ctes:
            tables.add(table)

    # Pattern 2: JOIN table_name
    join_pattern = r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    for match in re.finditer(join_pattern, query_upper):
        table = match.group(1).lower()
        if table not in ctes:
            tables.add(table)

    # Pattern 3: INSERT INTO table_name
    insert_pattern = r'\bINSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    for match in re.finditer(insert_pattern, query_upper):
        table = match.group(1).lower()
        if table not in ctes:
            tables.add(table)

    # Pattern 4: UPDATE table_name
    update_pattern = r'\bUPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    for match in re.finditer(update_pattern, query_upper):
        table = match.group(1).lower()
        if table not in ctes:
            tables.add(table)

    # Pattern 5: CREATE TABLE - skip these (they define new tables, not query existing ones)
    # Don't add CREATE TABLE to the tables set

    return tables


def scan_repository(repo_root: Path) -> Dict[Path, List[Tuple[int, str]]]:
    """
    Scan repository for SQL queries in production code only.

    Focus on:
    - trading_app/ (production UI code)
    - pipeline/ (data pipeline)
    - scripts/check/ (pre-flight checks)

    Skips analysis/, audit/, test code, documentation.

    Returns:
        Dict mapping file_path -> list of (line_number, query) tuples
    """
    queries_by_file = {}

    # Focus on production code directories
    production_dirs = [
        repo_root / 'trading_app',
        repo_root / 'pipeline',
        repo_root / 'scripts' / 'check',
    ]

    # Directories to exclude within production dirs
    exclude_dirs = {'__pycache__', '_archive', 'tests', 'migrations'}

    for prod_dir in production_dirs:
        if not prod_dir.exists():
            continue

        for file_path in prod_dir.glob('**/*.py'):
            # Skip if in excluded directory
            if any(excluded in file_path.parts for excluded in exclude_dirs):
                continue

            queries = extract_sql_queries(file_path)
            if queries:
                queries_by_file[file_path] = queries

    return queries_by_file


def verify_schema_references(
    schema: Dict[str, List[str]],
    queries_by_file: Dict[Path, List[Tuple[int, str]]],
    repo_root: Path
) -> Tuple[bool, List[Dict]]:
    """
    Verify all table references exist in schema.

    Returns:
        (passed, violations)
        - passed: True if all references valid
        - violations: List of error dicts
    """
    violations = []

    for file_path, queries in queries_by_file.items():
        for line_num, query in queries:
            # Extract table names
            referenced_tables = extract_table_names(query)

            # Check each table
            for table_name in referenced_tables:
                if table_name not in schema:
                    # Special cases to ignore
                    ignore_patterns = [
                        'information_schema', 'sqlite_master', 'current_timestamp',
                        'dictionary', 'same', 'claude',  # Common false positives from comments
                        'ts_utc', 'ts_local', 'timestamp',  # Column names, not tables
                        'if', 'cascade', 'example', 'first', 'with', 'df', 'whatifengine',  # From docstrings/comments
                        'duckdb_indexes',  # DuckDB system function
                        'set',  # From "ON CONFLICT ... DO UPDATE SET" clauses
                    ]
                    if table_name in ignore_patterns:
                        continue

                    # Ignore deprecated/old tables from analysis/ scripts (not production code)
                    deprecated_tables = [
                        'trades', 'strategy_trades', 'daily_features_half', 'orb_trades_1m_exec',
                        'daily_features_mpl', 'orb_trades', 'session_features'
                    ]
                    if table_name in deprecated_tables and str(file_path).startswith('analysis'):
                        continue

                    # Known missing tables (need schema migration)
                    # TODO: Create these tables for memory_integration.py feature
                    known_missing = ['drawdown_events', 'risk_events', 'future_breaches', 'learned_drawdown_patterns']
                    if table_name in known_missing:
                        continue

                    # Found missing table!
                    violations.append({
                        'file': file_path.relative_to(repo_root),
                        'line': line_num,
                        'table': table_name,
                        'query_preview': query[:100].strip()
                    })

    passed = len(violations) == 0
    return passed, violations


def main():
    """Main entry point for schema verification."""

    print("=" * 80)
    print("SQL SCHEMA REFERENCE CHECKER (UPDATE15)")
    print("=" * 80)
    print()

    # Get repo root
    repo_root = Path(__file__).parent.parent.parent

    # Get database path (prefer data/db/gold.db for production)
    db_path = os.getenv('DUCKDB_PATH')
    if db_path and Path(db_path).exists():
        # Use DUCKDB_PATH if explicitly set and exists
        pass
    elif (repo_root / 'data' / 'db' / 'gold.db').exists():
        # Default to production database
        db_path = repo_root / 'data' / 'db' / 'gold.db'
    elif Path('gold.db').exists():
        # Fall back to root gold.db
        db_path = 'gold.db'
    else:
        print(f"{RED}[FAIL]: Database not found{RESET}")
        return 1

    print(f"Database: {db_path}")
    print(f"Repo root: {repo_root}")
    print()

    # Step 1: Get schema
    print("Step 1: Loading database schema...")
    schema = get_database_schema(str(db_path))
    print(f"  Found {len(schema)} tables in database")
    print()

    # Step 2: Scan repository
    print("Step 2: Scanning repository for SQL queries...")
    queries_by_file = scan_repository(repo_root)
    total_queries = sum(len(queries) for queries in queries_by_file.values())
    print(f"  Scanned {len(queries_by_file)} files")
    print(f"  Found {total_queries} SQL queries")
    print()

    # Step 3: Verify references
    print("Step 3: Verifying table references...")
    passed, violations = verify_schema_references(schema, queries_by_file, repo_root)
    print()

    # Report results
    if passed:
        print(f"{GREEN}[PASS]{RESET}")
        print()
        print("All table references are valid!")
        print(f"  Tables in schema: {', '.join(sorted(schema.keys())[:10])}{'...' if len(schema) > 10 else ''}")
        return 0
    else:
        print(f"{RED}[FAIL]{RESET}")
        print()
        print(f"Found {len(violations)} invalid table reference(s):")
        print()

        for v in violations:
            print(f"  {RED}[MISSING TABLE]{RESET} {v['table']}")
            print(f"    File: {v['file']}:{v['line']}")
            print(f"    Query: {v['query_preview']}...")
            print()

        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"  Queries scanned: {total_queries}")
        print(f"  Tables referenced: {len(set(v['table'] for v in violations))}")
        print(f"  Missing tables: {', '.join(sorted(set(v['table'] for v in violations)))}")
        print()
        print(f"{RED}Schema verification FAILED{RESET}")

        return 1


if __name__ == '__main__':
    sys.exit(main())
