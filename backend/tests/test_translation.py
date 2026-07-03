"""Translation service: HTML stripping, skip-if-target, and the unavailable path.
The model call and language detection are stubbed — no network, no key needed."""

from __future__ import annotations

import pytest

from app.services import llm, translation
from app.services.translation import TranslationService, TranslationUnavailable


def _cfg(key: str = "") -> llm.LLMConfig:
    # model is only set alongside a key so is_configured mirrors "usable".
    return llm.LLMConfig(
        provider="anthropic", model="claude-x" if key else "", base_url="", api_key=key
    )


def test_strip_html_reduces_to_text():
    out = translation._strip_html("<p>Hello <b>team</b></p><br><script>x()</script>")
    assert "Hello" in out
    assert "team" in out
    assert "<" not in out
    assert "x()" not in out  # script contents dropped


def test_skip_when_source_equals_target(monkeypatch):
    monkeypatch.setattr(translation, "detect_language", lambda t: "en")
    svc = TranslationService(_cfg())  # no key needed when skipping
    result = svc.translate("<p>Hello team</p>", target_lang="en")
    assert result.skipped is True
    assert result.source_lang == "en"
    assert "Hello team" in result.translated


def test_unavailable_without_key(monkeypatch):
    monkeypatch.setattr(translation, "detect_language", lambda t: "fr")
    svc = TranslationService(_cfg())
    with pytest.raises(TranslationUnavailable):
        svc.translate("Bonjour l'équipe", target_lang="en")


def test_translate_calls_model_when_needed(monkeypatch):
    monkeypatch.setattr(translation, "detect_language", lambda t: "fr")
    monkeypatch.setattr(
        TranslationService, "_call_model", lambda self, text, target: "Hello team"
    )
    svc = TranslationService(_cfg("sk-test"))
    result = svc.translate("Bonjour l'équipe", target_lang="en")
    assert result.skipped is False
    assert result.source_lang == "fr"
    assert result.translated == "Hello team"


def test_empty_body_is_skipped():
    svc = TranslationService(_cfg())
    result = svc.translate("   ", target_lang="en")
    assert result.skipped is True
    assert result.translated == ""
