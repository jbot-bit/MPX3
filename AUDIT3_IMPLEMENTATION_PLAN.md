# AUDIT3 IMPLEMENTATION PLAN - Deterministic Priority Engine + ε-Exploration

**Date**: 2026-01-29
**Status**: 📋 PLANNING
**Estimated Time**: 2-3 hours
**Complexity**: HIGH (new feature, not just ADD-ON)

---

## EXECUTIVE SUMMARY

**Goal**: Add deterministic search engine extension with priority-based candidate selection and ε-exploration (exploration budget).

**Key Principle**: AI cannot judge profitability or make decisions. Only deterministic rules-based classification.

**Core Components**:
1. **search_knowledge** table - Versioned results with result_class
2. **Priority Engine** - Scores axes deterministically from past results
3. **ε-Exploration** - 15% of each chunk tests untested combinations
4. **Result Classification** - GOOD/NEUTRAL/BAD from fixed thresholds
5. **Versioning** - ruleset_version, priority_version, param_hash_version
6. **Provenance** - git commit, timestamps, db path tracking

---

## CURRENT STATE (Before audit3)

### Existing Infrastructure (Good - We Build On This)
✅ **search_runs** table - Tracks search executions
✅ **search_candidates** table - Stores promising candidates
✅ **search_memory** table - Deduplication (param_hash → tested/not tested)
✅ **auto_search_engine.py** - Deterministic scoring, chunked execution
✅ **compute_param_hash()** - SHA256 hashing (first 16 chars)

### What's Missing (What We Need to Add)
❌ **search_knowledge** table - No versioned result storage
❌ **Priority engine** - Currently random/exhaustive, not priority-based
❌ **ε-Exploration** - No explicit exploration budget
❌ **Result classification** - No GOOD/NEUTRAL/BAD logic
❌ **Versioning** - No ruleset_version, priority_version tracking
❌ **Provenance** - No git commit tracking in artifacts

---

## DESIGN DECISIONS

### 1. Canonical Param Serialization (Hash v2)

**Current (v1)**:
```python
# compute_param_hash() - lines 81-107 in auto_search_engine.py
sorted_params = {
    'instrument': params.get('instrument', ''),
    'setup_family': params.get('setup_family', ''),
    'orb_time': params.get('orb_time', ''),
    'rr_target': params.get('rr_target', 0.0),
    'filters': params.get('filters', {})
}
json_str = json.dumps(sorted_params, sort_keys=True)
hash_obj = hashlib.sha256(json_str.encode('utf-8'))
return hash_obj.hexdigest()[:16]
```

**Problem**: Uses Python dict order (relies on sort_keys=True, but filters nested)

**Solution (v2)**: Explicit field ordering
```python
def compute_param_hash_v2(params: Dict) -> str:
    """
    Canonical param serialization for deterministic hashing

    Version: 2.0 (audit3 - explicit field order)
    Algorithm: SHA256
    Encoding: UTF-8

    Field order (fixed):
    1. instrument (str)
    2. setup_family (str)
    3. orb_time (str)
    4. rr_target (float, 2 decimals)
    5. filters (sorted dict, recursive)
    """
    # Explicit order (no dict assumptions)
    canonical = [
        ('instrument', params.get('instrument', '')),
        ('setup_family', params.get('setup_family', '')),
        ('orb_time', params.get('orb_time', '')),
        ('rr_target', round(float(params.get('rr_target', 0.0)), 2)),
        ('filters', _sort_dict_recursive(params.get('filters', {})))
    ]

    json_str = json.dumps(canonical, ensure_ascii=True)
    hash_obj = hashlib.sha256(json_str.encode('utf-8'))
    return hash_obj.hexdigest()[:16]
```

**Versioning**: Store `param_hash_version = "2.0"` in search_knowledge

---

### 2. Result Classification (Rules-Based)

**GOOD Threshold**:
- expected_r >= 0.25R (strong edge)
- sample_size >= 50 (statistical confidence)
- robust_flags = 0 (passes all gates)

