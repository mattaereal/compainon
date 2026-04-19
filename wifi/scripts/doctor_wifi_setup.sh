#!/bin/bash
# doctor_wifi_setup.sh - Diagnostic script for the Wi-Fi setup subsystem
set -euo pipefail

pass() { echo "  [OK]   $1"; }
fail() { echo "  [FAIL] $1"; }
info() { echo "  [INFO] $1"; }
sep()   { echo "--- $1 ---"; }

sep "Python"
PY_VER=$(python3 --version 2>/dev/null || echo "NOT FOUND")
if [[ "$PY_VER" == "NOT FOUND" ]]; then fail "python3 not found"; else pass "$PY_VER"; fi

sep "nmcli"
if command -v nmcli &>/dev/null; then
    pass "nmcli found: $(command -v nmcli)"
    NM_VER=$(nmcli --version 2>/dev/null || echo "unknown")
    info "version: $NM_VER"
else
    fail "nmcli not found"
fi

sep "NetworkManager"
if command -v nmcli &>/dev/null; then
    if nmcli general status &>/dev/null; then
        pass "NetworkManager is running"
        nmcli general status 2>/dev/null | while read -r line; do info "$line"; done
    else
        fail "NetworkManager is NOT running"
    fi
else
    fail "cannot check (nmcli missing)"
fi

sep "Wireless interface (wlan0)"
if ip link show wlan0 &>/dev/null; then
    pass "wlan0 exists"
    WLAN_STATE=$(cat /sys/class/net/wlan0/operstate 2>/dev/null || echo "unknown")
    info "operstate: $WLAN_STATE"
else
    fail "wlan0 not found"
fi

sep "Current connections"
if command -v nmcli &>/dev/null; then
    ACTIVE=$(nmcli -t -f NAME,TYPE,DEVICE connection show --active 2>/dev/null || true)
    if [ -n "$ACTIVE" ]; then
        echo "$ACTIVE" | while IFS= read -r line; do info "$line"; done
    else
        info "no active connections"
    fi
else
    fail "cannot check (nmcli missing)"
fi

sep "Saved Wi-Fi profiles"
if command -v nmcli &>/dev/null; then
    PROFILES=$(nmcli -t -f NAME,TYPE,AUTOCONNECT connection show 2>/dev/null \
        | grep ":wifi:" || true)
    if [ -n "$PROFILES" ]; then
        echo "$PROFILES" | while IFS= read -r line; do info "$line"; done
    else
        info "no saved Wi-Fi profiles"
    fi
fi

sep "Current IP addresses"
ip -4 addr show 2>/dev/null | grep -E "inet " | while IFS= read -r line; do
    IFACE=$(echo "$line" | awk '{print $NF}')
    ADDR=$(echo "$line" | awk '{print $2}')
    info "$IFACE: $ADDR"
done

sep "Trigger file"
for f in /boot/setup-wifi /boot/firmware/setup-wifi; do
    if [ -f "$f" ]; then
        pass "trigger file present: $f"
    else
        info "not found: $f"
    fi
done

sep "Hotspot capability"
if command -v nmcli &>/dev/null && ip link show wlan0 &>/dev/null; then
    AP_CHECK=$(nmcli -f WIFI-PROPERTIES dev show wlan0 2>/dev/null | grep -i "AP" || true)
    if [ -n "$AP_CHECK" ]; then
        info "$AP_CHECK"
    else
        info "AP property not reported (may still work)"
    fi
else
    fail "cannot check"
fi

sep "Flask"
PY_FLASK=$(python3 -c "import flask; print(flask.__version__)" 2>/dev/null || echo "NOT FOUND")
if [[ "$PY_FLASK" == "NOT FOUND" ]]; then
    fail "Flask not installed (pip3 install flask)"
else
    pass "Flask $PY_FLASK"
fi

sep "wifi-setup service"
if systemctl list-unit-files wifi-setup.service &>/dev/null; then
    if systemctl is-active --quiet wifi-setup.service 2>/dev/null; then
        pass "wifi-setup.service is active"
    else
        info "wifi-setup.service is NOT active"
    fi
    if systemctl is-enabled --quiet wifi-setup.service 2>/dev/null; then
        pass "wifi-setup.service is enabled"
    else
        info "wifi-setup.service is NOT enabled"
    fi
else
    info "wifi-setup.service not installed"
fi

echo ""
echo "Doctor complete."
