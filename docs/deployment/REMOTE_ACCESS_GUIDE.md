# Remote Access Setup - URGENT GUIDE

## FASTEST METHOD (2 minutes)

### Step 1: Install ngrok (if not installed)

**Windows:**
```bash
winget install ngrok
```

OR download from: https://ngrok.com/download

### Step 2: Run the automated script

**Double-click:** `start_remote_app.bat`

OR run in Command Prompt:
```bash
cd C:\Users\sydne\OneDrive\myprojectx
start_remote_app.bat
```

### Step 3: Get your public URL

ngrok will display a URL like:
```
Forwarding    https://1234-56-78-90.ngrok-free.app -> http://localhost:8501
```

Copy the `https://...ngrok-free.app` URL

### Step 4: Access on your phone

Open the URL in your phone's browser. Done!

---

## MANUAL METHOD (if script doesn't work)

### Terminal 1: Start Streamlit
```bash
cd C:\Users\sydne\OneDrive\myprojectx
streamlit run app_trading_hub.py --server.port 8501
```

### Terminal 2: Start ngrok
```bash
ngrok http 8501
```

Copy the public URL from ngrok output and open on your phone.

---

## IMPORTANT NOTES

1. **Free ngrok** URLs expire after ~2 hours. Just restart ngrok to get a new URL.

2. **Security**: The URL is public but hard to guess. For production, use ngrok auth:
   ```bash
   ngrok http 8501 --basic-auth="username:password"
   ```

3. **Keep terminals open**: Don't close the Command Prompt windows while using the app remotely.

4. **Network**: Your computer must stay on and connected to internet.

---

## ALTERNATIVE: Streamlit Community Cloud (Free, Permanent)

If you need a permanent solution:

1. Push code to GitHub
2. Go to https://share.streamlit.io
3. Deploy your app (free)
4. Get a permanent URL like: https://yourapp.streamlit.app

---

## TROUBLESHOOTING

**"ngrok not found"**
- Install: `winget install ngrok`
- OR download manually from ngrok.com

**"Port 8501 already in use"**
- Kill existing Streamlit: `taskkill /F /IM streamlit.exe`
- Try again

**App not loading on phone**
- Check firewall isn't blocking ngrok
- Try restarting ngrok for a new URL
- Ensure computer stays awake

---

**URGENT TIP:** Save the ngrok URL to your phone's home screen for quick access!
