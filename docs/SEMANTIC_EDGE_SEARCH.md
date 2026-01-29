# Semantic Edge Search System

**Problem:** Current edge discovery requires manual filter configuration. Can't search by characteristics like "large and narrow" or "explosive breakout."

**Solution:** Natural language edge search that translates characteristics to filter ranges.

---

## Edge Archetypes (Pre-Defined Patterns)

### 1. Range Characteristics

**Large Range:**
- ORB size: > 0.10 ATR (top 25%)
- Pre-travel: Any
- Use case: Momentum continuations, breakout trades

**Narrow Range:**
- ORB size: < 0.05 ATR (bottom 25%)
- Pre-travel: Any
- Use case: Compression breakouts, tight coils

**Medium Range:**
- ORB size: 0.05 - 0.10 ATR
- Pre-travel: Any
- Use case: Standard breakouts

### 2. Session Activity

**Explosive Session:**
- Pre-travel: > 2.0 ATR (active before ORB)
- ORB size: Any
- Use case: Momentum trades, continuation patterns

**Quiet Session:**
- Pre-travel: < 0.5 ATR (dead before ORB)
- ORB size: Any
- Use case: Breakout from rest, fresh moves

**Compressed Session:**
- Pre-travel: < 0.5 ATR AND ORB size < 0.05 ATR
- Use case: Coiled spring, tight consolidation

### 3. Combined Patterns

**Large and Narrow:**
- ORB size: > 0.10 ATR (large breakout)
- Pre-travel: < 0.5 ATR (narrow/quiet before)
- Interpretation: Explosive breakout from rest

**Tight Consolidation:**
- ORB size: < 0.05 ATR
- Pre-travel: < 0.5 ATR
- Asia type: RANGE or QUIET
- Interpretation: Compressed, waiting for move

**Momentum Continuation:**
- ORB size: > 0.08 ATR
- Pre-travel: > 1.5 ATR
- Asia type: TRENDING
- Interpretation: Strong move continues

**False Breakout Fade:**
- ORB size: > 0.10 ATR (large initial move)
- Pre-travel: > 2.0 ATR (already traveled far)
- Outcome: LOSS (fades back)
- Interpretation: Exhaustion, late entry

---

## Search Interface

### Option 1: Dropdown Archetypes (Simplest)

```python
# In Research Lab tab
archetype = st.selectbox(
    "Search by Pattern:",
    [
        "Custom (manual filters)",
        "Large and Narrow (explosive from rest)",
        "Tight Consolidation (compressed coil)",
        "Momentum Continuation (trending)",
        "Quiet Session (low pre-travel)",
        "Large Range (big ORBs)",
        "Narrow Range (small ORBs)"
    ]
)

if archetype != "Custom (manual filters)":
    # Auto-set filters based on archetype
    filters = ARCHETYPE_FILTERS[archetype]
    st.info(f"Auto-set filters: {filters}")
    # Run discovery with those filters
```

### Option 2: Natural Language Search (Advanced)

```python
# In Research Lab tab
search_query = st.text_input(
    "Describe the edge you're looking for:",
    placeholder="e.g., 'large breakout from quiet session' or 'tight range before trending'"
)

if search_query:
    # Parse query using simple keyword matching
    filters = parse_search_query(search_query)
    st.success(f"Interpreted as: {filters}")
    # Run discovery
```

### Option 3: Slider-Based Explorer (Visual)

```python
# In Research Lab tab
st.subheader("Edge Explorer")

col1, col2 = st.columns(2)

with col1:
    orb_size_pref = st.select_slider(
        "ORB Size Preference:",
        options=["Narrow (< 0.05)", "Medium (0.05-0.10)", "Large (> 0.10)", "Any"]
    )

with col2:
    pre_travel_pref = st.select_slider(
        "Pre-Travel Preference:",
        options=["Quiet (< 0.5)", "Medium (0.5-1.5)", "Active (> 1.5)", "Any"]
    )

# Translate to actual filter ranges
filters = translate_preferences(orb_size_pref, pre_travel_pref)
```

---

## Implementation (Minimal Viable)

### 1. Define Archetypes Dictionary

