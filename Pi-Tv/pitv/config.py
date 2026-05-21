"""Persistent settings for Pi-TV."""

from __future__ import annotations

import json
import os
from pathlib import Path


def config_dir() -> Path:
    path = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "pitv"
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_dir() -> Path:
    path = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "pitv"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return config_dir() / "config.json"


def load_config() -> dict:
    path = config_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(data: dict) -> None:
    config_path().write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_last_country() -> str | None:
    code = load_config().get("last_country")
    if isinstance(code, str) and code.upper() == "GB":
        return "UK"
    return code


def set_last_country(code: str) -> None:
    data = load_config()
    data["last_country"] = code
    save_config(data)


def get_theme() -> dict:
    theme = load_config().get("theme", {})
    return theme if isinstance(theme, dict) else {}


def get_merged_theme() -> dict:
    from .ui.window import DEFAULT_THEME

    return {**DEFAULT_THEME, **get_theme()}
