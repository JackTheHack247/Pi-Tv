"""Scan your aerial for channels in range (offline, no internet)."""

from __future__ import annotations

import sys

from .app import _find_country, _prepare_countries
from .config import get_last_country
from .dvb.device import has_tv_hat
from .dvb.scanner import scan_region


def main() -> int:
    if not has_tv_hat():
        print("No TV HAT found at /dev/dvb/adapter0", file=sys.stderr)
        print("Enable the overlay in /boot/config.txt: dtoverlay=tvhat", file=sys.stderr)
        return 1

    code = get_last_country()
    if len(sys.argv) > 1 and sys.argv[1] != "--all":
        code = sys.argv[1].upper()

    if code and sys.argv[-1] != "--all":
        countries = _prepare_countries()
        country = _find_country(countries, code)
        if country is None:
            print(f"Unknown region: {code}", file=sys.stderr)
            return 1
        scan_region(country, progress=lambda msg: print(msg, flush=True), force=True)
        return 0

    countries = _prepare_countries()
    print(f"Scanning aerial for {len(countries)} regions (only local transmitters)…", flush=True)
    for country in countries:
        try:
            scan_region(country, progress=lambda msg: print(f"{country.name}: {msg}", flush=True), force=True)
        except RuntimeError as exc:
            print(f"  {country.name}: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
