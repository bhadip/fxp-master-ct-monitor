# Multi-Strategy Trading Monitor

A headless Python daemon that monitors FXPrimus copy-trading APIs in real-time, logs new trades to CSV, and sends instant Telegram alerts.

## Features
- **Real-time Polling**: Checks for new trades every 30 seconds.
- **Multi-Strategy Support**: Monitor multiple trader IDs simultaneously.
- **Telegram Commands**: 
  - `/status` - Check monitor status and last check time.
  - `/log` - View the last 10 lines of the system log.
- **Secure**: Credentials are isolated in a `.env` file.

## Installation & Setup
1. **Install Dependencies**:
   `sudo apt update && sudo apt install python3-requests python3-dotenv -y`
2. **Configure Secrets**:
   Create a `.env` file in the project directory with `BOT_TOKEN` and `CHAT_ID`.
3. **Start the Systemd Service**:
   `sudo systemctl daemon-reload`
   `sudo systemctl enable --now trading-monitor.service`

## How to Add a New Strategy
1. Open `monitor_strategies.py`.
2. Add to the `STRATEGIES` dictionary:
   `"NewStrategyName": "NEW_TRADER_ID"`
3. Restart: `sudo systemctl restart trading-monitor.service`

## Management Commands
- **Logs**: `~/trading/mtj/superman.sh logs`
- **Status**: `~/trading/mtj/superman.sh status`
- **Restart**: `~/trading/mtj/superman.sh restart`
- **Stop**: `~/trading/mtj/superman.sh stop`

## GitHub Deployment
The `.gitignore` file protects your sensitive data. The following are automatically excluded from pushes:
- `.env` (Secrets)
- `*.csv` (Live trade data)
- `*_last_seen.txt` (State tracking)
- `monitor.log` (Local logs)
