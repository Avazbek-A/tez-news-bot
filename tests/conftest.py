"""Pytest fixtures shared across tests.

Sets BOT_TOKEN to a dummy value before any spot_bot module is imported,
so tests don't fail at import time on the BOT_TOKEN check.
"""
import os
import tempfile
from pathlib import Path

# Must run before spot_bot.config is imported anywhere.
os.environ.setdefault("BOT_TOKEN", "test:dummy_token")

import pytest


@pytest.fixture
def temp_settings_path(monkeypatch):
    """Redirect settings persistence to a fresh temp file for the test."""
    tmpdir = Path(tempfile.mkdtemp())
    settings_file = tmpdir / "user_settings.json"
    from spot_bot import settings as settings_mod
    monkeypatch.setattr(settings_mod, "SETTINGS_PATH", settings_file)
    yield settings_file
