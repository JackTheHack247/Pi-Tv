#!/usr/bin/env bash
set -euo pipefail

echo "=== Pi-TV installer for Raspberry Pi OS ==="

if [[ "$(uname -m)" != "aarch64" && "$(uname -m)" != "armv7l" && "$(uname -m)" != "armv6l" ]]; then
  echo "Warning: this script is intended for Raspberry Pi (ARM)."
fi

sudo apt-get update
sudo apt-get install -y mpv python3 python3-pip python3-evdev dtv-scan-tables dvb5-tools

INSTALL_DIR="${PITV_INSTALL_DIR:-$HOME/pitv}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Installing Pi-TV to $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
rsync -a --delete "$SCRIPT_DIR/pitv" "$SCRIPT_DIR/requirements.txt" "$SCRIPT_DIR/pitv-run" "$INSTALL_DIR/"

python3 -m pip install --user -r "$INSTALL_DIR/requirements.txt"

mkdir -p "$HOME/.local/bin"
ln -sf "$INSTALL_DIR/pitv-run" "$HOME/.local/bin/pitv"

if ! groups "$USER" | grep -q '\bvideo\b'; then
  echo ""
  echo "Adding $USER to the video group (needed for the TV HAT / DVB devices)."
  sudo usermod -aG video "$USER"
fi

if ! groups "$USER" | grep -q '\binput\b'; then
  echo ""
  echo "Adding $USER to the input group (needed for keyboard/remote while mpv is fullscreen)."
  sudo usermod -aG input "$USER"
fi

if [[ ! -e /dev/dvb/adapter0 ]]; then
  echo ""
  echo "TV HAT not detected yet."
  echo "Add this to /boot/firmware/config.txt (or /boot/config.txt), then reboot:"
  echo "  dtoverlay=tvhat"
else
  echo ""
  echo "TV HAT detected — Pi-TV scans your aerial for channels in range."
fi

cat <<'EOF'

Install complete.

Run Pi-TV:
  pitv

How it works:
  - Pick your region (e.g. United Kingdom) — this sets which transmitter frequencies to scan.
  - Pi-TV scans your aerial and ONLY saves channels your local transmitters actually send.
  - No internet. No pre-made lists. Just what's in the air where you are.
  - Rescan any time: python3 -m pitv.dvb_scan

Tips:
  - Connect a DVB-T/T2 aerial to the TV HAT.
  - ↑/↓ change channel, Enter = open/close region menu, Q quit.
  - Log out and back in if you were added to the video or input groups.

EOF
