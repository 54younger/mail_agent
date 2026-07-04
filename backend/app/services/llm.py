"""Vendor-agnostic LLM access: text completion + tool/function calling.

Supports **Anthropic** (Claude), **OpenAI**, and any **OpenAI-compatible**
endpoint (custom ``base_url`` — e.g. DeepSeek, Together, or a local Ollama).
Each *role* (``translate`` / ``classify`` / ``extract``) is configured
independently in ``settings.json`` (provider/model/base_url) plus the secrets
store (API key), so the cheap classifier and the strong extractor may use
different vendors, models, and keys.

These are **blocking** calls (the SDKs are synchronous) meant to be run in a
threadpool from the async routers. The module never imports the vendor SDKs at
top level — they're imported lazily inside the provider branch so the app still
starts (and tests still run) without OpenAI installed unless it's actually used.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .. import config, secrets_store

PROVIDER_ANTHROPIC = "anthropic"
PROVIDER_OPENAI = "openai"
PROVIDER_OPENAI_COMPATIBLE = "openai_compatible"
PROVIDERS = (PROVIDER_ANTHROPIC, PROVIDER_OPENAI, PROVIDER_OPENAI_COMPATIBLE)

ROLES = ("translate", "classify", "extract")

# Per-role defaults. Cheap tiers use Haiku; extraction defaults to a stronger
# model. ``max_tokens`` sizes the output budget per role; ``temperature`` is
# ``None`` meaning "use the provider default" (and, importantly, never sent to
# reasoning models that reject a custom temperature); ``prompt`` is empty meaning
# "use the role's built-in template" (the domain defaults live in the caller,
# e.g. ``job_extractor``). Users override any of these in Settings.
_DEFAULT_ROLE_CONFIG: dict[str, dict[str, object]] = {
    "translate": {
        "provider": PROVIDER_ANTHROPIC, "model": "claude-haiku-4-5-20251001",
        "base_url": "", "max_tokens": 4096, "temperature": None, "prompt": "",
    },
    "classify": {
        "provider": PROVIDER_ANTHROPIC, "model": "claude-haiku-4-5-20251001",
        "base_url": "", "max_tokens": 8, "temperature": None, "prompt": "",
    },
    "extract": {
        "provider": PROVIDER_ANTHROPIC, "model": "claude-sonnet-5",
        "base_url": "", "max_tokens": 1024, "temperature": None, "prompt": "",
    },
}


class LLMUnavailable(Exception):
    """Raised when a role has no usable config (missing API key or model)."""

    def __init__(self, message: str = "LLM 未配置：请先在设置中为该功能配置厂商 API Key 与模型。"):
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    model: str
    base_url: str
    api_key: str
    max_tokens: int = 4096
    temperature: float | None = None
    prompt: str = ""  # per-role prompt template ("" = caller's built-in default)

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.model)


# ── Role configuration (settings.json + secrets store) ───────────────────────


def _role_secret_key(role: str) -> str:
    return f"llm_key::{role}"


def _coerce_int(value: object, fallback: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return fallback


def _coerce_temp(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def role_settings(role: str) -> dict[str, object]:
    """Non-secret config for a role (provider/model/base_url + max_tokens/
    temperature/prompt), merged over defaults."""
    defaults = _DEFAULT_ROLE_CONFIG.get(role, _DEFAULT_ROLE_CONFIG["extract"])
    raw = config.load_settings().get("llm", {})
    stored = raw.get(role, {}) if isinstance(raw, dict) else {}
    merged = {**defaults, **(stored if isinstance(stored, dict) else {})}
    provider = str(merged.get("provider") or defaults["provider"])
    if provider not in PROVIDERS:
        provider = str(defaults["provider"])
    return {
        "provider": provider,
        "model": str(merged.get("model") or ""),
        "base_url": str(merged.get("base_url") or ""),
        "max_tokens": _coerce_int(merged.get("max_tokens"), int(defaults["max_tokens"])),  # type: ignore[arg-type]
        "temperature": _coerce_temp(merged.get("temperature")),
        "prompt": str(merged.get("prompt") or ""),
    }


def _resolve_key(role: str) -> str:
    """Role key, falling back to the legacy single Claude key for back-compat."""
    key = secrets_store.get_secret(_role_secret_key(role))
    if key:
        return key
    return secrets_store.get_claude_key() or ""


def role_key_configured(role: str) -> bool:
    return bool(_resolve_key(role))


def get_llm_config(role: str) -> LLMConfig:
    s = role_settings(role)
    return LLMConfig(
        provider=str(s["provider"]),
        model=str(s["model"]),
        base_url=str(s["base_url"]),
        api_key=_resolve_key(role),
        max_tokens=int(s["max_tokens"]),  # type: ignore[arg-type]
        temperature=s["temperature"],  # type: ignore[arg-type]
        prompt=str(s["prompt"]),
    )


def set_role_key(role: str, value: str) -> None:
    secrets_store.set_secret(_role_secret_key(role), value)


# Sentinel so callers can distinguish "leave unchanged" from "set to None/clear".
_UNSET: object = object()


def set_role_settings(
    role: str,
    *,
    provider: str,
    model: str,
    base_url: str,
    max_tokens: object = _UNSET,
    temperature: object = _UNSET,
    prompt: object = _UNSET,
) -> None:
    if role not in ROLES:
        raise ValueError("未知的模型用途")
    if provider not in PROVIDERS:
        raise ValueError("不支持的厂商")
    llm = dict(config.load_settings().get("llm", {}) or {})
    prev = llm.get(role, {}) if isinstance(llm.get(role), dict) else {}
    # Advanced fields only change when explicitly supplied, so a basic save (which
    # omits them) keeps a stored prompt/params — while an explicit ``None`` on
    # temperature clears it back to the provider default.
    entry: dict[str, object] = {
        "provider": provider,
        "model": model.strip(),
        "base_url": base_url.strip(),
        "max_tokens": prev.get("max_tokens") if max_tokens is _UNSET else max_tokens,
        "temperature": prev.get("temperature") if temperature is _UNSET else temperature,
        "prompt": (prev.get("prompt", "") if prompt is _UNSET else prompt) or "",
    }
    llm[role] = entry
    config.save_settings({"llm": llm})


# ── Completion entry points ──────────────────────────────────────────────────


def complete_text(cfg: LLMConfig, prompt: str, *, max_tokens: int | None = None) -> str:
    if not cfg.is_configured:
        raise LLMUnavailable()
    budget = cfg.max_tokens if max_tokens is None else max_tokens
    if cfg.provider == PROVIDER_ANTHROPIC:
        return _anthropic_text(cfg, prompt, budget)
    return _openai_text(cfg, prompt, budget)


def complete_tool(
    cfg: LLMConfig, prompt: str, tool_schema: dict, *, max_tokens: int | None = None
) -> dict | None:
    """Force a single tool/function call and return its parsed arguments.

    ``tool_schema`` is the Anthropic tool shape
    ``{"name", "description", "input_schema"}``; it's adapted to OpenAI's
    function-calling shape for the OpenAI/compatible branch.
    """
    if not cfg.is_configured:
        raise LLMUnavailable()
    budget = cfg.max_tokens if max_tokens is None else max_tokens
    if cfg.provider == PROVIDER_ANTHROPIC:
        return _anthropic_tool(cfg, prompt, tool_schema, budget)
    return _openai_tool(cfg, prompt, tool_schema, budget)


def _temp_kwargs(cfg: LLMConfig) -> dict[str, float]:
    """Only send ``temperature`` when the user set one — reasoning models reject a
    non-default temperature, so an unset (None) value keeps prior behavior."""
    return {} if cfg.temperature is None else {"temperature": cfg.temperature}


# ── Anthropic ────────────────────────────────────────────────────────────────


def _anthropic_client(cfg: LLMConfig):
    from anthropic import Anthropic

    return Anthropic(api_key=cfg.api_key)


def _anthropic_text(cfg: LLMConfig, prompt: str, max_tokens: int) -> str:
    msg = _anthropic_client(cfg).messages.create(
        model=cfg.model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
        **_temp_kwargs(cfg),
    )
    parts = [b.text for b in msg.content if getattr(b, "type", "") == "text"]
    return "\n".join(parts).strip()


def _anthropic_tool(cfg: LLMConfig, prompt: str, tool_schema: dict, max_tokens: int) -> dict | None:
    msg = _anthropic_client(cfg).messages.create(
        model=cfg.model,
        max_tokens=max_tokens,
        tools=[tool_schema],
        tool_choice={"type": "tool", "name": tool_schema["name"]},
        messages=[{"role": "user", "content": prompt}],
        **_temp_kwargs(cfg),
    )
    for block in msg.content:
        if getattr(block, "type", "") == "tool_use":
            return dict(block.input)
    return None


# ── OpenAI / OpenAI-compatible ───────────────────────────────────────────────


def _openai_client(cfg: LLMConfig):
    from openai import OpenAI

    kwargs: dict[str, str] = {"api_key": cfg.api_key}
    if cfg.base_url:
        kwargs["base_url"] = cfg.base_url
    return OpenAI(**kwargs)


# Reasoning models (o-series/gpt-5) spend internal reasoning tokens *out of* the
# completion budget before emitting any visible output. Small caps meant for plain
# output (a one-word yes/no, a short tool call) starve that reasoning pass and the
# response truncates before any content -> HTTP 400. Floor the budget on that path
# so reasoning has room; billing is by tokens actually used, so a high cap is safe.
_REASONING_MIN_TOKENS = 16384


def _openai_create(client, max_tokens: int, **kwargs):
    """Call chat.completions.create, tolerating models that renamed the token
    limit param. Newer OpenAI models (o-series/gpt-5) reject ``max_tokens`` and
    require ``max_completion_tokens``; older models and most OpenAI-compatible
    endpoints (DeepSeek/Ollama) only accept ``max_tokens``. Default to the widely
    supported name and transparently retry only when the server asks for the
    newer one. On that retry we also raise the budget to ``_REASONING_MIN_TOKENS``
    (a floor, not a target) so reasoning models don't truncate mid-thought."""
    try:
        return client.chat.completions.create(max_tokens=max_tokens, **kwargs)
    except Exception as e:  # noqa: BLE001 — inspect the message, then retry or re-raise
        if "max_completion_tokens" in str(e):
            budget = max(max_tokens, _REASONING_MIN_TOKENS)
            return client.chat.completions.create(max_completion_tokens=budget, **kwargs)
        raise


def _openai_text(cfg: LLMConfig, prompt: str, max_tokens: int) -> str:
    resp = _openai_create(
        _openai_client(cfg),
        max_tokens,
        model=cfg.model,
        messages=[{"role": "user", "content": prompt}],
        **_temp_kwargs(cfg),
    )
    return (resp.choices[0].message.content or "").strip()


def _openai_tool(cfg: LLMConfig, prompt: str, tool_schema: dict, max_tokens: int) -> dict | None:
    fn = {
        "type": "function",
        "function": {
            "name": tool_schema["name"],
            "description": tool_schema.get("description", ""),
            "parameters": tool_schema["input_schema"],
        },
    }
    resp = _openai_create(
        _openai_client(cfg),
        max_tokens,
        model=cfg.model,
        tools=[fn],
        tool_choice={"type": "function", "function": {"name": tool_schema["name"]}},
        messages=[{"role": "user", "content": prompt}],
        **_temp_kwargs(cfg),
    )
    calls = resp.choices[0].message.tool_calls
    if not calls:
        return None
    try:
        return json.loads(calls[0].function.arguments)
    except (json.JSONDecodeError, TypeError):
        return None
