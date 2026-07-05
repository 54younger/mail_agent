"""Two-model stages of the job-email pipeline: cheap classify + strong extract.

Stage 0 (keyword pre-filter) lives in ``job_keywords`` and runs in the API layer
before any model call. Here:

- ``classify_is_job`` uses the cheap ``classify`` role to answer a single
  yes/no: is this the recipient's own job-application email?
- ``extract`` uses the stronger ``extract`` role (tool/function calling) to pull
  company / applied date / status.

The caller (``app/api/jobs.py``) marks each email's ``job_screened`` state and
upserts a ``JobApplication`` (never overwriting manually-edited rows). HTML
bodies are stripped to text first. Provider/model per role are configured in
Settings (Claude, OpenAI, or an OpenAI-compatible endpoint).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import JobStatus
from . import job_config, llm
from .job_config import STATUS_BY_NAME as _STATUS_MAP
from .translation import _strip_html

# email_message.job_screened states.
SCREEN_UNSCREENED = 0  # not yet run through the pipeline
SCREEN_NOT_JOB = 1  # keyword/classify/extract decided it isn't a job email
SCREEN_LINKED = 2  # a JobApplication was created for it
SCREEN_EXCLUDED = 3  # matched an exclusion rule (e.g. Google Meet) — no record

_CLASSIFY_BODY_CHARS = 2_000
_MAX_BODY_CHARS = 8_000

# Built-in prompt templates (user-overridable per role in Settings). Placeholders
# {sender}/{subject}/{body} are filled at call time.
DEFAULT_CLASSIFY_PROMPT = (
    "You are a strict binary classifier. Decide whether this email is about the "
    "RECIPIENT'S OWN job application: application received/acknowledged, online "
    "assessment, interview invite, offer, or rejection. Job-listing digests, "
    "marketing, newsletters, and account/security notices are NOT. "
    "Answer with exactly one word: YES or NO.\n\n"
    "From: {sender}\nSubject: {subject}\n\n{body}"
)
DEFAULT_EXTRACT_PROMPT = (
    "Analyze this email and call record_job_application. Note: an automated/AI "
    "screening interview (e.g. 'AI面试', 'AI interview') counts as an online "
    "assessment, not a live interview.\n\n"
    "From: {sender}\nSubject: {subject}\n\n{body}"
)


def default_prompt(role: str) -> str:
    """The built-in template for a role, so Settings can seed an editable box."""
    return {"classify": DEFAULT_CLASSIFY_PROMPT, "extract": DEFAULT_EXTRACT_PROMPT}.get(role, "")


def _render(template: str, *, sender: str, subject: str, body: str) -> str:
    """Fill a prompt template. Tolerates a broken/unknown placeholder in a
    user-edited template by appending the email instead of raising."""
    try:
        return template.format(sender=sender, subject=subject, body=body)
    except (KeyError, IndexError, ValueError):
        return f"{template}\n\nFrom: {sender}\nSubject: {subject}\n\n{body}"

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
            "position": {
                "type": "string",
                "description": "Job title/role the email is about (e.g. 'Backend Engineer'), "
                "or empty if none is named.",
            },
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
    def __init__(self, message: str = "Job extraction unavailable: configure an API key for the classify/extract models in Settings first."):
        super().__init__(message)
        self.message = message


@dataclass
class JobExtraction:
    is_job: bool
    company: str
    applied_date: str  # ISO string or ""
    status_code: int
    position: str = ""


def classify_configured() -> bool:
    return llm.get_llm_config("classify").is_configured


def extract_configured() -> bool:
    return llm.get_llm_config("extract").is_configured


def classify_is_job(*, subject: str, sender: str, body: str) -> bool:
    """Cheap binary gate: is this the recipient's own job-application email?"""
    cfg = llm.get_llm_config("classify")
    if not cfg.is_configured:
        raise JobExtractionUnavailable()

    plain = _strip_html(body)[:_CLASSIFY_BODY_CHARS]
    prompt = _render(cfg.prompt or DEFAULT_CLASSIFY_PROMPT, sender=sender, subject=subject, body=plain)
    out = llm.complete_text(cfg, prompt).strip().lower()
    return out.startswith("y")


def extract(*, subject: str, sender: str, body: str) -> JobExtraction:
    """Strong-model structured extraction of company / date / status."""
    cfg = llm.get_llm_config("extract")
    if not cfg.is_configured:
        raise JobExtractionUnavailable()

    plain = _strip_html(body)[:_MAX_BODY_CHARS]
    content = _render(cfg.prompt or DEFAULT_EXTRACT_PROMPT, sender=sender, subject=subject, body=plain)
    data = llm.complete_tool(cfg, content, _TOOL)
    if data is None:
        return JobExtraction(False, "", "", JobStatus.UNKNOWN)

    status_code = _STATUS_MAP.get(str(data.get("status", "unknown")), JobStatus.UNKNOWN)
    # Deterministic keyword overrides (e.g. domestic "AI面试" is really an online
    # assessment, which the model often mislabels as a live interview). Terminal
    # outcomes (offer/rejected) win over a keyword hint so a rejection that merely
    # mentions an AI interview isn't downgraded to "assessment".
    override = job_config.load().status_override(subject=subject, body=plain)
    if override is not None and status_code not in (JobStatus.OFFER, JobStatus.REJECTED):
        status_code = override
    return JobExtraction(
        is_job=bool(data.get("is_job_related")),
        company=str(data.get("company", "")).strip(),
        applied_date=str(data.get("applied_date", "")).strip(),
        status_code=int(status_code),
        position=str(data.get("position", "")).strip(),
    )
