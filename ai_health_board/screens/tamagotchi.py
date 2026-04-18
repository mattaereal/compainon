"""Lotus tamagotchi screen with sprite-based character."""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from PIL import Image, ImageDraw

from .base import Screen
from ..models import LotusHealthStatus, LotusStatsData

logger = logging.getLogger(__name__)

_SPRITE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "img"
)
_SPRITE_FILES = ["irk_1.png", "irk_2.png", "irk_3.png", "irk_4.png"]
_SPRITE_W = 90
_SPRITE_H = 90


def _load_sprites() -> List[Image.Image]:
    sprites: List[Image.Image] = []
    for fname in _SPRITE_FILES:
        path = os.path.join(_SPRITE_DIR, fname)
        if os.path.exists(path):
            try:
                img = Image.open(path).convert("L")
                resized = img.resize((_SPRITE_W, _SPRITE_H), Image.LANCZOS)
                bw = resized.convert("1", dither=Image.FLOYDSTEINBERG)
                sprites.append(bw)
                logger.debug(f"Loaded sprite: {fname}")
            except Exception as e:
                logger.warning(f"Failed to load sprite {fname}: {e}")
    if not sprites:
        logger.warning("No sprites loaded, using fallback circle character")
    return sprites


class TamagotchiScreen(Screen):
    """Screen showing a Lotus tamagotchi character with sprite animation."""

    def __init__(
        self,
        url: str,
        poll_interval: int = 5,
        display_duration: int = 15,
        stats_url: str = "",
    ):
        self._url = url
        self._stats_url = stats_url
        self._poll_interval = poll_interval
        self._display_duration = display_duration
        self._health: Optional[LotusHealthStatus] = None
        self._stats: Optional[LotusStatsData] = None
        self._last_rendered_mood: Optional[str] = None
        self._last_rendered_pending: Optional[int] = None
        self._last_rendered_stats_hash: Optional[str] = None
        self._frame: int = 0
        self._sprites: List[Image.Image] = _load_sprites()

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

        if self._stats_url:
            try:
                stats_resp = await session.get(
                    self._stats_url, timeout=aiohttp.ClientTimeout(total=10)
                )
                stats_resp.raise_for_status()
                stats_data = await stats_resp.json()
                self._stats = LotusStatsData.from_dict(stats_data)
            except Exception as e:
                logger.debug(f"Stats fetch failed (non-critical): {e}")

    def render(self, width: int, height: int) -> Image.Image:
        img = Image.new("1", (width, height), 255)
        draw = ImageDraw.Draw(img)
        margin = 4
        line_h = 11

        draw.text((margin, 3), "LOTUS", fill=0)
        draw.line([(margin, 14), (width - margin, 14)], fill=0)

        mood = self._health.mood if self._health else "sad"

        sprite_y = 18
        if self._sprites:
            sprite = self._sprites[self._frame % len(self._sprites)]
            sx = (width - _SPRITE_W) // 2
            img.paste(sprite, (sx, sprite_y))
        else:
            self._draw_fallback_face(draw, width, sprite_y)

        text_y = sprite_y + _SPRITE_H + 6

        if self._health:
            icon = "[+]" if self._health.status == "ok" else "[-]"
            draw.text((margin, text_y), f"{icon} {self._health.status}", fill=0)
            text_y += line_h

            pending_label = (
                "idle"
                if self._health.pending == 0
                else f"{self._health.pending} pending"
            )
            draw.text((margin, text_y), pending_label, fill=0)
            text_y += line_h

        if self._stats:
            draw.text(
                (margin, text_y),
                f"PRs: +{self._stats.prs_created} M{self._stats.prs_merged}",
                fill=0,
            )
            text_y += line_h
            draw.text((margin, text_y), f"Issues: {self._stats.issues_created}", fill=0)
            text_y += line_h
            draw.text(
                (margin, text_y), f"Resolved: {self._stats.comments_resolved}", fill=0
            )
            text_y += line_h
            draw.text((margin, text_y), f"Commits: {self._stats.commits_today}", fill=0)
            text_y += line_h

            if self._stats.last_action:
                action = self._stats.last_action
                if len(action) > 20:
                    action = action[:17] + "..."
                draw.text((margin, text_y), action, fill=0)
                text_y += line_h

        if self._health and self._health.last_checked:
            ts = self._health.last_checked.strftime("%H:%M:%S")
            draw.text((margin, height - line_h - 2), f"{mood} | {ts}", fill=0)
        else:
            draw.text((margin, height - line_h - 2), f"mood: {mood}", fill=0)

        self._frame = (self._frame + 1) % max(len(self._sprites), 1)
        self._last_rendered_mood = mood
        self._last_rendered_pending = self._health.pending if self._health else 0
        self._last_rendered_stats_hash = self._stats_hash()

        return img

    def _draw_fallback_face(self, draw: ImageDraw.Draw, width: int, top_y: int) -> None:
        cx = width // 2
        cy = top_y + _SPRITE_H // 2
        face_r = 28
        eye_y = cy - 8
        left_eye_x = cx - 10
        right_eye_x = cx + 10
        mood = self._health.mood if self._health else "sad"

        draw.ellipse(
            [cx - face_r, cy - face_r, cx + face_r, cy + face_r],
            outline=0,
            width=1,
        )

        if self._frame % 2 == 1 and mood != "sad":
            draw.line(
                [(left_eye_x - 3, eye_y), (left_eye_x + 3, eye_y)], fill=0, width=1
            )
            draw.line(
                [(right_eye_x - 3, eye_y), (right_eye_x + 3, eye_y)], fill=0, width=1
            )
        else:
            draw.ellipse([left_eye_x - 3, eye_y - 3, left_eye_x + 3, eye_y + 3], fill=0)
            draw.ellipse(
                [right_eye_x - 3, eye_y - 3, right_eye_x + 3, eye_y + 3], fill=0
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
            draw.line([(cx - 6, mouth_y), (cx + 6, mouth_y)], fill=0, width=1)
        else:
            draw.arc(
                [cx - 8, mouth_y, cx + 8, mouth_y + 10],
                start=180,
                end=360,
                fill=0,
                width=1,
            )

    def has_changed(self) -> bool:
        if self._last_rendered_mood is None:
            return True
        mood = self._health.mood if self._health else "sad"
        pending = self._health.pending if self._health else 0
        if mood != self._last_rendered_mood or pending != self._last_rendered_pending:
            return True
        if self._stats_hash() != self._last_rendered_stats_hash:
            return True
        return False

    def _stats_hash(self) -> str:
        if self._stats is None:
            return ""
        return str(self._stats.to_dict())