**NEUTRAL Threshold**:
- expected_r >= 0.15R (viable edge)
- sample_size >= 30 (minimum sample)
- robust_flags <= 1 (minor concern)

**BAD Threshold**:
- expected_r < 0.15R (weak/no edge)
- OR sample_size < 30 (insufficient data)
- OR robust_flags > 1 (multiple concerns)

**Ruleset Version**: `"1.0"` (audit3 initial)

**Code**:
```python
def classify_result(
    expectancy_r: float,
    sample_size: int,
    robust_flags: int
) -> str:
    """
    Deterministic result classification

    Ruleset version: 1.0 (audit3)

    Returns: "GOOD" | "NEUTRAL" | "BAD"
    """
    if expectancy_r >= 0.25 and sample_size >= 50 and robust_flags == 0:
        return "GOOD"
    elif expectancy_r >= 0.15 and sample_size >= 30 and robust_flags <= 1:
        return "NEUTRAL"
    else:
        return "BAD"
```

---

### 3. Priority Scoring (Deterministic)

**Axis Scores** (0.0 to 1.0):

**ORB Time Priority**:
```python
# Past performance for this ORB time
good_count = COUNT(result_class='GOOD' WHERE orb_time=X)
neutral_count = COUNT(result_class='NEUTRAL' WHERE orb_time=X)
total_count = COUNT(*) WHERE orb_time=X

if total_count == 0:
    priority = 0.5  # Neutral (untested)
else:
    priority = (good_count * 1.0 + neutral_count * 0.5) / total_count
```

**RR Target Priority**:
```python
# Similar logic for RR targets
good_count = COUNT(result_class='GOOD' WHERE rr_target=X)
priority = (good_count * 1.0 + neutral_count * 0.5) / total_count
```

**Filter Type Priority**:
```python
# Filter families (SIZE, TRAVEL, SESSION_TYPE, etc.)
good_count = COUNT(result_class='GOOD' WHERE filter_type IN filters)
priority = (good_count * 1.0 + neutral_count * 0.5) / total_count
```

**Combined Priority**:
```python
priority = (orb_priority * 0.4 + rr_priority * 0.3 + filter_priority * 0.3)
```

**Weights**: ORB (40%), RR (30%), Filters (30%)

**Priority Version**: `"1.0"` (audit3 initial)

---

### 4. ε-Exploration (15% Budget)

**Each Chunk**:
- Total tests: N
- Exploitation (85%): Top N * 0.85 by priority score
- Exploration (15%): Random N * 0.15 from untested pool

**Exploration Selection** (Deterministic):
```python
# Get untested pool
untested = get_untested_combinations()

# Sort by param_hash (deterministic order)
untested_sorted = sorted(untested, key=lambda x: x['param_hash'])

# Take first ε * N (round up)
explore_count = math.ceil(N * epsilon)
explore_candidates = untested_sorted[:explore_count]
```

**Why hash-sorted**: Deterministic, reproducible, no randomness

**ε Value**: 0.15 (15%) - configurable

---

### 5. search_knowledge Schema

```sql
CREATE TABLE search_knowledge (
    knowledge_id INTEGER PRIMARY KEY,
    param_hash VARCHAR NOT NULL,
    param_hash_version VARCHAR NOT NULL,  -- "2.0"

    -- Parameters (denormalized for queries)
    instrument VARCHAR NOT NULL,
    setup_family VARCHAR NOT NULL,
    orb_time VARCHAR NOT NULL,
    rr_target DOUBLE NOT NULL,
    filters_json JSON,

    -- Results (from validation or backtest)
    result_class VARCHAR NOT NULL,  -- "GOOD" | "NEUTRAL" | "BAD"
    expectancy_r DOUBLE,
    sample_size INTEGER,
    robust_flags INTEGER,

    -- Versioning
    ruleset_version VARCHAR NOT NULL,  -- "1.0"
    priority_version VARCHAR NOT NULL,  -- "1.0"

    -- Provenance
    git_commit VARCHAR,
    db_path VARCHAR,
    created_at TIMESTAMP NOT NULL,
    last_seen_at TIMESTAMP NOT NULL,

    -- Notes
    notes VARCHAR,

    -- Constraints
    UNIQUE(param_hash)
);

CREATE INDEX idx_search_knowledge_result_class ON search_knowledge(result_class);
CREATE INDEX idx_search_knowledge_orb_time ON search_knowledge(orb_time);
CREATE INDEX idx_search_knowledge_rr_target ON search_knowledge(rr_target);
CREATE INDEX idx_search_knowledge_instrument ON search_knowledge(instrument);
```

