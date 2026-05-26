"""Application state shared between the menu window and TV playback."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from .config import get_merged_theme, set_last_country
from .dvb.device import default_adapter
from .dvb.epg import DvbEpgDatabase
from .dvb.player import DvbPlayer
from .dvb.scanner import ScanCancelled, load_region_channels
from .models import Country

CLOSE_LABEL = "← Close"
BACK_TO_TV_LABEL = "← Back to TV"


class AppController:
    def __init__(
        self,
        countries: list[Country],
        on_update: Callable[[], None] | None = None,
    ) -> None:
        self._lock = threading.Lock()
        self._on_update = on_update
        self.countries = countries
        self.country: Country | None = None
        self.channels = []
        self.channels_conf: Path | None = None
        self.view = "regions"
        self.selected_index = 0
        self.status = ""
        self.busy = False
        self._cancel_requested = False
        self._view_before_busy = "regions"
        self._busy_generation = 0
        self._resume_tv_index: int | None = None

    def restore_region(self, code: str | None) -> None:
        if not code:
            return
        country = self._find_country(code)
        if country is None:
            return

        def work() -> None:
            generation = self._begin_busy(f"Loading channels for {country.name}…")
            try:
                channels, conf_path = load_region_channels(country)
            except RuntimeError as exc:
                if not self._is_cancelled(generation):
                    self._set_busy(False, str(exc))
                return

            if self._is_cancelled(generation):
                return

            with self._lock:
                self.country = country
                self.channels = channels
                self.channels_conf = conf_path
                self.view = "channels"
                self.selected_index = 0
            self._set_busy(False, "")

        threading.Thread(target=work, name="pitv-restore", daemon=True).start()

    def item_labels(self) -> list[str]:
        with self._lock:
            if self.busy:
                return [CLOSE_LABEL]
            if self.view == "regions":
                labels = [
                    f"{country.name} ({country.code})" for country in self.countries
                ]
                if self._resume_tv_index is not None:
                    return [BACK_TO_TV_LABEL] + labels
                return labels
            return [channel.name for channel in self.channels]

    def title(self) -> str:
        with self._lock:
            if self.view == "regions":
                return "Select your region"
            region = self.country.name if self.country else "Channels"
            return f"Channels — {region}"

    def subtitle(self) -> str:
        with self._lock:
            if self.view == "regions":
                if self._resume_tv_index is not None:
                    return "Press Enter on Back to TV to keep watching."
                return "Pick the transmitter network for your aerial."
            return "Choose a channel, then watch in the same Pi-TV window."

    def show_regions(self) -> None:
        with self._lock:
            self.view = "regions"
            self.selected_index = 0
            self._resume_tv_index = None
        self._notify()

    def offer_resume_tv(self, index: int) -> None:
        with self._lock:
            if not self.channels:
                self._resume_tv_index = None
                return
            index = max(0, min(index, len(self.channels) - 1))
            self._resume_tv_index = index
            self.view = "regions"
            self.selected_index = 0
        self._notify()

    def take_resume_tv(self) -> int | None:
        with self._lock:
            if self._resume_tv_index is None:
                return None
            index = self._resume_tv_index
            self._resume_tv_index = None
            self.view = "channels"
            self.selected_index = index
            return index

    def clear_resume_tv(self) -> None:
        with self._lock:
            self._resume_tv_index = None
        self._notify()

    def resume_tv_index(self) -> int | None:
        with self._lock:
            return self._resume_tv_index

    def menu_to_country_index(self, menu_index: int) -> int | None:
        with self._lock:
            if self._resume_tv_index is not None:
                if menu_index == 0:
                    return None
                return menu_index - 1
            if 0 <= menu_index < len(self.countries):
                return menu_index
            return None

    def menu_to_channel_index(self, menu_index: int) -> int | None:
        with self._lock:
            if 0 <= menu_index < len(self.channels):
                return menu_index
            return None

    def select_region(
        self,
        code: str,
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        country = self._find_country(code)
        if country is None:
            self._set_busy(False, f"Unknown region: {code}")
            return

        def work() -> None:
            generation = self._begin_busy(f"Scanning for {country.name} channels…")

            def progress(msg: str) -> None:
                if not self._is_cancelled(generation):
                    self._set_busy(True, msg)

            try:
                channels, conf_path = load_region_channels(
                    country,
                    progress=progress,
                    is_cancelled=lambda: self._is_cancelled(generation),
                )
            except ScanCancelled:
                return
            except RuntimeError as exc:
                if not self._is_cancelled(generation):
                    self._set_busy(False, str(exc))
                return

            if self._is_cancelled(generation):
                return

            set_last_country(country.code)
            with self._lock:
                self.country = country
                self.channels = channels
                self.channels_conf = conf_path
                self.view = "channels"
                self.selected_index = 0
            self._set_busy(False, "")
            if on_complete and not self._is_cancelled(generation):
                on_complete()

        threading.Thread(target=work, name="pitv-scan", daemon=True).start()

    def run_player(self, index: int, embed_wid: int | None = None) -> str:
        with self._lock:
            channels = list(self.channels)
            conf_path = self.channels_conf
            if channels:
                index = max(0, min(index, len(channels) - 1))
                self.selected_index = index

        if not channels or conf_path is None:
            self._set_busy(False, "No channels available.")
            return "menu"

        adapter = default_adapter()
        player = DvbPlayer(
            channels,
            conf_path,
            DvbEpgDatabase(adapter=adapter),
            adapter=adapter,
            start_index=index,
            show_on_screen_overlay=True,
            embed_wid=embed_wid,
            theme=get_merged_theme(),
        )
        result, last_index = player.run()
        with self._lock:
            self.selected_index = last_index
        return result

    def _find_country(self, code: str) -> Country | None:
        upper = code.upper()
        if upper == "GB":
            upper = "UK"
        for country in self.countries:
            if country.code.upper() == upper:
                return country
        return None

    def set_status(self, message: str) -> None:
        self._set_busy(False, message)

    def cancel_busy(self) -> bool:
        with self._lock:
            if not self.busy:
                return False
            self._cancel_requested = True
            self.view = self._view_before_busy
            self.selected_index = 0
            self.busy = False
            self.status = ""
            self._busy_generation += 1
        self._notify()
        return True

    def _begin_busy(self, message: str) -> int:
        with self._lock:
            self._view_before_busy = self.view
            self._cancel_requested = False
            self._busy_generation += 1
            generation = self._busy_generation
            self.busy = True
            self.status = message
            self.selected_index = 0
        self._notify()
        return generation

    def _is_cancelled(self, generation: int) -> bool:
        with self._lock:
            return self._cancel_requested or generation != self._busy_generation

    def _set_busy(self, busy: bool, message: str) -> None:
        with self._lock:
            self.busy = busy
            self.status = message
            if busy:
                self.selected_index = 0
        self._notify()

    def _notify(self) -> None:
        if self._on_update:
            self._on_update()
