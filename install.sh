#!/bin/bash

set -e

SCRIPT_NAME="tabpp.py"
INSTALL_DIR="/usr/local/bin"
SERVICE_NAME="tabpp.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
CONFIG_PATH="/etc/tabpp"

echo "[+] Installing TABPP"

sudo cp tabpp.py "$INSTALL_DIR/"
sudo chmod +x "$INSTALL_DIR/$SCRIPT_NAME"

echo "[+] Creating config file"
sudo mkdir -p "$CONFIG_PATH"
sudo cp ./config.conf "$CONFIG_PATH/"

echo "[+] Installing systemd service"

# Write systemd service
sudo tee "$SERVICE_PATH" > /dev/null <<EOF
[Unit]
Description=Automatic Brightness and Power Profile Controller
After=multi-user.target

[Service]
Type=simple
EnvironmentFile=$CONFIG_PATH/config.conf
ExecStart=$INSTALL_DIR/$SCRIPT_NAME
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd, enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"


echo "[+] Brightness Controller installed and running"
