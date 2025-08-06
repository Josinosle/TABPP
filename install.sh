#!/bin/bash

set -e

SCRIPT_NAME="script.py"
INSTALL_DIR=$(pwd)
SERVICE_NAME="tabpp.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
CONFIG_PATH="/etc/tabpp"
PYTHON_PATH=$(which python3)

echo "[+] Installing Brightness Controller"

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
ExecStart=$PYTHON_PATH $INSTALL_DIR/$SCRIPT_NAME
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

echo "[+] Brightness Controller installed and running"
