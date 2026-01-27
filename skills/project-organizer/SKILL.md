---
name: project-organizer
description: Organizes messy project files into clean structure. Use when user says "organize", "clean up", "too many files", "can't find anything", "project is messy". Auto-activates when root directory has 50+ files.
allowed-tools: Bash(ls:*), Bash(mv:*), Bash(mkdir:*), Read, Glob
---

# Project Organizer - ADHD-Friendly File Management

You help maintain a clean, navigable project structure optimized for ADHD brains.

## Core Principle
**LESS IS MORE. Root directory = < 20 essential files.**

## Target Structure (Goal State)

```
MPX2_fresh/
├── 📄 CRITICAL FILES (keep in root, < 20 total)
│   ├── CLAUDE.md              # Project instructions
│   ├── README.md              # Overview
│   ├── QUICK_START.md         # Getting started
│   ├── PROJECT_MAP.md         # Visual navigation
│   ├── OPEN_PROJECT.bat       # Launch script
│   ├── test_app_sync.py       # Critical validator
│   ├── gold.db                # Main database
│   ├── .env                   # Environment config
│   ├── requirements.txt       # Dependencies
│   └── schema.sql             # Database schema
│
├── 🎯 PRODUCTION CODE
│   ├── pipeline/              # Data ingestion
│   ├── trading_app/           # Live trading
│   ├── analysis/              # Analysis tools
│   └── execution_metrics.py   # Core metrics
│
├── 🛠️ SCRIPTS (organized by purpose)
│   ├── scripts/
│   │   ├── check/             # Validation scripts (check_*.py)
│   │   ├── test/              # Test scripts (test_*.py)
│   │   ├── analyze/           # Analysis (analyze_*.py)
│   │   ├── optimize/          # Optimization (optimize_*.py)
│   │   └── utils/             # Utilities (everything else)
│
├── 📚 DOCUMENTATION
│   ├── docs/                  # Detailed guides
│   ├── skills/                # Claude skills
│   └── audits/                # Audit reports
│
├── 📊 RESULTS & LOGS
│   ├── results/               # Analysis results
│   ├── strategies/            # Strategy definitions
│   └── logs/                  # Log files (*.log)
│
└── 🗑️ ARCHIVE
    └── _archive/              # Old/deprecated code
```

## Current Problem

Root directory has **221 files**:
- 83 Python files
- 55 Markdown files
- 50 text files
- 41 one-off scripts with no clear organization

**This is overwhelming for ADHD brains.**

## Organization Workflow

### Phase 1: Audit Current State
```bash
# Count files by type
echo "Python files:" && ls -1 *.py 2>/dev/null | wc -l
echo "Markdown files:" && ls -1 *.md 2>/dev/null | wc -l
echo "Text files:" && ls -1 *.txt 2>/dev/null | wc -l
echo "Log files:" && ls -1 *.log 2>/dev/null | wc -l

# Identify categories
echo "\nCheck scripts:" && ls -1 check_*.py 2>/dev/null | wc -l
echo "Test scripts:" && ls -1 test_*.py 2>/dev/null | wc -l
echo "Analyze scripts:" && ls -1 analyze_*.py 2>/dev/null | wc -l
echo "Optimize scripts:" && ls -1 optimize_*.py 2>/dev/null | wc -l
```

### Phase 2: Create Organized Structure
```bash
# Create organized directories
mkdir -p scripts/{check,test,analyze,optimize,utils}
mkdir -p results logs
```

### Phase 3: Check for Imports FIRST (CRITICAL)

**BEFORE moving ANY file, check if it's imported elsewhere:**

```bash
# Check if file is imported by production code
echo "Checking imports for: [filename]"
grep -r "from [filename_without_py]\|import [filename_without_py]" \
  pipeline/ trading_app/ analysis/ *.py 2>/dev/null | \
  grep -v ".pyc" | grep -v "__pycache__"

# If ANY results found:
# - STOP immediately
# - DO NOT move the file
# - Warn user about broken imports
```

