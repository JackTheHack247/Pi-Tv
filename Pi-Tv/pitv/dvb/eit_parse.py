"""Parse DVB Event Information Table (EIT) sections from the broadcast."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

# Modified Julian Date epoch used by DVB SI.
_MJD_EPOCH = date(1858, 11, 17)

# Present/following on the tuned transport stream.
EIT_PF_ACTUAL_TABLE_IDS = frozenset({0x4E, 0x4F})
# Schedule tables for the tuned transport stream.
EIT_SCHEDULE_ACTUAL_TABLE_IDS = frozenset(range(0x50, 0x60))
EIT_TABLE_IDS = EIT_PF_ACTUAL_TABLE_IDS | EIT_SCHEDULE_ACTUAL_TABLE_IDS

SHORT_EVENT_DESCRIPTOR = 0x4D
EXTENDED_EVENT_DESCRIPTOR = 0x4E


@dataclass(frozen=True)
class EitEvent:
    event_id: int
    start: datetime
    duration_seconds: int
    title: str
    subtitle: str = ""
    description: str = ""

    @property
    def end(self) -> datetime:
        return self.start + timedelta(seconds=self.duration_seconds)

    def is_on_air(self, moment: datetime | None = None) -> bool:
        now = moment or datetime.now(timezone.utc)
        return self.start <= now < self.end


def parse_sections(buffer: bytes) -> list[bytes]:
    """Split a demux read buffer into individual SI sections."""
    if not buffer:
        return []

    if buffer[0] == 0x47 and len(buffer) >= 188:
        return _sections_from_ts(buffer)

    sections: list[bytes] = []
    offset = 0
    while offset + 3 <= len(buffer):
        length = section_length(buffer[offset:])
        total = 3 + length
        if total < 8 or offset + total > len(buffer):
            break
        sections.append(buffer[offset : offset + total])
        offset += total
    return sections


def parse_eit_section(section: bytes) -> tuple[int, list[EitEvent]]:
    """
    Parse one EIT section.

    Returns:
        (service_id, events)
    """
    if len(section) < 14:
        return 0, []

    table_id = section[0]
    if table_id not in EIT_TABLE_IDS:
        return 0, []

    if not (section[1] & 0x80):
        return 0, []

    total = 3 + section_length(section)
    if total > len(section):
        total = len(section)

    service_id = (section[3] << 8) | section[4]
    payload_end = max(14, total - 4)  # drop trailing CRC when present
    payload = section[14:payload_end]
    events = _parse_events(payload)
    return service_id, events


def current_event(events: list[EitEvent], moment: datetime | None = None) -> EitEvent | None:
    """Return the event that is on air at the given moment."""
    now = moment or datetime.now(timezone.utc)
    for event in sorted(events, key=lambda item: item.start):
        if event.is_on_air(now):
            return event
    return None


def merge_events(existing: list[EitEvent], incoming: list[EitEvent]) -> list[EitEvent]:
    """Merge EIT events, preferring richer text for the same event id."""
    by_id: dict[int, EitEvent] = {event.event_id: event for event in existing}
    for event in incoming:
        current = by_id.get(event.event_id)
        if current is None:
            by_id[event.event_id] = event
            continue
        by_id[event.event_id] = EitEvent(
            event_id=event.event_id,
            start=event.start,
            duration_seconds=event.duration_seconds,
            title=event.title or current.title,
            subtitle=event.subtitle or current.subtitle,
            description=_prefer_text(current.description, event.description),
        )
    return sorted(by_id.values(), key=lambda item: item.start)


def section_length(section: bytes) -> int:
    return ((section[1] & 0x0F) << 8) | section[2]


def parse_dvb_time(raw: bytes) -> datetime:
    """Decode a 40-bit DVB date/time field (UTC)."""
    if len(raw) < 5:
        raise ValueError("DVB time field must be 5 bytes")

    mjd = (raw[0] << 8) | raw[1]
    day = _MJD_EPOCH + timedelta(days=mjd)
    hour = _bcd(raw[2])
    minute = _bcd(raw[3])
    second = _bcd(raw[4])
    return datetime(day.year, day.month, day.day, hour, minute, second, tzinfo=timezone.utc)


def parse_dvb_duration(raw: bytes) -> int:
    if len(raw) < 3:
        return 0
    hours = _bcd(raw[0])
    minutes = _bcd(raw[1])
    seconds = _bcd(raw[2])
    return hours * 3600 + minutes * 60 + seconds


def decode_dvb_text(raw: bytes) -> str:
    if not raw:
        return ""
    if raw[0] == 0x15:
        return raw[1:].decode("utf-8", errors="replace")
    return raw.decode("iso-8859-1", errors="replace")


def _sections_from_ts(buffer: bytes) -> list[bytes]:
    """Extract SI sections from 188-byte MPEG-TS packets."""
    pending: dict[int, bytearray] = {}

    for offset in range(0, len(buffer), 188):
        if offset + 188 > len(buffer):
            break
        packet = buffer[offset : offset + 188]
        if packet[0] != 0x47:
            continue

        payload_unit_start = bool(packet[1] & 0x40)
        pid = ((packet[1] & 0x1F) << 8) | packet[2]
        adaptation = (packet[3] & 0x30) >> 4
        index = 4

        if adaptation in (2, 3):
            index += 1 + packet[4]
        if adaptation in (1, 3):
            continue

        payload = packet[index:]
        if not payload:
            continue

        if payload_unit_start:
            pointer = payload[0]
            if pointer:
                pending.setdefault(pid, bytearray()).extend(payload[1 : 1 + pointer])
            payload = payload[1 + pointer :]

        pending.setdefault(pid, bytearray()).extend(payload)

    sections: list[bytes] = []
    for data in pending.values():
        sections.extend(parse_sections(bytes(data)))
    return sections


def _parse_events(payload: bytes) -> list[EitEvent]:
    events: list[EitEvent] = []
    offset = 0
    while offset + 12 <= len(payload):
        event_id = (payload[offset] << 8) | payload[offset + 1]
        start = parse_dvb_time(payload[offset + 2 : offset + 7])
        duration = parse_dvb_duration(payload[offset + 7 : offset + 10])
        desc_length = ((payload[offset + 10] & 0x0F) << 8) | payload[offset + 11]
        desc_start = offset + 12
        desc_end = desc_start + desc_length
        if desc_end > len(payload):
            break

        title, subtitle, description = _parse_descriptors(payload[desc_start:desc_end])
        events.append(
            EitEvent(
                event_id=event_id,
                start=start,
                duration_seconds=duration,
                title=title,
                subtitle=subtitle,
                description=description,
            )
        )
        offset = desc_end
    return events


def _parse_descriptors(data: bytes) -> tuple[str, str, str]:
    title = ""
    subtitle = ""
    description_parts: dict[int, str] = {}

    offset = 0
    while offset + 2 <= len(data):
        tag = data[offset]
        length = data[offset + 1]
        offset += 2
        end = offset + length
        if end > len(data):
            break
        body = data[offset:end]
        offset = end

        if tag == SHORT_EVENT_DESCRIPTOR and len(body) >= 4:
            name_len = body[3]
            title = decode_dvb_text(body[4 : 4 + name_len])
            text_offset = 4 + name_len
            if text_offset < len(body):
                text_len = body[text_offset]
                text = decode_dvb_text(body[text_offset + 1 : text_offset + 1 + text_len])
                if text and not subtitle:
                    subtitle = text
        elif tag == EXTENDED_EVENT_DESCRIPTOR and len(body) >= 6:
            desc_num = (body[0] >> 4) & 0x0F
            extended_last = (body[1] >> 4) & 0x0F
            items_len = body[5]
            text_offset = 6 + items_len
            if text_offset <= len(body):
                text = decode_dvb_text(body[text_offset:])
                description_parts[desc_num] = description_parts.get(desc_num, "") + text

    description = "".join(description_parts[index] for index in sorted(description_parts))
    return title, subtitle, description


def _prefer_text(left: str, right: str) -> str:
    if len(right) > len(left):
        return right
    return left


def _bcd(value: int) -> int:
    return ((value >> 4) & 0x0F) * 10 + (value & 0x0F)
