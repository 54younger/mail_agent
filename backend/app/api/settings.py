"""App settings: translation target language + Claude API key.

Target language is a non-secret pref (settings.json). The Claude key is a secret
(keyring/encrypted file) — we only ever report whether it's configured, never the
value.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from .. import config, secrets_store
from ..schemas.settings import (
    ClaudeKeyIn,
    SettingsOut,
    TranslationTargetIn,
    TranslationTargetOption,
)
from ..services import translation

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _current() -> SettingsOut:
    settings = config.load_settings()
    target = str(settings.get("translation_target", translation.DEFAULT_TARGET))
    return SettingsOut(
        translation_target=target,
        claude_key_configured=bool(secrets_store.get_claude_key()),
        translation_targets=[
            TranslationTargetOption(code=code, label=label)
            for code, (label, _en) in translation.TRANSLATION_TARGETS.items()
        ],
    )


@router.get("", response_model=SettingsOut)
async def get_settings() -> SettingsOut:
    return _current()


@router.put("/translation-target", response_model=SettingsOut)
async def set_translation_target(payload: TranslationTargetIn) -> SettingsOut:
    if payload.translation_target not in translation.TRANSLATION_TARGETS:
        raise HTTPException(status_code=400, detail="不支持的目标语言")
    config.save_settings({"translation_target": payload.translation_target})
    return _current()


@router.put("/claude-key", response_model=SettingsOut)
async def set_claude_key(payload: ClaudeKeyIn) -> SettingsOut:
    await run_in_threadpool(secrets_store.set_claude_key, payload.api_key.strip())
    return _current()
