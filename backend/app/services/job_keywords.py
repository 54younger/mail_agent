"""Stage-0 keyword pre-filter for job-application emails.

Purely local and free: an email whose subject/body contains none of these terms
is almost certainly not about the recipient's own job application, so we skip the
paid LLM classify/extract stages entirely and mark it screened. Called from
``app/api/jobs.py:extract_jobs`` before any model call.
"""

from __future__ import annotations

import re

# Mixed EN/ZH terms seen across application acknowledgements, assessments,
# interview invites, offers, and rejections. Kept intentionally broad — this is
# a recall-first pre-filter; the cheap classifier removes false positives.
_KEYWORDS: tuple[str, ...] = (
    # English
    "application", "applied", "apply", "candidate", "interview", "offer",
    "assessment", "online test", "coding challenge", "recruit", "recruiter",
    "hiring", "position", "vacancy", "screening", "shortlist", "onsite",
    "phone screen", "talent", "resume", "cv", "regret", "unfortunately",
    "not moving forward", "next steps", "onboarding", "job",
    # Chinese
    "求职", "投递", "简历", "面试", "笔试", "测评", "录用", "招聘", "应聘",
    "岗位", "职位", "初试", "复试", "终面", "感谢您的申请", "感谢你的申请",
    "很遗憾", "不合适", "入职", "内推", "校招", "社招", "人才", "面邀",
)

_PATTERN = re.compile("|".join(re.escape(k) for k in _KEYWORDS), re.IGNORECASE)


def looks_like_candidate(subject: str, body: str) -> bool:
    """True if the email might be job-related (keyword hit in subject or body)."""
    return bool(_PATTERN.search(f"{subject or ''}\n{body or ''}"))
