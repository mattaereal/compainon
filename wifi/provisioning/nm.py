"""NetworkManager (nmcli) wrapper for Wi-Fi operations.

All subprocess calls go through ``_run_nmcli`` which enforces
timeouts and basic error handling.  No shell=True is ever used.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from typing import Any

from provisioning import config

logger = logging.getLogger(__name__)


def _nmcli_bin() -> str:
    return config.NMCLI_PATH


def _run_nmcli(
    args: list[str], timeout: int | None = None
) -> subprocess.CompletedProcess[str]:
    cmd = [_nmcli_bin()] + args
    t = timeout or config.NMCLI_TIMEOUT
    logger.debug("nmcli: %s (timeout=%d)", " ".join(cmd), t)
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=t,
        )
    except subprocess.TimeoutExpired:
        logger.error("nmcli timed out: %s", " ".join(cmd))
        raise
    except FileNotFoundError:
        logger.error("nmcli not found at %s", _nmcli_bin())
        raise


def nmcli_available() -> bool:
    return shutil.which(_nmcli_bin()) is not None


def networkmanager_running() -> bool:
    r = _run_nmcli(["general", "status"])
    return r.returncode == 0


def wifi_device_exists() -> bool:
    r = _run_nmcli(["device", "status"])
    if r.returncode != 0:
        return False
    for line in r.stdout.strip().splitlines():
        parts = line.split()
        if parts and parts[0] == config.HOTSPOT_IFACE:
            return True
    return False


def get_active_connection() -> str | None:
    """Return the active connection name on the Wi-Fi interface, or None."""
    r = _run_nmcli(["device", "status"])
    if r.returncode != 0:
        return None
    for line in r.stdout.strip().splitlines():
        parts = line.split()
        if (
            len(parts) >= 4
            and parts[0] == config.HOTSPOT_IFACE
            and parts[2] == "connected"
        ):
            return parts[3] if len(parts) > 3 else None
    return None


def is_connected() -> bool:
    """True if the Wi-Fi interface has an active connection (not hotspot)."""
    r = _run_nmcli(["device", "status"])
    if r.returncode != 0:
        return False
    for line in r.stdout.strip().splitlines():
        parts = line.split()
        if (
            len(parts) >= 4
            and parts[0] == config.HOTSPOT_IFACE
            and parts[2] == "connected"
        ):
            conn = parts[3] if len(parts) > 3 else ""
            if conn != config.HOTSPOT_CONN_NAME:
                return True
    return False


def scan_networks() -> list[dict[str, Any]]:
    """Return a list of nearby Wi-Fi networks.

    Each entry is a dict with keys: ssid, signal, security, hidden.
    Duplicates (same SSID) are collapsed, keeping the strongest signal.
    """
    r = _run_nmcli(
        [
            "-t",
            "-f",
            "SSID,SIGNAL,SECURITY,IN-USE",
            "dev",
            "wifi",
            "list",
            "--rescan",
            "yes",
        ],
        timeout=30,
    )
    if r.returncode != 0:
        logger.warning("scan failed: %s", r.stderr.strip())
        return []

    networks: dict[str, dict[str, Any]] = {}
    for line in r.stdout.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split(":")
        if len(parts) < 3:
            continue
        ssid = parts[0].strip()
        if not ssid or ssid == "--":
            continue
        try:
            signal = int(parts[1].strip())
        except ValueError:
            signal = 0
        security = parts[2].strip() if len(parts) > 2 else ""
        in_use = parts[3].strip() if len(parts) > 3 else ""

        existing = networks.get(ssid)
        if existing is None or signal > existing["signal"]:
            networks[ssid] = {
                "ssid": ssid,
                "signal": signal,
                "security": security,
                "hidden": False,
                "in_use": in_use == "*",
            }

    return sorted(networks.values(), key=lambda n: n["signal"], reverse=True)


def connection_profile_exists(ssid: str) -> str | None:
    """Return the connection name if a profile for this SSID exists, else None."""
    r = _run_nmcli(["-t", "-f", "NAME,TYPE", "connection", "show"])
    if r.returncode != 0:
        return None
    for line in r.stdout.strip().splitlines():
        parts = line.split(":")
        if len(parts) >= 2 and parts[0].strip() == ssid and "wifi" in parts[1].strip():
            return parts[0].strip()
    return None


def delete_connection(name: str) -> bool:
    r = _run_nmcli(["connection", "delete", name])
    if r.returncode != 0:
        logger.warning("failed to delete connection %s: %s", name, r.stderr.strip())
        return False
    logger.info("deleted connection profile: %s", name)
    return True


def create_wifi_connection(
    ssid: str,
    password: str | None = None,
    hidden: bool = False,
    open_network: bool = False,
) -> bool:
    """Create (or replace) a NetworkManager Wi-Fi connection profile.

    Returns True on success.
    """
    existing = connection_profile_exists(ssid)
    if existing:
        logger.info("updating existing profile for %s", ssid)
        delete_connection(existing)

    args: list[str] = [
        "connection",
        "add",
        "type",
        "wifi",
        "con-name",
        ssid,
        "ssid",
        ssid,
        "ifname",
        config.HOTSPOT_IFACE,
        "connection.autoconnect",
        "yes",
        "connection.autoconnect-priority",
        str(config.AUTOCONNECT_PRIORITY),
        "save",
        "yes",
    ]

    if open_network or password is None:
        args += ["wifi-sec.key-mgmt", "none"]
    else:
        args += [
            "wifi-sec.key-mgmt",
            "wpa-psk",
            "wifi-sec.psk",
            password,
        ]

    if hidden:
        args += ["wifi.hidden", "yes"]

    r = _run_nmcli(args, timeout=20)
    if r.returncode != 0:
        logger.error("failed to create connection: %s", r.stderr.strip())
        return False
    logger.info("created connection profile: %s", ssid)
    return True


def activate_connection(ssid: str) -> bool:
    """Activate a connection profile. Returns True on success."""
    r = _run_nmcli(["connection", "up", ssid], timeout=config.CONNECT_TIMEOUT)
    if r.returncode != 0:
        logger.error("failed to activate %s: %s", ssid, r.stderr.strip())
        return False
    logger.info("activated connection: %s", ssid)
    return True


def verify_connectivity() -> tuple[bool, str]:
    """Check whether we have working internet access.

    Returns (ok, message).
    """
    r = _run_nmcli(["networking", "connectivity", "check"], timeout=10)
    if r.returncode == 0:
        status = r.stdout.strip()
        if status == "full":
            return True, "full internet connectivity"
        if status == "limited":
            return True, "connected to Wi-Fi but internet is limited"
    return False, "no connectivity"


def verify_association() -> tuple[bool, str]:
    """Check if we are associated to a Wi-Fi network (not necessarily internet)."""
    r = _run_nmcli(["-t", "-f", "DEVICE,STATE", "device", "status"])
    if r.returncode != 0:
        return False, "cannot query device state"
    for line in r.stdout.strip().splitlines():
        parts = line.split(":")
        if len(parts) >= 2 and parts[0] == config.HOTSPOT_IFACE:
            state = parts[1].strip()
            if state in ("connected", "100"):
                return True, f"associated (state: {state})"
            return False, f"device state: {state}"
    return False, "device not found"


def hotspot_active() -> bool:
    """Check whether our setup hotspot is currently active."""
    r = _run_nmcli(["-t", "-f", "NAME,DEVICE,STATE", "connection", "show", "--active"])
    if r.returncode != 0:
        return False
    for line in r.stdout.strip().splitlines():
        parts = line.split(":")
        if len(parts) >= 2 and parts[0] == config.HOTSPOT_CONN_NAME:
            return True
    return False


def start_hotspot() -> bool:
    """Start the setup hotspot via nmcli. Returns True on success."""
    if hotspot_active():
        logger.info("hotspot already active")
        return True

    args = [
        "device",
        "wifi",
        "hotspot",
        "ifname",
        config.HOTSPOT_IFACE,
        "ssid",
        config.HOTSPOT_SSID,
        "con-name",
        config.HOTSPOT_CONN_NAME,
    ]

    r = _run_nmcli(args, timeout=30)
    if r.returncode != 0:
        logger.error("failed to start hotspot: %s", r.stderr.strip())
        return False
    logger.info(
        "hotspot started: SSID=%s IP=%s", config.HOTSPOT_SSID, config.HOTSPOT_IP
    )
    return True


def stop_hotspot() -> bool:
    """Stop the setup hotspot. Returns True on success."""
    if not hotspot_active():
        logger.debug("hotspot not active, nothing to stop")
        return True

    r = _run_nmcli(["connection", "down", config.HOTSPOT_CONN_NAME], timeout=15)
    if r.returncode != 0:
        logger.warning("failed to stop hotspot connection: %s", r.stderr.strip())

    delete_connection(config.HOTSPOT_CONN_NAME)
    logger.info("hotspot stopped")
    return True


def get_device_ip() -> str | None:
    """Get the current IP address of the Wi-Fi interface."""
    r = _run_nmcli(["-t", "-f", "DEVICE,IP4.ADDRESS", "device", "status"])
    if r.returncode != 0:
        return None
    for line in r.stdout.strip().splitlines():
        parts = line.split(":")
        if len(parts) >= 2 and parts[0] == config.HOTSPOT_IFACE:
            addr = parts[1].strip()
            if addr and addr != "--":
                return addr.split("/")[0]
    return None


def get_connections() -> list[dict[str, str]]:
    """List saved Wi-Fi connection profiles."""
    r = _run_nmcli(["-t", "-f", "NAME,TYPE,AUTOCONNECT", "connection", "show"])
    if r.returncode != 0:
        return []
    result = []
    for line in r.stdout.strip().splitlines():
        parts = line.split(":")
        if len(parts) >= 3 and "wifi" in parts[1].strip():
            result.append(
                {
                    "name": parts[0].strip(),
                    "type": parts[1].strip(),
                    "autoconnect": parts[2].strip() if len(parts) > 2 else "yes",
                }
            )
    return result
