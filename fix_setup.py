import os

readme_content = """# Multi-Strategy Trading Monitor

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
"""

service_content = """[Unit]
Description=Multi-Strategy Trading Real-Time Monitor
After=network.target

[Service]
Type=simple
User=tom
WorkingDirectory=/home/tom/trading/mtj
ExecStart=/usr/bin/python3 /home/tom/trading/mtj/monitor_strategies.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

with open('/home/tom/trading/mtj/README.md', 'w') as f:
    f.write(readme_content)
print("README.md created successfully.")

with open('/tmp/trading-monitor.service', 'w') as f:
    f.write(service_content)
print("Service file created in /tmp.")
