"""Read EIT sections from the Linux DVB demux device."""

from __future__ import annotations

import os
import struct
import sys
import threading
from collections.abc import Callable

from .device import demux_paths
from .eit_parse import parse_eit_section, parse_sections

# linux/dvb/dmx.h
_DMX_FILTER_SIZE = 16
_DMX_SET_FILTER = 0x40106F20
_DMX_START = 0x20006F29
EIT_PID = 0x12

if sys.platform.startswith("linux"):
    import fcntl
else:
    fcntl = None  # type: ignore[assignment]


class EitCollector:
    """Background thread that listens for EIT sections on the DVB demux."""

    def __init__(self, adapter: int = 0) -> None:
        self._adapter = adapter
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._callback: Callable[[int, list], None] | None = None
        self._fd: int | None = None
        self._active_path: str | None = None

    @property
    def active_path(self) -> str | None:
        return self._active_path

    def start(self, callback: Callable[[int, list], None]) -> None:
        if not sys.platform.startswith("linux"):
            return
        if self._thread and self._thread.is_alive():
            return

        self._callback = callback
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="pitv-eit", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        fd = self._fd
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
            self._fd = None
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        self._active_path = None

    def _run(self) -> None:
        if fcntl is None:
            return

        for path in demux_paths(self._adapter):
            fd = self._open_demux(path)
            if fd is not None:
                self._read_loop(fd)
                return

    def _open_demux(self, path: str) -> int | None:
        if not os.path.exists(path):
            return None

        try:
            fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
        except OSError:
            return None

        try:
            fcntl.ioctl(fd, _DMX_SET_FILTER, _build_filter(EIT_PID))
            fcntl.ioctl(fd, _DMX_START, 0)
        except OSError:
            os.close(fd)
            return None

        self._fd = fd
        self._active_path = path
        return fd

    def _read_loop(self, fd: int) -> None:
        while not self._stop.is_set():
            try:
                data = os.read(fd, 4096)
            except BlockingIOError:
                self._stop.wait(0.25)
                continue
            except OSError:
                break

            if not data or not self._callback:
                continue

            for section in parse_sections(data):
                service_id, events = parse_eit_section(section)
                if service_id and events:
                    self._callback(service_id, events)

        try:
            os.close(fd)
        except OSError:
            pass
        if self._fd == fd:
            self._fd = None


def _build_filter(pid: int) -> bytes:
    # Accept all section types on the EIT PID; table ids are filtered in software.
    filter_bytes = bytes(_DMX_FILTER_SIZE)
    mask_bytes = bytes(_DMX_FILTER_SIZE)
    mode_bytes = bytes(_DMX_FILTER_SIZE)
    return struct.pack(
        "H16s16s16sII",
        pid,
        filter_bytes,
        mask_bytes,
        mode_bytes,
        0,
        0,
    )
