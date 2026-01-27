# MCP Integration Plan for Trading App

## Executive Summary

This document assesses current API integrations against MCP (Model Context Protocol) best practices and provides a refactoring plan to align with the mcp-builder skill guidelines.

## Current Integration Assessment

### 1. ProjectX API Integration
**Location:** `lib/projectx/projectx_client.py`

**Current State:**
- Direct HTTP client implementation using httpx
- Token-based authentication
- Three main operations:
  - Login/authentication
  - Contract search
  - Historical bar retrieval

**MCP Alignment:** ❌ Not aligned
- Direct API calls without MCP wrapper
- No tool definitions
- No structured error handling
- No pagination support

**Recommendation:** **CREATE MCP SERVER** - High priority
- ProjectX data is critical for trading
- Would benefit from standardized access across tools
- Multiple consumers (backtesting, live trading, analysis)

---

### 2. Databento API Integration
**Location:** `pipeline/backfill_databento_continuous.py`, `pipeline/inspect_dbn.py`

**Current State:**
- Uses official `databento` Python client
- DBN (Databento Binary) file format handling
- Contract selection logic
- Historical data backfilling

**MCP Alignment:** ⚠️ Partially aligned
- Uses official SDK (good practice)
- Well-structured for single-purpose pipeline
- Not exposed as reusable tools

**Recommendation:** **KEEP AS-IS** - Low priority
- Pipeline scripts work well
- Databento SDK is well-maintained
- Not frequently accessed by multiple components
- MCP wrapper would add unnecessary complexity

---

### 3. AI Assistant (Anthropic/OpenAI)
**Location:** `trading_app/ai_assistant.py`, `trading_app/ai_guard.py`

**Current State:**
- **AI Guard system** already implemented
- Source lock enforced (all calls go through `guarded_chat_answer()`)
- Evidence Pack pattern for context injection
- Prompt validation and safety checks
- Memory persistence
- Multi-provider support (Anthropic/OpenAI)

**MCP Alignment:** ✅ Well-aligned conceptually
- Guard system is similar to MCP tool pattern
- Structured inputs (EvidencePack, SetupInfo)
- Controlled access through wrapper
- **BUT:** Not using MCP protocol

**Recommendation:** **CONSIDER MCP FORMALIZATION** - Medium priority
- Current AI Guard is working well
- MCP would provide:
  - Standard protocol for LLM interactions
  - Better separation of concerns
  - Reusability across different AI tools
  - Tool discoverability
- Migration path: Wrap existing guard as MCP server

---

## MCP Integration Plan

### Phase 1: ProjectX MCP Server (HIGH PRIORITY)

**Goal:** Create production-grade MCP server for ProjectX API

**Implementation Steps:**

1. **Research Phase**
   - Load MCP best practices: `skills/mcp-builder/reference/mcp_best_practices.md`
   - Load TypeScript guide: `skills/mcp-builder/reference/node_mcp_server.md`
   - Review ProjectX API documentation
   - Choose transport: **Streamable HTTP** (stateless, scalable)

2. **Tool Design**
   - `projectx_login` - Authenticate and get token
   - `projectx_search_contracts` - Find active contracts by symbol
   - `projectx_get_bars` - Retrieve historical bars with pagination
   - `projectx_get_contract_info` - Get contract details
   - `projectx_get_active_contract` - Get current front month

3. **Implementation**
   ```
   projectx-mcp-server/
   ├── src/
   │   ├── index.ts           # Server entry point
   │   ├── tools/
   │   │   ├── auth.ts        # Login tool
   │   │   ├── contracts.ts   # Contract search
   │   │   └── bars.ts        # Historical data
   │   ├── client.ts          # ProjectX API client
   │   └── schemas.ts         # Zod schemas
   ├── package.json
   ├── tsconfig.json
   └── README.md
   ```

4. **Quality Checklist**
   - ✅ Clear tool names with `projectx_` prefix
   - ✅ Zod schemas for input validation
   - ✅ Output schemas defined
   - ✅ Actionable error messages
   - ✅ Pagination support for bars
   - ✅ Proper hints (readOnlyHint, etc.)
   - ✅ Stateless HTTP transport
   - ✅ Comprehensive tests
   - ✅ 10 evaluation questions

5. **Integration**
   - Update `data_loader.py` to use MCP client
   - Update `backfill_range.py` to use MCP tools
   - Migrate `projectx_client.py` consumers

**Timeline:** 2-3 days
**Risk:** Medium (requires ProjectX API testing)

---

### Phase 2: AI Guard → MCP Server (MEDIUM PRIORITY)

**Goal:** Formalize AI Guard as MCP server while maintaining security

**Implementation Steps:**

1. **Current Architecture Review**
   - AI Guard enforces source lock
   - Evidence Pack provides structured context
   - Safety checks prevent leaks
   - Memory persistence works

