"""Data models for AI health board."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ServiceStatus(str, Enum):
    OK = "OK"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"
    UNKNOWN = "UNKNOWN"

    def icon(self) -> str:
        mapping = {
            self.OK: "[+]",
            self.DEGRADED: "[!]",
            self.DOWN: "[-]",
            self.UNKNOWN: "[?]",
        }
        return mapping.get(self, "[?]")


@dataclass
class ComponentStatus:
    name: str
    status: ServiceStatus
    upstream_status: Optional[Any] = None
    upstream_output: Optional[Any] = None
    failure_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "upstream_status": self.upstream_status,
            "failure_count": self.failure_count,
        }


@dataclass
class ProviderStatus:
    name: str
    provider_type: str
    status: ServiceStatus = ServiceStatus.UNKNOWN
    components: List[ComponentStatus] = field(default_factory=list)
    last_successful_refresh: Optional[datetime] = None
    consecutive_failures: int = 0
    raw_upstream: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "provider_type": self.provider_type,
            "status": self.status.value,
            "components": [c.to_dict() for c in self.components],
            "last_successful_refresh": (
                self.last_successful_refresh.isoformat()
                if self.last_successful_refresh
                else None
            ),
            "consecutive_failures": self.consecutive_failures,
        }


@dataclass
class LotusHealthStatus:
    status: str = "unknown"
    proxy: bool = False
    pending: int = 0
    last_checked: Optional[datetime] = None

    @property
    def mood(self) -> str:
        if self.status == "ok" and self.pending == 0:
            return "happy"
        if self.status == "ok" and self.pending > 0:
            return "working"
        return "sad"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "proxy": self.proxy,
            "pending": self.pending,
            "mood": self.mood,
            "last_checked": (
                self.last_checked.isoformat() if self.last_checked else None
            ),
        }


@dataclass
class LotusStatsData:
    prs_created: int = 0
    prs_merged: int = 0
    issues_created: int = 0
    comments_resolved: int = 0
    commits_today: int = 0
    lines_changed: int = 0
    uptime_seconds: int = 0
    last_action: str = ""
    last_action_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prs_created": self.prs_created,
            "prs_merged": self.prs_merged,
            "issues_created": self.issues_created,
            "comments_resolved": self.comments_resolved,
            "commits_today": self.commits_today,
            "lines_changed": self.lines_changed,
            "uptime_seconds": self.uptime_seconds,
            "last_action": self.last_action,
            "last_action_time": (
                self.last_action_time.isoformat() if self.last_action_time else None
            ),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LotusStatsData":
        raw_time = data.get("last_action_time")
        last_action_time = None
        if raw_time:
            if isinstance(raw_time, str):
                try:
                    last_action_time = datetime.fromisoformat(
                        raw_time.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass
            elif isinstance(raw_time, datetime):
                last_action_time = raw_time
        return cls(
            prs_created=data.get("prs_created", 0),
            prs_merged=data.get("prs_merged", 0),
            issues_created=data.get("issues_created", 0),
            comments_resolved=data.get("comments_resolved", 0),
            commits_today=data.get("commits_today", 0),
            lines_changed=data.get("lines_changed", 0),
            uptime_seconds=data.get("uptime_seconds", 0),
            last_action=data.get("last_action", ""),
            last_action_time=last_action_time,
        )


@dataclass
class AppState:
    last_refresh: Optional[datetime] = None
    providers: List[ProviderStatus] = field(default_factory=list)
    stale: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "last_refresh": (
                self.last_refresh.isoformat() if self.last_refresh else None
            ),
            "stale": self.stale,
            "providers": [p.to_dict() for p in self.providers],
        }
