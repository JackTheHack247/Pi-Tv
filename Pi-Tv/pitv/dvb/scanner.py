"""Scan DVB-T/T2 services from the TV HAT and cache them locally."""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from ..channel_store import channel_from_dict, channel_to_dict
from ..config import cache_dir
from ..models import Country
from .channels_conf import load_channels_conf
from .device import default_adapter, dvr_path, has_tv_hat
from .scanfiles import resolve_scan_table

DVB_CACHE = cache_dir() / "dvb"


def region_dir(country_code: str) -> Path:
    return DVB_CACHE / country_code.lower()


def channels_conf_path(country_code: str) -> Path:
    return region_dir(country_code) / "channels.conf"


def channels_json_path(country_code: str) -> Path:
    return region_dir(country_code) / "channels.json"


def is_region_scanned(country_code: str, max_age_hours: float = 24 * 7) -> bool:
    path = channels_json_path(country_code)
    conf = channels_conf_path(country_code)
    if not path.exists() or not conf.exists():
        return False
    age_hours = (time.time() - path.stat().st_mtime) / 3600
    return age_hours < max_age_hours


def scan_region(
    country: Country,
    progress: Callable[[str], None] | None = None,
    force: bool = False,
) -> tuple[list, Path]:
    """
    Scan the aerial for channels actually in range of local transmitters.

    Only services received over the air are saved — nothing from the internet.
    """
    if not has_tv_hat():
        raise RuntimeError("No TV HAT or DVB adapter found at /dev/dvb/adapter0")

    scan_table = resolve_scan_table(country.code)
    if scan_table is None:
        raise RuntimeError(
            f"No DVB-T scan table for {country.name}. "
            "Install: sudo apt install dtv-scan-tables"
        )

    region_dir(country.code).mkdir(parents=True, exist_ok=True)
    conf_path = channels_conf_path(country.code)

    if force or not conf_path.exists() or conf_path.stat().st_size == 0:
        if progress:
            progress(
                f"Scanning local transmitters for {country.name} ({scan_table.name})…"
            )
            progress("Only channels your aerial can actually receive will be found.")
        adapter = default_adapter()
        cmd = [
            "dvbv5-scan",
            "-a",
            str(adapter),
            "-o",
            str(conf_path),
            str(scan_table),
        ]
        try:
            subprocess.run(cmd, check=True)
        except FileNotFoundError as exc:
            raise RuntimeError(
                "dvbv5-scan not found. Install: sudo apt install dvb5-tools"
            ) from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"Scan failed for {country.name}. Check the aerial is connected."
            ) from exc

    dvr = dvr_path()
    channels = load_channels_conf(conf_path, dvr)
    if not channels:
        raise RuntimeError(
            f"No channels received for {country.name}. "
            "Check your aerial and try: python3 -m pitv.dvb_scan"
        )

    payload = {
        "country": asdict(country),
        "scan_table": str(scan_table),
        "channels_conf": str(conf_path),
        "channel_count": len(channels),
        "scanned_at": int(time.time()),
        "channels": [channel_to_dict(channel) for channel in channels],
    }
    channels_json_path(country.code).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if progress:
        progress(f"Found {len(channels)} channels in range of your aerial.")
    return channels, conf_path


def load_region_channels(
    country: Country,
    progress: Callable[[str], None] | None = None,
    force_scan: bool = False,
) -> tuple[list, Path]:
    """Load channels from a previous scan, or scan the aerial if needed."""
    if not force_scan and is_region_scanned(country.code):
        data = json.loads(channels_json_path(country.code).read_text(encoding="utf-8"))
        channels = [channel_from_dict(item) for item in data.get("channels", [])]
        conf_path = Path(data.get("channels_conf", channels_conf_path(country.code)))
        if channels and conf_path.exists():
            if progress:
                progress(
                    f"Using {len(channels)} channels from your last aerial scan "
                    f"for {country.name}."
                )
            return channels, conf_path

    return scan_region(country, progress=progress, force=force_scan)
