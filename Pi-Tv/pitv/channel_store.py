"""Serialize channels from DVB aerial scans."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .m3u_parser import Channel


def channel_to_dict(channel: Channel) -> dict[str, Any]:
    return asdict(channel)


def channel_from_dict(data: dict[str, Any]) -> Channel:
    return Channel(
        name=data["name"],
        url=data["url"],
        tvg_id=data.get("tvg_id", ""),
        tvg_logo=data.get("tvg_logo", ""),
        group_title=data.get("group_title", ""),
        duration=int(data.get("duration", -1)),
        attrs=dict(data.get("attrs", {})),
    )
