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
    max_tokens: int
    temperature: float | None = None
    prompt: str  # effective template (built-in default filled in when unset)


# ── Job pipeline config (Settings → 求职识别) ─────────────────────────────────


class StatusRuleModel(BaseModel):
    keywords: list[str] = []
    status: str


class JobsExcludeOut(BaseModel):
    meeting_links: list[str]
    senders: list[str]


class JobsConfigOut(BaseModel):
    keywords: list[str]
    exclude: JobsExcludeOut
    company_strip_suffixes: list[str]
    company_aliases: dict[str, str]
    status_rules: list[StatusRuleModel]
    default_range_days: int


class JobStatusOption(BaseModel):
    name: str  # "online_test"
    code: int  # 1


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
    # User-tunable job pipeline config + the status vocabulary rules can target.
    jobs: JobsConfigOut
    job_status_options: list[JobStatusOption]
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
    # Advanced (optional): only applied when provided, so a basic save that omits
    # them never wipes a stored prompt/params.
    max_tokens: int | None = Field(default=None, ge=1, le=200_000)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    prompt: str | None = None


class LLMKeyIn(BaseModel):
    api_key: str = Field(min_length=1)


class JobsExcludeIn(BaseModel):
    meeting_links: list[str] | None = None
    senders: list[str] | None = None


class JobsConfigIn(BaseModel):
    keywords: list[str] | None = None
    exclude: JobsExcludeIn | None = None
    company_strip_suffixes: list[str] | None = None
    company_aliases: dict[str, str] | None = None
    status_rules: list[StatusRuleModel] | None = None
    default_range_days: int | None = Field(default=None, ge=1, le=3650)


class AutoRefreshIn(BaseModel):
    enabled: bool
    minutes: int = Field(ge=1, le=1440)


class DataFolderChangeIn(BaseModel):
    path: str = Field(min_length=1, description="Absolute or ~-relative folder path")
