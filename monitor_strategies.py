import os, requests, json, csv, time, logging, base64, urllib.parse
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
TZ_STR = os.getenv('TIMEZONE', 'Asia/Singapore')
try: TARGET_TZ = ZoneInfo(TZ_STR)
except ZoneInfoNotFoundError: TARGET_TZ = timezone(timedelta(hours=8))

BASE_DIR = '/home/tom/trading/mtj'
CONFIG_FILE = f'{BASE_DIR}/config.json'
TRADE_POLL_INTERVAL = 30
COMMAND_CHECK_INTERVAL = 2
LAST_UPDATE_ID = 0

class TzFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=TARGET_TZ)
        return dt.strftime("%Y-%m-%d %H:%M:%S %Z")

formatter = TzFormatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler(f'{BASE_DIR}/monitor.log')
file_handler.setFormatter(formatter)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        default = {"Superman": {"id": "133", "active": True}, "Boat": {"id": "46", "active": True}, "Canoe": {"id": "267", "active": True}, "Captain": {"id": "277", "active": True}}
        save_config(default)
        return default
    with open(CONFIG_FILE, 'r') as f: return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w') as f: json.dump(config, f, indent=2)

def resolve_trader_id(input_val):
    input_val = input_val.strip()
    if input_val.startswith('http'):
        try:
            parsed = urllib.parse.urlparse(input_val)
            params = urllib.parse.parse_qs(parsed.query)
            if 'preview' in params:
                decoded = base64.b64decode(params['preview'][0]).decode('utf-8')
                for part in decoded.split('&'):
                    if part.startswith('a='):
                        return part.split('=')[1], parsed.path.split('/')[-1]
            widget_id = parsed.path.split('/')[-1]
            if widget_id.isdigit(): return widget_id, widget_id
        except Exception: pass
    if input_val.isdigit(): return input_val, input_val
    return None, None

def get_dynamic_url(trader_id, skip=0, top=100):
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    base = f'https://copy-trading-adm.fxprimus.com/api/trading/{trader_id}/positions/public'
    params = {'scope': 'Any', '$top': str(top), '$skip': str(skip), '$filter': f'openTime ge 2024-01-01T00:00:00.000Z and openTime le {now}', '$orderby': 'openTime desc', '$count': 'true', 'widget_key': 'social-ratings'}
    return f"{base}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"

def fetch_all_trades(trader_id, last_seen):
    all_trades, skip, max_limit = [], 0, 500
    while skip < max_limit:
        try:
            items = requests.get(get_dynamic_url(trader_id, skip=skip), timeout=15).json().get('items', [])
        except: break
        if not items: break
        reached_old = False
        for item in items:
            ot = item['openTime'].replace('Z', '').split('.')[0]
            ls = last_seen.replace('Z', '').split('.')[0]
            if ot > ls: all_trades.append(item)
            else: reached_old = True; break
        if reached_old or len(items) < 100: break
        skip += 100
    return all_trades

