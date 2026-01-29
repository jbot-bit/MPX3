# Auto Search - Deterministic Edge Discovery

**Version:** 1.0
**Date:** 2026-01-29
**Status:** Production Add-On

---

## What is Auto Search?

Auto Search is a deterministic edge discovery system that systematically tests parameter combinations to find new trading edge candidates.

**Key Features:**
- No LLM. No bias. Pure parameter space exploration.
- Runs only when you click (manual trigger)
- Hard 300-second timeout (≤5 minutes)
- Stores search memory to prevent re-testing
- Never auto-promotes (human decides)

---

## Why 5 Minutes?

**Hard constraint:** Streamlit must remain responsive.

300 seconds = enough time to test hundreds of combinations while keeping the UI interactive. If a search times out, partial results are saved and can be reviewed.

**Design principle:** Fast feedback loops. If you need deeper analysis, promote promising candidates to the Validation Gate.

---

## Architecture

### Tables

**search_runs**
- Tracks each search execution
- Status: RUNNING, COMPLETED, TIMEOUT, FAILED
- Records tested/skipped/promising counts

**search_candidates**
- Stores promising edge candidates found by search
- Scored using fast proxies (existing ORB outcome columns)
- Not validated (needs manual promotion)

**search_memory**
- Deduplication registry (param_hash → last_seen)
- Prevents re-testing same combinations
- Accumulates over time as you run searches

**validation_queue**
- Manual promotion target
- Ingress to existing validation workflow
- Status: PENDING → IN_VALIDATION → APPROVED/REJECTED

### Data Flow

```
[Auto Search] → search_candidates → [Manual Review] → validation_queue → [Validation Gate]
                     ↓
              search_memory (dedupe)
```

---

## How It Works

### 1. Parameter Generation

Systematically generates combinations:
- ORB times: 0900, 1000, 1100, 1800, 2300, 0030
- RR targets: 1.5, 2.0, 2.5, 3.0
- Filters: (future) size, travel, session type

**Example:** 6 ORBs × 4 RRs = 24 baseline combinations

### 2. Memory Check

Before testing each combination:
- Compute `param_hash = sha256(instrument + family + orb + rr + filters)`
- Check if hash exists in `search_memory`
- If yes: skip (already tested)
- If no: proceed to scoring

### 3. Fast Scoring

Uses existing `daily_features` columns for speed:
- **Preferred:** `orb_*_tradeable_realized_rr_*` (if exists for this RR)
- **Fallback:** `orb_*_r_multiple` and `orb_*_outcome` (baseline proxy)

**No deep backtests.** Just fast proxies to filter down to promising candidates.

### 4. Win Rate Metrics (IMPORTANT)

Auto Search displays **TWO** different win rate metrics. They measure different things:

#### Profitable Trade Rate
- **Definition:** % of trades where `realized_rr > 0` (any positive return)
- **Includes:** Trades that closed profitably but didn't hit target
- **Example:** Trade closes at +0.3R (missed 1.5R target) = counts as profitable
- **Typical values:** 60-80% (higher than target hit rate)
- **Use case:** Shows how often you make ANY money

#### Target Hit Rate
- **Definition:** % of trades where `outcome = 'WIN'` (hit profit target)
- **Requires:** Trade must reach full profit target to count
- **Example:** Same +0.3R trade = does NOT count (target was 1.5R)
- **Typical values:** 45-65% (lower than profitable rate)
- **Use case:** True "win rate" used in validated_setups

**Why both matter:**
- **Expectancy** (score_proxy) is the same regardless of which metric you use
- But understanding the difference helps set correct expectations
- A candidate with 80% profitable rate but only 50% target hit rate tells you: "I make money often, but I don't always hit full targets"

**Which to trust:** Both are correct, just measuring different things. For comparing to validated_setups, use Target Hit Rate.

### 5. Thresholds

Candidate is "promising" if:
- `sample_size >= 30` trades
- `score_proxy >= 0.15R` (minimum expectancy)

### 6. Results

Promising candidates are:
- Saved to `search_candidates` (for this run)
- Added to `search_memory` (permanent dedupe registry)
- Displayed in UI for manual review

---

## Usage

### From Streamlit App

1. Open `trading_app/app_canonical.py`
2. Go to **Research** tab
3. Find **Auto Search** section
4. Click "Run Auto Search"
5. Wait ≤5 minutes (watch progress)
6. Review results table
7. Select a candidate
8. Click "Send to Validation Queue"
9. Confirm (checkbox required)
10. Candidate now pending in Validation Gate tab

### From CLI (Testing)

```bash
# Test the engine directly
python trading_app/auto_search_engine.py

# Check tables
python scripts/check/check_auto_search_tables.py

# Query results
python -c "import duckdb; conn = duckdb.connect('data/db/gold.db');
results = conn.execute('SELECT * FROM search_candidates ORDER BY score_proxy DESC LIMIT 10').fetchall();
print(results)"
```

---

## Where Memory is Stored

**Table:** `search_memory`
**Location:** `data/db/gold.db`

**Schema:**
```sql
search_memory (
    memory_id INTEGER PRIMARY KEY,
    param_hash VARCHAR UNIQUE,  -- Dedupe key
    instrument VARCHAR,
    setup_family VARCHAR,
    filters_json JSON,
    first_seen_at TIMESTAMP,
    last_seen_at TIMESTAMP,
    test_count INTEGER,  -- How many times tested
    best_score DOUBLE,  -- Best score seen for this combo
    notes TEXT
)
```

**Growth rate:**
- Each unique parameter combination = 1 row
- ~100-500 combinations tested per run
- Memory accumulates (not cleared)
- Over time: fewer new combinations, more skips

**To clear memory** (if you want to re-test everything):
```sql
DELETE FROM search_memory WHERE instrument = 'MGC';
```
(Not recommended unless you're testing changes to scoring logic)

---

## Manual Promotion Workflow

**Step 1:** Run Auto Search
- System: Tests combinations, saves promising candidates

**Step 2:** Review Results
- You: Check score_proxy, sample_size, notes
- You: Decide which candidates are worth validating

**Step 3:** Send to Validation Queue
- You: Select candidate
- You: Click "Send to Validation Queue"
- You: Confirm with checkbox

**Step 4:** Validation Gate
- You: Go to Validation Gate tab
- You: See candidate in pending queue
- You: Run full validation (walk-forward, stress test, etc.)
- System: Approves or rejects based on evidence

**Step 5:** Production (if approved)
- You: Manually promote to validated_setups
- System: Edge now tradeable in Production tab

**Human confirmation at every step. No auto-promotion.**

---

## Technical Details

### Hash Computation

```python
def compute_param_hash(params: Dict) -> str:
    sorted_params = {
        'instrument': params.get('instrument', ''),
        'setup_family': params.get('setup_family', ''),
        'orb_time': params.get('orb_time', ''),
        'rr_target': params.get('rr_target', 0.0),
        'filters': params.get('filters', {})
    }
    json_str = json.dumps(sorted_params, sort_keys=True)
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()[:16]
```

**Properties:**
- Deterministic (same params → same hash)
- Order-independent (sorted keys)
- Collision-resistant (SHA256, 16-char hex = 64 bits)

### Timeout Handling

```python
for combo in combinations:
    if time.time() - start_time > max_seconds:
        raise TimeoutError()
    # ... test combo
```

**On timeout:**
- Search status → TIMEOUT
- Partial results saved
- Memory updated for tested combos
- UI shows "Search timeout" warning

---

## Limitations

1. **No filters yet** - Currently baseline only (ORB × RR). Filter combinations (size, travel, session) planned for future.

2. **Fast proxies only** - Uses existing outcome columns. Not a full backtest. Promising candidates still need full validation.

3. **Single instrument** - MGC only for now. NQ/MPL support planned.

4. **No live data** - Searches historical data only. Does not connect to live markets.

5. **Memory never expires** - Tested combinations stay in memory forever. Intentional (prevents repeat work).

---

## Maintenance

### Check Tables
```bash
python scripts/check/check_auto_search_tables.py
```

### View Search History
```sql
SELECT run_id, instrument, status, duration_seconds, candidates_found
FROM search_runs
ORDER BY created_at DESC
LIMIT 10;
```

### View Memory Size
```sql
SELECT instrument, COUNT(*) as tested_combinations
FROM search_memory
GROUP BY instrument;
```

### Clear Old Runs (Optional)
```sql
-- Delete runs older than 30 days
DELETE FROM search_runs
WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '30 days';

-- Cascade deletes search_candidates (foreign key)
```

---

## Troubleshooting

**"Table does not exist"**
- Run migration: `python scripts/migrations/create_auto_search_tables.py`

**"Search timeout"**
- Normal if testing many combinations
- Partial results are saved
- Run search again (will skip already-tested combos)

**"No promising candidates found"**
- All combinations below threshold (< 0.15R or < 30 trades)
- Or all combinations already in memory (skipped)
- Try different instrument or setup family

**"Failed to enqueue"**
- Database connection issue
- Check validation_queue table exists
- Check logs in app_errors.txt

---

## Future Enhancements

1. **Filter combinations** - Size, travel, session type filters
2. **Multi-instrument** - NQ, MPL support
3. **Parallel search** - Multiple instruments simultaneously
4. **Smart sampling** - Focus on promising parameter regions
5. **Visualization** - Parameter space heatmap
6. **Export results** - CSV/JSON export for external analysis

---

## Files

**Engine:**
- `trading_app/auto_search_engine.py` (core logic)

**UI:**
- `trading_app/app_canonical.py` (Research tab integration)

**Database:**
- `scripts/migrations/create_auto_search_tables.py` (schema)
- `scripts/check/check_auto_search_tables.py` (verification)

**Docs:**
- `docs/AUTO_SEARCH.md` (this file)

---

## Principles

1. **Deterministic discovery** - No randomness, no LLM inference
2. **Fast feedback** - ≤5 min, always responsive
3. **Fail closed** - Exit codes, error logging, validation gates
4. **Human decides** - Manual promotion, no auto-approval
5. **Evidence-driven** - Score proxies based on real data
6. **Auditability** - Every search logged, every candidate traceable

---

**Version History:**
- 1.0 (2026-01-29): Initial release
