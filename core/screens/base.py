"""Base screen interface for the multi-screen display system."""

from __future__ import annotations

import abc
from typing import Any

from PIL import Image


class Screen(abc.ABC):
    """Abstract screen for the multi-screen display system."""

    @abc.abstractmethod
    async def fetch(self, session: Any) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def render(self, width: int, height: int) -> Image.Image:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def poll_interval(self) -> int:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def display_duration(self) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def has_changed(self) -> bool:
        raise NotImplementedError
