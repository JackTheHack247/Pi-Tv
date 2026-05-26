# Pi-TV

Keyboard-driven live TV for **Raspberry Pi 4** with the **official TV HAT**. No mouse, no internet required for normal use.

Pi-TV opens **full screen** in one window — a menu, then live TV **in that same window**.

See **`Pi-Tv-Manual.txt`** for the full setup guide.

## Requirements

- Raspberry Pi 4 (or compatible Pi)
- [Raspberry Pi TV HAT](https://www.raspberrypi.com/products/raspberry-pi-tv-hat/)
- DVB-T/T2 aerial
- Keyboard or remote (arrow keys + Enter)
- Raspberry Pi OS with desktop (Python Tk + display)

## Quick setup

1. Fit the TV HAT and connect an aerial.
2. Add `dtoverlay=tvhat` to `/boot/firmware/config.txt` (or `/boot/config.txt`), then reboot.
3. Install:

   ```bash
   cd Pi-Tv
   chmod +x scripts/install-pi.sh pitv-run
   ./scripts/install-pi.sh
   ```

4. Log out and back in if added to the `video` or `input` groups.
5. Run:

   ```bash
   pitv
   ```

   Windowed mode for testing: `PITV_WINDOWED=1 pitv`

## How it works

1. Pick your **region** — Pi-TV scans your aerial for channels in range (no internet).
2. Watch live TV in the same window.
3. **Enter** while watching opens the country list with **← Back to TV** selected.
4. Programme info (channel, title, description) appears top-right when you change channel.

## Controls

| Where | Key | Action |
|-------|-----|--------|
| Menu | ↑ / ↓ | Move selection |
| Menu | Enter | Select country or channel |
| Menu | Esc | Quit (desktop) |
| Scanning | Enter on ← Close | Cancel scan |
| Watching TV | Enter | Country list (← Back to TV) |
| Country list | Enter on ← Back to TV | Same channel as before |
| Country list | ↓ + country + Enter | Rescan → channel 1 |
| Channel list | Change region | Country list |
| Watching TV | ↑ / ↓ | Change channel |
| Watching TV | Esc | Quit (desktop) |

On a TV remote, Back/Exit usually works like Esc.

## Colours

Edit `DEFAULT_THEME` in `pitv/ui/window.py`, or override in `~/.config/pitv/config.json`:

```json
{
  "theme": {
    "bg": "#ffffff",
    "sidebar_bg": "#f3f3f3",
    "sidebar_text": "#222222",
    "overlay_bg": "#111111d9",
    "overlay_border": "#666666"
  }
}
```

Menu keys (`bg`, `text`, `sidebar_bg`, …) style the list. `overlay_*` keys style the programme box on TV.

Restart `pitv` after changes.

## Rescan channels

Pick a country again in the menu, or:

```bash
python3 -m pitv.dvb_scan
```

## Troubleshooting

| Problem | Try |
|---------|-----|
| No TV HAT found | `dtoverlay=tvhat`, reboot, `ls /dev/dvb/` |
| No channels | Check aerial, rescan, improve signal |
| Black video | `PITV_VO=x11 pitv` |
| Keyboard dead while watching | Log out/in after install (`input` group) |
| `pitv` not found | `export PATH="$HOME/.local/bin:$PATH"` |

## Project layout

```
pitv/
  app.py            Entry point
  controller.py     App state
  ui/window.py      Menu window + theme
  overlay.lua       TV programme overlay styling
  dvb/              Scan, EIT, tune, play
  player.py         mpv playback
scripts/
  install-pi.sh     Pi installer
Pi-Tv-Manual.txt    Full user manual
```

## License

MIT.