---

### 6. Priority Engine Flow

```
1. Load search_knowledge (past results)
   ↓
2. Calculate axis priorities:
   - ORB time priorities (from GOOD/NEUTRAL counts)
   - RR target priorities (from GOOD/NEUTRAL counts)
   - Filter type priorities (from GOOD/NEUTRAL counts)
   ↓
3. Generate all untested combinations
   ↓
4. Score each combination:
   priority = (orb_priority * 0.4 + rr_priority * 0.3 + filter_priority * 0.3)
   ↓
5. Sort by priority (descending)
   ↓
6. Split into exploitation (85%) and exploration (15%):
   - Exploitation: Top 85% by priority
   - Exploration: First 15% from hash-sorted untested pool
   ↓
7. Merge and return chunk
```

---

## IMPLEMENTATION PLAN

### Phase 1: Schema + Versioning (30 min)

**Files to Create**:
1. `pipeline/schema_search_knowledge.sql` (NEW)
   - CREATE TABLE search_knowledge
   - CREATE INDEXES

2. `pipeline/init_search_knowledge.py` (NEW)
   - Create search_knowledge table
   - Migrate existing search_memory data (if needed)

**Files to Modify**:
3. `trading_app/auto_search_engine.py`
   - Add `compute_param_hash_v2()` function
   - Add `param_hash_version = "2.0"` constant
   - Store version in search_knowledge

**Verification**:
```bash
python pipeline/init_search_knowledge.py
python -c "import duckdb; con = duckdb.connect('data/db/gold.db'); print(con.execute('SELECT COUNT(*) FROM search_knowledge').fetchone())"
```

---

### Phase 2: Result Classification (30 min)

**Files to Create**:
4. `trading_app/result_classifier.py` (NEW)
   - `classify_result(expectancy_r, sample_size, robust_flags) -> str`
   - `RULESET_VERSION = "1.0"`
   - Deterministic thresholds (GOOD/NEUTRAL/BAD)

**Files to Modify**:
5. `trading_app/auto_search_engine.py`
   - Import result_classifier
   - Call `classify_result()` after scoring
   - Store result_class in search_knowledge

**Verification**:
```python
from result_classifier import classify_result

# Test GOOD
assert classify_result(0.30, 60, 0) == "GOOD"

# Test NEUTRAL
assert classify_result(0.20, 40, 1) == "NEUTRAL"

# Test BAD
assert classify_result(0.10, 25, 2) == "BAD"
```

---

### Phase 3: Priority Engine (60 min)

**Files to Create**:
6. `trading_app/priority_engine.py` (NEW)
   - `PriorityEngine` class
   - `calculate_axis_priorities(db_conn) -> Dict`
   - `score_combination(combo, priorities) -> float`
   - `PRIORITY_VERSION = "1.0"`
   - Weights: ORB (40%), RR (30%), Filters (30%)

