"""Status board template -- live data rendering.

Renders categories with icons, item rows with status markers,
and overflow handling. Used by core/screens/status_board.py.
"""

from __future__ import annotations

from PIL import Image

from ..canvas import Canvas
from .. import layout, MARGIN
from ..assets import get_icon
from . import register


@register("status_board")
def render(c: Canvas, data: dict) -> Image.Image:
    name = data.get("name", "Status")
    timestamp = data.get("timestamp", "")
    categories = data.get("categories", [])
    footer_text = data.get("footer_text", "no data")

    y = layout.header(c, name, MARGIN, timestamp)

    for cat in categories:
        if layout.is_overflow(y, c.h):
            y = layout.overflow_marker(c, y)
            break

        icon_key = cat.get("icon", "generic")
        icon_img = get_icon(icon_key)
        cat_name = cat.get("name", "")
        y = layout.category_row(c, cat_name, icon_img, y)

        items = cat.get("items", [])
        for item in items:
            if layout.is_overflow(y, c.h):
                break
            label = item.get("label", "")
            status = item.get("status", "UNKNOWN")
            y = layout.item_row(c, label, status, y)

    layout.footer(c, footer_text)

    return c.to_image()
