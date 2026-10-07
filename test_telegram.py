   import requests
   import os
   from dotenv import load_dotenv

   load_dotenv('/home/tom/trading/mtj/.env')
   token = os.getenv('BOT_TOKEN')
   chat_id = os.getenv('CHAT_ID')

   print(f"Token starts with: {token[:10] if token else 'MISSING'}...")
   print(f"Chat ID: {chat_id if chat_id else 'MISSING'}")

   url = f"https://api.telegram.org/bot{token}/getUpdates"
   print("Connecting to Telegram... (will timeout in 5 seconds)")
   
   try:
       r = requests.get(url, timeout=5)
       print(f"Status Code: {r.status_code}")
       print(f"Response: {r.text}")
   except Exception as e:
       print(f"CONNECTION FAILED: {e}")
