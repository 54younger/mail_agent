"""Translation service: HTML stripping, skip-if-target, and the unavailable path.
Claude and language detection are stubbed — no network, no key needed."""

from __future__ import annotations

import pytest

from app.services import translation
from app.services.translation import TranslationService, TranslationUnavailable


def test_strip_html_reduces_to_text():
    out = translation._strip_html("<p>Hello <b>team</b></p><br><script>x()</script>")
    assert "Hello" in out
    assert "team" in out
    assert "<" not in out
    assert "x()" not in out  # script contents dropped


def test_skip_when_source_equals_target(monkeypatch):
    monkeypatch.setattr(translation, "detect_language", lambda t: "en")
    svc = TranslationService(api_key="")  # no key needed when skipping
    result = svc.translate("<p>Hello team</p>", target_lang="en")
    assert result.skipped is True
    assert result.source_lang == "en"
    assert "Hello team" in result.translated


def test_unavailable_without_key(monkeypatch):
    monkeypatch.setattr(translation, "detect_language", lambda t: "fr")
    svc = TranslationService(api_key="")
    with pytest.raises(TranslationUnavailable):
        svc.translate("Bonjour l'équipe", target_lang="en")


def test_translate_calls_claude_when_needed(monkeypatch):
    monkeypatch.setattr(translation, "detect_language", lambda t: "fr")
    monkeypatch.setattr(
        TranslationService, "_call_claude", lambda self, text, target: "Hello team"
    )
    svc = TranslationService(api_key="sk-test")
    result = svc.translate("Bonjour l'équipe", target_lang="en")
    assert result.skipped is False
    assert result.source_lang == "fr"
    assert result.translated == "Hello team"


def test_empty_body_is_skipped():
    svc = TranslationService(api_key="")
    result = svc.translate("   ", target_lang="en")
    assert result.skipped is True
    assert result.translated == ""
