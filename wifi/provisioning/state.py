"""Explicit state machine for the Wi-Fi onboarding subsystem.

States
------
NORMAL_BOOT   – device is booting; waiting to see if Wi-Fi connects
SETUP_MODE    – hotspot is up, web UI is running, awaiting user input
USER_SUBMITS  – user submitted credentials; attempting connection
TEARDOWN      – connection succeeded; shutting down setup mode
FAILED        – last attempt failed; still in setup mode (retry possible)
"""

from __future__ import annotations

import enum
import logging
import time
from typing import Callable

logger = logging.getLogger(__name__)


class State(enum.Enum):
    NORMAL_BOOT = "normal_boot"
    SETUP_MODE = "setup_mode"
    USER_SUBMITS = "user_submits"
    TEARDOWN = "teardown"
    FAILED = "failed"


class StateMachine:
    def __init__(self) -> None:
        self._state: State = State.NORMAL_BOOT
        self._entered_at: float = time.monotonic()
        self._last_activity: float = time.monotonic()
        self._last_error: str = ""

    @property
    def state(self) -> State:
        return self._state

    @property
    def last_error(self) -> str:
        return self._last_error

    @property
    def seconds_in_state(self) -> float:
        return time.monotonic() - self._entered_at

    @property
    def idle_seconds(self) -> float:
        return time.monotonic() - self._last_activity

    def touch(self) -> None:
        self._last_activity = time.monotonic()

    def transition(self, new: State, error: str = "") -> None:
        old = self._state
        self._state = new
        self._entered_at = time.monotonic()
        self._last_activity = time.monotonic()
        self._last_error = error
        logger.info(
            "state transition: %s -> %s%s",
            old.value,
            new.value,
            f" (error: {error})" if error else "",
        )

    def to_dict(self) -> dict:
        return {
            "state": self._state.value,
            "last_error": self._last_error,
            "seconds_in_state": round(self.seconds_in_state, 1),
            "idle_seconds": round(self.idle_seconds, 1),
        }
