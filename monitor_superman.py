import requests
import json
import csv
import os
import time
from datetime import datetime, timezone

# ================= CONFIGURATION =================
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
CHAT_ID = "YOUR_TELEGRAM_CHAT_ID_HERE"

# Hardcoded absolute paths for the project directory
BASE_DIR = "/home/tom/trading/mtj"
CSV_FILE = f"{BASE_DIR}/superman_live_trades.csv"
STATE_FILE = f"{BASE_DIR}/superman_last_seen.txt"
POLL_INTERVAL = 30  # Seconds between checks
TRADER_ID = "133"
# =================================================

def get_dynamic_url():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    base_url = f"https://copy-trading-adm.fxprimus.com/api/trading/{TRADER_ID}/positions/public"
    params = {
        "scope": "Any",
        "$top": "25",
        "$filter": f"openTime ge 2024-01-01T00:00:00.000Z and openTime le {now}",
        "$orderby": "openTime desc",
        "$count": "true",
        "widget_key": "social-ratings"
    }
    query = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{base_url}?{query}"

def load_last_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return f.read().strip()
    return "2020-01-01T00:00:00.000Z"

def save_last_seen(open_time):
    with open(STATE_FILE, 'w') as f:
        f.write(open_time)

def save_csv_newest_first(new_trades):
    fieldnames = ['symbol', 'direction', 'volume', 'openTime', 'openPrice', 'closePrice', 'closeTime', 'profit', 'profitPoints', 'hold_duration_mins']
    
    existing_trades = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'r', newline='') as f:
            reader = csv.DictReader(f)
            existing_trades = list(reader)
    
    all_trades = new_trades + existing_trades
    
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_trades)

def send_telegram_alert(trade):
    # Updated message with Open and Close Prices
    msg = (
        f" *New Superman Trade Detected!*\n\n"
        f"📈 Symbol: `{trade['symbol']}`\n"
        f"➡️ Direction: *{trade['direction']}*\n"
        f"📦 Volume: `{trade['volume']}`\n"
        f"💲 Open Price: `{trade['openPrice']}`\n"
        f"💲 Close Price: `{trade['closePrice']}`\n"
        f" Profit: *${trade['profit']}* ({trade['profitPoints']} pts)\n"
        f"⏱️ Open: `{trade['openTime'].replace('T', ' ').replace('Z', '')}`\n"
        f"⏱️ Close: `{trade['closeTime'].replace('T', ' ').replace('Z', '')}`"
    )
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Telegram alert sent for trade at {trade['openTime']}")
        else:
            print(f"⚠️ Telegram API Error: {response.text}")
    except Exception as e:
        print(f"❌ Failed to send Telegram alert: {e}")

def main():
    print("🚀 Starting Superman Real-Time Monitor...")
    last_seen = load_last_seen()
    print(f"📌 Resuming from last seen: {last_seen}")
    
    while True:
        try:
            url = get_dynamic_url()
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            items = data.get("items", [])
            new_trades = []
            
            for item in items:
                if item["openTime"] > last_seen:
                    new_trades.append(item)
            
            if new_trades:
                new_trades.sort(key=lambda x: x["openTime"], reverse=True)
                print(f"🔔 Found {len(new_trades)} new trade(s)!")
                
                last_seen = new_trades[0]["openTime"]
                save_last_seen(last_seen)
                
                save_csv_newest_first(new_trades)
                print(f"💾 Appended to {CSV_FILE}")
                
                for trade in new_trades:
                    send_telegram_alert(trade)
            else:
                print(f"⏳ No new trades. Checking again in {POLL_INTERVAL}s...")
                
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Network error: {e}. Retrying in {POLL_INTERVAL}s...")
        except json.JSONDecodeError:
            print("⚠️ Failed to parse JSON response. Retrying...")
            
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
