#!/usr/bin/env bash
#
# Setup script for bed-earnings on a Pi / Mac Mini / any Linux or macOS host.
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh          # install deps + create systemd service (Linux)
#   ./setup.sh --run    # just install deps and start Streamlit directly
#
set -euo pipefail

PORT="${PORT:-8501}"
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$APP_DIR/.venv"

echo "=== bed-earnings setup ==="
echo "App directory: $APP_DIR"
echo "Port: $PORT"
echo ""

# --- Python venv ---
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

echo "Installing dependencies..."
pip install --upgrade pip -q
pip install -r "$APP_DIR/requirements.txt" -q
echo "Dependencies installed."

# --- Direct run mode ---
if [ "${1:-}" = "--run" ]; then
    echo ""
    echo "Starting Streamlit on port $PORT..."
    echo "Open http://localhost:$PORT or http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'your-ip'):$PORT"
    echo ""
    exec streamlit run "$APP_DIR/app.py" \
        --server.port "$PORT" \
        --server.headless true \
        --server.address 0.0.0.0
fi

# --- systemd service (Linux only) ---
if [[ "$(uname)" == "Linux" ]]; then
    SERVICE_NAME="bed-earnings"
    SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
    STREAMLIT_BIN="$VENV_DIR/bin/streamlit"

    echo ""
    echo "Creating systemd service: $SERVICE_NAME"

    sudo tee "$SERVICE_FILE" > /dev/null <<UNIT
[Unit]
Description=Bed Earnings - Norwegian Property Finance Dashboard
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$APP_DIR
ExecStart=$STREAMLIT_BIN run $APP_DIR/app.py --server.port $PORT --server.headless true --server.address 0.0.0.0
Restart=on-failure
RestartSec=5
Environment=PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
UNIT

    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    sudo systemctl restart "$SERVICE_NAME"

    echo ""
    echo "Service '$SERVICE_NAME' is running."
    echo "  Status:   sudo systemctl status $SERVICE_NAME"
    echo "  Logs:     sudo journalctl -u $SERVICE_NAME -f"
    echo "  Stop:     sudo systemctl stop $SERVICE_NAME"
    echo ""

# --- launchd plist (macOS) ---
elif [[ "$(uname)" == "Darwin" ]]; then
    PLIST_NAME="com.bed-earnings.dashboard"
    PLIST_FILE="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"
    STREAMLIT_BIN="$VENV_DIR/bin/streamlit"
    LOG_DIR="$APP_DIR/logs"
    mkdir -p "$LOG_DIR"

    echo ""
    echo "Creating launchd agent: $PLIST_NAME"

    cat > "$PLIST_FILE" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_NAME</string>
    <key>ProgramArguments</key>
    <array>
        <string>$STREAMLIT_BIN</string>
        <string>run</string>
        <string>$APP_DIR/app.py</string>
        <string>--server.port</string>
        <string>$PORT</string>
        <string>--server.headless</string>
        <string>true</string>
        <string>--server.address</string>
        <string>0.0.0.0</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$APP_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/stderr.log</string>
</dict>
</plist>
PLIST

    launchctl unload "$PLIST_FILE" 2>/dev/null || true
    launchctl load "$PLIST_FILE"

    echo ""
    echo "Agent '$PLIST_NAME' is running."
    echo "  Logs:     tail -f $LOG_DIR/stdout.log"
    echo "  Stop:     launchctl unload $PLIST_FILE"
    echo "  Restart:  launchctl unload $PLIST_FILE && launchctl load $PLIST_FILE"
    echo ""
fi

LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || ipconfig getifaddr en0 2>/dev/null || echo "your-ip")
echo "=== Ready ==="
echo "Local:     http://localhost:$PORT"
echo "Network:   http://$LOCAL_IP:$PORT"
echo "Tailscale: http://\$(tailscale ip -4 2>/dev/null || echo 'install-tailscale'):$PORT"
echo ""
echo "Next steps:"
echo "  1. Install Tailscale: https://tailscale.com/download"
echo "  2. Run 'sudo tailscale up' on this machine"
echo "  3. Install Tailscale on your phone"
echo "  4. Browse to http://<tailscale-ip>:$PORT from your phone"
