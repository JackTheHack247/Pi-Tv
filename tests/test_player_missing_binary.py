"""Missing system binaries should surface as RuntimeError, not crash silently."""

from __future__ import annotations

import pytest

from pitv import player as player_module
from pitv.dvb import player as dvb_player_module
from pitv.m3u_parser import Channel


class _FakeEpg:
    def lookup(self, tvg_id, channel_name=""):
        return None


def test_mpv_missing_raises_runtime_error(monkeypatch) -> None:
    def fake_popen(*_args, **_kwargs):
        raise FileNotFoundError(2, "No such file or directory", "mpv")

    monkeypatch.setattr(player_module.subprocess, "Popen", fake_popen)

    mpv = player_module.MpvPlayer(
        channels=[Channel(name="X", url="dummy")],
        epg=_FakeEpg(),
    )

    with pytest.raises(RuntimeError, match="mpv not found"):
        mpv._start_mpv()


def test_dvbv5_zap_missing_raises_runtime_error(monkeypatch) -> None:
    monkeypatch.setattr(
        dvb_player_module.MpvPlayer,
        "_start_mpv",
        lambda self: None,
    )

    def fake_popen(*_args, **_kwargs):
        raise FileNotFoundError(2, "No such file or directory", "dvbv5-zap")

    monkeypatch.setattr(dvb_player_module.subprocess, "Popen", fake_popen)

    class _FakeEpgWithStart(_FakeEpg):
        def set_on_update(self, _cb):
            pass

        def start(self):
            pass

    player = dvb_player_module.DvbPlayer(
        channels=[Channel(name="X", url="dummy", attrs={"dvb_service": "X"})],
        channels_conf=None,
        epg=_FakeEpgWithStart(),
    )

    with pytest.raises(RuntimeError, match="dvbv5-zap not found"):
        player._play_current(show_overlay=False)
