# BUGS.TXT FAST VERIFICATION RESULTS
**Date:** 2026-01-28
**Status:** VERIFICATION COMPLETE

---

## ✅ **CONFIRMED BUGS**

### **Bug A: NO_TRADE Ambiguity** ✅ CONFIRMED
**Problem:** NO_TRADE is used for BOTH "no entry" AND "open position"

**Evidence:**
- Found NO_TRADE with break_dir=UP/DOWN (entry happened)
- Examples: 2024-02-08, 2025-04-22, 2025-06-24

**Impact:** Cannot distinguish "no setup" from "open position"

---

### **Bug B: Tradeable-Truth Mismatch** ✅ CONFIRMED
**Problem:** Uses ORB-edge anchor, not entry-anchor

**Evidence:**
- NO entry_price columns in daily_features
- CANONICAL_LOGIC.txt requires "1R = |Entry−Stop|"

**Impact:** Stored R-multiples don't reflect tradeable reality

---

### **Bug C: Schema Mismatch** ✅ CONFIRMED
**Problem:** Code expects london_type_code, database has london_type

**Evidence:**
- daily_features has london_type ✅
- daily_features does NOT have london_type_code ❌
- Code queries london_type_code = 'L4_CONSOLIDATION'
- Database has london_type = 'CONSOLIDATION'

**Impact:** 6/8 strategies cannot validate

---

## 📊 **CURRENT STATE**

**EXISTS:**
✅ daily_features (canonical)
✅ london_type column
✅ STRUCTURAL metrics only
✅ WIN/LOSS/NO_TRADE outcomes

**MISSING:**
❌ TRADEABLE metrics
❌ OPEN outcome
❌ Entry price columns

---

## 🎯 **BUGS.TXT SPECIFICATION**

Requires implementing **Dual-Track Edge Pipeline**:

**STRUCTURAL** (ORB-anchored) = Discovery lens
**TRADEABLE** (entry-anchored) = Promotion truth

This is a MAJOR refactor, not a quick fix.

**Next:** Use Plan agent to create implementation plan.