**Key Functions**:
```python
class PriorityEngine:
    VERSION = "1.0"

    def __init__(self, db_conn):
        self.conn = db_conn
        self.priorities = self.calculate_axis_priorities()

    def calculate_axis_priorities(self) -> Dict:
        """
        Calculate priority scores for each axis
        Returns: {
            'orb_times': {'0900': 0.75, '1000': 0.85, ...},
            'rr_targets': {1.5: 0.60, 2.0: 0.70, ...},
            'filter_types': {'SIZE': 0.65, 'TRAVEL': 0.55, ...}
        }
        """

    def score_combination(self, combo: Dict) -> float:
        """
        Score a parameter combination
        Returns: 0.0 to 1.0 priority score
        """
```

**Files to Modify**:
7. `trading_app/auto_search_engine.py`
   - Import PriorityEngine
   - Replace `_generate_candidates()` logic
   - Use priority scoring instead of exhaustive

**Verification**:
```python
from priority_engine import PriorityEngine

engine = PriorityEngine(db_conn)
priorities = engine.calculate_axis_priorities()

# Should have priorities for each axis
assert 'orb_times' in priorities
assert 'rr_targets' in priorities
assert 'filter_types' in priorities

# Scores should be 0.0 to 1.0
score = engine.score_combination({'orb_time': '1000', 'rr_target': 2.0, 'filters': {}})
assert 0.0 <= score <= 1.0
```

---

### Phase 4: ε-Exploration (45 min)

**Files to Modify**:
8. `trading_app/auto_search_engine.py`
   - Add `EPSILON = 0.15` constant (exploration budget)
   - Modify `_generate_candidates()` to split:
     - 85% exploitation (top priority)
     - 15% exploration (hash-sorted untested)
   - Add `_get_exploration_candidates()` method
   - Add `_get_exploitation_candidates()` method

**Key Logic**:
```python
def _generate_candidates(self, settings):
    # Calculate budget
    total_budget = settings.max_candidates
    exploit_budget = int(total_budget * (1 - EPSILON))
    explore_budget = total_budget - exploit_budget

    # Exploitation: Top priority
    exploit_candidates = self._get_exploitation_candidates(
        settings,
        limit=exploit_budget
    )

    # Exploration: Hash-sorted untested
    explore_candidates = self._get_exploration_candidates(
        settings,
        limit=explore_budget
    )

    # Merge (exploitation first, then exploration)
    return exploit_candidates + explore_candidates
```

**Verification**:
```python
# Run search with 100 candidates
results = engine.run_search(
    instrument='MGC',
    settings={'max_candidates': 100},
    max_seconds=60
)

# Should have ~85 exploitation + ~15 exploration
assert len(results['exploitation']) == 85
assert len(results['exploration']) == 15
```

---

### Phase 5: Provenance Tracking (30 min)

**Files to Create**:
9. `trading_app/provenance.py` (NEW)
   - `get_git_commit() -> str`
   - `get_db_path() -> str`
   - `get_timestamp() -> str`
   - `create_provenance_dict() -> Dict`

**Files to Modify**:
10. `trading_app/auto_search_engine.py`
    - Import provenance
    - Store git_commit in search_knowledge
    - Store db_path in search_knowledge
    - Add provenance to JSON artifacts

**Key Functions**:
```python
def create_provenance_dict() -> Dict:
    return {
        'timestamp': datetime.now().isoformat(),
        'git_commit': get_git_commit(),
        'db_path': str(DB_PATH),
        'ruleset_version': RULESET_VERSION,
        'priority_version': PRIORITY_VERSION,
        'param_hash_version': PARAM_HASH_VERSION
    }
```

**Verification**:
```python
from provenance import create_provenance_dict

prov = create_provenance_dict()

# Should have all required fields
assert 'timestamp' in prov
assert 'git_commit' in prov
assert 'db_path' in prov
assert 'ruleset_version' in prov
assert 'priority_version' in prov
assert 'param_hash_version' in prov
```

---

### Phase 6: Integration + Testing (30 min)

**Files to Create**:
11. `scripts/check/check_priority_engine.py` (NEW)
    - Verify priority engine determinism
    - Verify ε-exploration split
    - Verify result classification
    - Verify versioning

