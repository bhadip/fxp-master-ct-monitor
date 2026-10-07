#!/bin/bash
case "$1" in
    logs)
        sudo journalctl -u superman-monitor.service -f --no-pager
        ;;
    stop)
        sudo systemctl stop superman-monitor.service
        echo "✅ Monitor stopped."
        ;;
    restart)
        sudo systemctl restart superman-monitor.service
        echo "✅ Monitor restarted."
        ;;
    status)
        sudo systemctl status superman-monitor.service --no-pager
        ;;
    *)
        echo "Usage: ./superman.sh {logs|stop|restart|status}"
        ;;
esac
