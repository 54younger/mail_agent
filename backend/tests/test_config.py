"""Data-folder path normalization: absolute-only, with WSL→Windows mapping."""

from __future__ import annotations

import pytest

from app import config


@pytest.mark.parametrize("bad", ["", "   ", "data", "./data", "relative/path"])
def test_relative_or_empty_is_rejected(bad):
    with pytest.raises(ValueError):
        config.normalize_input_path(bad)


def test_absolute_posix_path_is_accepted():
    p = config.normalize_input_path("/tmp/mail-agent-data")
    assert p.is_absolute()
    assert str(p) == "/tmp/mail-agent-data"


def test_home_relative_expands_to_absolute():
    p = config.normalize_input_path("~/mail-data")
    assert p.is_absolute()
    assert "mail-data" in str(p)


def test_windows_path_maps_to_wsl_mount_when_on_wsl(monkeypatch):
    monkeypatch.setattr(config, "_running_on_wsl", lambda: True)
    p = config.normalize_input_path(r"C:\Users\You\MailData")
    assert str(p).startswith("/mnt/c/")
    assert str(p).lower().endswith("maildata")


def test_windows_forward_slash_path_maps_too(monkeypatch):
    monkeypatch.setattr(config, "_running_on_wsl", lambda: True)
    # Force the manual fallback (no wslpath) to keep the test host-independent.
    monkeypatch.setattr(config.subprocess, "run", _raise)
    p = config.normalize_input_path("D:/data/mail")
    assert str(p) == "/mnt/d/data/mail"


def _raise(*_a, **_k):
    raise OSError("wslpath not available")
