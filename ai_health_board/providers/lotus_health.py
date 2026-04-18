"""Lotus health endpoint provider."""

import logging
from typing import Any, Dict

from .base import StatusProvider, ServiceStatus

logger = logging.getLogger(__name__)


class LotusHealthProvider(StatusProvider):
    """Provider for the Lotus health endpoint.

    Expected response: {"status": "ok", "proxy": true, "pending": 0}
    """

    def __init__(self, display_name: str, url: str, component_keys: list):
        self._display_name = display_name
        self.url = url
        self.component_keys = component_keys

    def provider_type(self) -> str:
        return "lotus_health"

    def display_name(self) -> str:
        return self._display_name

    async def fetch_status(self, session: Any, timeout: int = 10) -> Dict[str, Any]:
        import aiohttp

        resp = await session.get(self.url, timeout=aiohttp.ClientTimeout(total=timeout))
        resp.raise_for_status()
        return await resp.json()

    def normalize(self, raw: Dict[str, Any]) -> Dict[str, ServiceStatus]:
        result: Dict[str, ServiceStatus] = {}

        status_val = raw.get("status", "unknown")
        result["Lotus"] = self._infer_status_from_value(status_val)

        pending = raw.get("pending", 0)
        if pending > 0:
            result["Queue"] = ServiceStatus.DEGRADED
        else:
            result["Queue"] = ServiceStatus.OK

        proxy = raw.get("proxy", False)
        if proxy:
            result["Proxy"] = ServiceStatus.OK
        else:
            result["Proxy"] = ServiceStatus.DEGRADED

        return result
