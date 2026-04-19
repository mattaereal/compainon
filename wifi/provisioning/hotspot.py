"""Hotspot lifecycle management.

Provides ``start`` / ``stop`` / ``is_active`` helpers that
coordinate nmcli hotspot operations with the state machine
and optional display hooks.
"""

from __future__ import annotations

import logging

from provisioning import config, nm, state

logger = logging.getLogger(__name__)


def start(sm: state.StateMachine) -> bool:
    """Start the setup hotspot and transition to SETUP_MODE.

    Returns True on success.
    """
    logger.info("starting setup hotspot …")

    if not nm.wifi_device_exists():
        sm.transition(state.State.FAILED, error="wlan0 device not found")
        logger.error("wlan0 not found – cannot start hotspot")
        return False

    ok = nm.start_hotspot()
    if not ok:
        sm.transition(state.State.FAILED, error="failed to start hotspot")
        return False

    sm.transition(state.State.SETUP_MODE)
    _display_hook(
        "SETUP MODE", f"SSID: {config.HOTSPOT_SSID}", f"http://{config.HOTSPOT_IP}"
    )
    return True


def stop(sm: state.StateMachine) -> bool:
    """Stop the setup hotspot."""
    logger.info("stopping setup hotspot …")
    nm.stop_hotspot()
    _display_hook("", "", "")
    return True


def is_active() -> bool:
    return nm.hotspot_active()


def _display_hook(line1: str, line2: str, line3: str) -> None:
    """Optionally push setup-mode info to the e-paper display.

    This is a no-op unless ``config.DISPLAY_HOOK_MODULE`` is set
    to a module path that exposes ``show_setup_info(line1, line2, line3)``.
    """
    mod_name = config.DISPLAY_HOOK_MODULE
    if not mod_name:
        return
    try:
        import importlib

        mod = importlib.import_module(mod_name)
        if hasattr(mod, "show_setup_info"):
            mod.show_setup_info(line1, line2, line3)
    except Exception as exc:
        logger.debug("display hook error (non-fatal): %s", exc)
