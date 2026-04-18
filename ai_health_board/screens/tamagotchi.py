"""Lotus tamagotchi screen with pixel art character."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from PIL import Image, ImageDraw

from .base import Screen
from ..models import LotusHealthStatus

logger = logging.getLogger(__name__)


class TamagotchiScreen(Screen):
    """Screen showing a Lotus tamagotchi character based on health data."""

    def __init__(
        self,
        url: str,
        poll_interval: int = 5,
        display_duration: int = 15,
    ):
        self._url = url
        self._poll_interval = poll_interval
        self._display_duration = display_duration
        self._health: Optional[LotusHealthStatus] = None
        self._last_mood: Optional[str] = None
        self._last_pending: Optional[int] = None
        self._last_rendered_mood: Optional[str] = None
        self._last_rendered_pending: Optional[int] = None
        self._frame: int = 0

    @property
    def poll_interval(self) -> int:
        return self._poll_interval

    @property
    def display_duration(self) -> int:
        return self._display_duration

    async def fetch(self, session: Any) -> None:
        import aiohttp

        resp = await session.get(self._url, timeout=aiohttp.ClientTimeout(total=10))
        resp.raise_for_status()
        data = await resp.json()
        self._health = LotusHealthStatus(
            status=data.get("status", "unknown"),
            proxy=data.get("proxy", False),
            pending=data.get("pending", 0),
            last_checked=datetime.now(timezone.utc),
        )
        self._frame = (self._frame + 1) % 2

    def render(self, width: int, height: int) -> Image.Image:
        img = Image.new("1", (width, height), 255)
        draw = ImageDraw.Draw(img)
        margin = 4
        line_h = 12

        draw.text((margin, 4), "LOTUS", fill=0)
        draw.line([(margin, 16), (width - margin, 16)], fill=0)

        mood = self._health.mood if self._health else "sad"

        cx = width // 2
        cy = 85
        face_r = 28
        eye_y = cy - 8
        left_eye_x = cx - 10
        right_eye_x = cx + 10

        draw.ellipse(
            [cx - face_r, cy - face_r, cx + face_r, cy + face_r],
            outline=0,
            width=1,
        )

        if self._frame == 1 and mood != "sad":
            draw.line(
                [(left_eye_x - 3, eye_y), (left_eye_x + 3, eye_y)],
                fill=0,
                width=1,
            )
            draw.line(
                [(right_eye_x - 3, eye_y), (right_eye_x + 3, eye_y)],
                fill=0,
                width=1,
            )
        else:
            draw.ellipse(
                [left_eye_x - 3, eye_y - 3, left_eye_x + 3, eye_y + 3],
                fill=0,
            )
            draw.ellipse(
                [right_eye_x - 3, eye_y - 3, right_eye_x + 3, eye_y + 3],
                fill=0,
            )

        mouth_y = cy + 10
        if mood == "happy":
            draw.arc(
                [cx - 8, mouth_y - 4, cx + 8, mouth_y + 6],
                start=0,
                end=180,
                fill=0,
                width=1,
            )
        elif mood == "working":
            draw.line(
                [(cx - 6, mouth_y), (cx + 6, mouth_y)],
                fill=0,
                width=1,
            )
        else:
            draw.arc(
                [cx - 8, mouth_y, cx + 8, mouth_y + 10],
                start=180,
                end=360,
                fill=0,
                width=1,
            )
            tear_x = right_eye_x + 5
            draw.ellipse(
                [tear_x, eye_y + 4, tear_x + 3, eye_y + 9],
                fill=0,
            )

        text_y = cy + face_r + 16
        if self._health:
            draw.text((margin, text_y), f"status: {self._health.status}", fill=0)
            text_y += line_h
            draw.text((margin, text_y), f"pending: {self._health.pending}", fill=0)
            text_y += line_h
            proxy_str = "yes" if self._health.proxy else "no"
            draw.text((margin, text_y), f"proxy: {proxy_str}", fill=0)
            text_y += line_h
            if self._health.last_checked:
                ts = self._health.last_checked.strftime("%H:%M:%S")
                draw.text((margin, text_y), f"checked: {ts}", fill=0)
        else:
            draw.text((margin, text_y), "no data", fill=0)

        draw.text((margin, height - line_h - 2), f"mood: {mood}", fill=0)

        self._last_rendered_mood = mood
        self._last_rendered_pending = self._health.pending if self._health else 0

        return img

    def has_changed(self) -> bool:
        if self._last_rendered_mood is None:
            return True
        mood = self._health.mood if self._health else "sad"
        pending = self._health.pending if self._health else 0
        if mood != self._last_rendered_mood or pending != self._last_rendered_pending:
            return True
        return False
