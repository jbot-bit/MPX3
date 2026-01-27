# Quick Remote Access with Ngrok (Testing Only)

**Use this for quick testing. For production, use Streamlit Cloud (see DEPLOY_TO_CLOUD.md)**

## What is Ngrok?

Ngrok creates a temporary public URL that tunnels to your local PC.

## Setup (5 minutes):

1. **Download Ngrok:**
   - Go to: https://ngrok.com/download
   - Create free account
   - Download for Windows

2. **Install:**
   - Unzip to: `C:\ngrok\`
   - Add to PATH or copy to project folder

3. **Authenticate:**
   ```bash
   ngrok config add-authtoken YOUR_AUTHTOKEN_FROM_NGROK
   ```

4. **Start Streamlit on PC:**
   ```bash
   START_MOBILE_APP.bat
   ```

5. **In NEW terminal, start Ngrok:**
   ```bash
   ngrok http 8501
   ```

6. **Copy the HTTPS URL** (looks like: `https://abc123.ngrok.io`)

7. **Use this URL in your phone APK**

## Limitations:

⚠️ **Temporary** - URL changes every time you restart Ngrok
⚠️ **PC must be running** - Not truly mobile
⚠️ **Free tier** - Limited hours per month
⚠️ **APK update** - Need to rebuild APK each time URL changes

## For Production:

**Use Streamlit Cloud instead!** See: `DEPLOY_TO_CLOUD.md`

- ✅ Permanent URL
- ✅ No PC needed
- ✅ Unlimited usage
- ✅ Free for public repos
- ✅ Auto-updates from GitHub
