"""Extract job-application facts from an email using Claude Haiku (tool_use).

Given an email's subject / sender / body, Claude decides whether it's a job
application email and, if so, returns the company, applied date, and current
status. The caller upserts a JobApplication (never overwriting manually-edited
rows). HTML bodies are stripped to text first.
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import secrets_store
from ..models import JobStatus
from .translation import _strip_html

_MODEL = "claude-haiku-4-5-20251001"
_MAX_BODY_CHARS = 8_000

# Claude's status string -> JobStatus code.
_STATUS_MAP: dict[str, int] = {
    "applied": JobStatus.APPLIED,
    "online_test": JobStatus.ONLINE_TEST,
    "interview": JobStatus.INTERVIEW,
    "offer": JobStatus.OFFER,
    "rejected": JobStatus.REJECTED,
    "unknown": JobStatus.UNKNOWN,
}

_TOOL = {
    "name": "record_job_application",
    "description": "Record structured facts about a job-application-related email.",
    "input_schema": {
        "type": "object",
        "properties": {
            "is_job_related": {
                "type": "boolean",
                "description": "True only if this email concerns the recipient's own job "
                "application (application received, online assessment, interview "
                "invite, offer, or rejection). Newsletters/marketing are false.",
            },
            "company": {"type": "string", "description": "Hiring company name, or empty."},
            "applied_date": {
                "type": "string",
                "description": "ISO-8601 date the application/status refers to, or empty.",
            },
            "status": {
                "type": "string",
                "enum": list(_STATUS_MAP.keys()),
                "description": "Current stage implied by this email.",
            },
        },
        "required": ["is_job_related", "company", "status"],
    },
}


class JobExtractionUnavailable(Exception):
    def __init__(self, message: str = "求职抽取不可用：请先在设置中配置 Claude API Key。"):
        super().__init__(message)
        self.message = message


@dataclass
class JobExtraction:
    is_job: bool
    company: str
    applied_date: str  # ISO string or ""
    status_code: int


class JobExtractor:
    def __init__(self, api_key: str | None):
        self._api_key = api_key or ""

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def extract(self, *, subject: str, sender: str, body: str) -> JobExtraction:
        if not self.is_configured:
            raise JobExtractionUnavailable()

        from anthropic import Anthropic

        plain = _strip_html(body)[:_MAX_BODY_CHARS]
        content = (
            "Analyze this email and call record_job_application.\n\n"
            f"From: {sender}\nSubject: {subject}\n\n{plain}"
        )
        client = Anthropic(api_key=self._api_key)
        msg = client.messages.create(
            model=_MODEL,
            max_tokens=512,
            tools=[_TOOL],
            tool_choice={"type": "tool", "name": "record_job_application"},
            messages=[{"role": "user", "content": content}],
        )

        data = _first_tool_input(msg)
        if data is None:
            return JobExtraction(False, "", "", JobStatus.UNKNOWN)

        status_code = _STATUS_MAP.get(str(data.get("status", "unknown")), JobStatus.UNKNOWN)
        return JobExtraction(
            is_job=bool(data.get("is_job_related")),
            company=str(data.get("company", "")).strip(),
            applied_date=str(data.get("applied_date", "")).strip(),
            status_code=int(status_code),
        )


def _first_tool_input(msg) -> dict | None:
    for block in msg.content:
        if getattr(block, "type", "") == "tool_use":
            return block.input
    return None


def get_extractor() -> JobExtractor:
    return JobExtractor(secrets_store.get_claude_key())
