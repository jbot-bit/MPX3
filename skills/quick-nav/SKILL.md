---
name: quick-nav
description: Instant navigation for ADHD-friendly project browsing. Use when someone asks "where is", "find", "locate", "navigate to", "show me", or needs to quickly find files/folders. Auto-activates on navigation questions.
allowed-tools: Read, Glob, Grep, Bash(ls:*)
---

# Quick Navigation - ADHD-Optimized

You help users navigate the MPX2 Gold Trading Pipeline project instantly, without overwhelming them.

## Core Principle
**ONE clear answer. NO walls of text. Action-oriented.**

## Navigation Patterns

### When user asks "where is X?"

1. **Identify the item type:**
   - Script/tool → Check category (check_, test_, analyze_, optimize_)
   - Config → Look in config/, trading_app/, or root
   - Data → Check pipeline/, data/, or dbn/
   - Docs → Check docs/ or root *.md files
   - Skill → Check skills/

2. **Respond with:**
   - **Exact path** (file:line_number format)
   - **One-line description** of what it does
   - **Common command** to use it (if applicable)

### File Categories (Quick Reference)

**Production Code (Use These):**
- `pipeline/` - Data ingestion & processing
- `trading_app/` - Live trading application
- `analysis/` - Analysis tools
- `skills/` - Claude Code skills

**Scripts (One-off utilities):**
- `scripts/check/` - Validation scripts
- `scripts/test/` - Test scripts
- `scripts/analyze/` - Analysis scripts
- `scripts/optimize/` - Optimization scripts

**Documentation:**
- `CLAUDE.md` - Project instructions (THIS IS YOUR GUIDE)
- `README.md` - Project overview
- `QUICK_START.md` - Getting started
- `docs/` - Detailed documentation

**Archive (Don't Use):**
- `_archive/` - Old experiments and deprecated code

## Common Requests

### "Find X function/class"
```bash
# Use Grep to search code
grep -r "def function_name" --include="*.py"
grep -r "class ClassName" --include="*.py"
```

### "Show me all test files"
```bash
ls scripts/test/*.py
```

### "Where are the ORB calculations?"
- **Location:** `pipeline/build_daily_features.py:150-300`
- **Also in:** `trading_app/setup_detector.py:45-120`

### "Where is the database schema?"
- **Location:** `schema.sql`
- **Summary script:** `pipeline/check_db.py`

### "Show me validated setups"
- **Database:** `gold.db → validated_setups` table
- **Config:** `trading_app/config.py:MGC_ORB_SIZE_FILTERS`
- **Checker:** `test_app_sync.py` (ALWAYS run after changes)

## Response Format

Always respond in this format:

```
📍 Found: [filename]:[line]

What it does: [one-line description]

Common usage: [command or pattern]

Related: [1-2 related files]
```

## ADHD-Friendly Rules

✅ **DO:**
- Give exact file paths
- Show one clear next action
- Use visual markers (📍 🔧 ⚠️)
- Keep responses < 5 lines

❌ **DON'T:**
- List 10+ files
- Show complex directory trees
- Give vague "it's in the codebase" answers
- Overwhelm with options

## Project Structure (Mental Map)

```
MPX2_fresh/
├── 🎯 Core Production
│   ├── pipeline/           # Data processing
│   ├── trading_app/        # Live trading
│   └── analysis/           # Analysis tools
│
├── 🛠️ Utilities
│   ├── scripts/            # One-off scripts (organized)
│   └── tests/              # Test suite
│
├── 📚 Documentation
│   ├── CLAUDE.md           # Instructions
│   ├── docs/               # Detailed guides
│   └── skills/             # Claude skills
│
├── 💾 Data
│   ├── gold.db             # Main database
│   └── dbn/                # Raw data files
│
└── 🗑️ Archive
    └── _archive/           # Old/deprecated
```

## Quick Commands Reference

**Database:**
```bash
python pipeline/check_db.py              # Check database contents
python analysis/query_features.py        # Query features
python test_app_sync.py                  # Verify sync (CRITICAL)
```

**Data:**
```bash
python backfill_databento_continuous.py  # Backfill data
python pipeline/build_daily_features.py  # Build features
```

**Trading:**
```bash
python trading_app/app_trading_hub.py    # Launch app
python edge_discovery_live.py            # Discover edges
```

## When User Says "I'm Lost"

1. Ask: "What are you trying to do?"
2. Match to category: Data? Trading? Testing? Analysis?
3. Give ONE file path and ONE command
4. Offer to show related files IF they ask

## Dynamic Context Injection

Get real-time file counts:
- Total Python files: !`find . -name "*.py" -not -path "./_archive/*" -not -path "./venv/*" | wc -l`
- Scripts to organize: !`find scripts/ -name "*.py" 2>/dev/null | wc -l`

## Remember

**The goal is SPEED, not completeness.**

Fast, clear, actionable. That's how you help ADHD brains stay on track.
