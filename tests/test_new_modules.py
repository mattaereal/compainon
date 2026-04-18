"""Tests for new modules: LotusHealthStatus, LotusHealthProvider, screens."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_health_board.models import LotusHealthStatus, ServiceStatus
from ai_health_board.providers.lotus_health import LotusHealthProvider
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
                "options": {"url": "http://test"},
            },
        ],
    }
    cfg = AppConfig.from_dict(data)
    assert len(cfg.screens) == 2
    assert cfg.screens[0].type == "health"
    assert cfg.screens[1].type == "tamagotchi"
    assert cfg.screens[1].options["url"] == "http://test"


def test_create_screens_default():
    cfg = AppConfig(display=DisplayConfig("mock"))
    screens = create_screens(cfg)
    assert len(screens) == 1
    assert isinstance(screens[0], HealthScreen)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