def save_csv_newest_first(csv_file, new_trades):
    fields = ['symbol', 'direction', 'volume', 'openTime', 'openPrice', 'closePrice', 'closeTime', 'profit', 'profitPoints', 'hold_duration_mins']
    existing = list(csv.DictReader(open(csv_file, 'r', newline=''))) if os.path.exists(csv_file) else []
    processed = []
    for t in new_trades:
        row = {k: t.get(k, '') for k in fields[:-1]}
        try:
            ot = datetime.fromisoformat(t['openTime'].replace('Z', '+00:00'))
            ct = datetime.fromisoformat(t['closeTime'].replace('Z', '+00:00')) if t.get('closeTime') else None
            row['hold_duration_mins'] = round((ct - ot).total_seconds() / 60, 2) if ct else ''
        except: row['hold_duration_mins'] = ''
        processed.append(row)
    with open(csv_file, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(processed + existing)

def calculate_floating_time(ot_str, ct_str):
    try:
        is_open = not ct_str or str(ct_str).lower() == "null"
        ct = datetime.now(timezone.utc) if is_open else datetime.fromisoformat(str(ct_str).replace('Z', '+00:00'))
        ot = datetime.fromisoformat(ot_str.replace('Z', '+00:00'))
        ts = int((ct - ot).total_seconds())
        y, r = divmod(ts, 31536000); mo, r = divmod(r, 2592000); w, r = divmod(r, 604800)
        d, r = divmod(r, 86400); h, r = divmod(r, 3600); mi, s = divmod(r, 60)
        parts = []
        if y: parts.append(f"{y}y")
        if mo: parts.append(f"{mo}mo")
        if w: parts.append(f"{w}w")
        if d: parts.append(f"{d}d")
        if h: parts.append(f"{h}h")
        if mi: parts.append(f"{mi}mi")
        if s or not parts: parts.append(f"{s}s")
        return " ".join(parts) + (" (Open)" if is_open else "")
    except: return "N/A"

def format_trade_time(utc_str):
    if not utc_str: return "N/A"
    try:
        clean = str(utc_str).replace('Z', '+00:00')
        if '.' in clean: clean = clean.split('.')[0] + '+00:00'
        return datetime.fromisoformat(clean).astimezone(TARGET_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
    except: return str(utc_str)

def send_telegram_message(text, parse_mode=None):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': CHAT_ID, 'text': text}
    if parse_mode: payload['parse_mode'] = parse_mode
    try:
        r = requests.post(url, json=payload, timeout=5)
        if r.status_code != 200: logger.error(f'TG send failed: {r.text}')
    except Exception as e: logger.error(f'TG send exception: {e}')

def check_telegram_commands(config):
    global LAST_UPDATE_ID, TARGET_TZ, TZ_STR
    try:
        data = requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={LAST_UPDATE_ID + 1}&timeout=0.5', timeout=5).json()
        if data.get('ok'):
            for update in data.get('result', []):
                LAST_UPDATE_ID = update['update_id']
                msg = update.get('message', {})
                if str(msg.get('chat', {}).get('id')) == str(CHAT_ID):
                    text = msg.get('text', '').strip()
                    tl = text.lower()
                    logger.info(f'Received TG command: {text}')
                    
                    if tl == '/status':
                        now_tz = datetime.now(TARGET_TZ).strftime('%Y-%m-%d %H:%M:%S %Z')
                        send_telegram_message(f"Monitor Status\nStrategies: {', '.join(config.keys())}\nTimezone: {TZ_STR}\nLast Check: {now_tz}", parse_mode=None)
                    elif tl in ['/log', '/logs']:
                        logs = ''.join(open(f'{BASE_DIR}/monitor.log', 'r').readlines()[-10:]) if os.path.exists(f'{BASE_DIR}/monitor.log') else 'No log file.'
                        send_telegram_message(f"Recent Logs\n{logs}", parse_mode=None)
                    elif tl == '/settz':
                        common_tz = "Common Acceptable Timezones:\n• UTC\n• Asia/Singapore (SGT)\n• Asia/Kuala_Lumpur (MYT)\n• Asia/Tokyo (JST)\n• Asia/Shanghai (CST)\n• Asia/Dubai (GST)\n• Europe/London (GMT)\n• Europe/Paris (CET)\n• America/New_York (EST)\n• America/Los_Angeles (PST)\n• Australia/Sydney (AEST)\n\nNote: You can use ANY valid IANA timezone string.\nExample: /settz Asia/Singapore"
                        send_telegram_message(f"Current Timezone: {TZ_STR}\n\n{common_tz}", parse_mode=None)
                    elif tl.startswith('/settz '):
                        new_tz = text.split(' ', 1)[1].strip()
                        try:
                            ZoneInfo(new_tz)
                            env_path = os.path.join(BASE_DIR, '.env')
                            with open(env_path, 'r') as f: lines = f.readlines()
                            with open(env_path, 'w') as f:
                                tz_found = False
                                for line in lines:
                                    if line.startswith('TIMEZONE='): f.write(f'TIMEZONE={new_tz}\n'); tz_found = True
                                    else: f.write(line)
                                if not tz_found: f.write(f'TIMEZONE={new_tz}\n')
                            TARGET_TZ = ZoneInfo(new_tz); TZ_STR = new_tz
                            send_telegram_message(f"Timezone successfully changed to {new_tz}", parse_mode=None)
                        except ZoneInfoNotFoundError:
                            send_telegram_message(f"Invalid timezone: {new_tz}. Use IANA format.", parse_mode=None)
                    elif tl.startswith('/add '):
                        parts = text.split(maxsplit=2)
                        if len(parts) >= 3:
                            name, input_val = parts[1], parts[2]
                            trader_id, widget_id = resolve_trader_id(input_val)
                            if not trader_id:
                                send_telegram_message(f"Could not resolve Trader ID from: {input_val}", parse_mode=None)
                            else:
                                config[name] = {"id": trader_id, "active": True}; save_config(config)
                                if widget_id and widget_id != trader_id:
                                    send_telegram_message(f"Widget ID {widget_id} has Trader Account ID {trader_id}.\nMonitoring added as '{name}'.", parse_mode=None)
                                else:
                                    send_telegram_message(f"Monitoring added as '{name}' with ID {trader_id}.", parse_mode=None)
                        else: send_telegram_message("Usage: /add Name URL_or_ID", parse_mode=None)
                    elif tl.startswith('/activate '):
                        name = text.split()[1]
                        real_name = next((k for k in config.keys() if k.lower() == name.lower()), None)
                        if real_name: config[real_name]['active'] = True; save_config(config); send_telegram_message(f"Activated {real_name}", parse_mode=None)
                        else: send_telegram_message(f"Master {name} not found", parse_mode=None)
                    elif tl.startswith('/deactivate '):
                        name = text.split()[1]
                        real_name = next((k for k in config.keys() if k.lower() == name.lower()), None)
                        if real_name: config[real_name]['active'] = False; save_config(config); send_telegram_message(f"Deactivated {real_name}", parse_mode=None)
                        else: send_telegram_message(f"Master {name} not found", parse_mode=None)
                    elif tl.startswith('/remove '):
                        name = text.split()[1]
                        real_name = next((k for k in config.keys() if k.lower() == name.lower()), None)
                        if real_name:
                            config.pop(real_name)
                            save_config(config)
                            for ext in ['_last_seen.txt', '_live_trades.csv']:
                                f_path = f"{BASE_DIR}/{real_name.lower()}{ext}"
                                if os.path.exists(f_path): os.remove(f_path)
                            send_telegram_message(f"Removed {real_name} and deleted local files.", parse_mode=None)
                        else: send_telegram_message(f"Master {name} not found", parse_mode=None)
                    elif tl == '/list':
                        msg = "Monitored Masters:\n"
                        for n, d in config.items(): msg += f"{'[ON]' if d['active'] else '[OFF]'} {n} (ID: {d['id']})\n"
                        send_telegram_message(msg, parse_mode=None)
    except Exception as e: logger.error(f'TG command loop error: {e}')

def main():
    logger.info('Starting Multi-Strategy Real-Time Monitor...')
    config = load_config()
    last_seen_tracker = {n: (open(f"{BASE_DIR}/{n.lower()}_last_seen.txt").read().strip() if os.path.exists(f"{BASE_DIR}/{n.lower()}_last_seen.txt") else '2020-01-01T00:00:00.000Z') for n in config}
    last_trade_check = 0

    while True:
        check_telegram_commands(config)
        if time.time() - last_trade_check >= TRADE_POLL_INTERVAL:
            config = load_config()
            for name, data in config.items():
                if not data['active']: continue
                trader_id = data['id']
                state_file = f"{BASE_DIR}/{name.lower()}_last_seen.txt"
                last_seen = last_seen_tracker.get(name, '2020-01-01T00:00:00.000Z')
                try:
                    new_trades = fetch_all_trades(trader_id, last_seen)
                    if new_trades:
                        new_trades.sort(key=lambda x: x['openTime'], reverse=True)
                        logger.info(f'[{name}] Found {len(new_trades)} new trade(s)!')
                        last_seen_tracker[name] = new_trades[0]['openTime']
                        with open(state_file, 'w') as f: f.write(last_seen_tracker[name])
                        save_csv_newest_first(f"{BASE_DIR}/{name.lower()}_live_trades.csv", new_trades)
                        for trade in new_trades[:50]:
                            ot = format_trade_time(trade['openTime'])
                            ct = format_trade_time(trade.get('closeTime')) if trade.get('closeTime') else "Still Open"
                            dur = calculate_floating_time(trade['openTime'], trade.get('closeTime'))
                            msg = (f"New {name} Trade!\n"
                                   f"Symbol: {trade['symbol']} | {trade['direction']} | Vol: {trade['volume']}\n"
                                   f"Open: {trade['openPrice']} | Close: {trade.get('closePrice', 'N/A')}\n"
                                   f"Profit: ${trade.get('profit', 0)} ({trade.get('profitPoints', 0)} pts)\n"
                                   f"Time: {ot} to {ct}\n"
                                   f"Duration: {dur}")
                            send_telegram_message(msg, parse_mode='Markdown')
                            time.sleep(0.2)
                except Exception as e: logger.error(f'[{name}] Error: {e}')
                time.sleep(1)
            last_trade_check = time.time()
        time.sleep(COMMAND_CHECK_INTERVAL)

if __name__ == '__main__': main()
