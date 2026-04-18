"""Screen registry and factory."""

import logging
from typing import List

from .base import Screen
from ..config import AppConfig, ScreenConfig

logger = logging.getLogger(__name__)


def create_screens(config: AppConfig) -> List[Screen]:
    """Create screen instances from AppConfig."""
    screens: List[Screen] = []

    for sc in config.screens:
        if sc.template == "status_board":
            from .status_board import StatusBoardScreen

            screens.append(StatusBoardScreen(sc))
        elif sc.template == "tamagotchi":
            from .tamagotchi import TamagotchiScreen

            screens.append(TamagotchiScreen(sc))
        else:
            raise ValueError(f"Unknown screen template: {sc.template}")

    if not screens:
        from .status_board import StatusBoardScreen

        logger.info("No screens configured, defaulting to status_board")
        screens.append(
            StatusBoardScreen(ScreenConfig(name="Status", template="status_board"))
        )

    logger.info(f"Created {len(screens)} screen(s)")
    return screens
