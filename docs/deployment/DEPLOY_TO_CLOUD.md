# 🚀 Deploy Trading Hub to Streamlit Cloud

**Goal:** Get your Trading Hub running in the cloud so your mobile app works from anywhere without needing your PC.

**Time:** 10-15 minutes

**Result:** Your app at `https://yourapp.streamlit.app` with seamless auto-updates

---

## ✅ Prerequisites

- [ ] GitHub account (free)
- [ ] Anthropic API key (for AI assistant)
- [ ] ProjectX API credentials (for live data)
- [ ] Your code committed to GitHub repo

---

## 📋 Step-by-Step Deployment

### **Step 1: Push Code to GitHub**

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Prepare Trading Hub for cloud deployment"

# Create GitHub repo (go to github.com/new)
# Then push:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

**Important files being deployed:**
- ✅ `trading_app/app_mobile.py` - Main app
- ✅ `trading_app/requirements.txt` - Dependencies
- ✅ `trading_app/.streamlit/config.toml` - Streamlit settings
- ✅ `trading_app/cloud_mode.py` - Cloud detection
- ❌ `.env` - Not deployed (protected by .gitignore)
- ❌ `gold.db` - Not deployed (protected by .gitignore)

---

### **Step 2: Deploy to Streamlit Cloud**

1. **Go to:** https://share.streamlit.io/

2. **Sign in** with your GitHub account

3. **Click "New app"**

4. **Configure deployment:**
   - **Repository:** Select your repo
   - **Branch:** `main`
   - **Main file path:** `trading_app/app_mobile.py`
   - **App URL:** Choose a name (e.g., `trading-hub`)

5. **Click "Deploy"**

6. **Wait 2-3 minutes** for first deployment

---

### **Step 3: Add API Keys to Secrets**

Your app is deployed but needs API keys!

1. **On Streamlit Cloud**, click **"⚙️ Settings"** (bottom right)

2. **Click "Secrets"** tab

3. **Open:** `trading_app/.streamlit/secrets.toml.template` on your PC

4. **Copy the REQUIRED section** and update with your real keys:

```toml
# Copy this to Streamlit Cloud Secrets:

ANTHROPIC_API_KEY = "sk-ant-api03-YOUR_REAL_KEY_HERE"

PROJECTX_USERNAME = "your_actual_username"
PROJECTX_API_KEY = "your_actual_api_key"
PROJECTX_BASE_URL = "https://api.topstepx.com"
PROJECTX_LIVE = "false"

TZ_LOCAL = "Australia/Brisbane"
SYMBOL = "MGC"
DUCKDB_PATH = "trading_app.db"
```

5. **Paste into Streamlit Cloud secrets editor**

6. **Click "Save"**

7. **App auto-restarts** (takes 30 seconds)

---

### **Step 4: Test Your Cloud App**

1. **Open:** `https://yourapp.streamlit.app` (your app URL)

2. **Check:**
   - ✅ App loads
   - ✅ No database errors
   - ✅ AI chat works
   - ✅ ProjectX live data loads

3. **Try on your phone browser:**
   - Open the URL on your phone
   - Should work perfectly
   - Test swipe navigation

---

### **Step 5: Update Your Android APK**

Now update your APK to point to the cloud URL instead of local PC:

1. **Edit:** `android_app/www/index.html`

2. **Find line 86:**
   ```html
   value="http://192.168.0.128:8501"
   ```

3. **Replace with your cloud URL:**
   ```html
   value="https://yourapp.streamlit.app"
   ```

4. **Rebuild APK:**
   ```bash
   BUILD_APK_FIXED.bat
   ```

5. **Reinstall APK on your phone**

6. **Done!** App now works from anywhere (no PC needed)

---

## 🔄 How Updates Work (SEAMLESS!)

### **To Update Your App:**

1. **Edit Python code** on your PC:
   ```
   trading_app/
   ├── app_mobile.py         ← Edit this
   ├── strategy_engine.py    ← Or this
   ├── setup_detector.py     ← Or this
   └── ...
   ```

2. **Commit and push to GitHub:**
   ```bash
   git add .
   git commit -m "Add new strategy filter"
   git push
   ```

3. **Streamlit Cloud auto-deploys** (takes 1-2 minutes)

4. **Phone app sees changes immediately:**
   - Just pull down to refresh
   - Or reopen the app
   - No APK rebuild needed!

### **When Updates Appear:**

```
Code change → Git push → Cloud auto-deploy → Phone refresh → DONE
   10 sec        5 sec         90 sec           instant
```

**Total time: ~2 minutes from code to phone!**

---

## 📱 App Architecture (Cloud Mode)

### **Before (Local):**
```
Phone APK → PC Streamlit → gold.db (local database)
```
- ❌ PC must be running
- ❌ Only works on same Wi-Fi
- ✅ Fast local database

