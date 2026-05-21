"""Playback from the Raspberry Pi TV HAT (offline DVB-T/T2)."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from ..epg import ProgramInfo
from ..player import MpvPlayer
from .device import dvr_path


class DvbPlayer(MpvPlayer):
    """Tune services with dvbv5-zap and decode via mpv from the DVR device."""

    TUNE_WAIT_SECONDS = 2.0
    EPG_WAIT_SECONDS = 4.0

    def __init__(
        self,
        channels,
        channels_conf: Path,
        epg,
        adapter: int | None = None,
    ) -> None:
        super().__init__(channels, epg)
        self._channels_conf = channels_conf
        self._adapter = adapter if adapter is not None else 0
        self._dvr = dvr_path(self._adapter)
        self._zap_proc: subprocess.Popen | None = None
        self._last_overlay_title = ""

        if hasattr(self.epg, "set_on_update"):
            self.epg.set_on_update(self._on_epg_update)
        if hasattr(self.epg, "start"):
            self.epg.start()

    def _start_mpv(self) -> None:
        super()._start_mpv()
        # DVB streams are local — drop IPTV network timeout if present.
        self._ipc_command(["set_property", "network-timeout", 0])

    def _play_current(self, show_overlay: bool) -> None:
        channel = self.channels[self.index]
        service = channel.attrs.get("dvb_service", channel.name)
        self._stop_zap()

        self._zap_proc = subprocess.Popen(
            [
                "dvbv5-zap",
                "-a",
                str(self._adapter),
                "-c",
                str(self._channels_conf),
                "-r",
                service,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        time.sleep(self.TUNE_WAIT_SECONDS)
        self._ipc_command(["loadfile", self._dvr, "replace"])

        if show_overlay:
            self._last_overlay_title = ""
            self._show_overlay_for_current(wait_for_epg=True)

    def _show_overlay_for_current(self, wait_for_epg: bool = False) -> None:
        channel = self.channels[self.index]
        deadline = time.time() + (self.EPG_WAIT_SECONDS if wait_for_epg else 0)

        while True:
            info = self._program_info(channel)
            title = info.title if info else "Loading programme info…"
            if title != self._last_overlay_title:
                self._write_overlay(channel.name, info or self._loading_info())
                self._last_overlay_title = title
                self._overlay_deadline = time.time() + self.OVERLAY_SECONDS

            if title != "Loading programme info…" or time.time() >= deadline:
                break
            time.sleep(0.2)

    def _on_epg_update(self) -> None:
        if not hasattr(self, "_overlay_deadline"):
            return
        if time.time() > self._overlay_deadline:
            return
        channel = self.channels[self.index]
        info = self._program_info(channel)
        if info and info.title != "Loading programme info…":
            self._show_overlay_for_current(wait_for_epg=False)

    def _program_info(self, channel) -> ProgramInfo | None:
        info = self.epg.lookup(channel.tvg_id, channel.name)
        if info:
            return info
        if hasattr(self.epg, "has_data_for") and self.epg.has_data_for(
            channel.tvg_id, channel.name
        ):
            return ProgramInfo(title="Unknown programme", description="")
        return None

    @staticmethod
    def _loading_info() -> ProgramInfo:
        return ProgramInfo(
            title="Loading programme info…",
            description="Reading programme data from the broadcast.",
        )

    def _overlay_loop(self) -> None:
        while not self._stop_overlay.is_set():
            if hasattr(self, "_overlay_deadline") and time.time() <= self._overlay_deadline:
                channel = self.channels[self.index]
                info = self._program_info(channel)
                if info and info.title != self._last_overlay_title:
                    self._write_overlay(channel.name, info)
                    self._last_overlay_title = info.title
            elif hasattr(self, "_overlay_deadline") and time.time() > self._overlay_deadline:
                payload = {"visible": False}
                try:
                    self._overlay_path.write_text(json.dumps(payload), encoding="utf-8")
                except OSError:
                    pass
                self._overlay_deadline = time.time() + 3600
            time.sleep(0.2)

    def _stop_zap(self) -> None:
        if self._zap_proc and self._zap_proc.poll() is None:
            self._zap_proc.terminate()
            try:
                self._zap_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._zap_proc.kill()
        self._zap_proc = None

    def _shutdown(self) -> None:
        if hasattr(self.epg, "stop"):
            self.epg.stop()
        self._stop_zap()
        super()._shutdown()
