# PHASE 2 Logic Explanation

## Your Question: Should backfill stop 2-3 days prior?

**Short answer:** NO for bars, YES for features (sort of)

---

## The Correct Approach

### 1. Backfill bars_1m → ALL THE WAY TO CURRENT ✅

**Why:** You want the LATEST bars for:
- Real-time scanning (setup detection NOW)
- Intraday monitoring
- Current session analysis

**Example:**
- Current time: 2026-01-29 12:40
- Latest bar in DB: 2026-01-29 12:23
- Backfill range: 2026-01-29 12:23 → 2026-01-29 12:40 ✅

### 2. Build daily_features → STOP 1 DAY BEFORE CURRENT ✅

**Why:** Today's trading day is INCOMPLETE:
- ORBs may not have resolved yet
- Trading day ends at next 09:00 Brisbane
- Don't want "partial day" features misleading your analysis

**Example:**
- Current time: 2026-01-29 12:40 (trading day still active)
- Latest features: 2026-01-15
- Should build: 2026-01-16 to 2026-01-28 (stop BEFORE today) ✅
- Skip: 2026-01-29 (today is incomplete)

### 3. REBUILD_TAIL_DAYS = 3 (Honesty Rule) ✅

**Why:** Late-arriving bars can change outcomes:
- ProjectX may backfill missing minutes
- Corrections happen
- Always rebuild last 3 completed days

**Example:**
- Latest features: 2026-01-25
- Current: 2026-01-29
- Naive range: 2026-01-26 to 2026-01-28
- With REBUILD_TAIL: 2026-01-23 to 2026-01-28 ✅ (catches late bars)

---

## Implementation

### Updated calculate_feature_build_range():

```python
def calculate_feature_build_range(db_path, latest_bar_ts):
    # 1. Get latest feature date
    last_feat_date = get_latest_feature_date(db_path)

    # 2. End = YESTERDAY (not today, day is incomplete)
    from zoneinfo import ZoneInfo
    tz_brisbane = ZoneInfo("Australia/Brisbane")
    today_local = datetime.now(tz_brisbane).date()
    end_date_local = today_local - timedelta(days=1)  # STOP BEFORE TODAY

    # 3. Start = last_feat_date + 1
    start_date_local = last_feat_date + timedelta(days=1) if last_feat_date else MIN_BAR_DATE

    # 4. Apply REBUILD_TAIL_DAYS (honesty rule)
    rebuild_from = end_date_local - timedelta(days=REBUILD_TAIL_DAYS)
    if start_date_local > rebuild_from:
        start_date_local = rebuild_from

    # 5. Clamp
    if start_date_local > end_date_local:
        return None, None  # No work needed

    return start_date_local, end_date_local
```

---

## Why This is Better Than Using latest_bar_ts

**Problem with using latest_bar_ts directly:**
- latest_bar_ts = 2026-01-29 12:40 → converts to 2026-01-29 (today)
- Today is INCOMPLETE (missing 2PM close, no 18:00 ORB yet, etc.)
- Features would be WRONG

**Solution:**
- Use `datetime.now()` to get TODAY
- Build features up to YESTERDAY only
- Today's bars are available for SCANNING but not for FEATURE CALCULATION

---

## Example Timeline

**Current time:** 2026-01-29 14:30 Brisbane

**bars_1m:**
- Latest: 2026-01-29 14:28 ✅ (2-minute lag, current)
- Used for: Real-time scanning, setup detection

**daily_features:**
- Latest: 2026-01-25 (old)
- Should rebuild: 2026-01-23 to 2026-01-28
- Skip: 2026-01-29 (today, incomplete)

**Why this works:**
- You can SCAN for setups on 2026-01-29 using bars_1m
- You can ANALYZE completed days 2026-01-23 to 2026-01-28 using daily_features
- You DON'T have misleading "partial day" features for 2026-01-29

---

## Edge Case: What if current time is BEFORE 09:00?

**Example:** 2026-01-30 08:00 Brisbane

**Logic:**
- TODAY (2026-01-30) hasn't started trading yet (starts at 09:00)
- YESTERDAY (2026-01-29) trading day JUST ENDED at 09:00
- Should build features for: 2026-01-29 ✅

**Implementation:**
```python
now_brisbane = datetime.now(tz_brisbane)
if now_brisbane.hour < 9:
    # Trading day for "today" hasn't started, yesterday just ended
    end_date_local = now_brisbane.date() - timedelta(days=1)
else:
    # Trading day active or ended, stop at yesterday
    end_date_local = now_brisbane.date() - timedelta(days=1)
```

Actually, this simplifies to: **Always use yesterday** (safe default).

---

## Summary

✅ **Backfill bars_1m:** To current minute (for scanning)
✅ **Build daily_features:** To yesterday (for analysis of completed days)
✅ **Rebuild last 3 days:** Always (catch late bars)
✅ **Skip today:** Never build features for incomplete day

This ensures:
- Fresh bars for real-time scanning
- Accurate features for completed days only
- No misleading partial-day data
- Late bars don't corrupt analysis
