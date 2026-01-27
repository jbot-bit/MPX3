---
name: brainstorming
description: Structured feature design process. Use when planning new features, redesigning components, or exploring architectural changes. Prevents bloat through YAGNI principles and incremental validation.
allowed-tools: Read, Grep, Glob, AskUserQuestion
context: fork
agent: general-purpose
---

# Brainstorming Skill

**Purpose:** Turn ideas into fully-formed designs through collaborative dialogue.

Use this skill when:
- Planning new features
- Redesigning existing components
- Exploring architectural changes
- Preventing feature bloat

---

## Process: 3 Phases

### Phase 1: Understanding the Idea

1. **Examine current state**
   - Read relevant code
   - Check existing patterns
   - Understand constraints

2. **Ask questions sequentially**
   - ONE question per message
   - Prefer multiple choice when possible
   - Open-ended questions are fine too
   - Don't overwhelm with many questions at once

3. **Apply YAGNI ruthlessly**
   - Challenge every feature: "Is this NEEDED or nice-to-have?"
   - Remove unnecessary complexity
   - Focus on core value

**Example Questions:**
```
Q: Which problem does this solve?
   A) User can't see valid setups quickly
   B) Data is outdated
   C) Too many clicks to update
   D) Something else (specify)

Q: How often will you use this feature?
   A) Every day (critical)
   B) Weekly (useful)
   C) Monthly (nice-to-have)
   D) Rarely (probably YAGNI)
```

---

### Phase 2: Exploring Approaches

Present 2-3 different approaches with trade-offs:

1. **Lead with recommended option**
   - Why it's best for this situation
   - Clear reasoning

2. **Show alternatives**
   - Different approaches
   - When they'd be better

3. **Present trade-offs**
   - Pros and cons of each
   - Implementation complexity
   - Maintenance burden

**Example:**
```
APPROACH 1 (Recommended): Single-screen layout
✅ Faster to use (one glance)
✅ Less clicking
✅ Mobile-friendly
❌ Less organized if many features

APPROACH 2: Tabbed interface
✅ More organized
✅ Can add features without crowding
❌ More clicks
❌ Harder to see everything at once

Recommendation: Approach 1 because you value speed over organization.
```

---

### Phase 3: Presenting the Design

Break explanation into 200-300 word sections:

1. **Architecture**
   - High-level structure
   - Component relationships

2. **Components**
   - What each piece does
   - Why it's needed

3. **Data Flow**
   - How data moves through system
   - Inputs and outputs

4. **Error Handling**
   - What can go wrong
   - How to handle failures

5. **Testing Strategy**
   - What to test
   - How to verify it works

**After each section:** Ask for validation before continuing.

---

## Key Principles

### 1. One Question at a Time
Don't ask: "What features do you want, when will you use it, and how should it look?"

Instead:
```
Q1: What's the main problem you're solving?
[Wait for answer]

Q2: How often will you use this?
[Wait for answer]

Q3: Should this be on main screen or separate tab?
[Wait for answer]
```

### 2. YAGNI (You Aren't Gonna Need It)
Challenge every feature:
- "Will you use this EVERY DAY?"
- "Can you live without it?"
- "Does it solve a real problem or is it 'nice to have'?"

If answer is "nice to have" → **CUT IT.**

### 3. Explore Alternatives
Never commit to first solution. Always show:
- Option A (recommended)
- Option B (alternative)
- Why you recommend A

### 4. Incremental Validation
Present design in chunks. After each section:
- "Does this make sense?"
- "Should I continue?"
- "Any concerns?"

Don't dump entire design at once.

### 5. Be Flexible
If user is confused:
- Stop
- Clarify
- Ask simpler questions
- Break down further

---

## Post-Design Steps

After design is validated:

1. **Document the design**
   ```
   docs/plans/YYYY-MM-DD-feature-name.md
   ```

2. **Commit to version control**
   ```bash
   git add docs/plans/
   git commit -m "Design: Feature name"
   ```

3. **Optionally: Start implementation**
   - Use git worktrees for clean isolation
   - Create detailed implementation plan
   - Break into small tasks

---

## Example Session

**User:** "I want to add a performance dashboard"

**Assistant:**
```
Let me understand this first.

Q: What's the PRIMARY problem you're solving?
   A) Can't see edge performance easily
   B) Need to track degradation over time
   C) Want historical performance charts
   D) Something else
```

**User:** "A - can't see edge performance easily"

**Assistant:**
```
Got it. Next question:

Q: How often will you check this dashboard?
   A) Every day before trading
   B) Weekly health check
   C) Monthly review
   D) Only when something seems wrong
```

**User:** "A - every day before trading"

**Assistant:**
```
Perfect. Since you'll use it daily, this is critical.

Q: Where should this live?
   A) Main screen (see it immediately)
   B) Separate tab (organized but extra click)
   C) Popup/modal (overlay on demand)
```

[Continue until fully understood, then present approaches]

---

## Anti-Patterns (Don't Do This)

❌ **Asking too many questions at once**
```
What features do you want, how should it look, where should it go,
and when will you use it?
```

❌ **Not challenging features**
```
User: "Add charts, animations, export to PDF, email reports"
Assistant: "Sure, I'll add all of that"
```
Should challenge: "Which of these will you use DAILY?"

❌ **Dumping entire design**
```
[3000 word design document with no checkpoints]
```

❌ **Not exploring alternatives**
```
"Here's THE solution" (no options presented)
```

---

## Success Criteria

✅ User clearly understands the problem being solved
✅ Feature is NEEDED (not nice-to-have)
✅ Multiple approaches were considered
✅ Design is validated incrementally
✅ Implementation is broken into small tasks
✅ Documentation is created

---

## Trading App Specific Guidelines

**Always ask:**
- "Will you check this EVERY DAY before trading?"
- "Does this help you make better trading decisions?"
- "Can you trade successfully without this?"

**If answer is NO to any → YAGNI it.**

**Keep lean:**
- Market Scanner = critical (you need this daily)
- Data update = critical (must have current data)
- AI Assistant = useful (but not critical)
- Edge Tracker = useful (but not critical)
- Bells and whistles = bloat (cut them)

**Golden rule:** If you wouldn't use it on your phone at 8:55am before the 9am ORB, you don't need it.
