"""Device status screen template.

Shows local device vitals: hostname, IP, WiFi, CPU temp, memory,
disk, uptime, battery, and app status.
"""

from __future__ import annotations

from PIL import Image

from ..canvas import Canvas
from .. import layout, MARGIN
from . import register


@register("device_status")
def render(c: Canvas, data: dict) -> Image.Image:
    hostname = data.get("hostname", "unknown")
    ip = data.get("ip", "--")
    ssid = data.get("ssid", "--")
    bssid = data.get("bssid", "--")
    wifi_status = data.get("wifi_status", "--")
    signal = data.get("signal", "--")
    cpu_temp = data.get("cpu_temp", "--")
    memory = data.get("memory", "--")
    disk = data.get("disk", "--")
    uptime = data.get("uptime", "--")
    battery = data.get("battery", "--")
    battery_charging = data.get("battery_charging", False)
    pid = data.get("pid", "--")
    version = data.get("version", "?")

    y = layout.header(c, "DEVICE", MARGIN)

    c.text((MARGIN, y), hostname, fill=0)
    y += layout.LINE_H

    y = layout.divider(c, y)

    network_lines = [
        ("IP", str(ip)),
        ("SSID", str(ssid)),
        ("BSSID", str(bssid)),
    ]

    wifi_icon = "[+]"
    ws = str(wifi_status).lower()
    if ws in ("full", "connected", "ok"):
        wifi_icon = "[+]"
    elif ws in ("limited", "degraded"):
        wifi_icon = "[!]"
    elif ws in ("no connectivity", "disconnected", "down", "offline"):
        wifi_icon = "[-]"
    else:
        wifi_icon = "[?]"

    network_lines.append(("WiFi", f"{wifi_icon} {wifi_status}"))
    if signal and str(signal) != "--":
        network_lines.append(("Signal", str(signal)))

    y = layout.info_lines(c, network_lines, y)

    y = layout.divider(c, y)

    system_lines = [
        ("CPU", str(cpu_temp)),
        ("Mem", str(memory)),
        ("Disk", str(disk)),
        ("Up", str(uptime)),
    ]
    y = layout.info_lines(c, system_lines, y)

    y = layout.divider(c, y)

    bat_display = str(battery)
    if battery_charging:
        bat_display += " [~]"
    power_lines = [
        ("Bat", bat_display),
        ("PID", str(pid)),
        ("Ver", str(version)),
    ]
    y = layout.info_lines(c, power_lines, y)

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).strftime("%H:%M:%S")
    layout.footer(c, now)

    return c.to_image()
