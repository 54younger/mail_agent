"""job_extractor: deterministic status-override rules and user-editable prompts.
The LLM tool/text calls are stubbed — no network."""

from __future__ import annotations

from app import secrets_store
from app.services import job_extractor, llm


def _tool_result(status: str):
    return {
        "is_job_related": True,
        "company": "Acme",
        "position": "",
        "applied_date": "",
        "status": status,
    }


def test_extract_overrides_ai_interview_to_assessment(monkeypatch, data_dir):
    secrets_store.set_claude_key("sk")
    monkeypatch.setattr(llm, "complete_tool", lambda *a, **k: _tool_result("interview"))
    res = job_extractor.extract(subject="AI面试通知", sender="hr@acme.com", body="请完成AI面试")
    assert res.status_code == job_extractor.JobStatus.ONLINE_TEST


def test_extract_keeps_rejection_over_rule(monkeypatch, data_dir):
    secrets_store.set_claude_key("sk")
    monkeypatch.setattr(llm, "complete_tool", lambda *a, **k: _tool_result("rejected"))
    # A terminal rejection is not downgraded even if the body mentions "AI面试".
    res = job_extractor.extract(subject="结果通知", sender="hr@acme.com", body="很遗憾，AI面试未通过")
    assert res.status_code == job_extractor.JobStatus.REJECTED


def test_classify_uses_custom_prompt(monkeypatch, data_dir):
    secrets_store.set_claude_key("sk")
    llm.set_role_settings(
        "classify", provider="anthropic", model="claude-x", base_url="", prompt="CUSTOM {subject}//{body}"
    )
    captured: dict[str, str] = {}

    def fake_complete_text(cfg, prompt, **k):
        captured["prompt"] = prompt
        return "YES"

    monkeypatch.setattr(llm, "complete_text", fake_complete_text)
    assert job_extractor.classify_is_job(subject="Hi", sender="x", body="Body") is True
    assert captured["prompt"].startswith("CUSTOM Hi//")
