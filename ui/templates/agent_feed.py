"""Agent feed template -- live data rendering.

Renders a compact row per agent: icon + name + status + message.
Used by core/screens/agent_feed.py.
"""

from __future__ import annotations

from datetime import datetime, timezone

from PIL import Image

from ..canvas import Canvas
from .. import layout, MARGIN
from . import register

_STATUS_ICONS = {
    "idle": "[+]",
    "ok": "[+]",
    "working": "[!]",
    "waiting_input": "[!]",
    "stuck": "[-]",
    "error": "[-]",
    "offline": "[-]",
    "success": "[*]",
}


@register("agent_feed")
def render(c: Canvas, data: dict) -> Image.Image:
    name = data.get("name", "Agents")
    agents = data.get("agents", [])
    num_agents = data.get("num_agents", len(agents))

    c.text((MARGIN, 3), name, fill=0)
    c.hline(14, fill=0)

    y = 18
    for agent in agents:
        if y + layout.LINE_H * 2 > c.h - layout.FOOTER_RESERVE:
            layout.overflow_marker(c, y)
            break

        agent_name = agent.get("name", "?")
        if len(agent_name) > 12:
            agent_name = agent_name[:9] + "..."

        status = str(agent.get("status", "")).lower()
        if agent.get("fetch_error"):
            status = "offline"
        icon = _STATUS_ICONS.get(status, "[?]")

        row = f"{icon} {agent_name}"
        if status and status not in ("idle", "ok"):
            row += f"  {status}"
        c.text((MARGIN, y), row, fill=0)
        y += layout.LINE_H

        msg = agent.get("message", "")
        if msg:
            if len(msg) > 22:
                msg = msg[:19] + "..."
            c.text((MARGIN + 8, y), msg, fill=0)
            y += layout.LINE_H_SMALL

    footer_y = c.h - layout.LINE_H - 2
    now = datetime.now(timezone.utc).strftime("%H:%M:%S")
    c.text((MARGIN, footer_y), f"{num_agents} agent(s) | {now}", fill=0)

    return c.to_image()
