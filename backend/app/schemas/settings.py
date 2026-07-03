from __future__ import annotations

from pydantic import BaseModel, Field


class TranslationTargetOption(BaseModel):
    code: str
    label: str


class LLMRoleOut(BaseModel):
    role: str  # "translate" | "classify" | "extract"
    provider: str  # "anthropic" | "openai" | "openai_compatible"
    model: str
    base_url: str
    key_configured: bool


class SettingsOut(BaseModel):
    translation_target: str
    claude_key_configured: bool
    translation_targets: list[TranslationTargetOption]
    # Per-role LLM configuration (cheap classify vs strong extract vs translate).
    llm: list[LLMRoleOut]
    providers: list[str]
    # Background auto-refresh of mail while the app is open.
    auto_refresh_enabled: bool
    auto_refresh_minutes: int
    # Current data folder (SQLite lives here); changeable below.
    data_dir: str | None = None


class TranslationTargetIn(BaseModel):
    translation_target: str = Field(min_length=2, max_length=5)


class ClaudeKeyIn(BaseModel):
    api_key: str = Field(min_length=1)


class LLMRoleIn(BaseModel):
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    base_url: str = ""


class LLMKeyIn(BaseModel):
    api_key: str = Field(min_length=1)


class AutoRefreshIn(BaseModel):
    enabled: bool
    minutes: int = Field(ge=1, le=1440)


class DataFolderChangeIn(BaseModel):
    path: str = Field(min_length=1, description="Absolute or ~-relative folder path")
