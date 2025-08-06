#!/bin/bash

set -e

SCRIPT_NAME="tabpp.py"
INSTALL_DIR="/usr/local/bin"
SERVICE_NAME="tabpp.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
CONFIG_PATH="/etc/tabpp"

echo "[+] Uninstalling TABPP"
sudo rm "$INSTALL_DIR/"tabpp.py

echo "[+] Uninstalling config file"
sudo rm -r "$CONFIG_PATH"

echo "[+] Uninstalling systemd service"
sudo systemctl disable tabpp
sudo rm "$SERVICE_PATH"

echo "[+] TABPP removed"
