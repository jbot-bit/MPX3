"""
Generate TSOT baseline from live checker output

This ensures baseline format matches exactly what the checker outputs.
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# Import checker functions
sys.path.insert(0, str(Path(__file__).parent))
from check_time_literals import (
    check_file,
    is_exception_file,
    FORBIDDEN_PATTERNS,
    PATTERN_REGEX
)

def main():
    repo_root = Path(__file__).resolve().parents[2]

    # Find all Python files (same as checker)
    python_files = []
    for directory in ['trading_app', 'pipeline', 'strategies', 'analysis']:
        dir_path = repo_root / directory
        if dir_path.exists():
            python_files.extend(dir_path.rglob('*.py'))

    # Check each file (same as checker)
    all_violations = []
    for file_path in python_files:
        if is_exception_file(file_path, repo_root):
            continue

        violations = check_file(file_path, repo_root)
        if violations:
            all_violations.append((file_path, violations))

    # Build baseline in checker-compatible format
    baseline = {
        "generated_at": datetime.now().isoformat(),
        "total_violations": sum(len(v) for _, v in all_violations),
        "total_files": len(all_violations),
        "by_file": {}
    }

    for file_path, violations in all_violations:
        rel_path = file_path.relative_to(repo_root)
        file_key = str(rel_path).replace('/', '\\')  # Normalize to backslash

        # Store ALL violations (line, pattern pairs)
        baseline['by_file'][file_key] = {
            "total": len(violations),
            "violations": [
                {
                    "line": line_num,
                    "pattern": pattern,
                    "content_preview": content[:80]
                }
                for line_num, content, pattern in violations
            ]
        }

    # Save baseline
    baseline_path = repo_root / 'artifacts' / 'tsot_baseline.json'
    baseline_path.parent.mkdir(exist_ok=True)

    with open(baseline_path, 'w') as f:
        json.dump(baseline, f, indent=2)

    print(f"Generated baseline: {baseline['total_violations']} violations")
    print(f"  Files: {baseline['total_files']}")
    print(f"Saved to: {baseline_path}")

if __name__ == "__main__":
    main()
