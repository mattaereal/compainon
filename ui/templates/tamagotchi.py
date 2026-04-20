"""Tamagotchi template -- live data rendering.

Renders a sprite or fallback face, info lines from data,
and mood/timestamp footer. Used by core/screens/tamagotchi.py.
"""

from __future__ import annotations

from datetime import datetime

from PIL import Image

from ..canvas import Canvas
from .. import layout, MARGIN
from ..assets import load_sprite
from . import register

_SPRITE_W = 90
_SPRITE_H = 90


@register("tamagotchi")
def render(c: Canvas, data: dict) -> Image.Image:
    name = data.get("name", "")
    mood = data.get("mood", "idle")
    frame = data.get("frame", 0)
    sprites = data.get("sprites", {})
    info_lines = data.get("info_lines", [])
    fetch_error = data.get("fetch_error", False)
    last_checked = data.get("last_checked", "")

    c.text((MARGIN, 3), name, fill=0)
    c.hline(14, fill=0)

    sprite_y = 18
    sprite = sprites.get(mood)
    if not sprite:
        available = list(sprites.values())
        if available:
            sprite = available[frame % len(available)]

    if sprite:
        sx = (c.w - _SPRITE_W) // 2
        c.paste(sprite, (sx, sprite_y))
    else:
        _draw_fallback_face(c, mood, sprite_y, frame)

    text_y = sprite_y + _SPRITE_H + 6

    if fetch_error:
        c.text((MARGIN, text_y), "[-] connection error", fill=0)
    else:
        for line in info_lines:
            if text_y + layout.LINE_H_SMALL > c.h - layout.FOOTER_RESERVE:
                break
            label = line.get("label", "")
            value = line.get("value", "")
            text = f"{label}: {value}" if label else value
            c.text((MARGIN, text_y), text, fill=0)
            text_y += layout.LINE_H_SMALL

    footer_y = c.h - layout.LINE_H - 2
    if last_checked:
        try:
            dt = datetime.fromisoformat(last_checked)
            ts = dt.strftime("%H:%M:%S")
            c.text((MARGIN, footer_y), f"{mood} | {ts}", fill=0)
        except (ValueError, TypeError):
            c.text((MARGIN, footer_y), f"mood: {mood}", fill=0)
    else:
        c.text((MARGIN, footer_y), f"mood: {mood}", fill=0)

    return c.to_image()


def _draw_fallback_face(c: Canvas, mood: str, top_y: int, frame: int) -> None:
    cx = c.w // 2
    cy = top_y + _SPRITE_H // 2
    face_r = 28
    eye_y = cy - 8
    left_eye_x = cx - 10
    right_eye_x = cx + 10

    c.ellipse([cx - face_r, cy - face_r, cx + face_r, cy + face_r], outline=0, width=1)

    if frame % 2 == 1 and mood != "error":
        c.line([(left_eye_x - 3, eye_y), (left_eye_x + 3, eye_y)], fill=0, width=1)
        c.line([(right_eye_x - 3, eye_y), (right_eye_x + 3, eye_y)], fill=0, width=1)
    else:
        c.ellipse([left_eye_x - 3, eye_y - 3, left_eye_x + 3, eye_y + 3], fill=0)
        c.ellipse([right_eye_x - 3, eye_y - 3, right_eye_x + 3, eye_y + 3], fill=0)

    mouth_y = cy + 10
    if mood == "idle":
        c.arc(
            [cx - 8, mouth_y - 4, cx + 8, mouth_y + 6],
            start=0,
            end=180,
            fill=0,
            width=1,
        )
    elif mood == "working":
        c.line([(cx - 6, mouth_y), (cx + 6, mouth_y)], fill=0, width=1)
    else:
        c.arc(
            [cx - 8, mouth_y, cx + 8, mouth_y + 10], start=180, end=360, fill=0, width=1
        )