12. `tests/test_priority_engine.py` (NEW)
    - Unit tests for PriorityEngine
    - Test axis priority calculation
    - Test combination scoring
    - Test ε-exploration split

**Files to Modify**:
13. `scripts/check/run_ci_smoke.py`
    - Add priority_engine check

14. `test_app_sync.py`
    - Add Test 7: Priority engine verification

**Verification**:
```bash
python scripts/check/check_priority_engine.py
python -m pytest tests/test_priority_engine.py -v
python test_app_sync.py
python scripts/check/run_ci_smoke.py
```

---

### Phase 7: Documentation (15 min)

**Files to Create**:
15. `AUDIT3_COMPLETE.md` (completion summary)
16. `docs/PRIORITY_ENGINE.md` (technical documentation)

**Content**:
- How priority engine works
- How ε-exploration is implemented
- Result classification thresholds
- Versioning strategy
- Example usage

---

## TODO LIST

### Phase 1: Schema + Versioning ⏱️ 30 min
- [ ] Create `pipeline/schema_search_knowledge.sql`
  - [ ] Define search_knowledge table schema
  - [ ] Add indexes (result_class, orb_time, rr_target, instrument)
- [ ] Create `pipeline/init_search_knowledge.py`
  - [ ] Initialize table
  - [ ] Optional: Migrate search_memory data
- [ ] Modify `trading_app/auto_search_engine.py`
  - [ ] Add `compute_param_hash_v2()` function
  - [ ] Add `PARAM_HASH_VERSION = "2.0"` constant
  - [ ] Test hash stability
- [ ] Run verification
  - [ ] `python pipeline/init_search_knowledge.py`
  - [ ] Check table created

### Phase 2: Result Classification ⏱️ 30 min
- [ ] Create `trading_app/result_classifier.py`
  - [ ] Define `RULESET_VERSION = "1.0"`
  - [ ] Implement `classify_result()` function
  - [ ] Define thresholds: GOOD (0.25R, 50 trades), NEUTRAL (0.15R, 30 trades), BAD (< 0.15R or < 30)
  - [ ] Add docstrings with versioning
- [ ] Modify `trading_app/auto_search_engine.py`
  - [ ] Import result_classifier
  - [ ] Call classify_result() after scoring
  - [ ] Store result_class in search_knowledge
- [ ] Run verification
  - [ ] Test GOOD classification
  - [ ] Test NEUTRAL classification
  - [ ] Test BAD classification

### Phase 3: Priority Engine ⏱️ 60 min
- [ ] Create `trading_app/priority_engine.py`
  - [ ] Define `PRIORITY_VERSION = "1.0"`
  - [ ] Create `PriorityEngine` class
  - [ ] Implement `calculate_axis_priorities()` method
    - [ ] ORB time priorities (from GOOD/NEUTRAL counts)
    - [ ] RR target priorities (from GOOD/NEUTRAL counts)
    - [ ] Filter type priorities (from GOOD/NEUTRAL counts)
  - [ ] Implement `score_combination()` method
    - [ ] Apply weights: ORB (40%), RR (30%), Filters (30%)
    - [ ] Return 0.0 to 1.0 score
  - [ ] Add docstrings with versioning
- [ ] Modify `trading_app/auto_search_engine.py`
  - [ ] Import PriorityEngine
  - [ ] Replace exhaustive generation with priority-based
  - [ ] Use priority scores to rank candidates
- [ ] Run verification
  - [ ] Test axis priority calculation
  - [ ] Test combination scoring
  - [ ] Verify determinism (same inputs → same outputs)

### Phase 4: ε-Exploration ⏱️ 45 min
- [ ] Modify `trading_app/auto_search_engine.py`
  - [ ] Add `EPSILON = 0.15` constant
  - [ ] Create `_get_exploitation_candidates()` method
    - [ ] Top 85% by priority score
  - [ ] Create `_get_exploration_candidates()` method
    - [ ] Bottom 15% from hash-sorted untested pool
  - [ ] Modify `_generate_candidates()` to split
    - [ ] Calculate budgets (85% exploit, 15% explore)
    - [ ] Merge candidates (exploitation first)
  - [ ] Log exploitation/exploration split
