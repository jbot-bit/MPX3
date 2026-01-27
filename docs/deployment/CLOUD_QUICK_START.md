# ⚡ Cloud Deployment - Quick Reference

**Fast guide for deploying to Streamlit Cloud with seamless updates**

---

## 🚀 Initial Deploy (Do Once)

### 1. Push to GitHub
```bash
git add .
git commit -m "Deploy to cloud"
git push origin main
```

### 2. Deploy on Streamlit Cloud
- Go to: https://share.streamlit.io/
- Click "New app"
- Select: `trading_app/app_mobile.py`
- Deploy!

### 3. Add API Keys
- Click "⚙️ Settings" → "Secrets"
- Copy from: `trading_app/.streamlit/secrets.toml.template`
- Paste your real keys:
  ```toml
  ANTHROPIC_API_KEY = "sk-ant-..."
  PROJECTX_USERNAME = "..."
  PROJECTX_API_KEY = "..."
  PROJECTX_BASE_URL = "https://api.topstepx.com"
  PROJECTX_LIVE = "false"
  TZ_LOCAL = "Australia/Brisbane"
  SYMBOL = "MGC"
  DUCKDB_PATH = "trading_app.db"
  ```
- Save → App restarts

### 4. Update APK (Last Time!)
```bash
# Edit: android_app/www/index.html
# Line 86: value="https://yourapp.streamlit.app"

BUILD_APK_FIXED.bat
# Install new APK on phone
```

**Done! Now your app:**
- ✅ Works from anywhere
- ✅ No PC needed
- ✅ Auto-updates from GitHub

---

## 🔄 Updating Your App (Every Time)

### Normal Code Updates:

```bash
# 1. Edit Python code
code trading_app/strategy_engine.py

# 2. Commit and push
git add .
git commit -m "Update strategy logic"
git push

# 3. Wait 90 seconds for auto-deploy
# (That's it!)

# 4. On phone: Pull down to refresh
# ✅ Changes appear instantly!
```

**No APK rebuild needed!**

---

## 📱 Two Modes

### **Local Mode** (Current default APK):
```
Phone → PC (http://192.168.0.128:8501)
```
- Works only on same Wi-Fi
- Requires PC running
- Fast local database

**Use for:** Development, testing

### **Cloud Mode** (After deploy):
```
Phone → Cloud (https://yourapp.streamlit.app)
```
- Works from anywhere
- No PC needed
- Uses ProjectX API

**Use for:** Daily trading, mobile access

---

## 🎯 Update Workflow

```
Edit Code → Git Push → Cloud Deploy → Phone Refresh
  10 sec      5 sec        90 sec         instant

Total: 2 minutes from code to phone!
```

---

## 🔧 Common Tasks

### **View Logs:**
https://share.streamlit.io/ → Your App → Settings → Logs

### **Update Secrets:**
https://share.streamlit.io/ → Your App → Settings → Secrets

### **Restart App:**
https://share.streamlit.io/ → Your App → Menu → Reboot

### **Check Deployment:**
https://share.streamlit.io/ → Your App → See deploy status

---

## 💡 What Updates Require

### **NO APK Rebuild:**
- ✅ Python code changes
- ✅ Strategy logic updates
- ✅ UI changes
- ✅ Bug fixes
- ✅ New features
- ✅ Database queries
- ✅ API calls

**Just push to GitHub → auto-deploys!**

### **APK Rebuild Required:**
- ❌ Change app icon
- ❌ Change app name
- ❌ Change default server URL
- ❌ Add native Android features

**Very rare!**

---

## 📊 Example: Adding New Strategy

```bash
# Edit the strategy
code trading_app/strategy_engine.py
# Add new 12:00 ORB logic

# Update config
code trading_app/config.py
# Add 12:00 settings

# Commit and push
git add .
git commit -m "Add 12:00 ORB strategy"
git push

# Wait 90 seconds...
# ✅ Done! Open app on phone and see new strategy
```

No APK, no PC, no fuss!

---

## 🔗 Your URLs

After deployment, bookmark these:

- **Cloud App:** https://yourapp.streamlit.app
- **Streamlit Dashboard:** https://share.streamlit.io/
- **GitHub Repo:** https://github.com/YOUR_USERNAME/YOUR_REPO
- **Anthropic Console:** https://console.anthropic.com/

---

## ✅ Deployment Checklist

- [ ] Code on GitHub
- [ ] Deployed to Streamlit Cloud
- [ ] API keys in secrets
- [ ] Cloud app loads correctly
- [ ] APK updated with cloud URL
- [ ] APK rebuilt and installed
- [ ] Phone works from anywhere
- [ ] Tested: push code → phone updates

---

**Need detailed instructions? See: `DEPLOY_TO_CLOUD.md`**