```python
# trading_app/edge_archetypes.py

ARCHETYPE_FILTERS = {
    "Large and Narrow": {
        "orb_size_min": 0.10,
        "orb_size_max": None,
        "pre_orb_travel_max": 0.5,
        "description": "Explosive breakout from quiet session"
    },
    "Tight Consolidation": {
        "orb_size_min": None,
        "orb_size_max": 0.05,
        "pre_orb_travel_max": 0.5,
        "description": "Compressed range, coiled spring"
    },
    "Momentum Continuation": {
        "orb_size_min": 0.08,
        "orb_size_max": None,
        "pre_orb_travel_min": 1.5,
        "description": "Strong trend continues through ORB"
    },
    "Quiet Session": {
        "pre_orb_travel_max": 0.5,
        "description": "Low activity before ORB"
    },
    "Large Range": {
        "orb_size_min": 0.10,
        "description": "Large ORBs (top 25%)"
    },
    "Narrow Range": {
        "orb_size_max": 0.05,
        "description": "Tight ORBs (bottom 25%)"
    }
}

def get_archetype_filters(archetype_name: str) -> dict:
    """Get filter configuration for named archetype"""
    return ARCHETYPE_FILTERS.get(archetype_name, {})
```

### 2. Add to Research Lab Tab

```python
# In app_canonical.py Research Lab section

from trading_app.edge_archetypes import ARCHETYPE_FILTERS, get_archetype_filters

st.subheader("Edge Discovery")

# Search mode
search_mode = st.radio(
    "Discovery Mode:",
    ["Archetype Search (recommended)", "Manual Filters"],
    horizontal=True
)

if search_mode == "Archetype Search (recommended)":
    archetype = st.selectbox(
        "Select Pattern:",
        ["Custom"] + list(ARCHETYPE_FILTERS.keys())
    )

    if archetype != "Custom":
        filters = get_archetype_filters(archetype)
        description = filters.pop('description', '')

        st.info(f"🎯 **{archetype}**: {description}")

        # Show what filters will be used
        with st.expander("Filter Details"):
            for key, value in filters.items():
                if value is not None:
                    st.write(f"- {key}: {value}")

        # Button to run discovery with these filters
        if st.button("Find Edges with This Pattern"):
            # Run discovery with archetype filters
            # ... (integrate with existing edge_discovery_live.py)
            pass
    else:
        # Show manual filter inputs (existing UI)
        pass

else:
    # Manual mode (existing filter inputs)
    pass
```

---

## Keyword Parsing (Future Enhancement)

```python
# trading_app/search_parser.py

def parse_search_query(query: str) -> dict:
    """
    Parse natural language search to filter config

    Examples:
    - "large and narrow" → orb_size > 0.10, pre_travel < 0.5
    - "tight consolidation" → orb_size < 0.05, pre_travel < 0.5
    - "explosive from quiet" → orb_size > 0.08, pre_travel < 0.5
    """
    query_lower = query.lower()
    filters = {}

    # Size keywords
    if "large" in query_lower or "big" in query_lower or "explosive" in query_lower:
        filters['orb_size_min'] = 0.10
    elif "narrow" in query_lower or "tight" in query_lower or "small" in query_lower:
        filters['orb_size_max'] = 0.05

    # Pre-travel keywords
    if "quiet" in query_lower or "rest" in query_lower or "compressed" in query_lower:
        filters['pre_orb_travel_max'] = 0.5
    elif "active" in query_lower or "trending" in query_lower or "momentum" in query_lower:
        filters['pre_orb_travel_min'] = 1.5

    # Session type keywords
    if "range" in query_lower and "session" in query_lower:
        filters['asia_types'] = ['RANGE']
    elif "trending" in query_lower and "session" in query_lower:
        filters['asia_types'] = ['TRENDING']

    return filters
```

---

## Benefits

1. **ADHD-Friendly:** No fiddling with numeric ranges
2. **Faster Discovery:** Click archetype → run → see results
3. **Learnable Patterns:** Named archetypes teach you what works
4. **Still Flexible:** Can drop to manual mode for fine-tuning

---

## Next Step

Add archetype dropdown to Research Lab tab in app_canonical.py (5-minute implementation).

This solves "I want to find X without configuring every filter" problem.
