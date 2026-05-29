"""Resolve where durable state lives.

By default the SQLite DB + settings JSON sit next to the code (fine for
local dev). In production set DATA_DIR to a mounted persistent volume
(e.g. /data on Railway) so they survive redeploys — no code change per
deploy, just the env var.
"""
import os
from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent


def data_dir() -> Path:
    """Directory for durable state. DATA_DIR env var, else the package dir."""
    configured = (os.environ.get("DATA_DIR") or "").strip()
    return Path(configured) if configured else _PKG_DIR


def data_path(filename: str) -> Path:
    """Absolute path to a durable-state file inside data_dir()."""
    return data_dir() / filename


def ensure_parent(path: Path) -> None:
    """Make sure a file's directory exists before writing. Best-effort."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
