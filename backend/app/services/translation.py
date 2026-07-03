"""On-demand email translation via the configured ``translate`` LLM role.

Flow: detect the source language; if it already equals the target, return the
original untouched (no API call). Otherwise translate with the configured
provider/model (Claude, OpenAI, or an OpenAI-compatible endpoint) and let the
caller cache the result on the row. HTML is stripped to plain text before
translation so we translate readable content, not markup.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import llm

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


# Lingua builds a sizable model; build it once and reuse it across calls.
_detector = None


def detect_language(text: str) -> str:
    """Best-effort ISO-639-1 detection via lingua; '' if undetectable."""
    global _detector
    try:
        if _detector is None:
            from lingua import LanguageDetectorBuilder

            _detector = LanguageDetectorBuilder.from_all_languages().build()
        lang = _detector.detect_language_of(text)
        if lang is None:
            return ""
        return lang.iso_code_639_1.name.lower()
    except Exception:
        return ""


class TranslationService:
    def __init__(self, cfg: llm.LLMConfig):
        self._cfg = cfg

    @property
    def is_configured(self) -> bool:
        return self._cfg.is_configured

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
        translated = self._call_model(snippet, target_name)
        return TranslationResult(translated=translated, source_lang=source, skipped=False)

    def _call_model(self, text: str, target_name: str) -> str:
        prompt = (
            f"Translate the following email into {target_name}. "
            "Preserve meaning and tone; output only the translation, no notes.\n\n"
            f"{text}"
        )
        return llm.complete_text(self._cfg, prompt, max_tokens=4096)


def get_service() -> TranslationService:
    return TranslationService(llm.get_llm_config("translate"))