**MANDATORY CHECKS before moving:**
1. ✅ Check for imports in production code (pipeline/, trading_app/)
2. ✅ Check for imports in root Python files
3. ✅ Check for imports in analysis/
4. ✅ If ANYTHING imports this file → DO NOT MOVE
5. ✅ Only move if ZERO imports found

**Example:**
```bash
# Moving check_db.py?
# First check:
grep -r "from check_db\|import check_db" pipeline/ trading_app/ *.py

# If output is empty → SAFE to move
# If output has results → DO NOT MOVE (imports will break)
```

### Phase 4: Move Files (Only After Import Check)

**ALWAYS ask before moving files. NEVER move without confirmation.**
**NEVER move without running import check first.**

**Check scripts (check_*.py):**
```bash
# Show what will be moved
ls -1 check_*.py

# Confirm with user first!
# Then move:
mv check_*.py scripts/check/
```

**Test scripts (test_*.py) - EXCEPT test_app_sync.py:**
```bash
# Show what will be moved
ls -1 test_*.py | grep -v "test_app_sync.py"

# Confirm with user first!
# Then move:
find . -maxdepth 1 -name "test_*.py" ! -name "test_app_sync.py" -exec mv {} scripts/test/ \;
```

**Analyze scripts (analyze_*.py):**
```bash
mv analyze_*.py scripts/analyze/
```

**Optimize scripts (optimize_*.py):**
```bash
mv optimize_*.py scripts/optimize/
```

**Results files (*.txt with results, *.csv):**
```bash
# Move results files
mv *results*.txt results/
mv *results*.csv results/
mv *validation*.txt results/
mv *optimization*.json results/
```

**Log files:**
```bash
mv *.log logs/
```

**Old/experimental files:**
```bash
# Move to archive (confirm first!)
mv *_old.py _archive/
mv *_backup.py _archive/
mv deprecated_*.py _archive/
```

### Phase 4: Update Import Paths

After moving scripts, some imports may break. Check for:

```python
# Old imports (before organization)
import check_db
from test_filters import something

# New imports (after organization)
import scripts.check.check_db
from scripts.test.test_filters import something
```

**IMPORTANT:** Ask user before updating imports. They may prefer to leave scripts as standalone.

### Phase 5: Create Navigation Helpers

**Create scripts/README.md:**
```markdown
# Scripts Directory

Organized one-off scripts and utilities.

## Categories

- `check/` - Validation and verification scripts
- `test/` - Test scripts and test runners
- `analyze/` - Data analysis and exploration
- `optimize/` - Strategy optimization tools
- `utils/` - General utilities

## Usage

Run scripts from project root:
```bash
python scripts/check/check_db.py
python scripts/test/test_filters.py
```

Most scripts are standalone and don't require imports.
```

## File Classification Rules

### ✅ KEEP IN ROOT (< 20 files)
- **Critical validators:** test_app_sync.py
- **Core executables:** gold.db, schema.sql, execution_metrics.py
- **Launch scripts:** OPEN_PROJECT.bat, run_*.bat
- **Documentation:** CLAUDE.md, README.md, QUICK_START.md, PROJECT_MAP.md
- **Config:** .env, requirements.txt, .gitignore

### 📁 MOVE TO scripts/
- **All check_*.py** → scripts/check/
- **All test_*.py (except test_app_sync.py)** → scripts/test/
- **All analyze_*.py** → scripts/analyze/
- **All optimize_*.py** → scripts/optimize/
- **All other one-off scripts** → scripts/utils/

### 📊 MOVE TO results/
- **All *results*.txt** → results/
- **All *results*.csv** → results/
- **All *validation*.txt** → results/
- **All optimization_*.json** → results/

### 📝 MOVE TO docs/
- **All audit reports** → docs/audits/ (if not in audits/ already)
- **All implementation guides** → docs/
- **Historical summaries** → docs/history/

### 🗑️ MOVE TO _archive/
- **Old versions:** *_old.py, *_backup.py
- **Deprecated code:** deprecated_*.py
- **Experiments:** experiment_*.py
- **Superseded files:** (files replaced by new versions)

