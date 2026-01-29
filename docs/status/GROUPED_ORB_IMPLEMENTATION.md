# Grouped ORB Variant Display - Implementation Complete

## Location
**File:** `trading_app/app_canonical.py`
**Section:** Production Zone (Tab 4)
**Lines:** ~1511-1700 (after Promotion Gate section)

## Implementation Summary

### What Was Built

A professional trading terminal UI for displaying validated setups grouped by ORB time, with the following features:

#### 1. **Collapsed View (Best Variant Summary)**
- Shows 1 row per ORB time
- Displays BEST variant (highest expected_r)
- Metrics shown:
  - **BEST VARIANT**: RR value + SL mode
  - **Expected R**: Expected return in R-multiples
  - **Win Rate**: Percentage win rate
  - **Sample Size**: Number of historical trades
  - **Friction Pass**: Percentage of trades passing >+0.15R threshold

#### 2. **Expanded View (All Variants)**
- Click expander to see all variants for that ORB
- Each variant shows:
  - Selection checkbox (MAX 1 per ORB enforced)
  - RR value, SL mode, and size filter
  - Expected R (highlighted in green)
  - Win rate percentage
  - Sample size
  - Friction pass percentage
  - Notes (if available)

#### 3. **Selection Enforcement**
- Hard block: MAX 1 variant per ORB
- Selecting a new variant auto-deselects the previous one
- Selected variants highlighted with amber border and glow
- Immediate visual feedback on selection

#### 4. **Current Selections Summary**
- Shows all selected variants at the bottom
- Displays key metrics for each selection
- Styled with amber accents and green highlights

#### 5. **Data Source**
- Reads from `validated_setups` table (production strategies)
- Joins with `validated_trades` table for real performance data
- Groups by ORB time, sorted by best expected_r (descending)

## Design Aesthetic

**Theme:** Bloomberg Terminal meets Industrial Design

### Typography
- **Headers**: JetBrains Mono (bold, uppercase, amber glow)
- **Data**: IBM Plex Mono (monospace data terminal feel)
- **Size**: Large metrics (32px), medium data (14-18px), small labels (10-11px)

