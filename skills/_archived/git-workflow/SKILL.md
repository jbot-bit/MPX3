---
name: git-workflow
description: Git workflow for solo trading project. Use when committing changes, creating branches, or managing git history. Simple workflow optimized for ADHD and rapid iteration.
allowed-tools: Bash(git:*)
---

# Git Workflow - Solo Trading Project

Simplified git workflow for solo development with ADHD-friendly patterns.

## Core Principle
**COMMIT OFTEN. SIMPLE MESSAGES. NO COMPLEXITY.**

## Daily Workflow

### 1. Morning: Check Status

```bash
git status
git log --oneline -5
```

**What to look for:**
- Uncommitted changes from yesterday?
- Where did you leave off?
- Any WIP branches?

### 2. Before Starting Work: Save Point

```bash
git add .
git commit -m "checkpoint: [what you're about to work on]"
```

**Why:**
- Creates restore point
- ADHD-friendly: can experiment without fear
- Easy rollback if you break something

### 3. During Work: Micro-Commits

**Commit after EVERY meaningful change:**
```bash
git add [specific files]
git commit -m "[action]: [what changed]"
```

**Examples:**
- `fix: test_app_sync validation for NQ setups`
- `add: 0900 ORB stress test with adverse slippage`
- `update: MGC RR from 1.0 to 2.0 based on analysis`
- `refactor: move check scripts to scripts/check/`
- `docs: add AUTO_ARCHIVE_RULE.md`

**Commit Prefixes:**
- `fix:` - Bug fixes
- `add:` - New features/files
- `update:` - Changes to existing logic
- `refactor:` - Code cleanup (no logic change)
- `docs:` - Documentation only
- `test:` - Test changes
- `checkpoint:` - Save point (WIP)

### 4. End of Day: Clean Commit

```bash
# Review what you did today
git log --oneline --since="1 day ago"

# If last commit was "checkpoint", squash into clean commit
git reset --soft HEAD~1
git commit -m "[clean message describing today's work]"
```

### 5. Push to Remote (Optional)

```bash
git push origin main
```

**When to push:**
- End of session (backup)
- Before major changes
- After completing feature
- Before experimenting with risky changes

## Branch Strategy (Simple)

### Main Branch
- **main** - Always working code
- Commit often, keep it stable
- If something breaks, revert immediately

### Feature Branches (Rare)
Only use for:
- Major refactors
- Risky experiments
- Multi-day features

```bash
# Create feature branch
git checkout -b feature/limit-order-execution

# Work on feature...
git add .
git commit -m "add: limit order execution mode"

# Merge back when done
git checkout main
git merge feature/limit-order-execution
git branch -d feature/limit-order-execution
```

**ADHD tip:** Avoid branches if possible. They add complexity.

## Commit Messages (ADHD-Friendly)

### Good Messages (Clear, Specific)
```
✅ fix: test_app_sync.py failing on NQ validation
✅ add: 0900 ORB with RR=2.0 based on stress test
✅ update: MGC filter from None to 0.05
✅ refactor: organize 235 root files into scripts/
✅ docs: create PROJECT_MAP.md for navigation
```

### Bad Messages (Vague, Useless)
```
❌ fix bug
❌ update stuff
❌ checkpoint
❌ WIP
❌ changes
```

### Message Template
```
[type]: [what changed] [optional: why]

Examples:
- fix: database sync check for MPL setups
- add: auto-archive script for strategy updates
- update: RR=1.0→2.0 based on adverse slippage test
- refactor: move test scripts to scripts/test/
- docs: document ADHD-friendly skills
```

## Common Git Tasks

### Undo Last Commit (Keep Changes)
```bash
git reset --soft HEAD~1
```
**Use when:** Commit message was wrong, or committed too early

### Undo Last Commit (Discard Changes)
```bash
git reset --hard HEAD~1
```
**⚠️ DANGEROUS:** Loses all changes. Only use if you're sure.

### Restore File to Last Commit
```bash
git checkout HEAD -- [filename]
```
**Use when:** Broke a file, want to restore working version

### See What Changed
```bash
git diff                    # Unstaged changes
git diff --staged           # Staged changes
git diff HEAD~1             # Changes since last commit
git diff main..branch-name  # Changes between branches
```

### View History
```bash
git log --oneline -10           # Last 10 commits
git log --oneline --since="2 days ago"
git log --oneline --grep="ORB"  # Search commits
```

### Stash Changes (Temporary Save)
```bash
git stash                   # Save current changes
git stash list              # See all stashes
git stash pop               # Restore last stash
git stash drop              # Delete last stash
```
**Use when:** Need to switch context quickly (ADHD!)

## ADHD-Specific Patterns

### Pattern 1: Checkpoint Commits
```bash
# Starting new experiment
git add .
git commit -m "checkpoint: before testing limit orders"

# Experiment...

# If it works:
git add .
git commit -m "add: limit order execution (tested)"

# If it fails:
git reset --hard HEAD~1  # Restore checkpoint
```

### Pattern 2: End-of-Day Cleanup
```bash
# View today's commits
git log --oneline --since="1 day ago"

# Squash multiple checkpoints into clean commit
git reset --soft HEAD~5  # Go back 5 commits, keep changes
git commit -m "add: limit order execution with slippage analysis"
```

