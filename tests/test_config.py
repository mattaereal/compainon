"""Tests for config loading."""

import pytest
import tempfile
import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_health_board.config import load_config, AppConfig, DisplayConfig


def test_load_valid_config():
    yaml_content = """
refresh_seconds: 60
timezone: UTC
display:
  backend: mock
  width: 122
  height: 250
  rotation: 0
  full_refresh_every_n_updates: 3
screens:
  - name: Test
    template: status_board
    categories:
      - name: TestService
        url: https://example.com/api/summary.json
        type: statuspage
        items:
          - key: comp1
            label: Comp1
          - key: comp2
            label: Comp2
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        fname = f.name

    try:
        cfg = load_config(fname)
        assert isinstance(cfg, AppConfig)
        assert cfg.refresh_seconds == 60
        assert cfg.timezone == "UTC"
        assert isinstance(cfg.display, DisplayConfig)
        assert cfg.display.backend == "mock"
        assert cfg.display.full_refresh_every_n_updates == 3
        assert len(cfg.screens) == 1
        s = cfg.screens[0]
        assert s.template == "status_board"
        assert len(s.categories) == 1
        assert s.categories[0].name == "TestService"
    finally:
        os.unlink(fname)


def test_load_config_defaults():
    yaml_content = """
refresh_seconds: 60
display:
  backend: mock
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        fname = f.name

    try:
        cfg = load_config(fname)
        assert cfg.refresh_seconds == 60
        assert cfg.display.backend == "mock"
        assert cfg.display.full_refresh_every_n_updates == 50
    finally:
        os.unlink(fname)


def test_load_config_invalid_refresh():
    yaml_content = """
refresh_seconds: -1
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        fname = f.name

    try:
        with pytest.raises(ValueError, match="refresh_seconds must be positive"):
            load_config(fname)
    finally:
        os.unlink(fname)


def test_load_config_no_screens(caplog):
    yaml_content = """
refresh_seconds: 300
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        fname = f.name

    try:
        with caplog.at_level(logging.WARNING):
            cfg = load_config(fname)
        assert len(cfg.screens) == 0
        assert "No screens configured" in caplog.text
    finally:
        os.unlink(fname)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
