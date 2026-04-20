"""Preview renderer for e-paper screen templates.

Renders templates to PNG files for offline preview on a laptop.
"""

from __future__ import annotations

import os
from typing import Optional

from PIL import Image

from ..canvas import Canvas
from .. import templates


MOCK_DATA = {
    "boot": {
        "name": "Lotus Companion",
        "version": "1.0",
    },
    "setup": {
        "ssid": "AI-BOARD-SETUP",
        "url": "http://10.42.0.1",
    },
    "status_dashboard": {
        "name": "AI Status",
        "timestamp": "14:32:05",
        "categories": [
            {
                "name": "Claude",
                "icon": "anthropic",
                "items": [
                    {"label": "claude.ai", "status": "OK"},
                    {"label": "API", "status": "OK"},
                    {"label": "Claude Code", "status": "DEGRADED"},
                ],
            },
            {
                "name": "OpenAI",
                "icon": "openai",
                "items": [
                    {"label": "ChatGPT", "status": "OK"},
                    {"label": "API", "status": "DOWN"},
                ],
            },
            {
                "name": "Lotus",
                "icon": "lotus",
                "items": [
                    {"label": "Live", "status": "OK"},
                    {"label": "Queue", "status": "OK"},
                ],
            },
        ],
    },
    "detail": {
        "name": "Claude API",
        "status": "DEGRADED",
        "metrics": [
            {"label": "latency", "value": "340ms"},
            {"label": "uptime", "value": "99.2%"},
            {"label": "requests", "value": "1.2M"},
            {"label": "errors", "value": "0.8%"},
        ],
        "last_check": "14:32:05",
    },
    "message": {
        "title": "ALERT",
        "body": ["API latency above", "threshold (300ms)"],
        "hint": "press to dismiss",
    },
    "idle": {
        "name": "Lotus",
        "mood": "idle",
        "info": [
            {"label": "status", "value": "ok"},
            {"label": "pending", "value": "0"},
            {"label": "PRs", "value": "+3 M1"},
        ],
    },
    "error": {
        "message": "Connection lost",
        "detail": "Unable to reach status endpoints. Check WiFi.",
        "last_ok": "14:30",
    },
    "device_status": {
        "hostname": "tamagotchai.local",
        "ip": "192.168.1.42",
        "ssid": "Vault-TecNet",
        "bssid": "AA:BB:CC:DD:EE:FF",
        "wifi_status": "connected",
        "signal": "85%",
        "cpu_temp": "52.3C",
        "memory": "234/512MB",
        "disk": "3.2/28GB",
        "uptime": "2d 4h 32m",
        "battery": "87%",
        "battery_charging": True,
        "pid": "12345",
        "version": "1.0.0",
    },
}


def render_template(
    name: str, data: dict | None = None, output_dir: str = "out/screens"
) -> str:
    d = data or MOCK_DATA.get(name, {})
    img = templates.render(name, d)
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{name}.png")
    img.save(path, format="PNG")
    return path


def render_all(output_dir: str = "out/screens") -> list[str]:
    paths = []
    for name in templates.names():
        path = render_template(name, output_dir=output_dir)
        paths.append(path)
    return paths
