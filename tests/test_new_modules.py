"""Tests for new modules: LotusHealthStatus, LotusStatsData, LotusHealthProvider, screens."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_health_board.models import LotusHealthStatus, LotusStatsData, ServiceStatus
from ai_health_board.providers.lotus_health import LotusHealthProvider
from ai_health_board.providers.lotus_stats import LotusStatsProvider
from ai_health_board.screens.health import HealthScreen
from ai_health_board.screens.tamagotchi import TamagotchiScreen
from ai_health_board.screens import create_screens
from ai_health_board.config import (
    AppConfig,
    DisplayConfig,
    ScreenConfig,
    ProviderConfig,
)


# --- LotusHealthStatus ---


def test_lotus_health_happy():
    h = LotusHealthStatus(status="ok", proxy=True, pending=0)
    assert h.mood == "happy"


def test_lotus_health_working():
    h = LotusHealthStatus(status="ok", proxy=True, pending=5)
    assert h.mood == "working"


def test_lotus_health_sad():
    h = LotusHealthStatus(status="down", proxy=False, pending=0)
    assert h.mood == "sad"


def test_lotus_health_default():
    h = LotusHealthStatus()
    assert h.status == "unknown"
    assert h.mood == "sad"


def test_lotus_health_to_dict():
    h = LotusHealthStatus(status="ok", proxy=True, pending=0)
    d = h.to_dict()
    assert d["status"] == "ok"
    assert d["mood"] == "happy"
    assert d["proxy"] is True
    assert d["pending"] == 0


# --- LotusStatsData ---


def test_lotus_stats_defaults():
    s = LotusStatsData()
    assert s.prs_created == 0
    assert s.prs_merged == 0
    assert s.last_action == ""


def test_lotus_stats_to_dict():
    s = LotusStatsData(prs_created=5, prs_merged=3, last_action="merged PR #1")
    d = s.to_dict()
    assert d["prs_created"] == 5
    assert d["prs_merged"] == 3
    assert d["last_action"] == "merged PR #1"


def test_lotus_stats_from_dict():
    data = {
        "prs_created": 10,
        "prs_merged": 7,
        "issues_created": 2,
        "comments_resolved": 30,
        "commits_today": 4,
        "lines_changed": 1500,
        "uptime_seconds": 3600,
        "last_action": "pushed commit",
        "last_action_time": "2026-04-18T00:15:00Z",
    }
    s = LotusStatsData.from_dict(data)
    assert s.prs_created == 10
    assert s.prs_merged == 7
    assert s.last_action == "pushed commit"
    assert s.last_action_time is not None


def test_lotus_stats_from_dict_empty():
    s = LotusStatsData.from_dict({})
    assert s.prs_created == 0
    assert s.last_action == ""


# --- LotusHealthProvider ---


def test_lotus_provider_type():
    p = LotusHealthProvider(display_name="Lotus", url="http://test", component_keys=[])
    assert p.provider_type() == "lotus_health"


def test_lotus_provider_display_name():
    p = LotusHealthProvider(
        display_name="My Lotus", url="http://test", component_keys=[]
    )
    assert p.display_name() == "My Lotus"


def test_lotus_provider_normalize_ok():
    p = LotusHealthProvider(display_name="Lotus", url="http://test", component_keys=[])
    norm = p.normalize({"status": "ok", "proxy": True, "pending": 0})
    assert norm["Lotus"] == ServiceStatus.OK
    assert norm["Queue"] == ServiceStatus.OK
    assert norm["Proxy"] == ServiceStatus.OK


def test_lotus_provider_normalize_degraded():
    p = LotusHealthProvider(display_name="Lotus", url="http://test", component_keys=[])
    norm = p.normalize({"status": "ok", "proxy": False, "pending": 3})
    assert norm["Lotus"] == ServiceStatus.OK
    assert norm["Queue"] == ServiceStatus.DEGRADED
    assert norm["Proxy"] == ServiceStatus.DEGRADED


def test_lotus_provider_normalize_down():
    p = LotusHealthProvider(display_name="Lotus", url="http://test", component_keys=[])
    norm = p.normalize({"status": "down", "proxy": False, "pending": 0})
    assert norm["Lotus"] == ServiceStatus.DOWN


def test_lotus_provider_normalize_empty():
    p = LotusHealthProvider(display_name="Lotus", url="http://test", component_keys=[])
    norm = p.normalize({})
    assert norm["Lotus"] == ServiceStatus.UNKNOWN
    assert norm["Queue"] == ServiceStatus.OK
    assert norm["Proxy"] == ServiceStatus.DEGRADED


# --- LotusStatsProvider ---


def test_lotus_stats_provider_type():
    p = LotusStatsProvider(display_name="Stats", url="http://test", component_keys=[])
    assert p.provider_type() == "lotus_stats"


def test_lotus_stats_provider_display_name():
    p = LotusStatsProvider(
        display_name="My Stats", url="http://test", component_keys=[]
    )
    assert p.display_name() == "My Stats"


def test_lotus_stats_provider_normalize():
    p = LotusStatsProvider(display_name="Stats", url="http://test", component_keys=[])
    assert p.normalize({"prs_created": 5}) == {}


# --- ServiceStatus icon ---


def test_service_status_icons():
    assert ServiceStatus.OK.icon() == "[+]"
    assert ServiceStatus.DEGRADED.icon() == "[!]"
    assert ServiceStatus.DOWN.icon() == "[-]"
    assert ServiceStatus.UNKNOWN.icon() == "[?]"


# --- HealthScreen ---


def test_health_screen_defaults():
    s = HealthScreen(providers=[])
    assert s.poll_interval == 30
    assert s.display_duration == 30


def test_health_screen_render():
    s = HealthScreen(providers=[])
    img = s.render(122, 250)
    assert img.size == (122, 250)
    assert img.mode == "1"


def test_health_screen_has_changed_initial():
    s = HealthScreen(providers=[])
    assert s.has_changed() is True


def test_health_screen_has_changed_after_render():
    s = HealthScreen(providers=[])
    s.render(122, 250)
    assert s.has_changed() is False


def test_health_screen_icons():
    s = HealthScreen(providers=[])
    from ai_health_board.screens.health import _STATUS_ICONS

    assert _STATUS_ICONS["OK"] == "[+]"
    assert _STATUS_ICONS["DOWN"] == "[-]"
    assert _STATUS_ICONS["DEGRADED"] == "[!]"


# --- TamagotchiScreen ---


def test_tamagotchi_screen_defaults():
    s = TamagotchiScreen(url="http://test")
    assert s.poll_interval == 5
    assert s.display_duration == 15


def test_tamagotchi_screen_render():
    s = TamagotchiScreen(url="http://test")
    img = s.render(122, 250)
    assert img.size == (122, 250)
    assert img.mode == "1"


def test_tamagotchi_screen_has_changed_initial():
    s = TamagotchiScreen(url="http://test")
    assert s.has_changed() is True


def test_tamagotchi_screen_has_changed_after_render():
    s = TamagotchiScreen(url="http://test")
    s.render(122, 250)
    assert s.has_changed() is False


def test_tamagotchi_screen_has_changed_on_mood_change():
    s = TamagotchiScreen(url="http://test")
    s.render(122, 250)
    assert s.has_changed() is False
    s._health = LotusHealthStatus(status="ok", proxy=True, pending=3)
    assert s.has_changed() is True


def test_tamagotchi_screen_stats_url():
    s = TamagotchiScreen(url="http://test", stats_url="http://test/stats")
    assert s._stats_url == "http://test/stats"


def test_tamagotchi_screen_stats_change():
    s = TamagotchiScreen(url="http://test")
    s._health = LotusHealthStatus(status="ok", proxy=True, pending=0)
    s.render(122, 250)
    assert s.has_changed() is False
    s._stats = LotusStatsData(prs_created=5)
    assert s.has_changed() is True


# --- ScreenConfig ---


def test_screen_config_from_dict():
    data = {
        "refresh_seconds": 30,
        "display": {"backend": "mock"},
        "providers": [],
        "screens": [
            {
                "name": "health",
                "type": "health",
                "poll_interval": 30,
                "display_duration": 30,
            },
            {
                "name": "tamagotchi",
                "type": "tamagotchi",
                "poll_interval": 5,
                "display_duration": 15,
                "options": {"url": "http://test", "stats_url": "http://test/stats"},
            },
        ],
    }
    cfg = AppConfig.from_dict(data)
    assert len(cfg.screens) == 2
    assert cfg.screens[0].type == "health"
    assert cfg.screens[1].type == "tamagotchi"
    assert cfg.screens[1].options["url"] == "http://test"
    assert cfg.screens[1].options["stats_url"] == "http://test/stats"


def test_create_screens_default():
    cfg = AppConfig(display=DisplayConfig("mock"))
    screens = create_screens(cfg)
    assert len(screens) == 1
    assert isinstance(screens[0], HealthScreen)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
