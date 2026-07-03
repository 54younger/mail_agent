"""Data-folder behavior: a per-user default is used when nothing is configured,
and changing the folder migrates the DB + secrets so accounts survive the move."""

from __future__ import annotations

import json

from app import config


def test_default_data_dir_used_when_unconfigured(tmp_path, monkeypatch):
    monkeypatch.delenv("MAIL_AGENT_DATA_DIR", raising=False)
    monkeypatch.setattr(config, "_bootstrap_config_path", lambda: tmp_path / "cfg" / "config.json")
    monkeypatch.setattr(config, "default_data_dir", lambda: tmp_path / "default")

    assert config.is_configured() is True
    assert config.get_data_dir() == tmp_path / "default"


def test_change_data_dir_migrates_db_and_secrets(tmp_path, monkeypatch):
    monkeypatch.delenv("MAIL_AGENT_DATA_DIR", raising=False)
    pointer = tmp_path / "cfg" / "config.json"
    monkeypatch.setattr(config, "_bootstrap_config_path", lambda: pointer)

    old = tmp_path / "old"
    old.mkdir()
    (old / "app.sqlite").write_bytes(b"DB")
    (old / ".secrets.enc").write_bytes(b"SECRET")
    pointer.parent.mkdir(parents=True)
    pointer.write_text(json.dumps({"data_dir": str(old)}), encoding="utf-8")

    new = tmp_path / "new"
    result = config.change_data_dir(str(new))

    assert result == new.resolve()
    # DB + encrypted secrets moved so accounts/emails/keys aren't lost.
    assert (new / "app.sqlite").read_bytes() == b"DB"
    assert (new / ".secrets.enc").read_bytes() == b"SECRET"
    # Pointer now records the new folder.
    assert json.loads(pointer.read_text(encoding="utf-8"))["data_dir"] == str(new.resolve())
    assert config.get_data_dir() == new.resolve()
