#!/bin/bash
# add_wifi.sh - Add a Wi-Fi network from the command line
# Usage: add_wifi.sh <SSID> [PASSWORD]
# For open networks: add_wifi.sh MyOpenNetwork --open
set -euo pipefail

SSID="${1:?Usage: add_wifi.sh SSID [PASSWORD|--open]}"
shift
PASSWORD=""
OPEN=0

for arg in "$@"; do
    case "$arg" in
        --open|-o) OPEN=1 ;;
        *) PASSWORD="$arg" ;;
    esac
done

if ! command -v nmcli &>/dev/null; then
    echo "ERROR: nmcli not found" >&2
    exit 1
fi

EXISTING=$(nmcli -t -f NAME,TYPE connection show 2>/dev/null \
    | grep ":wifi:" | cut -d: -f1 | grep -xF "$SSID" || true)

if [ -n "$EXISTING" ]; then
    echo "Updating existing profile for '$SSID' …"
    nmcli connection delete "$SSID" 2>/dev/null || true
fi

if [ "$OPEN" -eq 1 ] || [ -z "$PASSWORD" ]; then
    nmcli connection add type wifi con-name "$SSID" ssid "$SSID" \
        ifname wlan0 connection.autoconnect yes connection.autoconnect-priority 10 save yes \
        wifi-sec.key-mgmt none
else
    nmcli connection add type wifi con-name "$SSID" ssid "$SSID" \
        ifname wlan0 connection.autoconnect yes connection.autoconnect-priority 10 save yes \
        wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PASSWORD"
fi

echo "Activating '$SSID' …"
nmcli connection up "$SSID" && echo "Connected to '$SSID'." || echo "Failed to connect to '$SSID'."
