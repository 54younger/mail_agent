"""On-demand email translation via Claude Haiku.

Flow: detect the source language; if it already equals the target, return the
original untouched (no API call). Otherwise translate with Claude and let the
caller cache the result on the row. HTML is stripped to plain text before
translation so we translate readable content, not markup.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .. import secrets_store

# Supported targets: ISO code -> (display label, English name for the prompt).
TRANSLATION_TARGETS: dict[str, tuple[str, str]] = {
    "en": ("English", "English"),
    "zh": ("中文", "Simplified Chinese"),
    "ja": ("日本語", "Japanese"),
    "ko": ("한국어", "Korean"),
    "fr": ("Français", "French"),
    "de": ("Deutsch", "German"),
    "es": ("Español", "Spanish"),
}
DEFAULT_TARGET = "en"

_MODEL = "claude-haiku-4-5-20251001"
_MAX_INPUT_CHARS = 12_000


class TranslationUnavailable(Exception):
    """Raised when translation can't run (no API key configured)."""

    def __init__(self, message: str = "翻译不可用：请先在设置中配置 Claude API Key。"):
        super().__init__(message)
        self.message = message


@dataclass
class TranslationResult:
    translated: str
    source_lang: str
    # True when source already equals target — `translated` is the original text.
    skipped: bool


def _strip_html(text: str) -> str:
    """Reduce HTML to readable text: drop script/style, tags, collapse space."""
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


def detect_language(text: str) -> str:
    """Best-effort ISO-639-1 detection via lingua; '' if undetectable."""
    try:
        from lingua import LanguageDetectorBuilder

        detector = LanguageDetectorBuilder.from_all_languages().build()
        lang = detector.detect_language_of(text)
        if lang is None:
            return ""
        return lang.iso_code_639_1.name.lower()
    except Exception:
        return ""


class TranslationService:
    def __init__(self, api_key: str | None):
        self._api_key = api_key or ""

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def translate(self, text: str, *, target_lang: str) -> TranslationResult:
        target = target_lang if target_lang in TRANSLATION_TARGETS else DEFAULT_TARGET
        plain = _strip_html(text)
        if not plain.strip():
            return TranslationResult(translated="", source_lang="", skipped=True)

        source = detect_language(plain)
        if source and source == target:
            return TranslationResult(translated=plain, source_lang=source, skipped=True)

        if not self.is_configured:
            raise TranslationUnavailable()

        target_name = TRANSLATION_TARGETS[target][1]
        snippet = plain[:_MAX_INPUT_CHARS]
        translated = self._call_claude(snippet, target_name)
        return TranslationResult(translated=translated, source_lang=source, skipped=False)

    def _call_claude(self, text: str, target_name: str) -> str:
        from anthropic import Anthropic

        client = Anthropic(api_key=self._api_key)
        prompt = (
            f"Translate the following email into {target_name}. "
            "Preserve meaning and tone; output only the translation, no notes.\n\n"
            f"{text}"
        )
        msg = client.messages.create(
            model=_MODEL,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        parts = [block.text for block in msg.content if getattr(block, "type", "") == "text"]
        return "\n".join(parts).strip()


def get_service() -> TranslationService:
    return TranslationService(secrets_store.get_claude_key())
