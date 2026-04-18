#!/usr/bin/env python3
"""Main entrypoint for the AI health board application."""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ai_health_board.config import load_config, AppConfig
from ai_health_board.display import get_display
from ai_health_board.display.base import DisplayBackend
from ai_health_board.screens import create_screens
from ai_health_board.screens.base import Screen
from ai_health_board.scheduler import screen_loop
from ai_health_board.cache import load_cache
from ai_health_board.models import AppState, ServiceStatus, ProviderStatus

logger = logging.getLogger(__name__)


async def _run_once(screens: List[Screen], display: DisplayBackend) -> None:
    """Fetch and render all screens once."""
    from aiohttp import ClientSession

    async with ClientSession() as session:
        for i, screen in enumerate(screens):
            try:
                await screen.fetch(session)
                img = screen.render(display.width, display.height)
                display.render_image(img, full_refresh=True)
                logger.info(f"Rendered screen {screen.__class__.__name__}")
            except Exception as e:
                logger.error(f"Failed screen {screen.__class__.__name__}: {e}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="AI health status board for Raspberry Pi e-paper display"
    )
    parser.add_argument(
        "--config",
        default="config/providers.yaml",
        help="Path to providers YAML config",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    run_parser = subparsers.add_parser("run", help="Run as a long-running service")
    run_parser.add_argument(
        "--once-after",
        type=int,
        default=0,
        help="Initial delay in seconds before first refresh",
    )

    subparsers.add_parser("once", help="Perform one refresh cycle and exit")

    subparsers.add_parser("preview", help="Render a single PNG without hardware")

    subparsers.add_parser("doctor", help="Validate configuration and environment")

    args = parser.parse_args()

    from ai_health_board.logging_setup import setup_logging

    setup_logging()

    if args.command == "doctor":
        import platform
        import os

        print("=== Doctor Check ===")
        print(f"Python: {platform.python_version()}")
        try:
            cfg = load_config(args.config)
            print(
                f"Config: loaded ({len(cfg.providers)} provider(s), {len(cfg.screens)} screen(s))"
            )
        except Exception as e:
            print(f"Config: ERROR - {e}")
            sys.exit(1)

        try:
            import ai_health_board

            print("Imports: OK")
        except Exception as e:
            print(f"Imports: FAIL - {e}")

        try:
            import aiohttp

            print(f"aiohttp: {aiohttp.__version__}")
        except ImportError:
            print("aiohttp: MISSING (install with: pip install aiohttp)")

        gpio_factory = os.environ.get("GPIOZERO_PIN_FACTORY", "")
        print(f"GPIOZERO_PIN_FACTORY: {gpio_factory or 'NOT SET'}")
        if not gpio_factory:
            print("  Set: export GPIOZERO_PIN_FACTORY=lgpio")

        print("")
        spi_devs = ["/dev/spidev0.0", "/dev/spidev0.1"]
        spi_found = False
        for d in spi_devs:
            if os.path.exists(d):
                print(f"SPI device: {d} - EXISTS")
                spi_found = True
            else:
                print(f"SPI device: {d} - NOT FOUND")

        if not spi_found:
            print("  Enable: sudo raspi-config -> Interface Options -> SPI -> Enable")

        try:
            import lgpio

            print(f"\nlgpio: {lgpio.__version__}")
        except ImportError:
            print("\nlgpio: MISSING (sudo apt install python3-lgpio)")

        try:
            from waveshare_epd import epd2in13_V3

            print("waveshare_epd V3: INSTALLED")
        except ImportError:
            print("waveshare_epd V3: NOT INSTALLED")
            print("  git clone https://github.com/waveshareteam/e-Paper.git")
            print("  cd e-Paper/RaspberryPi_JetsonNano/python")
            print("  sudo apt install -y python3-setuptools")
            print("  sudo python3 setup.py install")

        print("\n=== End Doctor ===")
        return

    cfg = load_config(args.config)

    if args.command == "preview":
        display = get_display(cfg.display)
        screens = create_screens(cfg)
        if screens:
            img = screens[0].render(display.width, display.height)
            display.render_image(img, full_refresh=True)
        print("Preview rendered to out/frame.png")
        return

    if args.command == "once":
        display = get_display(cfg.display)
        screens = create_screens(cfg)
        asyncio.run(_run_once(screens, display))
        display.close()
        return

    if args.command == "run":
        logger.info("Starting screen-cycling loop")
        display = get_display(cfg.display)
        screens = create_screens(cfg)

        if args.once_after:
            logger.info(f"Initial delay {args.once_after}s before first refresh")
            import time

            time.sleep(args.once_after)

        try:
            asyncio.run(screen_loop(screens, display))
        except KeyboardInterrupt:
            logger.info("Shutting down")
        finally:
            display.close()
        return

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
