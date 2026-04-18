"""Waveshare 2.13" V3 e-paper display backend.

Based on the working epd_2in13_V3_test.py patterns:
- Driver: waveshare_epd.epd2in13_V3
- EPD resolution: width=122, height=250 (portrait)
- Image created as (epd.height, epd.width) = (250, 122) in landscape
- getbuffer() auto-rotates if dimensions match (height, width)
- fill=255 for white, fill=0 for black in mode '1'
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Union

from PIL import Image, ImageDraw

from ..display.base import DisplayBackend
from ..config import DisplayConfig

logger = logging.getLogger(__name__)

try:
    from waveshare_epd import epd2in13_V3  # type: ignore
except Exception:
    epd2in13_V3 = None

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


class Waveshare2in13V3Display(DisplayBackend):
    """Waveshare 2.13" V3 b/w e-paper display backend."""

    def __init__(self, config: Union[DisplayConfig, Dict[str, Any]]):
        self._epd = None
        self._update_count = 0
        self._full_refresh_every = _get_display_value(
            config, "full_refresh_every_n_updates", 6
        )
        self._init_display()
        # After init, read actual resolution from the driver
        self._width = self._epd.width  # 122
        self._height = self._epd.height  # 250
        # Create image in landscape: (height, width) so getbuffer auto-rotates
        self._img: Image.Image = Image.new("1", (self._height, self._width), 255)
        self._draw = ImageDraw.Draw(self._img)
        logger.info(
            f"Waveshare2in13V3 initialized: "
            f"EPD {self._width}x{self._height}, "
            f"image {self._height}x{self._width}"
        )

    def _init_display(self) -> None:
        if epd2in13_V3 is None:
            raise RuntimeError(
                "waveshare_epd.epd2in13_V3 not available. "
                "Install: sudo apt install python3-lgpio python3-spidev && "
                "git clone https://github.com/waveshareteam/e-Paper && "
                "cd e-Paper/RaspberryPi_JetsonNano/python && "
                "sudo python3 setup.py install"
            )
        try:
            self._epd = epd2in13_V3.EPD()
            self._epd.init()
            self._epd.Clear(0xFF)
            logger.info("EPD 2in13 V3 init OK")
        except Exception as e:
            logger.error(f"EPD init failed: {e}")
            raise

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
        # Image is (250, 122) landscape; getbuffer will rotate to (122, 250)
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

        self._push_to_epaper()

    def _push_to_epaper(self) -> None:
        if self._epd is None:
            logger.warning("EPD not initialized, skipping flush")
            return
        try:
            buf = self._epd.getbuffer(self._img)
            self._epd.display(buf)
            self._update_count += 1
            logger.debug(f"EPD frame flushed (update #{self._update_count})")
        except Exception as e:
            logger.error(f"EPD flush error: {e}", exc_info=True)

    def flush(self) -> None:
        pass
