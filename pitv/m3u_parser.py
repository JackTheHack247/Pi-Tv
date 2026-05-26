"""Channel model used by DVB scan results and playback."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Channel:
    name: str
    url: str
    tvg_id: str = ""
    tvg_logo: str = ""
    group_title: str = ""
    duration: int = -1
    attrs: dict[str, str] = field(default_factory=dict)
