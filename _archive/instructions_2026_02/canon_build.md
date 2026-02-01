# Canonical AI Trading System Spec (Builder-Grade) — v0.1

## 0) Purpose
- Discover, validate, and deploy statistically real trading edges.
- Prevent: overfitting, silent drift, AI hallucinated authority, accidental execution risk.
- Support a single operator (you). AI is constrained tooling.

## 1) Non‑Negotiable Principles
- Fail‑closed always.
- Evidence > intuition.
- AI cannot write to production state.
- No execution without validation lineage.
- One canonical source per concept.
- Research freedom ≠ production permission.

## 2) 3‑Zone Architecture (Hard Separation)
### Zone A — RESEARCH (unsafe by default)
- Goal: generate candidate edges.
- AI: active but constrained (read‑only over market data; write only to research metadata).
- Cannot: trade, modify production logic, modify validated_setups.

### Zone B — VALIDATION (deterministic gate)
- Goal: prove or kill candidates.
- AI: assistive only.
- Outputs: reproducible, logged, hashable.

### Zone C — PRODUCTION (locked execution)
- Goal: run approved edges only.
- AI: no logic changes; read‑only explanation allowed.
- Any change = new edge_id.

## 3) Edge Memory System (No Spam, No Repeat Work)
### 3.1 Canonical Edge Registry (single source of truth)
**Table:** edge_registry (research schema)
Mandatory fields:
- edge_id (stable hash of definition)
- instrument, session, ORB_time, direction
- trigger_definition
- filters_applied (normalized JSON)
- test_window
- status: NEVER_TESTED | TESTED_FAILED | VALIDATED | PROMOTED | RETIRED
- failure_reason_code, failure_reason_text
- pass_reason_text
- last_tested_at, test_count
- similarity_fingerprint (vector hash)
Rules:
- Every edge attempt is logged once; no deletes; only state transitions.

## 4) Semantic Memory (How AI “Remembers”)
- Not chat memory.
- Programmatic semantic index over edge_registry.

### 4.1 Vector Index Inputs
- trigger_definition
- filters_applied
- failure_reason_text
- pass_reason_text

### 4.2 Silent Pre‑Check Flow
1) You propose an edge.
2) AI runs similarity search.
3) If match: returns prior outcome + why.
4) If no match: allows test + registers new edge.

## 5) AI Role (Programmed, Not Vibes)
AI MAY:
- Propose variants of known edges.
- Suggest adjacent ORB times and asset transfers.
- Explain failure patterns and “why this passed”.

AI MAY NOT:
- Approve/promote edges.
- Modify validation criteria.
- Override statistical rejection.
- Touch execution logic.

## 6) Cross‑ORB / Cross‑Asset Testing
### 6.1 Edge Abstraction
Each edge stored as: Structure + Context + Trigger.

### 6.2 Transfer Tests
- Validated edge can spawn child edges for other ORBs/assets.
- Parent/child lineage preserved.
- Child failure does not contaminate parent.

## 7) Validation Gates (Non‑Negotiable)
An edge passes only if it:
- Beats random baseline.
- Survives cost/slippage stress.
- Survives walk‑forward.
- Survives regime splits.
- Does not overlap existing production edges.
All failures stored with reason codes.

## 8) Production Promotion (Locked)
Promotion requires:
- Full lineage (inputs → tests → artifacts).
- Deterministic hash.
- Explicit operator approval.
Once promoted: read‑only.

---

# Implementation Plan (Agents / Skills / Triggers)

## A) Required Modules (Dependencies)
- **DuckDB**: canonical tables + lineage.
- **Vector index** (choose one):
  - local: FAISS
  - managed: Pinecone / Weaviate (optional)
- **Embedding model**: local or API-backed (your choice).
- **Streamlit**: Research Lab UI.