### **After (Cloud):**
```
Phone APK → Streamlit Cloud → ProjectX API
```
- ✅ Works from anywhere
- ✅ No PC needed
- ✅ Always online
- ✅ Auto-updates from GitHub

---

## 🔧 Managing Your Cloud App

### **View Logs:**
1. Go to: https://share.streamlit.io/
2. Open your app
3. Click "⚙️ Settings" → "Logs"
4. See real-time logs

### **Restart App:**
1. Go to: https://share.streamlit.io/
2. Open your app
3. Click "⋮ Menu" → "Reboot app"

### **Update Secrets:**
1. Go to: https://share.streamlit.io/
2. Open your app
3. Click "⚙️ Settings" → "Secrets"
4. Edit and save
5. App auto-restarts

### **Delete App:**
1. Go to: https://share.streamlit.io/
2. Open your app
3. Click "⋮ Menu" → "Delete app"

---

## 🐛 Troubleshooting

### **App won't deploy:**
- ✅ Check `requirements.txt` has all dependencies
- ✅ Check `app_mobile.py` path is correct
- ✅ Check logs for Python errors

### **"Module not found" error:**
- ✅ Add missing package to `requirements.txt`
- ✅ Push to GitHub
- ✅ Streamlit Cloud will auto-redeploy

### **"Database not found" warning:**
- ✅ Expected in cloud mode!
- ✅ App uses ProjectX API instead
- ✅ If you see data, it's working correctly

### **AI chat not working:**
- ✅ Check `ANTHROPIC_API_KEY` in secrets
- ✅ Check API key is valid at https://console.anthropic.com/
- ✅ Restart app after adding key

### **No live data:**
- ✅ Check `PROJECTX_API_KEY` in secrets
- ✅ Check `PROJECTX_USERNAME` is correct
- ✅ Try setting `PROJECTX_LIVE = "false"` for historical data first

---

## 💰 Costs

### **Streamlit Cloud:**
- ✅ FREE for public repos
- ✅ Unlimited apps
- ✅ Automatic SSL (HTTPS)
- ✅ Auto-scaling

### **APIs:**
- **Anthropic (AI chat):** Pay per message (~$0.01 per conversation)
- **ProjectX (data):** Your existing subscription
- **Databento (optional):** Only if backfilling historical data

**Monthly cost: ~$5-10 for typical use**

---

## 🎯 What You Get

After deployment:

✅ **Mobile app works from anywhere** (coffee shop, work, home)
✅ **No PC needed** (server runs in cloud)
✅ **Auto-updates** (push code → app updates in 2 min)
✅ **No APK rebuilds** for code changes
✅ **Always online** (never down)
✅ **Professional URL** (share with others)
✅ **Free hosting** (Streamlit Cloud)
✅ **Automatic SSL** (HTTPS security)

---

## 🚀 Next Steps

After cloud deployment:

1. **Test on phone** - Open cloud URL, verify everything works
2. **Update APK** - Point to cloud URL instead of localhost
3. **Rebuild APK once** - Last time rebuilding!
4. **From now on** - Just push code, it auto-deploys
5. **Share your app** - Send URL to friends/colleagues

---

## 📖 Example Update Workflow

**Scenario:** You want to add a new ORB time (12:00)

```bash
# 1. Edit code on PC
code trading_app/config.py
# Add 12:00 ORB configuration

# 2. Update database
python populate_validated_setups.py
# (Only affects local - cloud uses ProjectX)

# 3. Commit and push
git add .
git commit -m "Add 12:00 ORB strategy"
git push

# 4. Wait 90 seconds for auto-deploy
# (Watch at https://share.streamlit.io/)

# 5. On phone:
# Open Trading Hub app
# Pull down to refresh
# ✅ New 12:00 ORB appears!
```

**Total time: 2 minutes**
**APK rebuilds: 0**
**User interruption: 0**

---

## ✅ Success Checklist

Before considering deployment complete:

- [ ] Code pushed to GitHub
- [ ] App deployed to Streamlit Cloud
- [ ] API keys added to secrets
- [ ] Cloud app loads without errors
- [ ] AI chat works
- [ ] Live data appears
- [ ] APK updated with cloud URL
- [ ] APK rebuilt and installed
- [ ] Phone app works from anywhere
- [ ] Tested: push code → auto-deploy → phone refresh

**Done! You now have a professional cloud-deployed trading app with seamless updates! 🎉**

---

## 🔗 Important Links

- **Your Cloud App:** `https://yourapp.streamlit.app` (your custom URL)
- **Streamlit Cloud Dashboard:** https://share.streamlit.io/
- **Anthropic Console:** https://console.anthropic.com/
- **ProjectX API:** https://api.topstepx.com/
- **GitHub Repo:** https://github.com/YOUR_USERNAME/YOUR_REPO

---

**Need help? Check logs at Streamlit Cloud → Settings → Logs**
