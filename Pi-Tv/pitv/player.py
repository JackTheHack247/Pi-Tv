"""mpv playback with channel switching and info overlay."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import tempfile
import textwrap
import threading
import time
from pathlib import Path

from .epg import ProgramInfo
from .keyboard import KEY_DOWN, KEY_ENTER, KEY_ESC, KEY_UP, KeyboardReader
from .m3u_parser import Channel


class MpvPlayer:
    OVERLAY_SECONDS = 6

    def __init__(
        self,
        channels: list[Channel],
        epg,
        embed_wid: int | None = None,
        theme: dict | None = None,
    ) -> None:
        if not channels:
            raise ValueError("No channels to play")

        self.channels = channels
        self.epg = epg
        self.embed_wid = embed_wid
        self.theme = theme or {}
        self.index = 0
        self.show_on_screen_overlay = True
        self._ipc_path = os.path.join(tempfile.gettempdir(), f"pitv-mpv-{os.getpid()}.sock")
        self._overlay_path = Path(tempfile.gettempdir()) / f"pitv-overlay-{os.getpid()}.json"
        self._proc: subprocess.Popen | None = None
        self._sock: socket.socket | None = None
        self._request_id = 0
        self._stop_overlay = threading.Event()
        self._overlay_thread: threading.Thread | None = None

    def run(self) -> tuple[str, int]:
        """
        Play channels until the user opens the country menu or quits.

        Returns:
            (action, channel_index) where action is "menu" or "quit".
        """
        self._start_mpv()
        try:
            self._play_current(show_overlay=True)
            with KeyboardReader() as kb:
                while True:
                    key = kb.read()
                    if key is None:
                        if self._proc and self._proc.poll() is not None:
                            return "quit", self.index
                        time.sleep(0.05)
                        continue

                    if key is KEY_UP:
                        self._change_channel(-1)
                    elif key is KEY_DOWN:
                        self._change_channel(1)
                    elif key is KEY_ENTER:
                        return "menu", self.index
                    elif key is KEY_ESC:
                        return "quit", self.index
        finally:
            self._shutdown()

    def _script_path(self) -> Path:
        return Path(__file__).with_name("overlay.lua")

    def _start_mpv(self) -> None:
        if os.path.exists(self._ipc_path):
            os.remove(self._ipc_path)

        env = os.environ.copy()
        env["PITV_OVERLAY_FILE"] = str(self._overlay_path)

        cmd = [
            "mpv",
            "--no-terminal",
            "--keep-open=yes",
            "--osc=no",
            "--cursor-autohide=always",
            "--input-default-bindings=no",
            "--input-vo-keyboard=no",
            "--input-media-keys=no",
            f"--input-ipc-server={self._ipc_path}",
            "--hwdec=auto-safe",
            "--cache=yes",
            "--demuxer-max-bytes=50MiB",
            "--network-timeout=15",
        ]

        if self.embed_wid is not None:
            cmd.extend([f"--wid={self.embed_wid}"])
            if not os.environ.get("PITV_VO"):
                cmd.extend(["--vo=x11"])
        else:
            cmd.extend(["--fs", "--force-window=immediate"])

        if self.show_on_screen_overlay:
            cmd.append(f"--script={self._script_path()}")

        if os.environ.get("PITV_VO"):
            cmd.extend(["--vo", os.environ["PITV_VO"]])
        if os.environ.get("PITV_NO_FULLSCREEN") and self.embed_wid is None:
            cmd.remove("--fs")

        self._proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        self._wait_for_ipc()
        self._connect_ipc()

        self._stop_overlay.clear()
        if self.show_on_screen_overlay:
            self._overlay_thread = threading.Thread(target=self._overlay_loop, daemon=True)
            self._overlay_thread.start()

    def _wait_for_ipc(self, timeout: float = 10.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if os.path.exists(self._ipc_path):
                return
            if self._proc and self._proc.poll() is not None:
                raise RuntimeError("mpv failed to start — is mpv installed?")
            time.sleep(0.05)
        raise RuntimeError("Timed out waiting for mpv IPC socket")

    def _connect_ipc(self) -> None:
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.connect(self._ipc_path)
        self._sock.settimeout(2.0)

    def _ipc_command(self, command: list) -> None:
        if not self._sock:
            return
        self._request_id += 1
        payload = json.dumps({"command": command, "request_id": self._request_id}) + "\n"
        try:
            self._sock.sendall(payload.encode("utf-8"))
        except OSError:
            pass

    def _change_channel(self, delta: int) -> None:
        self.index = (self.index + delta) % len(self.channels)
        self._play_current(show_overlay=True)

    def _play_current(self, show_overlay: bool) -> None:
        channel = self.channels[self.index]
        self._ipc_command(["loadfile", channel.url, "replace"])

        if show_overlay and self.show_on_screen_overlay:
            info = self._program_info(channel)
            self._write_overlay(channel.name, info)
            self._overlay_deadline = time.time() + self.OVERLAY_SECONDS

    def _program_info(self, channel: Channel) -> ProgramInfo:
        info = self.epg.lookup(channel.tvg_id, channel.name)
        if info:
            return info
        return ProgramInfo(title="Programme guide unavailable", description="")

    def _write_overlay(self, channel_name: str, info: ProgramInfo) -> None:
        program_line = info.title
        if info.subtitle:
            program_line = f"{info.title} — {info.subtitle}"

        description = textwrap.fill(info.description or "", width=42)
        payload = {
            "visible": True,
            "channel": channel_name,
            "program": program_line,
            "description": description,
            "index": self.index + 1,
            "total": len(self.channels),
            "theme": {
                key: value
                for key, value in self.theme.items()
                if key.startswith("overlay_")
            },
        }
        self._overlay_path.write_text(json.dumps(payload), encoding="utf-8")

    def _overlay_loop(self) -> None:
        while not self._stop_overlay.is_set():
            if hasattr(self, "_overlay_deadline") and time.time() > self._overlay_deadline:
                payload = {"visible": False}
                try:
                    self._overlay_path.write_text(json.dumps(payload), encoding="utf-8")
                except OSError:
                    pass
                self._overlay_deadline = time.time() + 3600
            time.sleep(0.2)

    def _shutdown(self) -> None:
        self._stop_overlay.set()
        if self._overlay_thread:
            self._overlay_thread.join(timeout=1)

        if self._sock:
            try:
                self._ipc_command(["quit"])
            except OSError:
                pass
            self._sock.close()
            self._sock = None

        if self._proc:
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None

        for path in (self._ipc_path, str(self._overlay_path)):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass
