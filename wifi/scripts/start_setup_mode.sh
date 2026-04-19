#!/bin/bash
# start_setup_mode.sh - Manually start Wi-Fi setup mode
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo "[wifi-setup] Starting setup mode …"

if ! command -v nmcli &>/dev/null; then
    echo "[wifi-setup] ERROR: nmcli not found" >&2
    exit 1
fi

if ! nmcli general status &>/dev/null; then
    echo "[wifi-setup] ERROR: NetworkManager is not running" >&2
    exit 1
fi

exec python3 -m provisioning.app
