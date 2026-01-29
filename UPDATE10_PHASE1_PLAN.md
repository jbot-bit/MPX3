# Phase 1: Production Hero Implementation Plan

**Goal:** Time-aware hero display showing "What to trade NOW?"

---

## Current Structure (app_canonical.py lines 1800-2490)

```
with tab_production:
  1. Zone banner
  2. Promotion Gate (edge_registry VALIDATED → validated_setups)
  3. Production Registry (grouped ORB display with variants)
     - Summary metrics
     - Grouped by ORB time
     - Expandable variants per ORB
     - Selection UI
  4. Experimental Strategies section
```

---

## New Structure

```
with tab_production:
  1. Zone banner (keep as-is)
  2. 🎯 TIME-AWARE HERO (NEW) ← Insert here after banner
     - Get current ORB status
     - Query best setup for current/upcoming ORB
     - Display giant card with status
  3. 📊 ALL SETUPS GRID (NEW)
     - 3-column cards for all setups
     - Sorted by time relevance
     - Click card → shows trade plan
  4. ▼ View All Variants (expandable, collapsed by default)
     - Original grouped display
     - Fallback if hero isn't right
  5. Promotion Gate (keep as-is, move to bottom)
  6. Experimental Strategies (keep as-is)
```

---

## Implementation Steps

### Step 1: Add Import

At top of app_canonical.py (~line 40):
```python
from orb_time_logic import (
    get_current_orb_status,
    format_time_remaining,
    get_status_emoji,
    get_status_color
)
```

### Step 2: Time-Aware Hero Section

Insert after zone banner (~line 1820):

```python
# ====================================================================
# TIME-AWARE HERO - "What Should I Trade NOW?"
# ====================================================================
st.markdown("### 🎯 Current Setup Recommendation")

try:
    # Get current ORB status
    from orb_time_logic import get_current_orb_status
    orb_status = get_current_orb_status()

    # Determine which ORB to show
    hero_orb = orb_status['current_orb'] or orb_status['upcoming_orb']

    if hero_orb:
        # Query best setup for this ORB (highest expected_r)
        hero_setup = app_state.db_connection.execute("""
            SELECT
                id, instrument, orb_time, rr, sl_mode,
                orb_size_filter, win_rate, expected_r, sample_size, notes
            FROM validated_setups
            WHERE instrument = ? AND orb_time = ?
            ORDER BY expected_r DESC
            LIMIT 1
        """, [app_state.current_instrument, hero_orb]).fetchone()

        if hero_setup:
            (setup_id, instrument, orb_time, rr, sl_mode,
             orb_size_filter, win_rate, expected_r, sample_size, notes) = hero_setup

            # Status styling
            status = orb_status['status']
            emoji = get_status_emoji(status)
            color = get_status_color(status)

            # Time info
            if status == 'ACTIVE':
                time_text = f"Valid until {orb_status['end_time'].strftime('%H:%M')}"
                time_subtext = f"({format_time_remaining(orb_status['minutes_remaining'])} remaining)"
            else:
                time_text = f"Forms in {format_time_remaining(orb_status['minutes_until'])}"
                time_subtext = f"(at {orb_status.get('form_time', 'TBD')})"

            # Expected R color
            if expected_r > 0.30:
                exp_r_color = "#198754"  # Green
            elif expected_r >= 0.15:
                exp_r_color = "#0d6efd"  # Blue
            else:
                exp_r_color = "#6c757d"  # Gray

            # HERO CARD
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, {color}15 0%, {color}05 100%);
                border-left: 8px solid {color};
                border-radius: 12px;
                padding: 32px;
                margin: 20px 0;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            ">
                <div style="text-align: center;">
                    <!-- Status -->
                    <div style="font-size: 48px; margin-bottom: 16px;">
                        {emoji}
                    </div>
                    <div style="font-size: 24px; font-weight: 600; color: {color}; margin-bottom: 8px;">
                        {status}: {orb_time} ORB
                    </div>

                    <!-- Setup Info -->
                    <div style="font-size: 20px; color: #666; margin-bottom: 24px;">
                        RR {rr:.1f}  |  {sl_mode.upper()} SL
                    </div>

                    <!-- Expected R (HUGE) -->
                    <div style="font-size: 128px; font-weight: 700; color: {exp_r_color}; line-height: 1; margin: 24px 0;">
                        +{expected_r:.3f}R
                    </div>

                    <!-- Stats -->
                    <div style="font-size: 18px; color: #333; margin: 16px 0;">
                        <strong>Win Rate:</strong> {win_rate*100:.1f}%  |
                        <strong>Sample:</strong> {int(sample_size)} trades
                        {f" | <strong>Filter:</strong> {orb_size_filter*100:.0f}% ATR" if orb_size_filter else ""}
                    </div>

                    <!-- Time Info -->
                    <div style="font-size: 16px; color: #666; margin: 24px 0;">
                        ⏱ {time_text}<br>{time_subtext}
                    </div>

                    <!-- Action Button -->
                    <div style="margin-top: 24px;">
                        [📊 VIEW TRADE PLAN button here]
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        else:
            st.info(f"No validated setup found for {hero_orb} ORB")

except Exception as e:
    st.error(f"Could not load hero setup: {e}")
    logger.error(f"Hero display error: {e}")

st.divider()
```

