"""Offline programme info from the DVB broadcast (EIT)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import datetime, timezone

from ..epg import ProgramInfo
from .eit_collector import EitCollector
from .eit_parse import EitEvent, current_event, merge_events


class DvbEpgDatabase:
    """Programme guide built from EIT data in the transport stream."""

    def __init__(self, adapter: int = 0) -> None:
        self._lock = threading.Lock()
        self._events: dict[int, list[EitEvent]] = {}
        self._on_update: Callable[[], None] | None = None
        self._collector = EitCollector(adapter)
        self._started = False

    def set_on_update(self, callback: Callable[[], None] | None) -> None:
        self._on_update = callback

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._collector.start(self._ingest)

    def stop(self) -> None:
        self._collector.stop()
        self._started = False

    def lookup(self, tvg_id: str, channel_name: str = "") -> ProgramInfo | None:
        service_ids = _service_id_keys(tvg_id, channel_name)
        now = datetime.now(timezone.utc)

        with self._lock:
            for service_id in service_ids:
                events = self._events.get(service_id)
                if not events:
                    continue
                event = current_event(events, now)
                if event is None:
                    continue
                return ProgramInfo(
                    title=event.title or "Unknown programme",
                    subtitle=event.subtitle,
                    description=event.description,
                )

        return None

    def has_data_for(self, tvg_id: str, channel_name: str = "") -> bool:
        service_ids = _service_id_keys(tvg_id, channel_name)
        with self._lock:
            return any(service_id in self._events for service_id in service_ids)

    def _ingest(self, service_id: int, events: list[EitEvent]) -> None:
        updated = False
        with self._lock:
            merged = merge_events(self._events.get(service_id, []), events)
            if merged != self._events.get(service_id, []):
                self._events[service_id] = merged
                updated = True

        if updated and self._on_update:
            self._on_update()


def _service_id_keys(tvg_id: str, channel_name: str) -> list[int]:
    keys: list[int] = []
    if tvg_id.isdigit():
        keys.append(int(tvg_id))
    if channel_name.isdigit():
        value = int(channel_name)
        if value not in keys:
            keys.append(value)
    return keys
