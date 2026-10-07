import requests
import json
import csv
import os
import time
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError('Missing BOT_TOKEN or CHAT_ID in .env file')

BASE_DIR = '/home/tom/trading/mtj'
TRADE_POLL_INTERVAL = 30  # Check trades every 30 seconds
COMMAND_CHECK_INTERVAL = 2  # Check Telegram commands every 2 seconds
LAST_UPDATE_ID = 0

STRATEGIES = {
    'Superman': '133',
    'Boat': '46',
    'Canoe': '267'
}

logging.basicConfig(
    filename=f'{BASE_DIR}/monitor.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
console = logging.StreamHandler()
logging.getLogger().addHandler(console)

def get_dynamic_url(trader_id):
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    base_url = f'https://copy-trading-adm.fxprimus.com/api/trading/{trader_id}/positions/public'
    params = {
        'scope': 'Any', '$top': '25',
        '$filter': f'openTime ge 2024-01-01T00:00:00.000Z and openTime le {now}',
        '$orderby': 'openTime desc', '$count': 'true', 'widget_key': 'social-ratings'
    }
    query = '&'.join([f'{k}={v}' for k, v in params.items()])
    return f'{base_url}?{query}'

def get_file_paths(strategy_name):
    safe_name = strategy_name.lower()
    return {'csv': f'{BASE_DIR}/{safe_name}_live_trades.csv', 'state': f'{BASE_DIR}/{safe_name}_last_seen.txt'}

def load_last_seen(state_file):
    if os.path.exists(state_file):
        with open(state_file, 'r') as f: return f.read().strip()
    return '2020-01-01T00:00:00.000Z'

def save_last_seen(state_file, open_time):
    with open(state_file, 'w') as f: f.write(open_time)

def save_csv_newest_first(csv_file, new_trades):
    fieldnames = ['symbol', 'direction', 'volume', 'openTime', 'openPrice', 'closePrice', 'closeTime', 'profit', 'profitPoints', 'hold_duration_mins']
    existing = []
    if os.path.exists(csv_file):
        with open(csv_file, 'r', newline='') as f: existing = list(csv.DictReader(f))
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(new_trades + existing)

def send_telegram_message(text, parse_mode='Markdown'):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': CHAT_ID, 'text': text, 'parse_mode': parse_mode}
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code != 200:
            logging.error(f'Telegram send failed: {response.text}')
    except Exception as e:
        logging.error(f'Telegram send exception: {e}')

def get_last_log_lines(n=10):
    log_file = f'{BASE_DIR}/monitor.log'
    if not os.path.exists(log_file): return 'No log file found.'
    with open(log_file, 'r') as f: lines = f.readlines()
    return ''.join(lines[-n:])

def check_telegram_commands():
    global LAST_UPDATE_ID
    # Reduced timeout to 0.5s for instant response when no new messages exist
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={LAST_UPDATE_ID + 1}&timeout=0.5'
    try:
        response = requests.get(url, timeout=1)
        data = response.json()
        if data.get('ok'):
            for update in data.get('result', []):
                LAST_UPDATE_ID = update['update_id']
                message = update.get('message', {})
                if str(message.get('chat', {}).get('id')) == str(CHAT_ID):
                    text = message.get('text', '').strip().lower()
                    logging.info(f'Received Telegram command: {text}')
                    if text == '/status':
                        msg = f"Monitor Status\nStrategies: {', '.join(STRATEGIES.keys())}\nLast Check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        send_telegram_message(msg)
                    elif text in ['/log', '/logs']:
                        logs = get_last_log_lines(10)
                        send_telegram_message(f"Recent Logs\n```\n{logs}\n```")
    except Exception as e:
        # Silently ignore minor network hiccups to keep the loop running smoothly
        pass

def main():
    logging.info('Starting Multi-Strategy Real-Time Monitor...')
    last_seen_tracker = {s: load_last_seen(get_file_paths(s)['state']) for s in STRATEGIES}
    
    last_trade_check = 0

    while True:
        # 1. Check for Telegram commands frequently (low latency: ~1 second)
        check_telegram_commands()
        
        # 2. Only fetch trading data when the trade interval has passed
        current_time = time.time()
        if current_time - last_trade_check >= TRADE_POLL_INTERVAL:
            logging.info('Running trade check cycle...')
            for strategy, trader_id in STRATEGIES.items():
                paths = get_file_paths(strategy)
                last_seen = last_seen_tracker[strategy]

                try:
                    response = requests.get(get_dynamic_url(trader_id), timeout=15)
                    response.raise_for_status()
                    items = response.json().get('items', [])
                    new_trades = [item for item in items if item['openTime'] > last_seen]

                    if new_trades:
                        new_trades.sort(key=lambda x: x['openTime'], reverse=True)
                        logging.info(f'[{strategy}] Found {len(new_trades)} new trade(s)!')

                        last_seen_tracker[strategy] = new_trades[0]['openTime']
                        save_last_seen(paths['state'], last_seen_tracker[strategy])
                        save_csv_newest_first(paths['csv'], new_trades)

                        for trade in new_trades:
                            msg = (f"New {strategy} Trade!\n"
                                   f"Symbol: {trade['symbol']} | {trade['direction']}\n"
                                   f"Vol: {trade['volume']}\n"
                                   f"Open: {trade['openPrice']} | Close: {trade['closePrice']}\n"
                                   f"Profit: ${trade['profit']} ({trade['profitPoints']} pts)\n"
                                   f"Time: {trade['openTime'].replace('T', ' ')} to {trade['closeTime'].replace('T', ' ')}")
                            send_telegram_message(msg)
                except Exception as e:
                    logging.error(f'[{strategy}] Error: {e}')
                
                time.sleep(1) # 1 second pause between strategies to be polite to the API
            
            last_trade_check = current_time

        # 3. Sleep briefly before the next command check
        time.sleep(COMMAND_CHECK_INTERVAL)

if __name__ == '__main__':
    main()
