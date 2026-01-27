# 🔄 Update Workflow Reference

**How changes flow from your PC to your phone**

---

## 🎯 The Big Picture

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   Edit on   │  →    │     Git     │  →    │  Streamlit  │  →    │    Phone    │
│     PC      │       │    Push     │       │    Cloud    │       │     App     │
└─────────────┘       └─────────────┘       └─────────────┘       └─────────────┘
   Python code          5 seconds            90 seconds           Pull to refresh
```

**Total: ~2 minutes from edit to phone!**

---

## 📝 Standard Update Process

### **Step 1: Edit Code (PC)**

Edit any Python file:
```bash
trading_app/
├── app_mobile.py           ← Main app
├── strategy_engine.py      ← Strategy logic
├── setup_detector.py       ← Setup detection
├── data_loader.py          ← Data handling
├── ai_assistant.py         ← AI chat
└── config.py               ← Settings
```

**No rebuild needed after editing!**

### **Step 2: Commit and Push**

```bash
git add .
git commit -m "Description of change"
git push
```

### **Step 3: Auto-Deploy (Automatic)**

Streamlit Cloud:
- Detects GitHub push
- Pulls latest code
- Installs dependencies
- Restarts app
- **Takes: 90 seconds**

Watch progress: https://share.streamlit.io/

### **Step 4: See Changes on Phone**

- Open Trading Hub app
- Pull down to refresh (or reopen)
- ✅ Changes appear!

---

## 🚀 Example Workflows

### **Example 1: Fix a Bug**

```bash
# 1. Edit the buggy code
code trading_app/strategy_engine.py
# Fix calculation error on line 245

# 2. Test locally (optional)
python -m streamlit run trading_app/app_mobile.py
# Verify fix works

# 3. Deploy
git add trading_app/strategy_engine.py
git commit -m "Fix RR calculation for 0900 ORB"
git push

# 4. Wait 90 seconds
# Done! Bug fixed on phone
```

### **Example 2: Add New Feature**

```bash
# 1. Add feature code
code trading_app/setup_detector.py
# Add new setup detection logic

# Update config
code trading_app/config.py
# Add settings for new feature

# 2. Deploy
git add .
git commit -m "Add 1200 ORB detection"
git push

# 3. Wait 90 seconds
# Done! New feature live on phone
```

### **Example 3: Update UI**

```bash
# 1. Edit mobile UI
code trading_app/mobile_ui.py
# Change card layout

# 2. Deploy
git add trading_app/mobile_ui.py
git commit -m "Improve dashboard card layout"
git push

# 3. Wait 90 seconds
# 4. Refresh app on phone
# Done! New UI appears
```

### **Example 4: Change AI Prompts**

```bash
# 1. Edit AI assistant
code trading_app/ai_assistant.py
# Update system prompt

# 2. Deploy
git add trading_app/ai_assistant.py
git commit -m "Improve AI strategy explanations"
git push

# 3. Wait 90 seconds
# Done! Better AI responses on phone
```

---

## 🛠️ What About Database Changes?

### **Local Database (gold.db):**
- Lives on your PC only
- NOT deployed to cloud
- Cloud uses ProjectX API instead

### **If you update validated_setups:**

```bash
# 1. Update local database
python populate_validated_setups.py

# 2. Update config.py to match
code trading_app/config.py
# Update MGC_ORB_SIZE_FILTERS

# 3. Test sync
python test_app_sync.py
# Must pass!

# 4. Deploy config changes
git add trading_app/config.py
git commit -m "Update MGC filters after scan window fix"
git push

# 5. Cloud app uses updated config
# (Cloud gets data from ProjectX, not database)
```

**Remember:** Cloud mode doesn't use `gold.db` - it uses ProjectX API!

---

## 🔄 Deployment States

### **Development (Local PC):**
```bash
# Run locally for testing
python -m streamlit run trading_app/app_mobile.py

# Access: http://localhost:8501
# Uses: gold.db (local database)
```

### **Production (Cloud):**
```bash
# Push to GitHub
git push

# Access: https://yourapp.streamlit.app
# Uses: ProjectX API (live data)
```

### **Phone App:**
```
Before cloud deploy:
value="http://192.168.0.128:8501"  ← Local PC

After cloud deploy:
value="https://yourapp.streamlit.app"  ← Cloud
```

---

## ⚡ Quick Commands

### **Check Cloud Status:**
```bash
# View deployment logs
# Go to: https://share.streamlit.io/
# Click: Your App → Settings → Logs
```

### **Force Rebuild:**
```bash
# Streamlit Cloud dashboard
# Click: Menu → Reboot app
```

### **Rollback:**
```bash
# Git rollback
git revert HEAD
git push

# Cloud auto-deploys previous version
```

---

## 🎯 Update Frequency

**How often can you update?**

- ✅ As often as you want!
- ✅ Every push triggers deploy
- ✅ Multiple pushes queue up
- ✅ No cost per deploy
- ✅ No limits

**Typical usage:**
- **Multiple times per day** during active development
- **Once per week** for maintenance/tweaks
- **Instant** for critical bug fixes

---

## 📊 What Gets Deployed?

### **Deployed to Cloud:**
- ✅ All Python files in `trading_app/`
- ✅ `requirements.txt`
- ✅ `.streamlit/config.toml`
- ✅ Any other code files

### **NOT Deployed (Protected):**
- ❌ `.env` (API keys)
- ❌ `gold.db` (database)
- ❌ `*.log` (log files)
- ❌ `*.csv` (exports)
- ❌ `.streamlit/secrets.toml`

**Protected by `.gitignore`**

---

## 🔐 Managing Secrets

### **Local Development:**
```bash
# Uses: .env file
ANTHROPIC_API_KEY=sk-ant-...
PROJECTX_API_KEY=...
```

### **Cloud Production:**
```bash
# Uses: Streamlit Cloud Secrets
# Set at: https://share.streamlit.io/ → Settings → Secrets

ANTHROPIC_API_KEY = "sk-ant-..."
PROJECTX_API_KEY = "..."
```

**Never commit secrets to GitHub!**

---

## ✅ Update Checklist

Before each update:

- [ ] Code changes tested locally
- [ ] No syntax errors
- [ ] API keys NOT in code
- [ ] Ready to commit

After each push:

- [ ] Check deploy status (https://share.streamlit.io/)
- [ ] Wait for green "Running" status
- [ ] Test on phone
- [ ] Verify changes appear

---

## 🐛 Troubleshooting Updates

### **Changes don't appear:**
- Wait full 90 seconds for deploy
- Check deploy status (should be "Running")
- Hard refresh: Close app completely, reopen
- Check logs for errors

### **Deploy fails:**
- Check syntax errors in code
- Check requirements.txt for typos
- View logs: Settings → Logs
- Fix error, push again

### **App crashes after update:**
- Check logs for error message
- Quick fix: Git revert
  ```bash
  git revert HEAD
  git push
  ```
- App rolls back to previous version

---

## 🎉 Best Practices

1. **Test locally first**
   ```bash
   streamlit run trading_app/app_mobile.py
   ```

2. **Use descriptive commit messages**
   ```bash
   git commit -m "Add 1200 ORB strategy with 0.05 filter"
   ```

3. **Push frequently**
   - Small, focused changes
   - Easier to debug
   - Faster deploys

4. **Check logs after deploy**
   - Verify no errors
   - Confirm features work

5. **Keep .gitignore updated**
   - Never commit secrets
   - Never commit databases

---

**Remember: Push to GitHub → Auto-deploy → Phone refresh = DONE!**

No APK rebuilds, no manual deploys, no complexity!