## B) “Skills” (Tooling Contracts)
Create these as internal SKILL.md files (one per capability):
1) **edge-registry-skill**: create/read/update edge_registry, status transitions.
2) **edge-similarity-skill**: embed + query, return top-k matches with reasons.
3) **validation-runner-skill**: deterministic validation pipeline with artifacts.
4) **promotion-guard-skill**: ensure gates + lineage before writing to production.
5) **drift-monitor-skill**: detect feature/schema/logic drift; fail-closed.

## C) Agents (Responsibilities)
1) **Research Librarian Agent**
- Only reads: DB + edge_registry + results.
- Answers: “Have we tried this?” “What failed?” “What passed and why?”

2) **Candidate Generator Agent**
- Proposes new candidates using constraints.
- Must call similarity pre-check first.

3) **Validation Gatekeeper Agent**
- Runs deterministic tests.
- Outputs pass/fail + reason codes.
- Cannot promote.

4) **Production Sentinel Agent**
- Monitors: promoted edges only.
- Alerts on drift/perf decay.
- Cannot modify strategy logic.

## D) Triggers (When Agents Run)
- On “New candidate draft”: similarity pre-check trigger.
- On “Run validation”: validation pipeline trigger.
- On “Request promote”: promotion guard trigger.
- On “Daily rebuild / backfill”: drift + schema sync trigger.
- On “Perf drop threshold”: retirement review trigger.

## E) Addons (Optional but Useful)
- Evidence Pack exporter (one-click): candidate → zip of artifacts.
- “Why it failed” dashboard: aggregates failure_reason_code counts.
- “Transfer map” view: parent→child edge graph.

---

# Next Build Steps (Pick Order)
1) Define edge_id hash contract + normalized JSON schema.
2) Implement edge_registry table + CRUD.
3) Implement embeddings + similarity search.
4) Wire similarity pre-check into Research Lab UI.
5) Implement deterministic validation runner + artifact storage.
6) Implement promotion guard + production write lock.

---

# Master TODO (App Skeleton → Core → AI)

## 🔒 Meta-Rules (AUTO-ENFORCED)
- This spec is **append-only**.
- No section is deleted or rewritten unless explicitly requested.
- Build proceeds via **small build tickets**, not the full spec.
- Only one ticket is active at a time.

---

## Phase 0 — Decisions (LOCK)
- [x] Lock tech choice: Python + Streamlit (desktop-first).
- [x] Lock DB choice: DuckDB (local).
- [x] Lock semantic index choice: local (FAISS or equivalent) (later).

## Phase 1 — App Skeleton (UI + Navigation)
- [ ] Create Streamlit shell with pages: Research / Validation / Production / Memory / Settings.
- [ ] Add global Zone banner + active instrument + DB status indicator.
- [ ] Add unified logging panel (run_id, action, status).

## Phase 2 — Core Workflow (No AI yet)
- [ ] Candidate draft form → writes to edge_registry.
- [ ] Candidate list + filters + status transitions.
- [ ] Validation runner **stub** (no logic yet) → stores placeholder artifact.
- [ ] Promotion gate **stub** (hard write-block by default).

## Phase 3 — Edge Memory (Exact, No AI)
- [ ] edge_id hash contract (canonical).
- [ ] Exact-match pre-check (hash-based) before any run.
- [ ] Failure reason taxonomy.

## Phase 4 — Discovery Engine (Deterministic)
- [ ] Search-space generators (ORB, session, asset).
- [ ] Deterministic enumeration (no ML).
- [ ] Fast-screen metrics (cheap reject).
- [ ] Log every attempt (append-only).

## Phase 5 — Validation + Controls
- [ ] Full validation runner.
- [ ] Mandatory negative/random control per validation.
- [ ] Store control results alongside edge results.

## Phase 6 — Experiment Lineage (High ROI)
- [ ] experiment_run object.
- [ ] Generator version + seed tracking.
- [ ] Data version hash.
- [ ] Enforce: no status change without experiment_run.

## Phase 7 — Semantic Memory (AI Meta-Work)
- [ ] Embeddings for edge_registry.
- [ ] Similarity search UI.
- [ ] Silent semantic pre-check.

