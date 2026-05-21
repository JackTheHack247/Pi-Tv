"""Tests for DVB EIT parsing."""

from datetime import date, datetime, timezone

from pitv.dvb.eit_parse import (
    EitEvent,
    current_event,
    decode_dvb_text,
    merge_events,
    parse_dvb_duration,
    parse_dvb_time,
    parse_eit_section,
    parse_sections,
)
from pitv.dvb.epg import DvbEpgDatabase


def _bcd(value: int) -> int:
    tens, ones = divmod(value, 10)
    return (tens << 4) | ones


def _encode_dvb_time(moment: datetime) -> bytes:
    mjd = (moment.date() - date(1858, 11, 17)).days
    return bytes(
        [
            (mjd >> 8) & 0xFF,
            mjd & 0xFF,
            _bcd(moment.hour),
            _bcd(moment.minute),
            _bcd(moment.second),
        ]
    )


def _encode_duration(seconds: int) -> bytes:
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return bytes([_bcd(hours), _bcd(minutes), _bcd(secs)])


def _short_event_descriptor(title: str, text: str = "") -> bytes:
    title_bytes = title.encode("iso-8859-1")
    text_bytes = text.encode("iso-8859-1")
    body = b"eng" + bytes([len(title_bytes)]) + title_bytes + bytes([len(text_bytes)]) + text_bytes
    return bytes([0x4D, len(body)]) + body


def _extended_event_descriptor(text: str, number: int = 0, last: int = 0) -> bytes:
    text_bytes = text.encode("iso-8859-1")
    body = bytes([(number & 0x0F) << 4, (last & 0x0F) << 4]) + b"eng" + bytes([0]) + text_bytes
    return bytes([0x4E, len(body)]) + body


def _build_event(event_id: int, start: datetime, duration: int, descriptors: bytes) -> bytes:
    desc_len = len(descriptors)
    header = bytes(
        [
            (event_id >> 8) & 0xFF,
            event_id & 0xFF,
            *_encode_dvb_time(start),
            *_encode_duration(duration),
            (desc_len >> 8) & 0x0F,
            desc_len & 0xFF,
        ]
    )
    return header + descriptors


def _build_eit_section(service_id: int, events: bytes, table_id: int = 0x4E) -> bytes:
    payload = bytes(
        [
            (service_id >> 8) & 0xFF,
            service_id & 0xFF,
            0xC1,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            table_id,
        ]
    ) + events
    section_length = len(payload) + 4
    return bytes(
        [
            table_id,
            0x80 | ((section_length >> 8) & 0x0F),
            section_length & 0xFF,
        ]
    ) + payload + b"\x00\x00\x00\x00"


def test_parse_dvb_time_and_duration():
    moment = datetime(2024, 1, 15, 21, 30, tzinfo=timezone.utc)
    raw_time = _encode_dvb_time(moment)
    parsed = parse_dvb_time(raw_time)
    assert parsed.year == moment.year
    assert parsed.month == moment.month
    assert parsed.day == moment.day
    assert parsed.hour == 21
    assert parsed.minute == 30
    assert parse_dvb_duration(bytes([0x01, 0x00, 0x00])) == 3600


def test_decode_dvb_text_handles_utf8_prefix():
    assert decode_dvb_text(b"\x15EastEnders") == "EastEnders"
    assert decode_dvb_text(b"News") == "News"


def test_parse_eit_section_extracts_title_and_description():
    start = datetime(2024, 1, 15, 20, 0, tzinfo=timezone.utc)
    descriptors = _short_event_descriptor("EastEnders") + _extended_event_descriptor(
        "Ian learns the truth.", number=0, last=0
    )
    events = _build_event(1001, start, 3600, descriptors)
    section = _build_eit_section(49200, events)

    service_id, parsed = parse_eit_section(section)
    assert service_id == 49200
    assert len(parsed) == 1
    assert parsed[0].title == "EastEnders"
    assert "Ian learns the truth." in parsed[0].description


def test_current_event_selects_programme_on_air():
    now = datetime(2024, 1, 15, 20, 30, tzinfo=timezone.utc)
    events = [
        EitEvent(1, datetime(2024, 1, 15, 20, 0, tzinfo=timezone.utc), 3600, "EastEnders"),
        EitEvent(2, datetime(2024, 1, 15, 21, 0, tzinfo=timezone.utc), 1800, "News"),
    ]
    current = current_event(events, now)
    assert current is not None
    assert current.title == "EastEnders"


def test_merge_events_keeps_longer_description():
    first = EitEvent(1, datetime(2024, 1, 15, 20, 0, tzinfo=timezone.utc), 3600, "Show", description="Short")
    second = EitEvent(
        1,
        datetime(2024, 1, 15, 20, 0, tzinfo=timezone.utc),
        3600,
        "Show",
        description="Much longer description",
    )
    merged = merge_events([first], [second])
    assert merged[0].description == "Much longer description"


def test_dvb_epg_database_lookup_by_service_id():
    db = DvbEpgDatabase()
    now = datetime.now(timezone.utc)
    start = now.replace(minute=0, second=0, microsecond=0)
    db._ingest(49200, [EitEvent(1, start, 3600, "EastEnders", description="Drama.")])

    info = db.lookup("49200")
    assert info is not None
    assert info.title == "EastEnders"
    assert db.lookup("99999") is None


def test_parse_sections_splits_multiple_sections():
    section_a = _build_eit_section(
        1,
        _build_event(
            1,
            datetime(2024, 1, 15, 20, 0, tzinfo=timezone.utc),
            1800,
            _short_event_descriptor("A"),
        ),
    )
    section_b = _build_eit_section(
        2,
        _build_event(
            2,
            datetime(2024, 1, 15, 21, 0, tzinfo=timezone.utc),
            1800,
            _short_event_descriptor("B"),
        ),
    )
    sections = parse_sections(section_a + section_b)
    assert len(sections) == 2
