"""CLI behaviour for `python -m pitv.dvb_scan`."""

from __future__ import annotations

import pytest

from pitv import dvb_scan
from pitv.models import Country


def test_dvb_scan_imports_country_helpers() -> None:
    from pitv.app import _find_country, _prepare_countries

    assert callable(_prepare_countries)
    countries = [
        Country(name="United Kingdom", code="UK", flag=""),
        Country(name="Ireland", code="IE", flag=""),
    ]
    assert _find_country(countries, "ie") == countries[1]
    assert _find_country(countries, "gb") == countries[0]


@pytest.fixture
def fake_countries() -> list[Country]:
    return [
        Country(name="United Kingdom", code="UK", flag=""),
        Country(name="Ireland", code="IE", flag=""),
    ]


def test_main_returns_1_when_no_tv_hat(monkeypatch, fake_countries) -> None:
    monkeypatch.setattr(dvb_scan, "has_tv_hat", lambda: False)
    assert dvb_scan.main([]) == 1


def test_main_uses_last_country_when_no_arg(monkeypatch, fake_countries) -> None:
    monkeypatch.setattr(dvb_scan, "has_tv_hat", lambda: True)
    monkeypatch.setattr(dvb_scan, "_prepare_countries", lambda: fake_countries)
    monkeypatch.setattr(dvb_scan, "get_last_country", lambda: "UK")

    seen: list[Country] = []

    def fake_scan(country, progress=None, force=False, is_cancelled=None):
        seen.append(country)
        return [], None

    monkeypatch.setattr(dvb_scan, "scan_region", fake_scan)

    assert dvb_scan.main([]) == 0
    assert seen == [fake_countries[0]]


def test_main_scans_explicit_country(monkeypatch, fake_countries) -> None:
    monkeypatch.setattr(dvb_scan, "has_tv_hat", lambda: True)
    monkeypatch.setattr(dvb_scan, "_prepare_countries", lambda: fake_countries)
    monkeypatch.setattr(dvb_scan, "get_last_country", lambda: None)

    seen: list[Country] = []

    def fake_scan(country, progress=None, force=False, is_cancelled=None):
        seen.append(country)
        return [], None

    monkeypatch.setattr(dvb_scan, "scan_region", fake_scan)

    assert dvb_scan.main(["IE"]) == 0
    assert seen == [fake_countries[1]]


def test_main_rejects_unknown_country(monkeypatch, fake_countries) -> None:
    monkeypatch.setattr(dvb_scan, "has_tv_hat", lambda: True)
    monkeypatch.setattr(dvb_scan, "_prepare_countries", lambda: fake_countries)
    monkeypatch.setattr(dvb_scan, "get_last_country", lambda: None)

    assert dvb_scan.main(["ZZ"]) == 1


def test_main_all_iterates_every_country(monkeypatch, fake_countries) -> None:
    monkeypatch.setattr(dvb_scan, "has_tv_hat", lambda: True)
    monkeypatch.setattr(dvb_scan, "_prepare_countries", lambda: fake_countries)

    seen: list[Country] = []

    def fake_scan(country, progress=None, force=False, is_cancelled=None):
        seen.append(country)
        return [], None

    monkeypatch.setattr(dvb_scan, "scan_region", fake_scan)

    assert dvb_scan.main(["--all"]) == 0
    assert seen == fake_countries


def test_main_country_and_all_are_mutually_exclusive(monkeypatch, fake_countries) -> None:
    monkeypatch.setattr(dvb_scan, "has_tv_hat", lambda: True)
    monkeypatch.setattr(dvb_scan, "_prepare_countries", lambda: fake_countries)

    with pytest.raises(SystemExit):
        dvb_scan.main(["UK", "--all"])
