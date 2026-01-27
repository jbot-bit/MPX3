"""Replace all daily_features references with daily_features"""
import os
from pathlib import Path

# Get all Python files
python_files = list(Path('.').rglob('*.py'))

# Exclude venv and specific files
exclude_dirs = {'venv', '__pycache__', '.git', 'node_modules'}
python_files = [
    f for f in python_files
    if not any(excluded in f.parts for excluded in exclude_dirs)
]

print(f"Found {len(python_files)} Python files to process")
print()

updated_count = 0
total_replacements = 0

for file_path in python_files:
    try:
        content = file_path.read_text(encoding='utf-8')

        if 'daily_features' in content:
            new_content = content.replace('daily_features', 'daily_features')
            replacements = content.count('daily_features')

            file_path.write_text(new_content, encoding='utf-8')

            print(f"[OK] {file_path}: {replacements} replacements")
            updated_count += 1
            total_replacements += replacements

    except Exception as e:
        print(f"[ERROR] {file_path}: {e}")

print()
print("="*80)
print(f"COMPLETE: Updated {updated_count} files, {total_replacements} total replacements")
print("="*80)
print()
print("All references to 'daily_features' have been replaced with 'daily_features'")
