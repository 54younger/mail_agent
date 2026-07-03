"""App settings.

- Translation target language (non-secret pref in settings.json).
- Per-role LLM config: provider/model/base_url (settings.json) + API key
  (secrets store) for ``translate`` / ``classify`` / ``extract``. Keys are never
  returned — only a ``key_configured`` flag.
- Background auto-refresh toggle + interval.
- Data folder: report the current one and allow changing (with data migration).
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from .. import config, db, secrets_store
from ..schemas.settings import (
    AutoRefreshIn,
    ClaudeKeyIn,
    DataFolderChangeIn,
    LLMKeyIn,
    LLMRoleIn,
    LLMRoleOut,
    SettingsOut,
    TranslationTargetIn,
    TranslationTargetOption,
)
from ..services import llm, translation

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _current() -> SettingsOut:
    settings = config.load_settings()
    target = str(settings.get("translation_target", translation.DEFAULT_TARGET))
    data_dir = config.get_data_dir()
    roles = []
    for role in llm.ROLES:
        rs = llm.role_settings(role)
        roles.append(
            LLMRoleOut(
                role=role,
                provider=rs["provider"],
                model=rs["model"],
                base_url=rs["base_url"],
                key_configured=llm.role_key_configured(role),
            )
        )
    return SettingsOut(
        translation_target=target,
        claude_key_configured=bool(secrets_store.get_claude_key()),
        translation_targets=[
            TranslationTargetOption(code=code, label=label)
            for code, (label, _en) in translation.TRANSLATION_TARGETS.items()
        ],
        llm=roles,
        providers=list(llm.PROVIDERS),
        auto_refresh_enabled=bool(settings.get("auto_refresh_enabled", True)),
        auto_refresh_minutes=int(settings.get("auto_refresh_minutes", 15)),
        data_dir=str(data_dir) if data_dir else None,
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
    # Legacy single-key endpoint; still honored as a fallback for every role.
    await run_in_threadpool(secrets_store.set_claude_key, payload.api_key.strip())
    return _current()


@router.put("/llm/{role}", response_model=SettingsOut)
async def set_llm_role(role: str, payload: LLMRoleIn) -> SettingsOut:
    try:
        await run_in_threadpool(
            llm.set_role_settings,
            role,
            provider=payload.provider,
            model=payload.model,
            base_url=payload.base_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _current()


@router.put("/llm/{role}/key", response_model=SettingsOut)
async def set_llm_role_key(role: str, payload: LLMKeyIn) -> SettingsOut:
    if role not in llm.ROLES:
        raise HTTPException(status_code=400, detail="未知的模型用途")
    await run_in_threadpool(llm.set_role_key, role, payload.api_key.strip())
    return _current()


@router.put("/auto-refresh", response_model=SettingsOut)
async def set_auto_refresh(payload: AutoRefreshIn) -> SettingsOut:
    config.save_settings(
        {"auto_refresh_enabled": payload.enabled, "auto_refresh_minutes": payload.minutes}
    )
    return _current()


@router.put("/data-folder", response_model=SettingsOut)
async def change_data_folder(payload: DataFolderChangeIn) -> SettingsOut:
    try:
        await run_in_threadpool(config.change_data_dir, payload.path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except (PermissionError, OSError) as e:
        raise HTTPException(status_code=400, detail=f"无法使用该文件夹：{e}") from e

    # Reopen the engine against the (migrated) SQLite file and ensure schema.
    await db.reset_engine()
    await db.init_db()
    return _current()
