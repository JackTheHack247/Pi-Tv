"""Native Pi-TV menu window (no browser)."""

from __future__ import annotations

import os
import threading
import time
import tkinter as tk
from tkinter import font as tkfont

from ..config import get_merged_theme
from ..controller import AppController
from ..keyboard import KEY_DOWN, KEY_ENTER, KEY_ESC, KEY_UP, KeyboardReader


# Default colours — edit here or in ~/.config/pitv/config.json under "theme".
# Menu keys (bg, text, …) style the list window. overlay_* keys style the TV programme box.
DEFAULT_THEME = {
    "bg": "#ffffff",
    "text": "#111111",
    "sidebar_bg": "#f3f3f3",
    "sidebar_text": "#222222",
    "selected_bg": "#eeeeee",
    "muted": "#666666",
    "status_bg": "#fff8e1",
    "status_text": "#664d00",
    "border": "#dddddd",
    # EIT overlay while watching TV (see pitv/overlay.lua)
    "overlay_bg": "#111111d9",
    "overlay_border": "#666666",
    "overlay_channel": "#ffffff",
    "overlay_program": "#ffffff",
    "overlay_description": "#cccccc",
    "overlay_muted": "#888888",
    "overlay_radius": 10,
}


class PitvApp:
    WINDOW_TITLE = "Pi-TV"
    MIN_WIDTH = 880
    MIN_HEIGHT = 560

    def __init__(self, root: tk.Tk, controller: AppController) -> None:
        self.root = root
        self.controller = controller
        self.theme = get_merged_theme()
        self._closing = False
        self._mode = "menu"
        self._tv_thread: threading.Thread | None = None

        root.title(self.WINDOW_TITLE)
        root.configure(bg=self.theme["bg"])
        root.protocol("WM_DELETE_WINDOW", self._quit)
        self._apply_window_mode()

        self._build_layout()
        self._bind_keys()
        self._start_menu_keyboard()
        self.refresh()

    def _apply_window_mode(self) -> None:
        if os.environ.get("PITV_WINDOWED") == "1":
            self.root.minsize(self.MIN_WIDTH, self.MIN_HEIGHT)
            self.root.geometry(f"{self.MIN_WIDTH}x{self.MIN_HEIGHT}")
            return

        self.root.attributes("-fullscreen", True)
        try:
            self.root.wm_attributes("-fullscreen", True)
        except tk.TclError:
            pass

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.shell = tk.Frame(self.root, bg=self.theme["bg"])
        self.shell.grid(row=0, column=0, sticky="nsew")
        self.shell.columnconfigure(0, weight=1)
        self.shell.rowconfigure(0, weight=1)

        self.menu_frame = tk.Frame(self.shell, bg=self.theme["bg"])
        self.menu_frame.grid(row=0, column=0, sticky="nsew")
        self.menu_frame.columnconfigure(1, weight=1)
        self.menu_frame.rowconfigure(0, weight=1)

        self.video_frame = tk.Frame(self.shell, bg="#000000")
        self.video_frame.grid(row=0, column=0, sticky="nsew")
        self.video_frame.grid_remove()

        sidebar = tk.Frame(
            self.menu_frame,
            bg=self.theme["sidebar_bg"],
            width=240,
            padx=20,
            pady=24,
        )
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        title = tk.Label(
            sidebar,
            text="Pi-TV",
            bg=self.theme["sidebar_bg"],
            fg=self.theme["sidebar_text"],
            font=tkfont.Font(size=18, weight="bold"),
            anchor="w",
        )
        title.pack(fill="x")

        intro = tk.Label(
            sidebar,
            text="Offline live TV from your TV HAT.",
            bg=self.theme["sidebar_bg"],
            fg=self.theme["muted"],
            font=tkfont.Font(size=10),
            wraplength=200,
            justify="left",
            anchor="w",
        )
        intro.pack(fill="x", pady=(8, 24))

        for label, desc in (
            ("↑   ↓", "Move"),
            ("Enter", "Select / watch"),
            ("Enter", "Close while scanning"),
            ("Enter", "Back to menu (while watching)"),
            ("Enter", "Back to TV (country list)"),
            ("Esc", "Quit"),
        ):
            row = tk.Frame(sidebar, bg=self.theme["sidebar_bg"])
            row.pack(fill="x", pady=4)
            key = tk.Label(
                row,
                text=label,
                bg=self.theme["bg"],
                fg=self.theme["text"],
                width=8,
                padx=6,
                pady=2,
                relief="solid",
                borderwidth=1,
            )
            key.pack(side="left")
            text = tk.Label(
                row,
                text=desc,
                bg=self.theme["sidebar_bg"],
                fg=self.theme["sidebar_text"],
                anchor="w",
            )
            text.pack(side="left", padx=(10, 0))

        main = tk.Frame(self.menu_frame, bg=self.theme["bg"], padx=32, pady=28)
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1)

        self.heading = tk.Label(
            main,
            text="",
            bg=self.theme["bg"],
            fg=self.theme["text"],
            font=tkfont.Font(size=20, weight="bold"),
            anchor="w",
        )
        self.heading.grid(row=0, column=0, sticky="ew")

        self.subheading = tk.Label(
            main,
            text="",
            bg=self.theme["bg"],
            fg=self.theme["muted"],
            font=tkfont.Font(size=11),
            anchor="w",
        )
        self.subheading.grid(row=1, column=0, sticky="ew", pady=(6, 16))

        self.status = tk.Label(
            main,
            text="",
            bg=self.theme["status_bg"],
            fg=self.theme["status_text"],
            font=tkfont.Font(size=10),
            anchor="w",
            padx=12,
            pady=8,
        )
        self.status.grid(row=2, column=0, sticky="ew", pady=(0, 12))

        list_frame = tk.Frame(
            main,
            bg=self.theme["bg"],
            highlightbackground=self.theme["border"],
            highlightthickness=1,
        )
        list_frame.grid(row=3, column=0, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self.listbox = tk.Listbox(
            list_frame,
            activestyle="none",
            bg=self.theme["bg"],
            fg=self.theme["text"],
            selectbackground=self.theme["selected_bg"],
            selectforeground=self.theme["text"],
            highlightthickness=0,
            borderwidth=0,
            font=tkfont.Font(size=12),
            exportselection=False,
        )
        self.listbox.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.listbox.bind("<<ListboxSelect>>", self._on_list_select)

        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scrollbar.set)

        self.region_button = tk.Button(
            main,
            text="Change region",
            command=self._show_regions,
            bg=self.theme["bg"],
            fg=self.theme["text"],
            relief="solid",
            borderwidth=1,
            padx=10,
            pady=4,
        )
        self.region_button.grid(row=4, column=0, sticky="w", pady=(16, 0))

    def _bind_keys(self) -> None:
        self.root.bind_all("<Up>", lambda _event: self._move(-1))
        self.root.bind_all("<Down>", lambda _event: self._move(1))
        self.root.bind_all("<Return>", lambda _event: self._activate())
        self.root.bind_all("<Escape>", lambda _event: self._quit())
        self.listbox.bind("<Double-Button-1>", lambda _event: self._activate())

    def _start_menu_keyboard(self) -> None:
        thread = threading.Thread(
            target=self._menu_keyboard_loop,
            name="pitv-menu-keys",
            daemon=True,
        )
        thread.start()

    def _menu_keyboard_loop(self) -> None:
        while not self._closing:
            if self._mode != "menu":
                time.sleep(0.05)
                continue

            try:
                with KeyboardReader() as kb:
                    if not kb.uses_evdev:
                        time.sleep(0.2)
                        continue
                    while self._mode == "menu" and not self._closing:
                        key = kb.read()
                        if key is None:
                            continue
                        if key is KEY_ESC:
                            self.root.after(0, self._quit)
                        elif key is KEY_UP:
                            self.root.after(0, lambda: self._move(-1))
                        elif key is KEY_DOWN:
                            self.root.after(0, lambda: self._move(1))
                        elif key is KEY_ENTER:
                            self.root.after(0, self._activate)
            except OSError:
                time.sleep(0.2)

    def refresh(self) -> None:
        if self._closing or self._mode == "tv":
            return

        self.heading.configure(text=self.controller.title())
        self.subheading.configure(text=self.controller.subtitle())

        if self.controller.status:
            self.status.configure(text=self.controller.status)
            self.status.grid()
        else:
            self.status.grid_remove()

        if self.controller.busy:
            self.subheading.configure(
                text="Scanning… press Enter on Close to cancel."
            )

        labels = self.controller.item_labels()
        self.listbox.delete(0, tk.END)
        for label in labels:
            self.listbox.insert(tk.END, label)

        if labels:
            index = min(self.controller.selected_index, len(labels) - 1)
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(index)
            self.listbox.activate(index)
            self.listbox.see(index)
            self.controller.selected_index = index

        if self.controller.view == "channels" and not self.controller.busy:
            self.region_button.grid()
        else:
            self.region_button.grid_remove()

        self.listbox.configure(state=tk.NORMAL)

    def _on_list_select(self, _event=None) -> None:
        selection = self.listbox.curselection()
        if selection:
            self.controller.selected_index = selection[0]

    def _move(self, delta: int) -> None:
        if self._closing or self._mode == "tv":
            return
        if self.controller.busy:
            self.controller.selected_index = 0
            self.refresh()
            return
        labels = self.controller.item_labels()
        if not labels:
            return
        self.controller.selected_index = (
            self.controller.selected_index + delta
        ) % len(labels)
        self.refresh()

    def _activate(self) -> None:
        if self._closing or self._mode == "tv":
            return
        if self.controller.busy:
            self.controller.cancel_busy()
            self.refresh()
            return

        labels = self.controller.item_labels()
        if not labels:
            return

        index = self.controller.selected_index
        if self.controller.view == "regions":
            resume_active = self.controller.resume_tv_index() is not None
            if resume_active and index == 0:
                resume = self.controller.take_resume_tv()
                if resume is not None:
                    self._enter_tv(resume)
                return

            country_index = self.controller.menu_to_country_index(index)
            if country_index is None:
                return
            country = self.controller.countries[country_index]
            self.controller.clear_resume_tv()
            self.controller.select_region(
                country.code,
                on_complete=lambda: self.root.after(0, self._enter_tv_after_scan),
            )
            return

        channel_index = self.controller.menu_to_channel_index(index)
        if channel_index is None:
            return
        self._enter_tv(channel_index)

    def _show_regions(self) -> None:
        if self._mode == "tv" or self.controller.busy:
            return
        self.controller.show_regions()
        self.refresh()

    def _enter_tv_after_scan(self) -> None:
        self._enter_tv(0)

    def _enter_tv(self, index: int) -> None:
        if self._tv_thread and self._tv_thread.is_alive():
            return

        self.menu_frame.grid_remove()
        self.video_frame.grid()
        self.root.update_idletasks()
        embed_wid = self.video_frame.winfo_id()
        self._mode = "tv"

        def work() -> None:
            try:
                result = self.controller.run_player(index, embed_wid=embed_wid)
                error = ""
            except RuntimeError as exc:
                result = "menu"
                error = str(exc)
            self.root.after(0, lambda: self._exit_tv(result, error))

        self._tv_thread = threading.Thread(target=work, name="pitv-tv", daemon=True)
        self._tv_thread.start()

    def _exit_tv(self, result: str, error: str) -> None:
        self._mode = "menu"
        self.video_frame.grid_remove()
        self.menu_frame.grid()
        if error:
            self.controller.set_status(error)
        elif result == "menu" and self.controller.channels:
            self.controller.offer_resume_tv(self.controller.selected_index)
        self.refresh()
        self.root.focus_force()
        if result == "quit":
            self._quit()

    def _quit(self) -> None:
        if self._closing:
            return
        self._closing = True
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def run_app(controller: AppController) -> None:
    root = tk.Tk()
    app = PitvApp(root, controller)
    app.run()
