# FXPrimus Master CT Monitor

A robust, headless Python daemon that monitors multiple FXPrimus Copy Trading (CT) masters in real-time. It fetches trade data, logs it to CSV, and sends instant, highly detailed alerts to Telegram.

## 🌟 Key Features
- **Multi-Strategy Polling**: Monitors multiple Master CTs simultaneously.
- **Smart URL Decoding**: Automatically extracts the real Trader Account ID from FXPrimus mobile widget URLs.
- **Dynamic Management**: Add, activate, deactivate, or remove masters directly from Telegram.
- **Exact Floating Duration**: Calculates and displays exactly how long a position was open (e.g., `1y 2mo 3w 4d 5h 10mi 30s`).
- **Timezone Control**: Change the bot's timezone on the fly via Telegram.
- **Historical Backfill**: Automatically fetches up to 500 past trades when a new master is added.
- **Secure**: Credentials are isolated in a `.env` file and never exposed to Git.

## 📱 Telegram Commands
| Command | Description |
| :--- | :--- |
| `/status` | Check monitor status, active strategies, and current timezone. |
| `/log` | View the last 10 lines of the system log. |
| `/settz` | View current timezone and a list of acceptable IANA timezones. |
| `/settz <TZ>` | Change timezone (e.g., `/settz Asia/Singapore`). |
| `/add <Name> <URL>` | Add a new master. Paste the full mobile widget URL or direct ID. |
| `/activate <Name>` | Resume monitoring for a paused master. |
| `/deactivate <Name>` | Pause monitoring for a master (keeps history intact). |
| `/remove <Name>` | Completely delete a master from the monitor and its local files. |
| `/list` | Show all monitored masters and their ON/OFF status. |

## 🛠️ Installation & Setup
1. **Install Dependencies**:
   ```bash
   sudo apt update && sudo apt install python3-requests python3-dotenv -y
   ```
2. **Configure Secrets**:
   Create a `.env` file in the project directory:
   ```env
   BOT_TOKEN=your_telegram_bot_token
   CHAT_ID=your_telegram_chat_id
   TIMEZONE=Asia/Singapore
   ```
3. **Start the Systemd Service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now superman-monitor.service
   ```

##  File Structure
- `monitor_strategies.py`: The core monitoring script.
- `config.json`: Stores the list of masters, their IDs, and active status.
- `.env`: Stores sensitive Telegram credentials and timezone.
- `*_live_trades.csv`: Historical trade data for each master.
- `*_last_seen.txt`: Tracks the last processed trade to prevent duplicates.

## 🚀 GitHub Deployment
This repository uses a `.gitignore` file to protect your data. The following are automatically excluded from pushes:
- `.env` (Secrets)
- `config.json` (Local master configurations)
- `*.csv` (Live trade data)
- `*_last_seen.txt` (State tracking)
- `*.log` (Local logs)
