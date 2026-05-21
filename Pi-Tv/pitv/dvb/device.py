"""Raspberry Pi TV HAT / Linux DVB device helpers."""

from __future__ import annotations

import glob
import os
from pathlib import Path


def adapter_paths() -> list[Path]:
    return sorted(Path(p) for p in glob.glob("/dev/dvb/adapter*") if Path(p).is_dir())


def has_tv_hat() -> bool:
    if os.environ.get("PITV_FORCE_TVHAT") == "1":
        return True
    if os.environ.get("PITV_FORCE_TVHAT") == "0":
        return False
    return bool(adapter_paths())


def default_adapter() -> int:
    adapters = adapter_paths()
    if not adapters:
        return 0
    name = adapters[0].name
    return int(name.replace("adapter", ""))


def dvr_path(adapter: int | None = None) -> str:
    adapter_id = default_adapter() if adapter is None else adapter
    return f"/dev/dvb/adapter{adapter_id}/dvr0"


def demux_path(adapter: int | None = None, index: int = 0) -> str:
    adapter_id = default_adapter() if adapter is None else adapter
    return f"/dev/dvb/adapter{adapter_id}/demux{index}"


def demux_paths(adapter: int | None = None) -> list[str]:
    adapter_id = default_adapter() if adapter is None else adapter
    base = Path(f"/dev/dvb/adapter{adapter_id}")
    if not base.is_dir():
        return [demux_path(adapter_id)]
    paths = sorted(base.glob("demux*"))
    if paths:
        return [str(path) for path in paths]
    return [demux_path(adapter_id)]
