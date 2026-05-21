# Pi-TV

Keyboard-driven live TV for **Raspberry Pi 4** with the **official TV HAT**. No mouse, no internet required for normal use.

Pi-TV scans your aerial for real DVB-T/T2 broadcasts, caches the channels locally, reads programme info from the signal, and plays through mpv.

## Requirements

- Raspberry Pi 4 (or compatible Pi)
- [Raspberry Pi TV HAT](https://www.raspberrypi.com/products/raspberry-pi-tv-hat/)
- DVB-T/T2 aerial
- Keyboard or remote (arrow keys)

## Setup

1. Fit the TV HAT and connect an aerial.

2. Enable the overlay in `/boot/firmware/config.txt` (or `/boot/config.txt` on older OS):

   ```
   dtoverlay=tvhat
   ```

3. Reboot, then install:

   ```bash
   cd Pi-Tv
   chmod +x scripts/install-pi.sh pitv-run
   ./scripts/install-pi.sh
   ```

4. Log out and back in if the installer added you to the `video` or `input` groups.

5. Run Pi-TV:

   ```bash
   pitv
   ```

## First run

1. Pick your region once (e.g. **United Kingdom**). This selects which transmitter frequencies to scan — not a channel list.
2. Pi-TV scans your aerial and saves only the stations your local transmitters actually broadcast.
3. After that, Pi-TV goes straight to TV on boot. Press **Enter** during playback to change region.

Scan results are stored at:

- `~/.cache/pitv/dvb/<country>/channels.json` — channel list
- `~/.cache/pitv/dvb/<country>/channels.conf` — tuner config for `dvbv5-zap`

Scans are reused for about a week. Rescan any time:

```bash
python3 -m pitv.dvb_scan
```

## Controls

| Screen | Key | Action |
|--------|-----|--------|
| Region menu (first launch) | ↑ / ↓ | Move selection |
| Region menu (first launch) | Enter | Select region and start TV |
| Region menu (first launch) | Q / Esc | Quit |
| Region menu (from TV) | ↑ / ↓ | Move selection |
| Region menu (from TV) | Enter | Select a new region, or close if unchanged |
| Region menu (from TV) | Esc | Close menu and return to TV |
| Watching TV | ↑ / ↓ | Previous / next channel |
| Watching TV | Enter | Open region menu |
| Watching TV | Q | Quit |

## Overlay

When you change channel, the top-right overlay shows:

- Channel name (from the aerial scan)
- Programme title and description (from DVB EIT in the broadcast)

Programme info may take a few seconds to appear after tuning.

## How it works

- **Tuner**: Raspberry Pi TV HAT via Linux DVB (`/dev/dvb/adapter0`)
- **Scan tables**: `dtv-scan-tables` (system package)
- **Tuning**: `dvbv5-scan` and `dvbv5-zap`
- **Programme guide**: EIT parsed from the transport stream (offline)
- **Playback**: [mpv](https://mpv.io/) reading `/dev/dvb/adapter0/dvr0`
- **Overlay**: Lua script (`pitv/overlay.lua`)

## Running on a TV

For direct HDMI output from the console:

```bash
pitv
```

If you use the Pi desktop instead:

```bash
PITV_VO=x11 pitv
```

## Configuration

Settings are stored in `~/.config/pitv/config.json` (last selected region).

## Project layout

```
pitv/
  app.py            Main loop
  dvb/              Scan, EIT, tune, play
  dvb_scan.py       Rescan all regions from the aerial
  data/             Region codes for the menu
  player.py         mpv playback + overlay
  overlay.lua       Top-right info overlay
  keyboard.py       Arrow-key input (evdev on Pi)
  menu.py           Region selection menu
```

## License

Pi-TV code: MIT.