## Safety Rules (NEVER VIOLATE)

### 🚨 RULE #0: CHECK IMPORTS FIRST (MOST CRITICAL)

**BEFORE moving ANY Python file:**
```bash
grep -r "from [filename_no_py]\|import [filename_no_py]" \
  pipeline/ trading_app/ analysis/ *.py 2>/dev/null
```

**If ANY imports found:**
- ❌ DO NOT MOVE THE FILE
- ⚠️  WARN USER: "This file is imported by [other_file]. Moving it will break imports."
- 🛡️ SUGGEST: "Keep in root or update imports in dependent files first"

**This check is MANDATORY. NO EXCEPTIONS.**

### 🛑 NEVER move these without explicit permission:
- test_app_sync.py (CRITICAL validator)
- gold.db (main database)
- .env (secrets)
- Any file in pipeline/
- Any file in trading_app/
- Any file currently in production use

### ⚠️  ALWAYS confirm before:
- Moving more than 10 files at once
- Deleting any file
- Moving files with dependencies
- Changing file locations that may break imports

### ✅ ALWAYS do:
- Ask user to confirm file list before moving
- Create backup of moved files list
- Test that nothing broke after moving
- Update documentation with new locations

## Organization Templates

### Interactive Organization (Recommended for ADHD)

```
🗂️  PROJECT ORGANIZER

I found [N] files in the root directory that could be organized.

Current state:
- Check scripts: [N] files
- Test scripts: [N] files
- Analyze scripts: [N] files
- Optimize scripts: [N] files
- Result files: [N] files
- Log files: [N] files

Proposed action:
□ Move check scripts to scripts/check/
□ Move test scripts to scripts/test/ (except test_app_sync.py)
□ Move analyze scripts to scripts/analyze/
□ Move optimize scripts to scripts/optimize/
□ Move results to results/
□ Move logs to logs/

This will reduce root directory from [N] files to < 20 files.

Show me the file list? [YES to see list, NO to proceed]
```

### Batch Organization (Fast mode)

```
🗂️  BATCH ORGANIZER

Organizing [N] files in [category]...

Moving:
- [file1]
- [file2]
- [file3]
...

[Progress bar]

✅ Done! Root directory now has [N] files (was [M]).
```

## Post-Organization Checklist

After organizing, verify:

```bash
# Verify critical files still work
python test_app_sync.py                  # Should still run
python pipeline/check_db.py              # Should still run
ls gold.db                               # Should exist

# Verify root directory is clean
ls -1 *.py | wc -l                       # Should be < 20

# Verify scripts are in place
ls scripts/check/ scripts/test/          # Should show files
```

## Maintenance Rules

### Weekly Cleanup (Automated)
- Move new check_*.py to scripts/check/
- Move new test_*.py to scripts/test/
- Move new logs to logs/
- Move new results to results/

### Monthly Archive
- Review _archive/ for files to delete
- Clean up old backup files
- Remove obsolete experiments

## ADHD-Specific Features

### Visual Progress
Always show:
```
📦 ORGANIZING: [category]
━━━━━━━━━━━━━━━━━━━━ 45% (12/26 files)

Moving: check_db.py → scripts/check/
```

### Undo Instructions
Always provide after major changes:
```
✅ Organization complete!

To undo:
mv scripts/check/*.py .
mv scripts/test/*.py .
(restore commands...)

Git restore:
git checkout HEAD -- .
```

### One Category at a Time
Don't overwhelm. Organize in steps:
1. First: Check scripts (smallest category)
2. Then: Test scripts
3. Then: Analyze scripts
4. Then: Results files
5. Finally: Logs and archives

## Integration with Other Skills

**Use quick-nav after organizing:**
- Update navigation to new structure
- Teach user new file locations

**Use focus-mode during organizing:**
- Stay on task
- Don't get distracted cleaning up code
- Just move files, don't refactor

## Remember

**The goal is FINDABILITY, not perfection.**

Clean root directory = Clear mind. That's the win.
