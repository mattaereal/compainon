"""Screen-cycling scheduler with input-driven interruption."""

import asyncio
import logging
import time
from typing import List, Optional

from .screens.base import Screen
from .display.base import DisplayBackend
from .input import InputManager

logger = logging.getLogger(__name__)


async def screen_loop(
    screens: List[Screen],
    display: DisplayBackend,
    input_mgr: Optional[InputManager] = None,
) -> None:
    """Cycle through screens, fetching and rendering as needed.

    Supports input-driven interruption:
    - SIGUSR1 (next_screen): skip to next screen immediately
    - SIGUSR2 (jump_tamagotchi): jump directly to tamagotchi screen

    For each screen:
    1. If poll_interval has elapsed, fetch new data
    2. Always render when switching screens; skip only if same screen and no change
    3. Wait up to display_duration (interruptible by input events)
    4. Move to next screen or jump per input
    """
    n = len(screens)
    if n == 0:
        logger.warning("No screens to cycle")
        return

    last_fetch_times: List[float] = [0.0] * n
    current_idx: int = 0
    prev_idx: int = -1

    from aiohttp import ClientSession

    async with ClientSession() as session:
        while True:
            screen = screens[current_idx]

            now = time.monotonic()
            if now - last_fetch_times[current_idx] >= screen.poll_interval:
                try:
                    await screen.fetch(session)
                    last_fetch_times[current_idx] = now
                    logger.debug(f"Fetched data for screen {screen.__class__.__name__}")
                except Exception as e:
                    logger.warning(
                        f"Fetch failed for screen {screen.__class__.__name__}: {e}"
                    )

            switching = current_idx != prev_idx
            if switching or screen.has_changed():
                try:
                    img = screen.render(display.width, display.height)
                    display.render_image(img)
                    prev_idx = current_idx
                    logger.debug(f"Rendered screen {screen.__class__.__name__}")
                except Exception as e:
                    logger.error(
                        f"Render failed for screen {screen.__class__.__name__}: {e}"
                    )

            interrupted = await _interruptible_sleep(screen.display_duration, input_mgr)

            if interrupted and input_mgr:
                if input_mgr.jump_tamagotchi.is_set():
                    input_mgr.jump_tamagotchi.clear()
                    if input_mgr.tamagotchi_idx is not None:
                        current_idx = input_mgr.tamagotchi_idx
                        logger.info("Jumping to tamagotchi screen")
                        continue
                    else:
                        logger.debug("No tamagotchi screen configured")
                if input_mgr.next_screen.is_set():
                    input_mgr.next_screen.clear()

            current_idx = (current_idx + 1) % n


async def _interruptible_sleep(
    duration: int, input_mgr: Optional[InputManager]
) -> bool:
    """Sleep for duration seconds, interrupted by input events.

    Returns True if interrupted by an input event, False if slept the full duration.
    """
    if input_mgr is None:
        await asyncio.sleep(duration)
        return False

    sleep_task = asyncio.ensure_future(asyncio.sleep(duration))
    next_task = asyncio.ensure_future(input_mgr.next_screen.wait())
    jump_task = asyncio.ensure_future(input_mgr.jump_tamagotchi.wait())

    try:
        done, pending = await asyncio.wait(
            [sleep_task, next_task, jump_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        return sleep_task in pending
    except Exception:
        for task in [sleep_task, next_task, jump_task]:
            if not task.done():
                task.cancel()
        return False
