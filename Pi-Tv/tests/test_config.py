from pitv.config import get_last_country, get_merged_theme, get_theme
from pitv.ui.window import DEFAULT_THEME


def test_get_merged_theme_includes_defaults_and_overrides(monkeypatch) -> None:
    monkeypatch.setattr(
        "pitv.config.load_config",
        lambda: {"theme": {"bg": "#000000", "overlay_channel": "#ff0000"}},
    )

    theme = get_merged_theme()

    assert theme["bg"] == "#000000"
    assert theme["overlay_channel"] == "#ff0000"
    assert theme["sidebar_bg"] == DEFAULT_THEME["sidebar_bg"]


def test_get_last_country_normalizes_gb_to_uk(monkeypatch) -> None:
    monkeypatch.setattr(
        "pitv.config.load_config",
        lambda: {"last_country": "GB"},
    )
    assert get_last_country() == "UK"


def test_get_theme_returns_empty_dict_when_missing(monkeypatch) -> None:
    monkeypatch.setattr("pitv.config.load_config", lambda: {})
    assert get_theme() == {}
