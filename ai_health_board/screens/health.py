"""AI health status screen (portrait layout)."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw

from .base import Screen
from ..models import AppState, ServiceStatus, ProviderStatus
from ..providers import get_provider
from ..config import ProviderConfig
from ..cache import load_cache, save_cache

logger = logging.getLogger(__name__)

_STATUS_ICONS = {
    "OK": "[OK]",
    "DEGRADED": "[!]",
    "DOWN": "[X]",
    "UNKNOWN": "[?]",
}


class HealthScreen(Screen):
    """Screen showing AI service health status in portrait layout."""

    def __init__(
        self,
        providers: List[ProviderConfig],
        poll_interval: int = 30,
        display_duration: int = 30,
    ):
        self._provider_configs = providers
        self._poll_interval = poll_interval
        self._display_duration = display_duration
        self._state: Optional[AppState] = None
        self._last_render_hash: Optional[str] = None

    @property
    def poll_interval(self) -> int:
        return self._poll_interval

    @property
    def display_duration(self) -> int:
        return self._display_duration

    async def fetch(self, session: Any) -> None:
        providers = []
        for pc in self._provider_configs:
            try:
                provider = get_provider(pc)
                providers.append(provider)
            except Exception as e:
                logger.error(f"Failed to create provider {pc.name}: {e}")

        tasks = [p.get_status(session) for p in providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        resolved: List[Optional[ProviderStatus]] = []
        for r in results:
            if isinstance(r, Exception):
                logger.warning(f"Provider fetch failed: {r}")
                resolved.append(None)
            else:
                resolved.append(r)

        cache = load_cache() or {}
        state = AppState(
            last_refresh=datetime.now(timezone.utc),
            providers=[r for r in resolved if r is not None],
            stale=False,
        )

        if cache and "providers" in cache:
            cached_provs = {p["name"]: p for p in cache["providers"]}
            for prov in state.providers:
                if prov.name in cached_provs:
                    cached = cached_provs[prov.name]
                    cached_map = {
                        c["name"]: c["status"] for c in cached.get("components", [])
                    }
                    for comp in prov.components:
                        if (
                            comp.status == ServiceStatus.UNKNOWN
                            and comp.name in cached_map
                        ):
                            comp.status = ServiceStatus(cached_map[comp.name])
                            comp.failure_count = cached.get("consecutive_failures", 0)

        save_cache(state.to_dict())
        self._state = state

    def render(self, width: int, height: int) -> Image.Image:
        img = Image.new("1", (width, height), 255)
        draw = ImageDraw.Draw(img)
        margin = 4
        line_h = 12
        y = 4

        draw.text((margin, y), "AI HEALTH", fill=0)
        y += line_h + 2

        if self._state and self._state.last_refresh:
            ts = self._state.last_refresh.strftime("%H:%M:%S")
            draw.text((margin, y), ts, fill=0)
        y += line_h + 2

        draw.line([(margin, y), (width - margin, y)], fill=0)
        y += 4

        if self._state:
            for prov in self._state.providers:
                if y + line_h > height - 14:
                    draw.text((margin, y), "...", fill=0)
                    break
                pstatus = prov.status.value
                icon = _STATUS_ICONS.get(pstatus, "[?]")
                name = prov.name
                if len(name) > 12:
                    name = name[:9] + "..."
                draw.text((margin, y), icon, fill=0)
                draw.text((margin + 26, y), name, fill=0)
                y += line_h

                for comp in prov.components:
                    if y + line_h > height - 14:
                        break
                    cicon = _STATUS_ICONS.get(comp.status.value, "[?]")
                    text = comp.name
                    if len(text) > 14:
                        text = text[:11] + "..."
                    draw.text((margin + 8, y), cicon, fill=0)
                    draw.text((margin + 30, y), text, fill=0)
                    y += line_h

        footer_y = height - line_h - 2
        footer = "ok" if self._state and self._state.last_refresh else "no data"
        if self._state and self._state.stale:
            footer += " | STALE"
        draw.text((margin, footer_y), footer, fill=0)

        self._last_render_hash = self._state_hash()
        return img

    def has_changed(self) -> bool:
        if self._last_render_hash is None:
            return True
        return self._state_hash() != self._last_render_hash

    def _state_hash(self) -> str:
        if self._state is None:
            return ""
        return str(self._state.to_dict())