## Phase 8 — Guardrails (Fail-Closed)
- [ ] Zone enforcement (single switch).
- [ ] Production write lock (promotion-only path).
- [ ] Evidence required for promotion.

## Phase 9 — Polish + Future Mobile
- [ ] Evidence Pack export.
- [ ] Drift/perf monitor.
- [ ] Later: mobile/read-only viewer.

---

# BUILD_TICKETS (Execution Plan — THIS is what we build from)

## T1 — Streamlit App Shell
**Goal:** App opens, navigation works.
**Done when:**
- App starts
- Pages exist (empty)
- Zone banner visible

## T2 — DB Connection + Health
**Goal:** App knows DB state.
**Done when:**
- DuckDB connects
- Health indicator shows OK / FAIL

## T3 — Edge Registry (Create + List)
**Goal:** First real object.
**Done when:**
- Create candidate
- See it in list

## T4 — Validation Stub
**Goal:** End-to-end flow without logic.
**Done when:**
- Click validate
- Placeholder artifact saved

## T5 — Promotion Lock Stub
**Goal:** Fail-closed safety.
**Done when:**
- Promotion blocked by default

## T6 — experiment_run Logging
**Goal:** Reproducibility backbone.
**Done when:**
- Every action creates experiment_run

## T7 — Control Run
**Goal:** Prevent false edges.
**Done when:**
- Validation auto-runs control

## T8 — Exact Duplicate Block
**Goal:** Stop wasted work.
**Done when:**
- Exact hash blocks run

## T9 — Semantic Search (Later)
**Goal:** High ROI AI assist.
**Done when:**
- Similar edges surfaced

## T10 — Drift Monitor Stub
**Goal:** Early warning.
**Done when:**
- Drift check runs + logs



---

# AMENDMENT v0.3 — Build Tickets + Context Discipline (Stop the 10,000-word problem)

## A) Build Method (Walking Skeleton)
Rule: Build via **small tickets** (1 feature per ticket), each producing a working increment.

Ticket template:
- Objective (1 paragraph)
- Acceptance criteria (bullets)
- Files touched (list)
- Tests / checks (list)
- “Done means” (bullets)

## B) LLM Context Discipline (Non-Negotiable)
Rule: Never feed the entire spec to an LLM.
Instead, each LLM task receives:
- The single ticket text
- Folder tree (relevant subset)
- Only the specific files it must edit (1–3 files)
- No unrelated history

## C) New Canonical Artifact: `docs/BUILD_TICKETS.md`
Create a build roadmap as a short list of tickets.

### Initial Ticket Set (v1)
**T1 — Streamlit shell + navigation**
- Pages: Research / Validation / Production / Memory / Settings
- Global header: Zone badge + DB status + instrument selector

**T2 — DB connection + health widget**
- DuckDB path config
- Read-only check + “connected/missing”

**T3 — edge_registry minimal CRUD (Create/List)**
- Create candidate draft
- List/filter candidates
- Status transitions (minimal)

**T4 — experiment_run logging (first-class)**
- Create experiment_run record for each major action
- Link to edge_id

**T5 — Validation runner stub + artifacts folder**
- Run deterministic placeholder validation
- Persist metrics + artifact references

**T6 — Mandatory control run (baseline)**
- At least one control per validation
- Store side-by-side results
- Block VALIDATED if control is not beaten

**T7 — Promotion gate + production write lock**
- Only Promotion path can write validated_setups
- Evidence/lineage required

**T8 — Exact-match “Do Not Re-Test” enforcement**
- Hash match blocks run
- Requires explicit override to re-test

**T9 — Semantic similarity pre-check (embeddings later ok)**
- UI: show “similar prior edges” before running
- Store similarity_fingerprint placeholder if embeddings not ready

**T10 — Drift/performance monitor stub**
- Schema sync check
- Perf decay alert placeholder

## D) Phase Numbering Note (No rewrite)
Current Master TODO has duplicated phase labels.
Rule: Treat the phase list as conceptual ordering; tickets are the execution plan.
(We can renumber phases later as a cosmetic-only change.)