- [ ] Run verification
  - [ ] Test 100 candidates → ~85 exploit + ~15 explore
  - [ ] Verify exploration is hash-sorted (deterministic)
  - [ ] Verify no overlap between exploit and explore

### Phase 5: Provenance Tracking ⏱️ 30 min
- [ ] Create `trading_app/provenance.py`
  - [ ] Implement `get_git_commit()` using subprocess
  - [ ] Implement `get_db_path()` returning relative path
  - [ ] Implement `get_timestamp()` ISO 8601 format
  - [ ] Implement `create_provenance_dict()`
    - [ ] Include: timestamp, git_commit, db_path
    - [ ] Include: ruleset_version, priority_version, param_hash_version
- [ ] Modify `trading_app/auto_search_engine.py`
  - [ ] Import provenance
  - [ ] Store git_commit in search_knowledge
  - [ ] Store db_path in search_knowledge
  - [ ] Add provenance to JSON artifacts (search_runs)
- [ ] Run verification
  - [ ] Check git_commit is captured
  - [ ] Check db_path is correct
  - [ ] Check all versions are stored

### Phase 6: Integration + Testing ⏱️ 30 min
- [ ] Create `scripts/check/check_priority_engine.py`
  - [ ] Verify PriorityEngine loads
  - [ ] Verify axis priorities calculated
  - [ ] Verify ε-exploration split (85/15)
  - [ ] Verify result_class assignment
  - [ ] Verify versioning in DB
- [ ] Create `tests/test_priority_engine.py`
  - [ ] Unit test: axis priority calculation
  - [ ] Unit test: combination scoring
  - [ ] Unit test: ε-exploration split
  - [ ] Unit test: determinism (same inputs → same outputs)
- [ ] Modify `scripts/check/run_ci_smoke.py`
  - [ ] Add Check 6: Priority engine verification
- [ ] Modify `test_app_sync.py`
  - [ ] Add Test 7: Priority engine integration
- [ ] Run verification
  - [ ] `python scripts/check/check_priority_engine.py`
  - [ ] `python -m pytest tests/test_priority_engine.py -v`
  - [ ] `python test_app_sync.py`
  - [ ] `python scripts/check/run_ci_smoke.py`

### Phase 7: Documentation ⏱️ 15 min
- [ ] Create `AUDIT3_COMPLETE.md`
  - [ ] List all files created/modified
  - [ ] Summarize priority engine implementation
  - [ ] Summarize ε-exploration implementation
  - [ ] Include verification results
  - [ ] Include commands to run
- [ ] Create `docs/PRIORITY_ENGINE.md`
  - [ ] Technical architecture
  - [ ] Priority scoring algorithm
  - [ ] ε-exploration algorithm
  - [ ] Result classification rules
  - [ ] Versioning strategy
  - [ ] Example usage

---

## FILES TO CREATE (9 new files)

1. `pipeline/schema_search_knowledge.sql`
2. `pipeline/init_search_knowledge.py`
3. `trading_app/result_classifier.py`
4. `trading_app/priority_engine.py`
5. `trading_app/provenance.py`
6. `scripts/check/check_priority_engine.py`
7. `tests/test_priority_engine.py`
8. `AUDIT3_COMPLETE.md`
9. `docs/PRIORITY_ENGINE.md`

---

## FILES TO MODIFY (3 existing files)

1. `trading_app/auto_search_engine.py`
   - Add `compute_param_hash_v2()`
   - Add constants: PARAM_HASH_VERSION, EPSILON
   - Import: result_classifier, priority_engine, provenance
   - Modify: `_generate_candidates()` for ε-exploration
   - Store: result_class, versions, provenance in search_knowledge

