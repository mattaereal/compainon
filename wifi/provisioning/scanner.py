"""Wi-Fi scanner module.

Thin wrapper around ``nm.scan_networks`` that adds caching
and retry logic so the web UI can request scans without
spamming nmcli.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from provisioning import nm

logger = logging.getLogger(__name__)

_CACHE_TTL: float = 5.0
_last_scan_time: float = 0.0
_cached_networks: list[dict[str, Any]] = []


def scan(force: bool = False) -> list[dict[str, Any]]:
    """Return scanned networks, with a short cache to avoid hammering nmcli.

    Set *force* to True to force a fresh rescan.
    """
    global _last_scan_time, _cached_networks

    now = time.monotonic()
    if not force and (now - _last_scan_time) < _CACHE_TTL and _cached_networks:
        return _cached_networks

    try:
        _cached_networks = nm.scan_networks()
        _last_scan_time = now
    except Exception as exc:
        logger.warning("scan error (returning stale cache): %s", exc)
        if not _cached_networks:
            _cached_networks = []

    return _cached_networks
