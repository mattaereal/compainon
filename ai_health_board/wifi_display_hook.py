"""Display hook for the Wi-Fi onboarding subsystem.

When the wifi-setup service activates, it calls show_setup_info()
to render setup instructions on the e-paper display.

This module is loaded via WIFI_SETUP_DISPLAY_HOOK=ai_health_board.wifi_display_hook
set in the wifi-setup systemd service environment.
"""

import logging
import os
import sys

logger = logging.getLogger(__name__)

_DISPLAY = None


def _get_display():
    global _DISPLAY
    if _DISPLAY is not None:
        return _DISPLAY
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from ai_health_board.config import load_config
        from ai_health_board.display import get_display

        config = load_config(
            os.path.join(os.path.dirname(__file__), "..", "config", "providers.yaml")
        )
        _DISPLAY = get_display(config.display)
        return _DISPLAY
    except Exception as e:
        logger.warning(f"Could not initialize display for wifi hook: {e}")
        return None


def show_setup_info(line1: str, line2: str, line3: str) -> None:
    """Render wifi setup info on the e-paper display.

    Called by provisioning.hotspot._display_hook() when entering/leaving setup mode.
    With empty strings, clears the display.
    """
    display = _get_display()
    if display is None:
        return

    try:
        from PIL import Image, ImageDraw

        img = Image.new("1", (display.width, display.height), 255)
        draw = ImageDraw.Draw(img)

        if line1 or line2 or line3:
            y = 80
            for line in [line1, line2, line3]:
                if line:
                    draw.text((10, y), line, fill=0)
                y += 16

        display.render_image(img)
        logger.info(f"Display hook: rendered '{line1}' / '{line2}' / '{line3}'")
    except Exception as e:
        logger.warning(f"Display hook render failed: {e}")
