# WHICH APP TO USE - SIMPLE ANSWER

## THE CURRENT APPS (USE THESE)

### 1. MOBILE APP (TINDER-STYLE CARDS) ⭐ **PRIMARY**
**File**: `trading_app/app_mobile.py`
**Launch**: `START_MOBILE_APP.bat`
**URL**: http://localhost:8501

**Use this for**:
- Trading on the go
- Quick glances
- Card-based navigation (swipe interface)
- Mobile phone access

**Features**:
- 5 swipeable cards (Dashboard, Chart, Trade, Positions, AI Chat)
- ML predictions
- Safety checks
- Setup scanner
- Enhanced charts
- AI assistant

**Status**: ✅ CURRENT - Just updated and verified

---

### 2. DESKTOP APP (FULL INTERFACE)
**File**: `trading_app/app_trading_hub.py`
**Launch**: `START_TRADING_APP.bat`
**URL**: http://localhost:8501

**Use this for**:
- Deep analysis
- Strategy hierarchy (CASCADE, NIGHT_ORB, etc.)
- Multi-instrument switching (MGC/NQ/MPL)
- Detailed journal and levels

**Features**:
- Wide layout with sidebar
- Full strategy engine with hierarchy
- Complete position tracking
- Journal integration

**Status**: ✅ CURRENT - Desktop version

---

## THE RULE: **ONLY 2 APPS**

1. **`app_mobile.py`** - Mobile/card interface
2. **`app_trading_hub.py`** - Desktop interface

**Everything else is either**:
- ❌ Archived (in `_archive/apps/`)
- ❌ Support files (not apps)
- ❌ Tests (not apps)

---

## OLD/DEPRECATED APPS (DON'T USE)

All stored in `_archive/apps/`:

1. ❌ `app_edge_research.py` - Old research dashboard
2. ❌ `app_trading_hub_ai_version.py` - Old AI version
3. ❌ `live_trading_dashboard.py` - Old dashboard
4. ❌ `orb_dashboard_simple.py` - Simple dashboard
5. ❌ `trading_dashboard_pro.py` - Pro dashboard
6. ❌ `MGC_NOW.py.OUTDATED_DANGEROUS` - Dangerous, don't use
7. ❌ `app_simplified.py.REDUNDANT` - Redundant

**Status**: All archived on Jan 15, 2026 cleanup

---

## HOW TO START

### For Mobile (Tinder Cards):
```bash
START_MOBILE_APP.bat
```
Opens: http://localhost:8501
File runs: `trading_app/app_mobile.py`

### For Desktop (Full Interface):
```bash
START_TRADING_APP.bat
```
Opens: http://localhost:8501
File runs: `trading_app/app_trading_hub.py`

**NOTE**: Only run ONE at a time (both use port 8501)

---

## CONFUSED? USE THIS:

**Just starting out?** → Use **MOBILE APP** (START_MOBILE_APP.bat)

**Need deep analysis?** → Use **DESKTOP APP** (START_TRADING_APP.bat)

**On your phone?** → Use **MOBILE APP** (access via PC IP)

---

## FILE LOCATIONS

**Current Apps**:
```
trading_app/
├── app_mobile.py         ← MOBILE APP (cards)
└── app_trading_hub.py    ← DESKTOP APP (full)
```

**Old Apps** (don't use):
```
_archive/apps/
├── app_edge_research.py
├── app_trading_hub_ai_version.py
├── live_trading_dashboard.py
├── orb_dashboard_simple.py
├── trading_dashboard_pro.py
├── MGC_NOW.py.OUTDATED_DANGEROUS
└── app_simplified.py.REDUNDANT
```

---

## SUMMARY

✅ **USE MOBILE APP**: `START_MOBILE_APP.bat` → `app_mobile.py`
✅ **USE DESKTOP APP**: `START_TRADING_APP.bat` → `app_trading_hub.py`
❌ **DON'T USE**: Anything in `_archive/apps/`

**That's it. Just 2 apps. Simple.** 🎯

---

**Updated**: January 17, 2026
**Apps cleaned**: 7 old apps archived
**Current apps**: 2 (mobile + desktop)
