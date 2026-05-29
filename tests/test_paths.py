"""Tests for DATA_DIR-based durable-state path resolution."""
from __future__ import annotations

from pathlib import Path

from spot_bot import paths


def test_defaults_to_package_dir(monkeypatch):
    monkeypatch.delenv("DATA_DIR", raising=False)
    assert paths.data_dir() == paths._PKG_DIR
    assert paths.data_path("history.db") == paths._PKG_DIR / "history.db"


def test_uses_data_dir_env(monkeypatch):
    monkeypatch.setenv("DATA_DIR", "/srv/spot-data")
    assert paths.data_dir() == Path("/srv/spot-data")
    assert paths.data_path("user_settings.json") == Path("/srv/spot-data/user_settings.json")


def test_blank_data_dir_falls_back(monkeypatch):
    monkeypatch.setenv("DATA_DIR", "   ")
    assert paths.data_dir() == paths._PKG_DIR


def test_ensure_parent_creates_dir(tmp_path):
    target = tmp_path / "nested" / "deeper" / "history.db"
    assert not target.parent.exists()
    paths.ensure_parent(target)
    assert target.parent.is_dir()


def test_ensure_parent_swallows_errors():
    # A path whose parent can't be created must not raise.
    paths.ensure_parent(Path("/dev/null/cannot/make/this/file.db"))


def test_db_path_resolves_via_data_path(monkeypatch, tmp_path):
    """history_db.DB_PATH is computed from data_path at import; recomputing
    with DATA_DIR set yields a path under the volume."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert paths.data_path("history.db") == tmp_path / "history.db"
