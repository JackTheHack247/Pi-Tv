"""Parse channels.conf files produced by dvbv5-scan."""

from __future__ import annotations

import re
from pathlib import Path

from ..m3u_parser import Channel

SECTION_RE = re.compile(r"^\[(?P<name>.+)\]\s*$")


def parse_channels_conf(text: str, dvr_device: str) -> list[Channel]:
    channels: list[Channel] = []
    current_name: str | None = None
    attrs: dict[str, str] = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        section = SECTION_RE.match(line)
        if section:
            if current_name:
                channels.append(_make_channel(current_name, attrs, dvr_device))
            current_name = section.group("name").strip()
            attrs = {}
            continue

        if "=" in line and current_name:
            key, value = line.split("=", 1)
            attrs[key.strip()] = value.strip()

    if current_name:
        channels.append(_make_channel(current_name, attrs, dvr_device))

    return channels


def _make_channel(service_name: str, attrs: dict[str, str], dvr_device: str) -> Channel:
    return Channel(
        name=service_name,
        url=dvr_device,
        tvg_id=attrs.get("SERVICE_ID", service_name),
        group_title=attrs.get("NETWORK_NAME", "DVB-T/T2"),
        attrs={"dvb_service": service_name, **attrs},
    )


def load_channels_conf(path: Path, dvr_device: str) -> list[Channel]:
    return parse_channels_conf(path.read_text(encoding="utf-8", errors="replace"), dvr_device)
