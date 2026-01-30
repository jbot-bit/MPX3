"""Extract Phase 1 violations from TSOT migration map"""
import json

# Read migration map
with open('tsot_migration_map.json', 'r') as f:
    data = json.load(f)

# Phase 1 files
phase1_files = [
    'trading_app\\live_scanner.py',
    'trading_app\\config.py',
    'trading_app\\execution_spec.py'
]

print("=" * 80)
print("PHASE 1 IMPACT MAP - STRUCTURAL VIOLATIONS ONLY")
print("=" * 80)
print()

total_structural = 0

for file_path in phase1_files:
    if file_path not in data['files']:
        print(f"WARNING: {file_path} not found in migration map")
        continue

    file_data = data['files'][file_path]
    violations = file_data.get('violations', [])

    # Filter structural only
    structural = [v for v in violations if v.get('category') == 'STRUCTURAL_MIGRATE']

    total_structural += len(structural)

    print(f"\n{'=' * 80}")
    print(f"FILE: {file_path}")
    print(f"{'=' * 80}")
    print(f"Total violations: {len(violations)}")
    print(f"Structural (to migrate): {len(structural)}")
    print(f"UI/Display (keep): {len(violations) - len(structural)}")
    print()

    if structural:
        print("STRUCTURAL VIOLATIONS:")
        for v in structural:
            line = v.get('line')
            content = v.get('content_preview', '')[:80]
            mapping = v.get('time_spec_mapping', 'NOT_MAPPED')
            notes = v.get('notes', '')

            print(f"  Line {line}: {content}")
            print(f"    -> Migrate to: {mapping}")
            if notes:
                print(f"    Notes: {notes}")
        print()

print("=" * 80)
print(f"TOTAL STRUCTURAL VIOLATIONS (PHASE 1): {total_structural}")
print("=" * 80)