### Step 3: All Setups Grid

After hero:

```python
# ====================================================================
# ALL SETUPS GRID - Quick Visual Scan
# ====================================================================
st.markdown("### 📊 All Active Setups")

try:
    # Load all setups
    all_setups = app_state.db_connection.execute("""
        SELECT
            id, instrument, orb_time, rr, sl_mode,
            orb_size_filter, win_rate, expected_r, sample_size
        FROM validated_setups
        WHERE instrument = ?
        ORDER BY expected_r DESC
    """, [app_state.current_instrument]).fetchall()

    if all_setups:
        # Display in 3-column grid
        num_setups = len(all_setups)
        rows = (num_setups + 2) // 3  # Ceiling division

        for row_idx in range(rows):
            cols = st.columns(3)

            for col_idx in range(3):
                setup_idx = row_idx * 3 + col_idx
                if setup_idx >= num_setups:
                    break

                setup = all_setups[setup_idx]
                (setup_id, instrument, orb_time, rr, sl_mode,
                 orb_size_filter, win_rate, expected_r, sample_size) = setup

                # Get time status for this ORB
                orb_status = get_current_orb_status()
                if orb_time == orb_status.get('current_orb'):
                    status_emoji = "🟢"
                    status_text = "ACTIVE"
                    border_color = "#198754"
                elif orb_time == orb_status.get('upcoming_orb'):
                    status_emoji = "🟡"
                    status_text = "UPCOMING"
                    border_color = "#ffc107"
                else:
                    status_emoji = "⏸️"
                    status_text = "STANDBY"
                    border_color = "#6c757d"

                # Expected R color
                if expected_r > 0.30:
                    exp_r_color = "#198754"
                elif expected_r >= 0.15:
                    exp_r_color = "#0d6efd"
                else:
                    exp_r_color = "#6c757d"

                with cols[col_idx]:
                    st.markdown(f"""
                    <div style="
                        background: #f8f9fa;
                        border-left: 4px solid {border_color};
                        border-radius: 8px;
                        padding: 16px;
                        margin-bottom: 16px;
                        min-height: 180px;
                    ">
                        <div style="text-align: center;">
                            <div style="font-size: 24px;">{status_emoji}</div>
                            <div style="font-size: 32px; font-weight: 700; color: #1a1a1a; margin: 8px 0;">
                                {orb_time}
                            </div>
                            <div style="font-size: 16px; color: #666; margin-bottom: 12px;">
                                RR {rr:.1f}
                            </div>
                            <div style="font-size: 48px; font-weight: 700; color: {exp_r_color}; margin: 12px 0;">
                                +{expected_r:.3f}R
                            </div>
                            <div style="font-size: 14px; color: #666;">
                                {win_rate*100:.0f}% | {int(sample_size)}N
                            </div>
                            <div style="font-size: 12px; color: {border_color}; margin-top: 8px;">
                                {status_text}
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    else:
        st.info("No validated setups found for " + app_state.current_instrument)

except Exception as e:
    st.error(f"Could not load setups grid: {e}")

st.divider()
```

### Step 4: Original Display (Expandable Fallback)

Wrap existing grouped display in expandable:

```python
# ====================================================================
# DETAILED VIEW - All Variants (Expandable)
# ====================================================================
with st.expander("▼ View All Variants (Detailed)", expanded=False):
    st.caption("Complete list of all setups with variant selection")

    # [Paste existing Production Registry code here - lines 2024-2483]
    # This becomes the fallback if hero/grid isn't enough
```

### Step 5: Move Promotion Gate to Bottom

Move lines 1823-1980 (Promotion Gate section) to AFTER the variants expandable.

---

## Testing Plan

### Manual Tests:
1. **Launch app at 10:30 AM**
   - Hero should show 1000 ORB as ACTIVE
   - Should show "20 min remaining"
   - Grid should show all setups with 1000 marked ACTIVE

2. **Launch app at 10:55 AM**
   - Hero should show 1100 ORB as UPCOMING
   - Should show "in 10 minutes"
   - Grid should show 1100 marked UPCOMING

3. **Launch app at 11:10 AM**
   - Hero should show 1100 ORB as ACTIVE
   - Should show "6h 40m remaining"

4. **Check grid colors**
   - Green cards: ExpR > 0.30R
   - Blue cards: ExpR 0.15-0.30R
   - Gray cards: ExpR < 0.15R

5. **Expandable works**
   - Can still see original grouped display
   - Variant selection still functional

---

## Rollback Plan

If hero breaks:
1. User can still use expandable "View All Variants"
2. Original functionality preserved
3. Can remove hero section entirely if needed

---

## Next Steps After Phase 1

Once hero is working and tested:
- Phase 2: Auto Search RR presets
- Phase 3: Auto Search visual cards
- Phase 4: Manual Draft auto-fill
- Phase 5: Remove jargon

---

**Approval needed before proceeding with implementation.**
