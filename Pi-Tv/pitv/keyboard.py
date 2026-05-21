"""Keyboard input helpers for console / Raspberry Pi."""

from __future__ import annotations

import glob
import os
import sys
from dataclasses import dataclass

if sys.platform == "win32":
    import msvcrt
else:
    import select
    import termios
    import tty


@dataclass(frozen=True)
class Key:
    name: str


KEY_UP = Key("up")
KEY_DOWN = Key("down")
KEY_ENTER = Key("enter")
KEY_ESC = Key("esc")


class KeyboardReader:
    """
    Read arrow keys for Pi-TV navigation.

    On Raspberry Pi, evdev is preferred so keys still work while mpv is fullscreen.
    Falls back to terminal input for development.
    """

    def __init__(self) -> None:
        self._fd = sys.stdin.fileno()
        self._old_term: list | None = None
        self._devices: list = []
        self._use_evdev = False

    @property
    def uses_evdev(self) -> bool:
        return self._use_evdev

    def __enter__(self) -> "KeyboardReader":
        if self._open_evdev():
            return self

        if sys.platform != "win32" and sys.stdin.isatty():
            self._old_term = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        for dev in self._devices:
            try:
                dev.close()
            except OSError:
                pass
        self._devices.clear()

        if self._old_term is not None:
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old_term)

    def _open_evdev(self) -> bool:
        if sys.platform == "win32":
            return False

        try:
            from evdev import InputDevice, ecodes, list_devices
        except ImportError:
            return False

        device_paths = list_devices()
        if not device_paths:
            device_paths = sorted(glob.glob("/dev/input/event*"))

        for path in device_paths:
            try:
                dev = InputDevice(path)
                caps = dev.capabilities()
                if ecodes.EV_KEY in caps and ecodes.KEY_UP in caps[ecodes.EV_KEY]:
                    dev.grab()
                    self._devices.append(dev)
            except (OSError, PermissionError):
                continue

        self._use_evdev = bool(self._devices)
        return self._use_evdev

    def read(self) -> Key | None:
        if self._use_evdev:
            return self._read_evdev()
        if sys.platform == "win32":
            return self._read_windows()
        return self._read_terminal()

    def _read_evdev(self) -> Key | None:
        from evdev import ecodes

        if not self._devices:
            return None

        readable, _, _ = select.select(self._devices, [], [], 0.05)
        for dev in readable:
            for event in dev.read():
                if event.type != ecodes.EV_KEY or event.value != 1:
                    continue
                if event.code in (ecodes.KEY_UP, ecodes.KEY_LEFT):
                    return KEY_UP
                if event.code in (ecodes.KEY_DOWN, ecodes.KEY_RIGHT):
                    return KEY_DOWN
                if event.code in (ecodes.KEY_ENTER, ecodes.KEY_KPENTER):
                    return KEY_ENTER
                if event.code in (ecodes.KEY_ESC, ecodes.KEY_BACK, ecodes.KEY_BACKSPACE, ecodes.KEY_EXIT):
                    return KEY_ESC
        return None

    def _read_windows(self) -> Key | None:
        if not msvcrt.kbhit():
            return None

        ch = msvcrt.getwch()
        if ch in ("\r", "\n"):
            return KEY_ENTER
        if ch == "\x1b":
            return KEY_ESC
        if ch == "\x00":
            ch = msvcrt.getwch()
            if ch == "H":
                return KEY_UP
            if ch == "P":
                return KEY_DOWN
        if ch == "\xe0":
            ch = msvcrt.getwch()
            if ch == "H":
                return KEY_UP
            if ch == "P":
                return KEY_DOWN
        return None

    def _read_terminal(self) -> Key | None:
        if not sys.stdin.isatty():
            return None

        if select.select([self._fd], [], [], 0.05)[0]:
            ch = os.read(self._fd, 1)
        else:
            return None

        if not ch:
            return None

        if ch in (b"\n", b"\r"):
            return KEY_ENTER
        if ch == b"\x1b":
            return self._read_escape()
        return None

    def _read_escape(self) -> Key:
        seq = b""
        if select.select([self._fd], [], [], 0.01)[0]:
            seq = os.read(self._fd, 2)
        if seq == b"[A":
            return KEY_UP
        if seq == b"[B":
            return KEY_DOWN
        return KEY_ESC
