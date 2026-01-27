# Auto-Update Guide - Scheduled Data Updates

## Current Setup: MANUAL ONLY (Recommended)

Your app is configured for **manual updates only** to save API calls and costs.

**Benefits:**
- ✅ No wasted API calls
- ✅ Full control over when data updates
- ✅ Lower costs
- ✅ Update only when you need it

---

## How to Update Data Manually

### Option 1: Via App (Easiest)
1. Open app: `streamlit run trading_app/app_simple.py`
2. Go to **Data Status** tab
3. Click **"UPDATE DATA NOW"**
4. Wait for completion

### Option 2: Via Command Line
```bash
# Update to current date
python pipeline/backfill_range.py 2026-01-11 2026-01-25

# Build features
python pipeline/build_daily_features.py 2026-01-11
```

---

## Optional: Scheduled Auto-Updates

If you want to enable auto-updates **30 minutes before each ORB**, follow these steps:

### Step 1: Add to .env

Add these lines to your `.env` file:

```bash
# Scheduled auto-updates (optional)
AUTO_UPDATE_ENABLED=true
AUTO_UPDATE_TIMES=08:30,09:30,10:30,17:30,22:30,00:00
```

### Step 2: Run Scheduler (Background Process)

**Windows (PowerShell):**
```powershell
# Start scheduler in background
Start-Process python -ArgumentList "trading_app/scheduled_update.py" -WindowStyle Hidden
```

**Windows (Command Prompt):**
```cmd
# Start scheduler (keep terminal open)
python trading_app/scheduled_update.py
```

**To stop:** Press Ctrl+C

### Step 3: (Optional) Run as Windows Service

To run scheduler 24/7 as a background service:

1. Install `nssm` (Non-Sucking Service Manager):
   ```powershell
   # Using Chocolatey
   choco install nssm
   ```

2. Create service:
   ```powershell
   cd C:\Users\sydne\OneDrive\Desktop\MPX2_fresh
   nssm install TradingDataUpdater "C:\path\to\python.exe" "trading_app/scheduled_update.py"
   nssm start TradingDataUpdater
   ```

3. Manage service:
   ```powershell
   nssm stop TradingDataUpdater    # Stop
   nssm restart TradingDataUpdater # Restart
   nssm remove TradingDataUpdater  # Remove
   ```

---

## Update Schedule (Brisbane Time)

If enabled, auto-updates will run **30 minutes before each ORB**:

| Time  | Purpose                  |
|-------|--------------------------|
| 08:30 | Before 0900 ORB          |
| 09:30 | Before 1000 ORB          |
| 10:30 | Before 1100 ORB          |
| 17:30 | Before 1800 ORB          |
| 22:30 | Before 2300 ORB          |
| 00:00 | Before 0030 ORB (next day)|

**Why 30 minutes before?**
- Gives time for backfill + feature building to complete
- Ensures fresh data when ORB forms
- Allows time to review scanner results before trading

---

## API Usage & Costs

### Manual Updates (Current Setup)
- **Cost:** ~1-2 API calls per update (only when you click button)
- **Frequency:** Only when needed
- **Monthly:** ~5-10 API calls (if you update daily before trading)

### Auto-Updates (If Enabled)
- **Cost:** 6 API calls per day (one per ORB)
- **Frequency:** Every scheduled time (even if no gap)
- **Monthly:** ~180 API calls

**Recommendation:** Stick with manual unless you're actively trading all ORBs daily.

---

## Check Scheduler Status

```bash
# Test scheduler (won't actually update)
python trading_app/scheduled_update.py
```

Expected output:
```
[INFO] Scheduled updates are DISABLED
[INFO] Set AUTO_UPDATE_ENABLED=true in .env to enable
[INFO] Using manual updates only (saves API calls)
```

---

## Smart Update Strategy

**Best practice for saving API calls:**

1. **Before trading session:**
   - Go to Data Status tab
   - Click "UPDATE DATA NOW" once
   - This gets all data you need for the day

2. **During trading:**
   - Use Market Scanner with existing data
   - No need to update between ORBs

3. **Next day:**
   - Update once before first ORB
   - Repeat

**Result:** ~1 API call per day instead of 6!

---

## Summary

✅ **Current Setup:** Manual only (recommended)
- Update via app when needed
- Saves API calls
- Full control

⚠️ **Optional:** Scheduled auto-updates
- Enable in .env if needed
- Runs 30min before each ORB
- Higher API usage but more convenient

**Recommendation:** Keep manual updates. Only enable scheduler if you trade all 6 ORBs daily and want automation.
