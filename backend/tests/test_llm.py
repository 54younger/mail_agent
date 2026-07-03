"""LLM abstraction: per-role config, legacy key fallback, and the Anthropic /
OpenAI completion branches (SDK clients are stubbed — no network)."""

from __future__ import annotations

from types import SimpleNamespace

from app import secrets_store
from app.services import llm


def test_role_settings_defaults(data_dir):
    s = llm.role_settings("classify")
    assert s["provider"] == "anthropic"
    assert s["model"]  # non-empty default model


def test_set_and_get_role_config(data_dir):
    llm.set_role_settings(
        "extract", provider="openai_compatible", model="deepseek-chat", base_url="https://x/v1"
    )
    assert llm.role_settings("extract") == {
        "provider": "openai_compatible",
        "model": "deepseek-chat",
        "base_url": "https://x/v1",
    }


def test_role_key_and_legacy_fallback(data_dir):
    assert llm.role_key_configured("classify") is False

    # The legacy single Claude key acts as a fallback for every role.
    secrets_store.set_claude_key("sk-legacy")
    assert llm.role_key_configured("classify") is True
    assert llm.get_llm_config("classify").api_key == "sk-legacy"

    # An explicit per-role key wins over the legacy fallback.
    llm.set_role_key("classify", "sk-role")
    assert llm.get_llm_config("classify").api_key == "sk-role"


def test_unknown_provider_rejected(data_dir):
    import pytest

    with pytest.raises(ValueError):
        llm.set_role_settings("classify", provider="mystery", model="m", base_url="")


def _anthropic_msg(blocks):
    return SimpleNamespace(content=blocks)


def test_complete_text_anthropic(monkeypatch, data_dir):
    block = SimpleNamespace(type="text", text="Hello")
    client = SimpleNamespace(
        messages=SimpleNamespace(create=lambda **k: _anthropic_msg([block]))
    )
    monkeypatch.setattr(llm, "_anthropic_client", lambda cfg: client)
    cfg = llm.LLMConfig("anthropic", "claude-x", "", "sk")
    assert llm.complete_text(cfg, "hi") == "Hello"


def test_complete_tool_anthropic(monkeypatch, data_dir):
    block = SimpleNamespace(type="tool_use", input={"is_job_related": True, "company": "Acme"})
    client = SimpleNamespace(
        messages=SimpleNamespace(create=lambda **k: _anthropic_msg([block]))
    )
    monkeypatch.setattr(llm, "_anthropic_client", lambda cfg: client)
    cfg = llm.LLMConfig("anthropic", "claude-x", "", "sk")
    out = llm.complete_tool(cfg, "hi", {"name": "t", "input_schema": {}})
    assert out == {"is_job_related": True, "company": "Acme"}


def test_complete_tool_openai_parses_arguments(monkeypatch, data_dir):
    call = SimpleNamespace(function=SimpleNamespace(arguments='{"company": "Beta"}'))
    resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[call]))]
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **k: resp))
    )
    monkeypatch.setattr(llm, "_openai_client", lambda cfg: client)
    cfg = llm.LLMConfig("openai", "gpt-x", "", "sk")
    out = llm.complete_tool(cfg, "hi", {"name": "t", "description": "", "input_schema": {}})
    assert out == {"company": "Beta"}


def test_unconfigured_raises(data_dir):
    import pytest

    cfg = llm.LLMConfig("anthropic", "", "", "")
    with pytest.raises(llm.LLMUnavailable):
        llm.complete_text(cfg, "hi")


def test_openai_falls_back_to_max_completion_tokens(monkeypatch, data_dir):
    # Newer OpenAI models reject max_tokens; the client should transparently
    # retry with max_completion_tokens.
    seen = []

    def create(**kwargs):
        if "max_tokens" in kwargs:
            seen.append("max_tokens")
            raise RuntimeError(
                "Unsupported parameter: 'max_tokens' ... Use 'max_completion_tokens' instead."
            )
        seen.append("max_completion_tokens")
        call = SimpleNamespace(function=SimpleNamespace(arguments='{"company": "Gamma"}'))
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[call]))]
        )

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(llm, "_openai_client", lambda cfg: client)
    cfg = llm.LLMConfig("openai", "gpt-5", "", "sk")
    out = llm.complete_tool(cfg, "hi", {"name": "t", "description": "", "input_schema": {}})
    assert out == {"company": "Gamma"}
    assert seen == ["max_tokens", "max_completion_tokens"]


def test_openai_reasoning_budget_floored(monkeypatch, data_dir):
    # Reasoning models bill reasoning tokens against the completion budget, so a
    # tiny cap (here 5, as classify uses) would truncate before any output. On the
    # max_completion_tokens retry the budget must be floored so it can finish.
    seen = {}

    def create(**kwargs):
        if "max_tokens" in kwargs:
            raise RuntimeError("Use 'max_completion_tokens' instead.")
        seen["budget"] = kwargs["max_completion_tokens"]
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="YES"))]
        )

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(llm, "_openai_client", lambda cfg: client)
    cfg = llm.LLMConfig("openai", "gpt-5", "", "sk")
    assert llm.complete_text(cfg, "hi", max_tokens=5) == "YES"
    assert seen["budget"] == llm._REASONING_MIN_TOKENS


def test_openai_reraises_unrelated_errors(monkeypatch, data_dir):
    import pytest

    def create(**kwargs):
        raise RuntimeError("invalid api key")

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(llm, "_openai_client", lambda cfg: client)
    cfg = llm.LLMConfig("openai", "gpt-4o-mini", "", "sk")
    with pytest.raises(RuntimeError, match="invalid api key"):
        llm.complete_text(cfg, "hi")