2. **MCP Server Design**
   ```
   trading-ai-mcp-server/
   ├── src/
   │   ├── index.ts
   │   ├── tools/
   │   │   ├── chat.ts           # guarded_chat_answer as tool
   │   │   ├── context.ts         # load setups/positions
   │   │   └── journal.ts         # trade journal access
   │   ├── guards/
   │   │   ├── source_lock.ts     # AI source lock
   │   │   └── prompt_validation.ts
   │   └── schemas.ts
   ├── package.json
   └── README.md
   ```

3. **Tool Definitions**
   - `trading_ai_chat` - Guarded chat with evidence pack
   - `trading_ai_load_context` - Get validated setups
   - `trading_ai_get_positions` - Get current positions
   - `trading_ai_journal_entry` - Create journal entry
   - `trading_ai_analyze_setup` - Analyze detected setup

4. **Benefits**
   - Standard MCP protocol
   - Tool-based context injection
   - Reusable across different UIs
   - Better separation of concerns
   - AI Guard logic preserved

5. **Migration Strategy**
   - **Keep existing AI Guard** during migration
   - Build MCP server alongside
   - Add MCP client to app
   - Gradual migration per feature
   - Remove old guard once stable

**Timeline:** 3-4 days
**Risk:** High (critical trading functionality, requires careful testing)

---

### Phase 3: Databento MCP Wrapper (LOW PRIORITY)

**Goal:** Optional MCP wrapper if needed for multi-tool access

**Recommendation:** **Defer until needed**
- Current pipeline works well
- Databento SDK is well-maintained
- No immediate benefit
- Add only if multiple tools need access

---

## Implementation Priorities

### Must Do Now (Week 1)
1. ✅ Copy mcp-builder skill to project (DONE)
2. ✅ Document current integrations (DONE)
3. ✅ Create integration plan (THIS DOCUMENT)

### Should Do Soon (Week 2-3)
4. **ProjectX MCP Server** (Phase 1)
   - Highest value add
   - Enables better tooling ecosystem
   - Standardizes data access

### Can Do Later (Month 2)
5. **AI Guard MCP Formalization** (Phase 2)
   - Lower priority (current system works)
   - High risk (critical functionality)
   - Do when time permits

### Optional (Backlog)
6. **Databento MCP Wrapper** (Phase 3)
   - Only if multi-tool access needed
   - Current pipeline sufficient

---

## MCP Development Workflow

When creating MCP servers, follow mcp-builder skill process:

### Phase 1: Deep Research
- Load MCP specification: `https://modelcontextprotocol.io/sitemap.xml`
- Load SDK docs: TypeScript (recommended) or Python
- Load `skills/mcp-builder/reference/mcp_best_practices.md`
- Study API documentation thoroughly

### Phase 2: Implementation
- Choose TypeScript + Streamable HTTP for remote servers
- Use Zod for schemas (TypeScript) or Pydantic (Python)
- Implement tools with proper error handling
- Add output schemas where possible
- Use proper hints (readOnlyHint, destructiveHint, etc.)

### Phase 3: Review and Test
- Build and verify compilation
- Test with MCP Inspector: `npx @modelcontextprotocol/inspector`
- Run full quality checklist
- Test all error cases

### Phase 4: Create Evaluations
- Load `skills/mcp-builder/reference/evaluation.md`
- Create 10 complex, realistic evaluation questions
- Verify answers are stable and verifiable
- Output as XML format

---

## Benefits of MCP Integration

### For ProjectX
- ✅ Standardized access across tools
- ✅ Better error handling
- ✅ Pagination built-in
- ✅ Tool discoverability
- ✅ Easier testing

### For AI Assistant
- ✅ Standard LLM protocol
- ✅ Reusable across UIs
- ✅ Better separation of concerns
- ✅ Easier to add new AI features
- ✅ Maintains AI Guard security

### General
- ✅ Follows industry best practices
- ✅ Easier onboarding for developers
- ✅ Better documentation
- ✅ Standard evaluation framework
- ✅ Future-proof architecture

---

## Next Steps

1. **Review this plan** with team/stakeholders
2. **Approve Phase 1** (ProjectX MCP Server)
3. **Create ProjectX MCP Server** following mcp-builder skill
4. **Test and integrate** into existing pipeline
5. **Document** usage and migration guide
6. **Evaluate** whether to proceed with Phase 2

---

## References

- MCP Builder Skill: `skills/mcp-builder/SKILL.md`
- MCP Best Practices: `skills/mcp-builder/reference/mcp_best_practices.md`
- TypeScript Guide: `skills/mcp-builder/reference/node_mcp_server.md`
- Python Guide: `skills/mcp-builder/reference/python_mcp_server.md`
- Evaluation Guide: `skills/mcp-builder/reference/evaluation.md`
- MCP Specification: https://modelcontextprotocol.io/
