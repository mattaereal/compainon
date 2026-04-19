# Wi-Fi Setup Onboarding Subsystem

## Overview

This subsystem allows a phone (or any Wi-Fi device) to configure the
Raspberry Pi's Wi-Fi credentials without a keyboard, serial console, or
SD-card edits.

When the Pi cannot connect to any known Wi-Fi network after a
configurable timeout, it automatically enters **setup mode**: a temporary
open hotspot is created and a local web UI is served.  The user connects
to the hotspot, picks a network, enters credentials, and the Pi
connects.  On success, the hotspot disappears and normal operation
resumes.

## Security Caveat

**The setup hotspot is open (no password).**  Anyone within radio range
can connect to it while it is active.  This is a deliberate trade-off
for ease of onboarding.  Mitigations:

- Setup mode only activates when the device has no working Wi-Fi.
- Setup mode can also be triggered manually via a boot-partition file.
- The web server binds only to the hotspot IP.
- No IP forwarding or NAT is enabled.
- Setup mode shuts down automatically after successful onboarding.
- Setup mode shuts down after a configurable idle timeout (default 10 min).
- No public internet-facing service exists in normal mode.

**Do not leave setup mode enabled longer than necessary.**

## How It Works

### State Machine

```
NORMAL_BOOT
  -> Wait for existing Wi-Fi (timeout: 45 s by default)
  -> If connected: done (service exits)
  -> If not connected: enter SETUP_MODE

SETUP_MODE
  -> Start open hotspot on wlan0
  -> Start web UI bound to hotspot IP
  -> Scan nearby networks
  -> Wait for user input

USER_SUBMITS_NETWORK
  -> Validate input
  -> Create/update NetworkManager connection profile
  -> Attempt activation
  -> Verify association

IF SUCCESS
  -> Persist config
  -> Stop hotspot
  -> Stop web service
  -> Exit setup mode

IF FAILURE
  -> Stay in SETUP_MODE
  -> Show error in UI
  -> Allow retry
```

### Trigger File

Place an empty file on the boot partition to force setup mode at the
next boot, even if Wi-Fi is currently working:

```sh
touch /boot/firmware/setup-wifi   # or /boot/setup-wifi
```

The file is consumed (deleted) after the setup service reads it.

## Installation

### 1. Copy the repository to the Pi

```sh
sudo cp -r /path/to/lotus-companion-wifi /opt/lotus-companion-wifi
```

### 2. Install Python dependency

```sh
pip3 install flask
```

### 3. Install systemd units

```sh
sudo cp /opt/lotus-companion-wifi/systemd/wifi-setup.service /etc/systemd/system/
sudo cp /opt/lotus-companion-wifi/systemd/wifi-setup-trigger.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### 4. Enable the automatic fallback service

```sh
sudo systemctl enable wifi-setup.service
```

This starts the service on every boot.  If Wi-Fi is already connected,
the service exits immediately.  If not, it enters setup mode.

### 5. (Optional) Enable the trigger-file service

```sh
sudo systemctl enable wifi-setup-trigger.service
```

This service only starts when the trigger file exists on boot.  It
forces setup mode regardless of current network state.

## Enable / Disable

```sh
# Enable automatic fallback on boot
sudo systemctl enable wifi-setup.service

# Disable automatic fallback
sudo systemctl disable wifi-setup.service

# Start setup mode manually right now
sudo systemctl start wifi-setup.service

