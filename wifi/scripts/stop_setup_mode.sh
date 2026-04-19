#!/bin/bash
# stop_setup_mode.sh - Manually stop Wi-Fi setup mode
set -euo pipefail

echo "[wifi-setup] Stopping setup mode …"

if systemctl is-active --quiet wifi-setup.service 2>/dev/null; then
    systemctl stop wifi-setup.service
    echo "[wifi-setup] Stopped wifi-setup.service"
else
    echo "[wifi-setup] wifi-setup.service not running"
fi

if command -v nmcli &>/dev/null; then
    nmcli connection down wifi-setup-hotspot 2>/dev/null || true
    nmcli connection delete wifi-setup-hotspot 2>/dev/null || true
    echo "[wifi-setup] Hotspot connection removed"
fi

echo "[wifi-setup] Setup mode stopped"
