# SKILL: reflect (session learning)

## Purpose
Capture useful learnings from the current session and update relevant skill files with flexible defaults.

## What to extract (signals)
- **Corrections**: user changed code, naming, architecture, UI, tests, or phrasing.
- **Approvals**: user said "yes / that's right / do that / ship it".
- **Repeated friction**: same mistake or preference showed up more than once.
- **Context-specific wins**: something worked well *in this project*.

## How to write memories (avoid boxing)
Write updates as:
- **Default preference**: "Default to X…"
- **Preference strength**: "Prefer / Default / Usually / Sometimes / Avoid"
- **Exception clause**: "Unless Y…"
- **Scope**: "In this repo / In this module / In UI code / In research scripts"

Never write memories as universal absolutes unless explicitly required.

## Confidence levels
- **High**: explicitly stated rule with clear scope and exception.
- **Medium**: repeated preference or validated pattern.
- **Low**: tentative observation—log as "Consider" not "Do".

## Auto-apply mode (Option 3: High confidence only)

**Confidence-based routing:**
- **High confidence** → AUTO-APPLY to target skill file + log to _memory_log.md
- **Medium confidence** → STAGE in _memory_log.md (user reviews)
- **Low confidence** → STAGE in _pending_review.md (user reviews)

**High confidence criteria (ALL must be true):**
1. User explicitly stated the rule/preference (not inferred)
2. Rule is scoped (not universal absolute)
3. Rule has exception clause OR clear context boundary
4. Not a style preference (only architecture/safety/canonical rules)
5. No risk of boxing user into rigid patterns

**Auto-apply safety limits:**
- Max 3 auto-applied updates per session
- Max 5 lines added per skill file
- Never delete existing rules (append/refine only)
- Never auto-apply to CLAUDE.md (too critical)

## Output format
1) **Detected signals** (quote short snippets)
2) **Confidence assessment** (High/Medium/Low + rationale)
3) **Auto-applied updates** (if High confidence)
4) **Staged updates** (if Medium/Low confidence)
5) **Risk check**: could this overfit or box the user in?
6) **Summary**: What was learned, what needs review

## Guardrails
- Do not add rigid rules about style unless the user explicitly wants it.
- Prefer "small, reversible" changes (1–5 bullets).
- If uncertain, log to a "review later" section instead of enforcing.
- Never overwrite existing rules; append or refine with scope/exception.

## Where to write updates
**DEFAULT: Write to `skills/_memory_log.md` (staging area)**

This prevents contamination of existing skills. User reviews and approves before moving to:
- `skills/code-guardian/SKILL.md` (if about code safety)
- `skills/database-design/SKILL.md` (if about database patterns)
- `skills/project_conventions.md` (if about repo-specific conventions)
- Or create `skills/_pending_review.md` for low-confidence items.

## Workflow
1. User says "run /reflect" or "reflect on this session"
2. Claude scans conversation for signals
3. Claude writes proposed learnings to `skills/_memory_log.md`
4. User reviews staged updates
5. User approves (Claude moves to real skills) OR edits/rejects

## Suggested commit message
`skills: reflect session learnings (scoped defaults)`
