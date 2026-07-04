"""Stage-0 keyword pre-filter for job-application emails.

Purely local and free: an email whose subject/body contains none of the
configured terms is almost certainly not about the recipient's own job
application, so we skip the paid LLM classify/extract stages entirely and mark it
screened. Called from ``job_extract_manager._process_one`` before any model call.

The keyword list is user-editable (Settings → 求职识别); defaults and the
compiled pattern live in ``job_config`` and are cached there.
"""

from __future__ import annotations

from . import job_config


def looks_like_candidate(
    subject: str, body: str, cfg: job_config.JobsConfig | None = None
) -> bool:
    """True if the email might be job-related (keyword hit in subject or body)."""
    cfg = cfg or job_config.load()
    return bool(cfg.keyword_pattern.search(f"{subject or ''}\n{body or ''}"))
