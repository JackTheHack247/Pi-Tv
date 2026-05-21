"""Main application loop."""

from __future__ import annotations

import sys

from .config import get_last_country, set_last_country
from .dvb.device import default_adapter, has_tv_hat
from .dvb.epg import DvbEpgDatabase
from .dvb.player import DvbPlayer
from .dvb.scanfiles import resolve_scan_table
from .dvb.scanner import load_region_channels
from .menu import CountryMenu, MenuResult
from .models import Country


def _find_country(countries: list[Country], code: str | None) -> Country | None:
    if not code:
        return None
    upper = code.upper()
    for country in countries:
        if country.code.upper() == upper:
            return country
    return None


def _pick_country(
    countries: list[Country],
    initial_code: str | None = None,
    *,
    allow_cancel: bool = False,
) -> MenuResult:
    menu = CountryMenu(countries, initial_code=initial_code, allow_cancel=allow_cancel)
    return menu.run()


def _play_tvhat(country: Country) -> str:
    print(f"Scanning for {country.name} channels in range of your aerial…", flush=True)
    channels, conf_path = load_region_channels(
        country,
        progress=lambda msg: print(msg, flush=True),
    )
    print(f"Ready — {len(channels)} channels received over the air.", flush=True)

    adapter = default_adapter()
    player = DvbPlayer(
        channels,
        conf_path,
        DvbEpgDatabase(adapter=adapter),
        adapter=adapter,
    )
    return player.run()


def _prepare_countries() -> list[Country]:
    """
    Build the region menu from DVB-T/T2 scan tables installed on the system.

    Each entry is a transmitter network to scan — not a pre-made channel list.
    """
    from .data.dvb_countries import ALL_DVB_COUNTRIES, COUNTRY_ALIASES

    result: list[Country] = []
    for code in sorted(ALL_DVB_COUNTRIES):
        if code == "GB":
            continue
        if resolve_scan_table(code) is None:
            continue
        result.append(
            Country(
                name=COUNTRY_ALIASES.get(code, code),
                code=code,
                flag="",
            )
        )

    if not result:
        raise RuntimeError(
            "No DVB scan tables found. Install: sudo apt install dtv-scan-tables"
        )
    return sorted(result, key=lambda country: country.name.lower())


def run() -> int:
    if not has_tv_hat():
        print("No TV HAT found at /dev/dvb/adapter0.", file=sys.stderr)
        print("Add dtoverlay=tvhat to /boot/firmware/config.txt, reboot, then try again.", file=sys.stderr)
        return 1

    print("Pi-TV starting (offline DVB-T/T2)…", flush=True)

    try:
        countries = _prepare_countries()
    except OSError as exc:
        print(f"Could not prepare regions: {exc}", file=sys.stderr)
        return 1

    if not countries:
        print("No scan regions available. Try: python3 -m pitv.dvb_scan", file=sys.stderr)
        return 1

    last_code = get_last_country()
    show_menu = last_code is None

    while True:
        if show_menu:
            selected = _pick_country(
                countries,
                last_code,
                allow_cancel=last_code is not None,
            )
            if selected is None:
                return 0
            if selected == "cancel":
                show_menu = False
                selected = _find_country(countries, last_code)
                if selected is None:
                    show_menu = True
                    continue
            else:
                set_last_country(selected.code)
                last_code = selected.code
        else:
            selected = _find_country(countries, last_code)
            if selected is None:
                show_menu = True
                continue

        show_menu = False

        try:
            result = _play_tvhat(selected)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            show_menu = True
            continue

        if result == "quit":
            return 0
        if result == "menu":
            show_menu = True


if __name__ == "__main__":
    raise SystemExit(run())