### Pattern 3: Safe Experimentation
```bash
# Create experiment branch
git checkout -b experiment/crazy-idea

# Try stuff...
# (no fear of breaking main)

# If it works:
git checkout main
git merge experiment/crazy-idea

# If it fails:
git checkout main
git branch -D experiment/crazy-idea  # Delete failed experiment
```

### Pattern 4: Context Switching (Fast)
```bash
# Working on feature A, need to switch to feature B
git stash                    # Save feature A
git checkout feature-b       # Switch
# Work on feature B...
git checkout main
git stash pop                # Resume feature A
```

## Safety Rules

### 🚨 NEVER do these on main branch:
- `git reset --hard` (unless you're SURE)
- `git push --force`
- `git rebase` (too complex for solo dev)
- `git commit --amend` on pushed commits

### ✅ ALWAYS do these:
- Commit before risky changes
- Push to backup regularly
- Use clear commit messages
- Test after major changes

## Integration with Other Skills

### With code-guardian:
```
🛡️ + 📝 CODE GUARDIAN + GIT WORKFLOW

Before editing [protected file]:
1. Create checkpoint commit
2. Edit with safety checks
3. Test with test_app_sync.py
4. Commit with clear message

If test fails:
git reset --hard HEAD~1  # Restore checkpoint
```

### With project-organizer:
```
🗂️ + 📝 PROJECT ORGANIZER + GIT WORKFLOW

After organizing files:
git add .
git commit -m "refactor: organize 235 root files into scripts/"
git push origin main  # Backup reorganization
```

### With focus-mode:
```
🎯 + 📝 FOCUS MODE + GIT WORKFLOW

Start of focus block:
git commit -m "checkpoint: [task]"

End of focus block:
git commit -m "[type]: [achievement]"
```

## Emergency Procedures

### "I broke everything"
```bash
# Option 1: Undo last commit
git reset --hard HEAD~1

# Option 2: Go back to working version
git log --oneline -10  # Find last working commit
git reset --hard [commit-hash]

# Option 3: Restore from remote
git fetch origin
git reset --hard origin/main
```

### "I committed wrong files"
```bash
# Undo commit, keep changes
git reset --soft HEAD~1

# Remove unwanted files
git reset HEAD [unwanted-file]

# Re-commit correctly
git add [correct-files]
git commit -m "[message]"
```

### "I need to see old version"
```bash
# View file from 5 commits ago
git show HEAD~5:[filename]

# Restore file from commit
git checkout [commit-hash] -- [filename]
```

## Common Scenarios

### Scenario 1: Adding New Strategy
```bash
# 1. Create checkpoint
git commit -m "checkpoint: adding 1100 ORB strategy"

# 2. Run edge discovery
python edge_discovery_live.py

# 3. Commit results
git add results/1100_results.txt
git commit -m "add: 1100 ORB edge discovery results"

# 4. Update validated_setups
python strategies/archive_strategy.py --setup-id 10 --reason "New analysis"
# Update database...
git add gold.db trading_app/config.py
git commit -m "add: 1100 ORB strategy (RR=2.0, filter=0.05)"

# 5. Test
python test_app_sync.py
git commit -m "test: verify 1100 ORB integration"
```

### Scenario 2: Fixing Bug
```bash
# 1. Identify bug
git status  # See what's changed

# 2. Fix
# Edit file...
python test_app_sync.py  # Verify fix

# 3. Commit
git add [fixed-file]
git commit -m "fix: [specific bug description]"

# 4. Push
git push origin main
```

### Scenario 3: Organizing Project
```bash
# 1. Checkpoint before big change
git commit -m "checkpoint: before organizing root directory"

# 2. Organize
# Move files...

# 3. Test
python test_app_sync.py
python pipeline/check_db.py

# 4. Commit
git add .
git commit -m "refactor: organize 235 files into scripts/, docs/, results/"

# 5. Push (backup important change)
git push origin main
```

## Reminders

**For ADHD:**
- Commit often (every 15-30 minutes)
- Use checkpoints for experiments
- Don't overthink commit messages
- Push to backup regularly
- Use stash for context switching

**For Trading:**
- ALWAYS commit before touching validated_setups
- ALWAYS commit after test_app_sync.py passes
- Include strategy parameters in commit messages
- Link commits to analysis/results files

**General:**
- Simple > Complex
- Commit > Perfect
- Backup > Sorry

## Quick Reference

```bash
# Daily workflow
git status                              # Check status
git add [files]                         # Stage files
git commit -m "[type]: [message]"       # Commit
git push origin main                    # Push to remote

# Undo/restore
git reset --soft HEAD~1                 # Undo commit, keep changes
git reset --hard HEAD~1                 # Undo commit, discard changes
git checkout HEAD -- [file]             # Restore file

# History
git log --oneline -10                   # Recent commits
git diff                                # See changes

# Context switching
git stash                               # Save changes
git stash pop                           # Restore changes

# Emergency
git reset --hard origin/main            # Reset to remote
```

## Remember

**Git is YOUR safety net, not your enemy.**

Use it to:
- Experiment without fear
- Save your work
- Rollback mistakes
- Track your progress

**Don't overthink it. Just commit.**
