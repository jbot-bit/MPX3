"""
Quick script to start ngrok and display the public URL
"""
import subprocess
import time
import json
import requests

print("=" * 50)
print("STARTING NGROK TUNNEL")
print("=" * 50)
print()

# Start ngrok in background
print("Starting ngrok on port 8501...")
proc = subprocess.Popen(
    ["ngrok", "http", "8501", "--log", "stdout"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Wait for ngrok to start
time.sleep(3)

try:
    # Get the public URL from ngrok API
    response = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=5)
    tunnels = response.json()

    if tunnels.get("tunnels"):
        public_url = tunnels["tunnels"][0]["public_url"]
        print()
        print("=" * 50)
        print("SUCCESS! Your public URL is:")
        print()
        print(f"  {public_url}")
        print()
        print("=" * 50)
        print()
        print("Open this URL on your phone to access the app!")
        print()
        print("Press Ctrl+C to stop ngrok when you're done.")
        print()

        # Keep running
        proc.wait()
    else:
        print("ERROR: Could not get ngrok URL")
        print("Try running manually: ngrok http 8501")

except Exception as e:
    print(f"ERROR: {e}")
    print()
    print("Ngrok is running, but couldn't auto-fetch URL.")
    print("Open http://localhost:4040 in your browser to see the URL")
    print("Or run manually: ngrok http 8501")
    proc.wait()
