# Trading Hub Mobile APK - Build Guide

## ✅ APK Ready to Install

**Latest APK:** `app-debug.apk` (4.0 MB)
**Built:** January 17, 2026
**Configured for:** Cloud deployment (https://myprojectx-4uh3okcgzcdlcweor45kmq.streamlit.app)

---

## 📲 Install on Android Phone

### Step 1: Transfer APK to Phone
- **USB Cable:** Copy `app-debug.apk` directly
- **Cloud:** Upload to Google Drive/Dropbox, download on phone
- **Email:** Attach APK file, open on phone

### Step 2: Enable Installation from Unknown Sources
1. Settings → Security → Install Unknown Apps
2. Select your file manager/browser
3. Enable "Allow from this source"

### Step 3: Install
1. Open `app-debug.apk` on your phone
2. Tap "Install"
3. Tap "Open"
4. App launches with cloud URL pre-configured!

---

## 🚀 Using the App

When you open Trading Hub Mobile:

1. **Pre-configured URL:** `https://myprojectx-4uh3okcgzcdlcweor45kmq.streamlit.app`
2. Tap **"🚀 Connect to Server"**
3. App loads your full trading interface
4. Works from anywhere (no PC needed!)

**Local Network Option:**
- If running locally: Change URL to `http://192.168.0.XXX:8501`
- Make sure your PC and phone are on same Wi-Fi
- Run `START_MOBILE_APP.bat` on PC

---

## 🔨 Rebuild APK (If Needed)

### Requirements
- Java JDK 21 (✅ installed at `C:\Program Files\Eclipse Adoptium\jdk-21.0.9.10-hotspot`)
- Android SDK (install Android Studio)

### Quick Rebuild
```bash
cd android_app/android
./gradlew assembleDebug
```

APK outputs to: `android_app/android/app/build/outputs/apk/debug/app-debug.apk`

### Update Cloud URL
Edit `android_app/www/index.html` line 86:
```html
value="https://your-new-url.streamlit.app"
```

Then rebuild.

---

## 📁 Project Structure

```
android_app/
├── www/
│   └── index.html              # Launcher screen with cloud URL
├── android/
│   ├── app/
│   │   └── build/
│   │       └── outputs/
│   │           └── apk/
│   │               └── debug/
│   │                   └── app-debug.apk  # ← YOUR APK
│   └── gradlew.bat            # Build tool
├── capacitor.config.json       # App configuration
└── package.json

app-debug.apk                   # ← Latest APK (root directory)
```

---

## 🔍 Troubleshooting

### APK won't install
- Enable "Unknown Sources" in Settings → Security
- Make sure Android 7.0+ (API 24+)

### App can't connect
- Check Streamlit app is running: https://myprojectx-4uh3okcgzcdlcweor45kmq.streamlit.app
- For local: Verify PC IP address with `ipconfig`
- Ensure phone/PC on same Wi-Fi network

### Build fails with OneDrive errors
- Gradle cache conflicts with OneDrive syncing
- Workaround: Copy project to `C:\temp` and build from there
- Or use BUILD_APK_FIXED.bat which handles this automatically

---

## ✨ Features

**The APK provides:**
- ✅ Native Android app experience
- ✅ App icon on home screen
- ✅ Full-screen interface (no browser chrome)
- ✅ Cloud connectivity (works anywhere)
- ✅ Swipeable cards and mobile-optimized UI
- ✅ Remembers server URL
- ✅ Professional trading hub on mobile

---

**Ready to trade on mobile!** 🚀📱