# Stop setup mode manually
sudo systemctl stop wifi-setup.service
# or:
/opt/lotus-companion-wifi/scripts/stop_setup_mode.sh
```

## How Automatic Fallback Works

The `wifi-setup.service` unit starts on every boot (when enabled).
The Python entrypoint:

1. Checks for a trigger file (forces setup mode).
2. If no trigger file, waits up to `BOOT_TIMEOUT` seconds for existing
   Wi-Fi to connect.
3. If Wi-Fi connects: the service exits 0 (no setup needed).
4. If Wi-Fi does not connect: the service enters setup mode.

## How the Manual Trigger File Works

1. Insert the Pi's SD card into a computer.
2. Create an empty file named `setup-wifi` on the boot partition:
   - `/boot/firmware/setup-wifi` (Raspberry Pi OS Trixie)
   - `/boot/setup-wifi` (some other layouts)
3. Boot the Pi.  The `wifi-setup-trigger.service` (if enabled) detects
   the file and forces setup mode.
4. The trigger file is deleted after it is read.

Alternatively, the `wifi-setup.service` also checks for the trigger file
at startup, so simply enabling that one service handles both automatic
fallback and manual trigger scenarios.

## Phone Onboarding Steps

1. The Pi enters setup mode (auto or triggered).
2. On your phone, connect to the Wi-Fi network `AI-BOARD-SETUP`.
3. Open a browser and go to **http://10.42.0.1**
4. Select a network from the list (or enter SSID manually).
5. Enter the password if the network is secured.
6. Tap **Connect**.
7. If successful, the hotspot disappears and the Pi joins your network.
8. You can close the browser.

## How the Network Is Applied

1. The web UI submits SSID + password to `/api/connect`.
2. The backend creates a NetworkManager connection profile via `nmcli`.
3. The profile is activated with `nmcli connection up`.
4. Association is verified.
5. On success: the hotspot is torn down, the service exits.
6. The profile persists across reboots (saved by NetworkManager).

## Configuration

All settings can be overridden via environment variables (prefix
`WIFI_SETUP_`):

| Variable                  | Default           | Description                          |
|---------------------------|-------------------|--------------------------------------|
| `WIFI_SETUP_HOTSPOT_SSID` | `AI-BOARD-SETUP`  | Hotspot SSID                         |
| `WIFI_SETUP_HOTSPOT_IP`   | `10.42.0.1`       | Hotspot IP address                   |
| `WIFI_SETUP_WEB_PORT`     | `80`              | Web UI port                          |
| `WIFI_SETUP_BOOT_TIMEOUT` | `45`              | Seconds to wait for Wi-Fi on boot    |
| `WIFI_SETUP_IDLE_TIMEOUT`| `600`             | Seconds before idle shutdown         |
| `WIFI_SETUP_CONNECT_TIMEOUT` | `60`           | Seconds to wait for connection attempt|
| `WIFI_SETUP_AUTOCONNECT_PRIORITY` | `10`      | NM autoconnect priority for new net  |

Set these in the systemd unit `Environment=` lines or override with a
drop-in:

```sh
sudo systemctl edit wifi-setup.service
```

## Recovery If Onboarding Fails

- **Wrong password**: The UI shows an error.  Re-enter and retry.
- **Hotspot won't start**: Check `journalctl -u wifi-setup.service`.
- **No networks found**: Tap "Refresh Scan".  Move closer to the router.
- **Connection succeeds but no internet**: The UI reports limited
  connectivity.  The Wi-Fi association worked; the issue is upstream.
- **Everything is broken**: Insert the SD card into a computer and
  create the trigger file `/boot/firmware/setup-wifi` to force setup
  mode on next boot.  Alternatively, use `scripts/add_wifi.sh` via
  serial console.

## Inspect Logs

```sh
journalctl -u wifi-setup.service -f
journalctl -u wifi-setup-trigger.service -f
```

## Non-Interference with the Existing App

- The setup subsystem lives entirely in `provisioning/`.
- Its systemd units have unique names (`wifi-setup.service`,
  `wifi-setup-trigger.service`).
- The web server binds only to the hotspot IP, not `0.0.0.0`.
- The service exits when Wi-Fi is already connected.
- No existing app ports, configs, or services are modified.
- The optional display hook (`config.DISPLAY_HOOK_MODULE`) is opt-in
  and requires explicit configuration.

## Display Integration (Optional)

If the repository has e-paper display support and you want the setup
mode to show its SSID and URL on the screen, set the environment
variable:

```
WIFI_SETUP_DISPLAY_HOOK=mypackage.display
```

The module must expose `show_setup_info(line1, line2, line3)`.  If the
module is missing or the function raises, the error is logged but
silently ignored -- setup mode does not depend on the display.

## Doctor Script

Run diagnostics:

```sh
/opt/lotus-companion-wifi/scripts/doctor_wifi_setup.sh
```

This checks Python, nmcli, NetworkManager, wlan0, connections, IPs,
trigger files, hotspot capability, Flask, and service status.

## File Structure

```
provisioning/
  __init__.py
  app.py          - Flask web application + entrypoint
  config.py       - All configuration constants
  nm.py           - NetworkManager/nmcli wrapper
  hotspot.py      - Hotspot lifecycle management
  state.py        - State machine
  scanner.py      - Wi-Fi scan with caching
  templates/
    index.html    - Single-page web UI
  static/
    style.css     - CSS styles

scripts/
  start_setup_mode.sh
  stop_setup_mode.sh
  add_wifi.sh
  doctor_wifi_setup.sh

systemd/
  wifi-setup.service
  wifi-setup-trigger.service

docs/
  wifi-setup.md   - This file
```
