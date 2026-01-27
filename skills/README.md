# Skills Directory

This directory contains Anthropic skills that guide Claude Code when working on specialized tasks in this project.

## Available Skills

### 🛡️ code-guardian **[AUTO-ACTIVATES]**
**Purpose:** Protects critical trading logic and research process from accidental breakage

**Source:** Custom (ADHD-friendly project safety)

**When to use:**
- BEFORE editing any protected file (pipeline/, trading_app/, config.py, etc.)
- Before trusting edge discovery results
- Before adding strategies to validated_setups
- Before manual transcription of optimization results
- AUTOMATICALLY activates on protected file edits

**Key files:**
- `SKILL.md` - Production safety protocol + research integrity gates

**Key protections:**
- Database/config sync validation
- File backups before edits
- test_app_sync.py enforcement
- Overfitting detection
- Confirmation bias checks
- Stress testing requirements
- Research integrity checklist (10-point gate)

---

### 📍 quick-nav **[AUTO-ACTIVATES]**
**Purpose:** ADHD-optimized instant project navigation

**Source:** Custom (ADHD-friendly navigation)

**When to use:**
- User asks "where is...", "find...", "locate..."
- User needs to navigate quickly
- AUTOMATICALLY activates on navigation questions

**Key files:**
- `SKILL.md` - Fast-find patterns and directory map

**Key features:**
- ONE clear answer (no walls of text)
- Exact file:line_number paths
- Visual markers (📍 🔧 ⚠️)
- Common command shortcuts
- Mental map of project structure

---

### 🗂️ project-organizer **[AUTO-ACTIVATES]**
**Purpose:** Organizes messy project structure (221 files → < 20 in root)

**Source:** Adapted from file-organizer skill

**When to use:**
- Root directory has 50+ files
- User says "organize", "clean up", "too many files"
- User seems overwhelmed by file count
- AUTOMATICALLY offers to organize when needed

**Key files:**
- `SKILL.md` - File organization workflow and safety rules

**Key features:**
- Categorizes scripts (check/, test/, analyze/, optimize/)
- Moves results and logs to organized folders
- Archives old/deprecated code
- ADHD-friendly: one category at a time
- Always asks before moving files

---

### 🎯 focus-mode **[AUTO-ACTIVATES]**
**Purpose:** ADHD task management and focus system

**Source:** Custom (ADHD-specific productivity)

**When to use:**
- User says "what should I do?", "I'm stuck", "overwhelmed"
- Multiple unrelated questions in one message
- User switches topics mid-conversation
- Decision paralysis detected
- AUTOMATICALLY activates when user needs focus help

**Key files:**
- `SKILL.md` - Focus protocols, timeboxing, context switching

**Key features:**
- ONE TASK at a time
- 25-minute Pomodoro focus blocks
- Context saving for task switches
- Decision paralysis helpers
- Progress tracking and celebration
- Anti-patterns detection (yak shaving, perfectionism, analysis paralysis)

---

### 📝 git-workflow
**Purpose:** Simple git workflow for solo trading project

**Source:** Adapted from git-workflow-guide (simplified for ADHD)

**When to use:**
- Committing changes
- Before risky edits (checkpoint commits)
- End of session (backup)
- Undoing mistakes

**Key files:**
- `SKILL.md` - Git workflow patterns and commands

**Key features:**
- COMMIT OFTEN principle
- Checkpoint commits for experiments
- Simple message templates
- ADHD-friendly patterns (stash for context switching)
- Emergency procedures (undo, restore)
- No complex branching (main branch only)

---

## Available Skills

### 🎨 frontend-design
**Purpose:** Creating distinctive, production-grade frontend interfaces

**Source:** https://github.com/anthropics/skills/tree/main/skills/frontend-design

**When to use:**
- Designing or creating new UI components
- Updating existing pages or interfaces
- Beautifying or styling web elements
- Creating React components or HTML/CSS layouts

**Key files:**
- `SKILL.md` - Core frontend design principles and guidelines
- `TRADING_APP_DESIGN.md` - Trading app specific design patterns
- `LICENSE.txt` - License information

**Trading App Design Direction:**
- Industrial/utilitarian aesthetic with refined data visualization
- Professional trading terminal look (dark theme, monospace fonts)
- Information density without clutter
- Green/red for P&L, clear visual hierarchy
- Real-time data must be instantly scannable

---

### 🔌 mcp-builder
**Purpose:** Building high-quality MCP (Model Context Protocol) servers

**Source:** https://github.com/anthropics/skills/tree/main/skills/mcp-builder

**When to use:**
- Creating MCP servers for external API integrations
- Refactoring existing API clients to use MCP
- Building tools that enable LLM interactions with services

**Key files:**
- `SKILL.md` - MCP development workflow and guidelines
- `reference/mcp_best_practices.md` - Universal MCP guidelines
- `reference/node_mcp_server.md` - TypeScript implementation guide
- `reference/python_mcp_server.md` - Python implementation guide
- `reference/evaluation.md` - Creating evaluation questions
- `scripts/` - Evaluation runner scripts

**Current MCP Status:**
See `docs/MCP_INTEGRATION_PLAN.md` for detailed integration plan.
- ❌ ProjectX API: Needs MCP server (high priority)
- ⚠️ AI Assistant: Consider MCP formalization (medium priority)
- ✅ Databento API: Keep as-is (low priority)

---

## How Skills Work

Skills provide specialized guidance to Claude Code when working on specific types of tasks. When you ask Claude to work on frontend design or create an MCP server, it will automatically reference the appropriate skill to ensure high-quality, consistent implementation.

### Integration with CLAUDE.md

The main project file `CLAUDE.md` references these skills and tells Claude when to use them:

```markdown
## ⚡ Skills Integration

### Frontend Design (`skills/frontend-design/`)
**When to use:** Designing, creating, or updating any UI components...

### MCP Server Development (`skills/mcp-builder/`)
**When to use:** Creating or refactoring API integrations...
```

This ensures Claude automatically applies skill guidelines when working on relevant tasks.

---

## Adding New Skills

To add a new skill from Anthropic's repository:

1. **Clone the skills repo:**
   ```bash
   git clone --depth 1 --filter=blob:none --sparse https://github.com/anthropics/skills.git temp_skills
   cd temp_skills
   git sparse-checkout set skills/SKILL_NAME
   ```

2. **Copy to project:**
   ```bash
   cp -r skills/SKILL_NAME ../skills/
   ```

3. **Update CLAUDE.md:**
   Add a section describing when to use the new skill.

4. **Create project-specific guide (optional):**
   If needed, create a project-specific guide like `TRADING_APP_DESIGN.md` that applies the skill to this project's context.

5. **Clean up:**
   ```bash
   cd .. && rm -rf temp_skills
   ```

---

## Skill Maintenance

Skills are versioned snapshots from the Anthropic skills repository. To update:

1. Re-pull from the source repository
2. Review changes for breaking modifications
3. Update project-specific guides if needed
4. Test that existing code still works with updated guidelines

**Last Updated:** 2026-01-25

---

## References

- Anthropic Skills Repository: https://github.com/anthropics/skills
- Model Context Protocol: https://modelcontextprotocol.io/
- Project Documentation: `docs/`
