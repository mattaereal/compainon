"""Screen registry and factory."""

import logging
from typing import List

from .base import Screen
from ..config import AppConfig

logger = logging.getLogger(__name__)


def create_screens(config: AppConfig) -> List[Screen]:
    """Create screen instances from AppConfig."""
    screens: List[Screen] = []

    for sc in config.screens:
        if sc.type == "health":
            from .health import HealthScreen

            screens.append(
                HealthScreen(
                    providers=config.providers,
                    poll_interval=sc.poll_interval,
                    display_duration=sc.display_duration,
                )
            )
        elif sc.type == "tamagotchi":
            from .tamagotchi import TamagotchiScreen

            url = sc.options.get("url", "")
            if not url:
                raise ValueError("Tamagotchi screen requires 'url' in options")
            screens.append(
                TamagotchiScreen(
                    url=url,
                    poll_interval=sc.poll_interval,
                    display_duration=sc.display_duration,
                )
            )
        else:
            raise ValueError(f"Unknown screen type: {sc.type}")

    if not screens:
        from .health import HealthScreen

        logger.info("No screens configured, defaulting to health screen")
        screens.append(HealthScreen(providers=config.providers))

    logger.info(f"Created {len(screens)} screen(s)")
    return screens
