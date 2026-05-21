"""Main application loop."""

from __future__ import annotations

import sys

from .config import get_last_country
from .controller import AppController
from .dvb.device import has_tv_hat
from .dvb.scanfiles import resolve_scan_table
from .models import Country
from .ui.window import PitvApp


def _prepare_countries() -> list[Country]:
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

    try:
        countries = _prepare_countries()
    except OSError as exc:
        print(f"Could not prepare regions: {exc}", file=sys.stderr)
        return 1

    root = None
    app: PitvApp | None = None

    def on_update() -> None:
        if app is not None:
            app.root.after(0, app.refresh)

    controller = AppController(countries, on_update=on_update)
    controller.restore_region(get_last_country())

    import tkinter as tk

    root = tk.Tk()
    app = PitvApp(root, controller)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