2. `scripts/check/run_ci_smoke.py`
   - Add Check 6: Priority engine verification

3. `test_app_sync.py`
   - Add Test 7: Priority engine integration

---

## VERIFICATION CHECKLIST

### Phase 1: Schema ✓
- [ ] search_knowledge table exists
- [ ] Indexes created
- [ ] param_hash_version stored

### Phase 2: Classification ✓
- [ ] classify_result() returns GOOD/NEUTRAL/BAD
- [ ] Thresholds correct (0.25R/50 trades, 0.15R/30 trades)
- [ ] ruleset_version stored

### Phase 3: Priority Engine ✓
- [ ] Axis priorities calculated from past results
- [ ] Combination scoring works (0.0 to 1.0)
- [ ] Deterministic (same inputs → same outputs)
- [ ] priority_version stored

### Phase 4: ε-Exploration ✓
- [ ] 85% exploitation (top priority)
- [ ] 15% exploration (hash-sorted untested)
- [ ] No overlap between sets
- [ ] Deterministic exploration order

### Phase 5: Provenance ✓
- [ ] git_commit captured
- [ ] db_path stored
- [ ] All versions present (ruleset, priority, param_hash)
- [ ] Timestamp in ISO 8601

### Phase 6: Integration ✓
- [ ] check_priority_engine.py passes
- [ ] test_priority_engine.py passes
- [ ] test_app_sync.py Test 7 passes
- [ ] run_ci_smoke.py Check 6 passes

### Phase 7: Documentation ✓
- [ ] AUDIT3_COMPLETE.md written
- [ ] docs/PRIORITY_ENGINE.md written
- [ ] All commands documented

---

## RISKS & MITIGATION

### Risk 1: Breaking Existing Search
**Mitigation**:
- Keep existing auto_search_engine.py functions intact
- Add new methods alongside (not replace)
- Feature flag: `USE_PRIORITY_ENGINE = True` (can disable)

### Risk 2: Performance Degradation
**Mitigation**:
- Priority calculation cached (per search run)
- Indexes on search_knowledge
- Limit lookback (last 1000 results only)

### Risk 3: Determinism Breaks
**Mitigation**:
- Unit tests for determinism
- Store param_hash_version
- Explicit field ordering (no dict assumptions)

### Risk 4: ε-Exploration Too Rigid
**Mitigation**:
- Make EPSILON configurable (default 0.15)
- Allow override in search settings
- Document tuning guidance

---

## SUCCESS CRITERIA

✅ **search_knowledge** table created and populated
✅ **Result classification** works (GOOD/NEUTRAL/BAD from thresholds)
✅ **Priority engine** scores combinations deterministically
✅ **ε-Exploration** splits 85/15 consistently
✅ **Versioning** tracked (ruleset, priority, param_hash)
✅ **Provenance** captured (git commit, db path, timestamp)
✅ **All tests passing** (check scripts + unit tests)
✅ **Documentation complete** (AUDIT3_COMPLETE.md + PRIORITY_ENGINE.md)
✅ **No breaking changes** (existing search still works)

---

## ESTIMATED TIMELINE

- Phase 1: Schema + Versioning - 30 min
- Phase 2: Result Classification - 30 min
- Phase 3: Priority Engine - 60 min
- Phase 4: ε-Exploration - 45 min
- Phase 5: Provenance Tracking - 30 min
- Phase 6: Integration + Testing - 30 min
- Phase 7: Documentation - 15 min

**Total**: ~4 hours (includes buffer for debugging)

---

## NEXT STEPS

**Option A**: Execute full implementation now (4 hours)
**Option B**: Execute Phase 1-2 only (1 hour), review, then continue
**Option C**: Review plan first, adjust, then execute

**Recommend**: Option B (Phase 1-2 first, verify direction)

---

**Created**: 2026-01-29
**Status**: 📋 READY FOR APPROVAL
**Complexity**: HIGH
**Impact**: MEDIUM (new feature, but isolated from core trading logic)
