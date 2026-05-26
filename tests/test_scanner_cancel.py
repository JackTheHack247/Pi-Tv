"""Cancel-during-scan must terminate the dvbv5-scan subprocess."""

from __future__ import annotations

import sys

import pytest

from pitv.dvb import scanner


def test_run_cancellable_terminates_when_cancelled(monkeypatch) -> None:
    cmd = [sys.executable, "-c", "import time\nwhile True: time.sleep(0.1)"]

    cancelled = {"value": False}

    def is_cancelled() -> bool:
        return cancelled["value"]

    cancelled["value"] = True

    with pytest.raises(scanner.ScanCancelled):
        scanner._run_cancellable(cmd, is_cancelled)


def test_run_cancellable_returns_on_zero_exit() -> None:
    cmd = [sys.executable, "-c", "import sys; sys.exit(0)"]

    scanner._run_cancellable(cmd, is_cancelled=None)


def test_run_cancellable_raises_on_nonzero_exit() -> None:
    cmd = [sys.executable, "-c", "import sys; sys.exit(3)"]

    with pytest.raises(Exception):
        scanner._run_cancellable(cmd, is_cancelled=None)
