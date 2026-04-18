"""Lotus /stats endpoint provider."""

import logging
from typing import Any, Dict

from .base import StatusProvider, ServiceStatus

logger = logging.getLogger(__name__)


class LotusStatsProvider(StatusProvider):
    """Provider for the Lotus /stats endpoint.

    Expected response (all fields optional):
    {
      "prs_created": 12,
      "prs_merged": 8,
      "issues_created": 3,
      "comments_resolved": 47,
      "commits_today": 6,
      "lines_changed": 2340,
      "uptime_seconds": 86400,
      "last_action": "merged PR #142",
      "last_action_time": "2026-04-18T00:15:00Z"
    }
    """

    def __init__(self, display_name: str, url: str, component_keys: list):
        self._display_name = display_name
        self.url = url
        self.component_keys = component_keys

    def provider_type(self) -> str:
        return "lotus_stats"

    def display_name(self) -> str:
        return self._display_name

    async def fetch_status(self, session: Any, timeout: int = 10) -> Dict[str, Any]:
        import aiohttp

        resp = await session.get(self.url, timeout=aiohttp.ClientTimeout(total=timeout))
        resp.raise_for_status()
        return await resp.json()

    def normalize(self, raw: Dict[str, Any]) -> Dict[str, ServiceStatus]:
        return {}
