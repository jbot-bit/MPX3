"""
Generate TSOT baseline from migration map

This creates a snapshot of known violations to enable NEW-only enforcement.
"""
import json
from datetime import datetime

# Read migration map
with open('tsot_migration_map.json', 'r') as f:
    migration_map = json.load(f)

# Build baseline
baseline = {
    "generated_at": datetime.now().isoformat(),
    "total_violations": migration_map['metadata']['total_violations'],
    "by_category": migration_map['metadata']['categories'],
    "by_file": {}
}

# Extract violations by file
for file_path, file_data in migration_map['files'].items():
    violations = file_data.get('violations', [])

    structural_lines = []
    ui_lines = []

    for v in violations:
        line = v.get('line')
        category = v.get('category', '')

        if category == 'STRUCTURAL_MIGRATE':
            structural_lines.append(line)
        elif category == 'UI_OPERATIONAL_ALLOW':
            ui_lines.append(line)

    baseline['by_file'][file_path] = {
        "structural": len(structural_lines),
        "ui_operational": len(ui_lines),
        "structural_lines": sorted(structural_lines),
        "ui_lines": sorted(ui_lines)
    }

# Write baseline
with open('artifacts/tsot_baseline.json', 'w') as f:
    json.dump(baseline, f, indent=2)

print(f"Generated baseline: {baseline['total_violations']} violations")
print(f"  Structural: {baseline['by_category']['STRUCTURAL_MIGRATE']}")
print(f"  UI/Operational: {baseline['by_category']['UI_OPERATIONAL_ALLOW']}")
print(f"Saved to: artifacts/tsot_baseline.json")
