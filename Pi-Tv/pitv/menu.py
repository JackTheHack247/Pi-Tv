"""Curses-based country selection menu."""

from __future__ import annotations

import curses
from typing import Literal

from .models import Country

MenuResult = Country | Literal["cancel"] | None


class CountryMenu:
    def __init__(
        self,
        countries: list[Country],
        initial_code: str | None = None,
        *,
        allow_cancel: bool = False,
    ) -> None:
        self.countries = countries
        self.selected = 0
        self.scroll = 0
        self.allow_cancel = allow_cancel
        self._initial_code = (initial_code or "").upper()

        if initial_code:
            for idx, country in enumerate(countries):
                if country.code.upper() == initial_code.upper():
                    self.selected = idx
                    break

    def run(self) -> MenuResult:
        return curses.wrapper(self._main)

    def _main(self, stdscr: curses.window) -> MenuResult:
        curses.curs_set(0)
        stdscr.keypad(True)
        curses.use_default_colors()

        if curses.has_colors():
            curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)
            curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)

        self._ensure_visible(stdscr)

        while True:
            self._draw(stdscr)
            key = stdscr.getch()

            if key in (curses.KEY_UP, ord("k")):
                if self.selected > 0:
                    self.selected -= 1
                    self._ensure_visible(stdscr)
            elif key in (curses.KEY_DOWN, ord("j")):
                if self.selected < len(self.countries) - 1:
                    self.selected += 1
                    self._ensure_visible(stdscr)
            elif key in (curses.KEY_PPAGE,):
                self.selected = max(0, self.selected - 10)
                self._ensure_visible(stdscr)
            elif key in (curses.KEY_NPAGE,):
                self.selected = min(len(self.countries) - 1, self.selected + 10)
                self._ensure_visible(stdscr)
            elif key in (curses.KEY_ENTER, 10, 13):
                country = self.countries[self.selected]
                if self.allow_cancel and country.code.upper() == self._initial_code:
                    return "cancel"
                return country
            elif key in (27, ord("q")):
                if self.allow_cancel:
                    return "cancel"
                return None

    def _ensure_visible(self, stdscr: curses.window) -> None:
        height, _ = stdscr.getmaxyx()
        list_height = max(1, height - 6)
        if self.selected < self.scroll:
            self.scroll = self.selected
        elif self.selected >= self.scroll + list_height:
            self.scroll = self.selected - list_height + 1

    def _draw(self, stdscr: curses.window) -> None:
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        title = "Pi-TV — Select your region"
        if self.allow_cancel:
            subtitle = "↑/↓ move  Enter select or close  Esc back to TV"
        else:
            subtitle = "↑/↓ move  Enter select  Q quit"

        stdscr.addstr(1, max(0, (width - len(title)) // 2), title[: width - 1], curses.A_BOLD)
        stdscr.addstr(2, max(0, (width - len(subtitle)) // 2), subtitle[: width - 1])

        list_top = 4
        list_height = max(1, height - list_top - 1)

        end = min(len(self.countries), self.scroll + list_height)
        for row, idx in enumerate(range(self.scroll, end)):
            country = self.countries[idx]
            label = f" {country.flag}  {country.name} ({country.code}) "
            y = list_top + row
            if idx == self.selected:
                stdscr.addstr(y, 2, label.ljust(width - 4)[: width - 3], curses.color_pair(1) | curses.A_BOLD)
            else:
                stdscr.addstr(y, 2, label[: width - 3])

        stdscr.refresh()
