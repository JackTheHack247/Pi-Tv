"""Scan your aerial for channels in range (offline, no internet).

Usage:
  python3 -m pitv.dvb_scan            # rescan the last-used country
  python3 -m pitv.dvb_scan UK         # rescan a specific country
  python3 -m pitv.dvb_scan --all      # rescan every country with a scan table
"""

from __future__ import annotations

import argparse
import sys

from .app import _find_country, _prepare_countries
from .config import get_last_country
from .dvb.device import has_tv_hat
from .dvb.scanner import ScanCancelled, scan_region


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m pitv.dvb_scan",
        description="Scan the Raspberry Pi TV HAT aerial for DVB-T/T2 channels.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "country",
        nargs="?",
        help="ISO country code to scan (e.g. UK, IE, DE). "
        "Defaults to your last-used country.",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Scan every country that has a DVB scan table installed.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if not has_tv_hat():
        print("No TV HAT found at /dev/dvb/adapter0", file=sys.stderr)
        print("Enable the overlay in /boot/config.txt: dtoverlay=tvhat", file=sys.stderr)
        return 1

    countries = _prepare_countries()

    if args.all:
        print(
            f"Scanning aerial for {len(countries)} regions (only local transmitters)…",
            flush=True,
        )
        for country in countries:
            try:
                scan_region(
                    country,
                    progress=lambda msg, name=country.name: print(
                        f"{name}: {msg}", flush=True
                    ),
                    force=True,
                )
            except ScanCancelled:
                print(f"  {country.name}: cancelled", file=sys.stderr)
            except RuntimeError as exc:
                print(f"  {country.name}: {exc}", file=sys.stderr)
        return 0

    code = args.country or get_last_country()
    if not code:
        print(
            "No country specified and no last-used country saved. "
            "Run `pitv` once, or pass a country code (e.g. `UK`).",
            file=sys.stderr,
        )
        return 1

    country = _find_country(countries, code)
    if country is None:
        print(f"Unknown region: {code}", file=sys.stderr)
        return 1

    try:
        scan_region(country, progress=lambda msg: print(msg, flush=True), force=True)
    except ScanCancelled:
        return 130
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
