"""Waveshare 2.13" e-paper display backend."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Union

from PIL import Image, ImageDraw

from ..display.base import DisplayBackend
from ..models import ProviderStatus, ServiceStatus
from ..config import DisplayConfig

logger = logging.getLogger(__name__)

try:
    # Waveshare e-paper SPI library (v2 board)
    from waveshare_epd import epd2in13  # type: ignore
except Exception:
    epd2in13 = None
    logger.warning("waveshare_epd not installed; e-paper hardware will not work")

_STATUS_ICONS = {
    "OK": "[OK]",
    "DEGRADED": "[!]",
    "DOWN": "[X]",
    "UNKNOWN": "[?]",
}


def _get_display_value(
    config: Union[DisplayConfig, Dict[str, Any]], key: str, default: Any
) -> Any:
    """Helper to get value from either DisplayConfig or dict."""
    if isinstance(config, DisplayConfig):
        return getattr(config, key, default)
    return config.get(key, default)


def _norm_providers(raw: List[Any]) -> List[Dict[str, Any]]:
    """Normalize providers to dicts whether they come from objects or JSON."""
    result = []
    for p in raw:
        if isinstance(p, dict):
            result.append(p)
        else:
            result.append(p.to_dict())
    return result


def _provider_field(provider: Dict[str, Any], field: str, default: str = "") -> str:
    return provider.get(field, default)


class Waveshare2in13Display(DisplayBackend):
    """Waveshare 2.13" b/w e-paper display backend."""

    def __init__(self, config: Union[DisplayConfig, Dict[str, Any]]):
        self._width = _get_display_value(config, "width", 250)
        self._height = _get_display_value(config, "height", 122)
        self.rotation = _get_display_value(config, "rotation", 0)

        self._epd = None
        self._img: Image.Image = Image.new("1", (self._width, self._height), 1)
        self._draw = ImageDraw.Draw(self._img)
        self._init_display()

    def _init_display(self) -> None:
        if epd2in13 is None:
            raise RuntimeError(
                "waveshare_epd package not available. "
                "Install from: https://github.com/waveshareteam/e-Paper"
            )
        try:
            self._epd = epd2in13.EPD()
            logger.info("EPD 2in13 init OK")
            self._epd.init()
            self._epd.Clear(0xFF)  # Clear to white
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
        self._draw.rectangle([0, 0, self._width, self._height], fill=1)
        margin = 6
        line_h = 10
        start_y = 2

        self._draw.text((margin, start_y), "AI HEALTH", fill=0)
        start_y += line_h + 2

        ts = state.get("last_refresh")
        if ts:
            try:
                if isinstance(ts, str):
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                else:
                    dt = ts
                self._draw.text(
                    (margin, start_y), dt.strftime("%Y-%m-%d %H:%M:%S"), fill=0
                )
            except Exception:
                self._draw.text((margin, start_y), str(ts), fill=0)
        start_y += line_h + 4

        providers = _norm_providers(state.get("providers", []))
        for provider in providers:
            ptype = _provider_field(provider, "provider_type", "?").upper()
            pname = _provider_field(provider, "name", "?")
            pstatus = _provider_field(provider, "status", "UNKNOWN")
            agg_icon = _STATUS_ICONS.get(pstatus, "[?]")
            self._draw.text((margin, start_y), f"[{ptype}]", fill=0)
            self._draw.text((margin + 60, start_y), pname, fill=0)
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
                if len(text) > 30:
                    text = text[:27] + "..."
                self._draw.text((margin + 10, start_y), comp_icon, fill=0)
                self._draw.text((margin + 30, start_y), text, fill=0)
                start_y += line_h

            for comp in provider.components:
                self._draw.text((margin + 10, start_y), comp.status.icon(), fill=0)
                text = f"{comp.name}"
                if len(text) > 30:
                    text = text[:27] + "..."
                self._draw.text((margin + 30, start_y), text, fill=0)
                start_y += line_h

        start_y = self._height - line_h - 2
        footer = "last ok" if state.get("last_refresh") else "no data"
        if state.get("stale"):
            footer += " | STALE"
        self._draw.text((margin, start_y), footer, fill=0)

        if self.rotation in (90, 270):
            self._img = self._img.rotate(self.rotation, expand=1)

        self._push_to_epaper()

    def _push_to_epaper(self) -> None:
        if self._epd is None:
            logger.warning("EPD not initialized, skipping flush")
            return
        try:
            # Convert to monochrome bilevel
            mono = self._img.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
            self._epd.display(self._epd.getbuffer(mono))
            self._epd.sleep()  # Enter deep sleep to preserve power
            logger.debug("EPD frame flushed")
        except Exception as e:
            logger.error(f"EPD flush error: {e}", exc_info=True)

    def flush(self) -> None:
        # For Waveshare, flush is done in render; this is a no-op
        pass
