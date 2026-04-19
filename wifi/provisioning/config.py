"""Configuration constants for the Wi-Fi onboarding subsystem.

All tuneable values are collected here.  Override at runtime via
environment variables (prefixed ``WIFI_SETUP_``) or by editing
this file directly before deployment.
"""

from __future__ import annotations

import os
import pathlib


def _env(name: str, default: str) -> str:
    return os.environ.get(f"WIFI_SETUP_{name}", default)


HOTSPOT_SSID: str = _env("HOTSPOT_SSID", "AI-BOARD-SETUP")
HOTSPOT_IFACE: str = _env("HOTSPOT_IFACE", "wlan0")
HOTSPOT_IP: str = _env("HOTSPOT_IP", "10.42.0.1")
HOTSPOT_PREFIX: int = int(_env("HOTSPOT_PREFIX", "24"))
HOTSPOT_CONN_NAME: str = _env("HOTSPOT_CONN_NAME", "wifi-setup-hotspot")

WEB_PORT: int = int(_env("WEB_PORT", "80"))
WEB_HOST: str = _env("WEB_HOST", "10.42.0.1")

CONNECT_TIMEOUT: int = int(_env("CONNECT_TIMEOUT", "60"))
BOOT_TIMEOUT: int = int(_env("BOOT_TIMEOUT", "45"))
IDLE_TIMEOUT: int = int(_env("IDLE_TIMEOUT", "600"))

NMCLI_PATH: str = _env("NMCLI_PATH", "/usr/bin/nmcli")

TRIGGER_FILE_PATHS: list[pathlib.Path] = [
    pathlib.Path("/boot/setup-wifi"),
    pathlib.Path("/boot/firmware/setup-wifi"),
]

AUTOCONNECT_PRIORITY: int = int(_env("AUTOCONNECT_PRIORITY", "10"))

NMCLI_TIMEOUT: int = int(_env("NMCLI_TIMEOUT", "15"))

VERIFY_PING_HOST: str = _env("VERIFY_PING_HOST", "1.1.1.1")
VERIFY_PING_COUNT: int = 1
VERIFY_PING_TIMEOUT: int = int(_env("VERIFY_PING_TIMEOUT", "5"))

REPO_DIR: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent

DISPLAY_HOOK_MODULE: str | None = os.environ.get("WIFI_SETUP_DISPLAY_HOOK", None)