### Color Palette
- **Background**: Near-black gradient (#0a0e14 → #0d1117)
- **Primary Accent**: Amber (#fbbf24) - headers, best variants, selections
- **Secondary Accent**: Green (#10b981) - positive metrics, highlights
- **Tertiary Accent**: Blue (#60a5fa) - filter tags
- **Borders**: Gray (#374151, #1f2937)

### Visual Effects
- **Scan line animation**: Subtle amber line sweeping down (retro CRT terminal effect)
- **Text shadows**: Glow effects on headers and key metrics
- **Hover states**: Row highlighting with shadow lift
- **Selected state**: Amber border glow, background tint
- **Gradients**: Subtle gradients on cards and containers

### Layout
- **Data density**: High information density without clutter
- **Grid system**: CSS Grid for precise alignment
- **Hierarchy**: Clear visual hierarchy (ORB groups → variants → metrics)
- **Spacing**: Consistent 8px/16px/24px rhythm

## UI Elements Breakdown

### Summary Metrics (Top)
```
┌─────────────────┬─────────────────┬─────────────────┐
│  Total Setups   │   ORB Times     │  Total Trades   │
│       17        │        6        │      1234       │
└─────────────────┴─────────────────┴─────────────────┘
```

### ORB Group (Per ORB Time)
```
┌────────────────────────────────────────────────────────┐
│ 1000 ORB - 4 variant(s)                    [AMBER BAR] │
├────────────────────────────────────────────────────────┤
│ BEST: RR=3.0  │ ExpR: 1.190R │ WR: 56.4% │ N: 55 │... │
│               │ [GREEN GLOW]  │           │       │    │
└────────────────────────────────────────────────────────┘
  ▼ Show all 4 variant(s) for 1000
  ┌─────────────────────────────────────────────────────┐
  │ [✓] RR=3.0 (FULL) Filter:0.050 │ 1.190R │ 56% │ 55 │
  │ [ ] RR=2.5 (FULL) Filter:0.050 │ 0.916R │ 56% │ 55 │
  │ [ ] RR=2.0 (FULL) Filter:0.050 │ 0.643R │ 56% │ 55 │
  │ [ ] RR=1.5 (FULL) Filter:0.050 │ 0.369R │ 56% │ 55 │
  └─────────────────────────────────────────────────────┘
```

### Current Selections (Bottom)
```
┌─────────────────────────────────────────────────────────┐
│ CURRENT SELECTIONS - 3 ACTIVE VARIANT(S)  [AMBER HEADER]│
├─────────────────────────────────────────────────────────┤
│ 0900: RR=1.5 (FULL) - ExpR=0.245R, WR=53.1%, N=53      │
│ 1000: RR=3.0 (FULL) - ExpR=1.190R, WR=56.4%, N=55      │
│ 1800: RR=1.5 (FULL) - ExpR=0.256R, WR=50.0%, N=32      │
└─────────────────────────────────────────────────────────┘
```

## Technical Details

### Query
- Joins `validated_setups` with `validated_trades`
- Aggregates trade statistics (wins, losses, avg_realized_rr, friction_pass_count)
- Filters by instrument (current: MGC)
- Groups by setup_id with all setup attributes
- Orders by ORB time, then expected_r DESC

### Selection State
- Stored in `st.session_state.selected_variants`
- Dictionary: `{orb_time: setup_id}`
- Example: `{'0900': 20, '1000': 23, '1800': 32}`
- Enforces MAX 1 per ORB (hard block with auto-deselect)

### Checkbox Behavior
1. User checks a box
2. If another variant for same ORB is selected → auto-unselect old, select new
3. If no variant selected for that ORB → select new
4. If unchecking current selection → remove from state
5. App reruns to update UI (shows selection state immediately)

## Column Headers (Virtual Table Structure)

### Best Variant Row
| BEST VARIANT | Expected R | Win Rate | Sample Size | Friction Pass |
|--------------|-----------|----------|-------------|---------------|
| RR=3.0 (FULL)| 1.190R    | 56.4%    | 55          | 100%          |

### Variant Rows (Expanded)
| Select | Variant Details          | ExpR   | WR    | N  | Pass% |
|--------|--------------------------|--------|-------|-----|-------|
| [✓]    | RR=3.0 (FULL) Filter:0.05| 1.190R | 56.4% | 55  | 100%  |
| [ ]    | RR=2.5 (FULL) Filter:0.05| 0.916R | 56.4% | 55  | 100%  |

## No Emojis Used

All text labels are plain ASCII:
- Headers: "PRODUCTION", "VALIDATED SETUPS"
- Labels: "BEST VARIANT", "Expected R", "Win Rate", etc.
- Selection: Checkboxes (Streamlit native)
- Status: Text only ("selected", "N/A", percentages)

Safe for Windows cp1252 encoding.

## File Dependencies

### Python Imports
- `streamlit` - UI framework
- `duckdb` - Database queries
- `pandas` - DataFrame operations (via .fetchdf())

### Database Tables
- `validated_setups` - Production strategies (id, instrument, orb_time, rr, sl_mode, orb_size_filter, win_rate, expected_r, sample_size, notes)
- `validated_trades` - Per-strategy trade results (date_local, setup_id, outcome, realized_rr)

### Custom Functions
- `log_error()` - Error logging (from error_logger.py)
- `app_state.db_connection` - DuckDB connection (from AppState class)

## Future Enhancements (Not Implemented)

1. **Export Selections**: Button to export selected variants to config file
2. **Trade History Drill-Down**: Click variant to see individual trades
3. **Performance Charts**: Sparklines showing equity curves per variant
4. **Live Filtering**: Filter by min sample size, min expected_r, etc.
5. **Multi-Instrument**: Tabs for MGC, NQ, MPL (currently hardcoded to MGC)
6. **Comparison Mode**: Side-by-side variant comparison

## Testing Checklist

- [x] No encoding errors (all ASCII text)
- [x] Checkbox selection works
- [x] MAX 1 per ORB enforced (hard block)
- [x] Auto-deselect previous variant when selecting new one
- [x] Expanders work for all ORBs
- [x] Metrics display correctly (ExpR, WR, Sample, Pass%)
- [x] Best variant highlighted properly
- [x] Current selections summary shows all selections
- [x] CSS loads without errors
- [x] Scan line animation works (visual check)
- [x] Hover states work (visual check)

## Known Limitations

1. **Instrument hardcoded**: Currently filters WHERE instrument = 'MGC' only
   - To support multi-instrument: Replace with `app_state.current_instrument`
2. **No trade drill-down**: Can't click variant to see individual trades
3. **No export**: Selections not persisted (session state only)
4. **No filtering**: Can't filter by sample size, expected_r thresholds, etc.

## Integration Points

This UI replaces the old "Production Registry" section that showed promoted edges from edge_registry. The new version:
- Reads directly from `validated_setups` (production table)
- Shows real trade statistics from `validated_trades`
- Allows selection for future export/config generation
- No longer depends on edge_registry promotion workflow

## CSS Classes Reference

| Class | Purpose |
|-------|---------|
| `.production-terminal` | Main container with dark gradient + scan line |
| `.orb-group-header` | ORB time header with amber left border |
| `.best-variant-row` | Grid layout for best variant metrics |
| `.metric-cell` | Individual metric cell (centered) |
| `.metric-value` | Large metric value (green glow) |
| `.metric-value.best` | Best variant value (amber, larger) |
| `.variant-row` | Grid layout for variant row |
| `.variant-row.selected` | Selected variant (amber border + glow) |
| `.variant-detail` | Variant RR/SL/filter text |
| `.variant-metric` | Metric cell in variant row |
| `.variant-note` | Optional notes below variant |
| `.selection-summary` | Bottom summary box |
| `.selection-item` | Individual selection row |
| `.summary-metrics` | Top 3-column metrics grid |
| `.summary-metric-card` | Individual metric card (top) |

## Performance Notes

- Query joins 2 tables but uses indexed columns (setup_id, date_local)
- DataFrame operations use pandas (fast)
- CSS is inline (no external file loads)
- Scan line animation is CSS-only (no JS, low overhead)
- Expanders lazy-render (only expanded content loads)

## Accessibility

- **Contrast**: High contrast text on dark background (WCAG AAA)
- **Font size**: Minimum 11px (readable)
- **Clickable areas**: Large checkbox targets
- **Keyboard navigation**: Streamlit native checkbox support
- **Screen readers**: Semantic HTML structure

## Browser Compatibility

- **Chrome/Edge**: Full support
- **Firefox**: Full support
- **Safari**: Full support (needs -webkit- prefixes for animations, already included)
- **Mobile**: Responsive grid (may need horizontal scroll on small screens)

## Deployment Notes

- No external dependencies (fonts loaded via Google Fonts CDN)
- No JS files (Streamlit handles all interactivity)
- No images (pure CSS styling)
- Works in Streamlit Cloud, local deployment, Docker
