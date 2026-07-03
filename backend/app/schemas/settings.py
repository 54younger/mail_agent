from __future__ import annotations

from pydantic import BaseModel, Field


class TranslationTargetOption(BaseModel):
    code: str
    label: str


class SettingsOut(BaseModel):
    translation_target: str
    claude_key_configured: bool
    translation_targets: list[TranslationTargetOption]


class TranslationTargetIn(BaseModel):
    translation_target: str = Field(min_length=2, max_length=5)


class ClaudeKeyIn(BaseModel):
    api_key: str = Field(min_length=1)
