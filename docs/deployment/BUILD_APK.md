# How to Rebuild APK with Updated URL

## Current Status
- ✅ Source code updated: `android_app/www/index.html`
- ✅ Default URL changed to: `https://myprojectx.streamlit.app`
- ✅ Committed to GitHub (commit `364ff79`)
- ⚠️ Automated build blocked by Capacitor dependencies

## Quick Solution (Recommended)

### Option 1: Manual URL Entry (5 seconds)
1. Install existing `app-debug.apk` on your device
2. When app launches, change URL to: `https://myprojectx.streamlit.app`
3. Click "🚀 Connect to Server"
4. **Done!** URL is saved forever (localStorage)

### Option 2: Android Studio Build (2 minutes)
1. Open Android Studio
2. Open project: `C:\Users\sydne\OneDrive\myprojectx\android_app\android\`
3. Click **Build → Build Bundle(s) / APK(s) → Build APK(s)**
4. Wait for build to complete
5. APK location: `android\app\build\outputs\apk\debug\app-debug.apk`
6. New APK will have `myprojectx.streamlit.app` baked in

### Option 3: Fix Capacitor and CLI Build
```bash
cd android_app

# Re-add Android platform
npx cap add android

# Sync everything
npx cap sync android

# Build APK
cd android
./gradlew assembleDebug --no-daemon

# APK location
ls app/build/outputs/apk/debug/app-debug.apk
```

## Why Automated Build Failed

**Error**: Missing Capacitor Cordova plugin dependencies
```
Could not read script 'capacitor-cordova-android-plugins/cordova.variables.gradle'
```

**Cause**: Capacitor platform needs to be re-initialized

**Solution**: Use Android Studio (Option 2) or fix Capacitor (Option 3)

## Current Files

### Updated Source
- `android_app/www/index.html` - Updated with correct URL
- Pushed to GitHub mobile branch

### Available APKs
- `app-debug.apk` - Original APK (Jan 17, 4.0 MB)
- Works perfectly with manual URL entry

## Verify APK Has Correct URL

To check if APK has the updated URL:

```bash
# Extract APK
unzip -q app-debug.apk -d extracted

# Check URL
grep "myprojectx.streamlit.app" extracted/assets/public/index.html
```

If this shows the old URL, the APK needs rebuilding via Option 2 or 3.

## Recommendation

**Use Option 1** (manual URL entry). It's:
- ✅ Fastest (5 seconds)
- ✅ Works immediately
- ✅ No build tools needed
- ✅ URL saved permanently

The only difference is a 5-second one-time setup vs having it pre-configured.
