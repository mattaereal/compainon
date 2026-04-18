"""Mock display backend that writes PNG files.

Simulates the same layout as the Waveshare 2.13" V3 e-paper:
- EPD native: 122x250 (portrait)
- Image created in landscape: (250, 122)
- Output PNG saved in landscape orientation
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Union

from PIL import Image, ImageDraw

from ..display.base import DisplayBackend
from ..config import DisplayConfig

logger = logging.getLogger(__name__)

_STATUS_ICONS = {
    "OK": "[OK]",
    "DEGRADED": "[!]",
    "DOWN": "[X]",
    "UNKNOWN": "[?]",
}


def _get_display_value(
    config: Union[DisplayConfig, Dict[str, Any]], key: str, default: Any
) -> Any:
    if isinstance(config, DisplayConfig):
        return getattr(config, key, default)
    return config.get(key, default)


def _norm_providers(raw: List[Any]) -> List[Dict[str, Any]]:
    result = []
    for p in raw:
        if isinstance(p, dict):
            result.append(p)
        else:
            result.append(p.to_dict())
    return result


class MockPNGDisplay(DisplayBackend):
    """Renders status to a local PNG file (useful for testing on laptops)."""

    def __init__(self, config: Union[DisplayConfig, Dict[str, Any]]):
        # EPD native portrait resolution
        self._width = _get_display_value(config, "width", 122)
        self._height = _get_display_value(config, "height", 250)
        # Create landscape image matching V3 getbuffer() expectations
        self._img: Image.Image = Image.new("1", (self._height, self._width), 255)
        self._draw = ImageDraw.Draw(self._img)
        self._out_dir = "out"
        os.makedirs(self._out_dir, exist_ok=True)
        logger.info(
            f"MockPNGDisplay initialized (landscape {self._height}x{self._width})"
        )

    @property
    def size(self) -> tuple[int, int]:
        return (self._width, self._height)

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def render(self, state: Dict[str, Any]) -> None:
        # Image is landscape: (height=250, width=122)
        img_w = self._height  # 250
        img_h = self._width  # 122

        self._draw.rectangle([0, 0, img_w, img_h], fill=255)
        margin = 4
        line_h = 12
        start_y = 2

        # Title
        self._draw.text((margin, start_y), "AI HEALTH", fill=0)
        start_y += line_h + 2

        # Timestamp
        ts = state.get("last_refresh")
        if ts:
            try:
                if isinstance(ts, str):
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                else:
                    dt = ts
                self._draw.text(
                    (margin, start_y), dt.strftime("%Y-%m-%d %H:%M"), fill=0
                )
            except Exception:
                self._draw.text((margin, start_y), str(ts), fill=0)
        start_y += line_h + 2

        # Providers
        providers = _norm_providers(state.get("providers", []))
        for provider in providers:
            ptype = provider.get("provider_type", "?").upper()
            pname = provider.get("name", "?")
            pstatus = provider.get("status", "UNKNOWN")
            agg_icon = _STATUS_ICONS.get(pstatus, "[?]")
            self._draw.text((margin, start_y), f"[{ptype}]", fill=0)
            self._draw.text((margin + 55, start_y), pname, fill=0)
            self._draw.text((margin + 160, start_y), agg_icon, fill=0)
            start_y += line_h

            for comp in provider.get("components", []):
                if isinstance(comp, dict):
                    cstatus = comp.get("status", "UNKNOWN")
                    cname = comp.get("name", "?")
                else:
                    cstatus = comp.status.value
                    cname = comp.name
                comp_icon = _STATUS_ICONS.get(cstatus, "[?]")
                text = str(cname)
                if len(text) > 28:
                    text = text[:25] + "..."
                self._draw.text((margin + 8, start_y), comp_icon, fill=0)
                self._draw.text((margin + 28, start_y), text, fill=0)
                start_y += line_h

        # Footer
        start_y = img_h - line_h - 2
        footer = "ok" if state.get("last_refresh") else "no data"
        if state.get("stale"):
            footer += " | STALE"
        self._draw.text((margin, start_y), footer, fill=0)

    def flush(self) -> None:
        tmp_path = os.path.join(self._out_dir, "frame.png.tmp")
        final_path = os.path.join(self._out_dir, "frame.png")
        self._img.save(tmp_path, format="PNG")
        os.replace(tmp_path, final_path)
        logger.debug("Mock PNG written to out/frame.png")
