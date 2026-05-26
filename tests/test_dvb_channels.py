"""Tests for TV HAT channel lists (offline, no internet)."""

from pitv.dvb.channels_conf import parse_channels_conf


def test_parse_channels_conf_uses_local_dvr_device():
    sample = """[BBC ONE HD]
SERVICE_ID = 49200
VIDEO_PID = 6200

[ITV1]
SERVICE_ID = 10290
"""
    dvr = "/dev/dvb/adapter0/dvr0"
    channels = parse_channels_conf(sample, dvr)

    assert len(channels) == 2
    assert channels[0].name == "BBC ONE HD"
    assert channels[0].url == dvr
    assert channels[0].attrs["dvb_service"] == "BBC ONE HD"
    assert not channels[0].url.startswith("http")
