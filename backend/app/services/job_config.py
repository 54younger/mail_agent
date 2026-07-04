"""User-tunable job-pipeline config: keywords, exclusions, company normalization,
status-mapping rules, and the default extraction range.

Everything here lives in ``settings.json`` under the ``"jobs"`` key, merged over
built-in defaults so a fresh (or old) settings file still behaves sensibly and
new fields appear without a migration. The Settings UI edits it via
``PUT /api/settings/jobs``.

The built config is cached and only rebuilt when ``settings.json`` changes on
disk, so the free Stage-0 keyword pre-filter (run on every candidate email)
doesn't re-read/re-compile per email.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .. import config
from ..models import JobStatus

# Canonical status name -> code. Single source of truth shared with the extractor
# (its tool-call ``status`` enum) and the status-override rules.
STATUS_BY_NAME: dict[str, int] = {
    "applied": JobStatus.APPLIED,
    "online_test": JobStatus.ONLINE_TEST,
    "interview": JobStatus.INTERVIEW,
    "offer": JobStatus.OFFER,
    "rejected": JobStatus.REJECTED,
    "unknown": JobStatus.UNKNOWN,
}

# ── Built-in defaults (migrated from previously hard-coded values) ────────────

_DEFAULT_KEYWORDS: tuple[str, ...] = (
    # English
    "application", "applied", "apply", "candidate", "interview", "offer",
    "assessment", "online test", "coding challenge", "recruit", "recruiter",
    "hiring", "position", "vacancy", "screening", "shortlist", "onsite",
    "phone screen", "talent", "resume", "cv", "regret", "unfortunately",
    "not moving forward", "next steps", "onboarding", "job",
    "ai interview", "hackerrank", "codility",
    # Chinese
    "求职", "投递", "简历", "面试", "笔试", "测评", "录用", "招聘", "应聘",
    "岗位", "职位", "初试", "复试", "终面", "感谢您的申请", "感谢你的申请",
    "很遗憾", "不合适", "入职", "内推", "校招", "社招", "人才", "面邀",
    "ai面试", "ai 面试", "自动化面试", "智能面试", "在线测评",
)

# Emails containing any of these are meeting logistics (e.g. a Google Meet invite
# that duplicates the "you advanced to interview" email) — excluded from the
# board so they don't create a second record. Editable in Settings.
_DEFAULT_MEETING_LINKS: tuple[str, ...] = ("meet.google.com", "谷歌会议")

# Trailing corporate suffixes dropped when normalizing a company name so
# "Sana" and "Sanalabs" collapse to one key. Short/ambiguous ones (co, inc, ai)
# are only stripped as standalone trailing tokens; distinctive/longer ones
# (labs, 科技, 有限公司…) are also stripped when glued to the stem.
_DEFAULT_STRIP_SUFFIXES: tuple[str, ...] = (
    "labs", "lab", "inc", "ltd", "llc", "co", "corp", "corporation", "company",
    "technologies", "technology", "tech", "group", "holdings", "ai",
    "科技", "技术", "网络", "信息", "有限公司", "股份有限公司", "公司",
)

# Deterministic status overrides: if any keyword appears in subject/body, force
# that status regardless of the model's guess. Default: domestic "AI interview"
# is really an automated assessment, not a live interview.
_DEFAULT_STATUS_RULES: tuple[dict, ...] = (
    {
        "keywords": ["ai面试", "ai interview", "ai 面试", "自动化面试", "智能面试"],
        "status": "online_test",
    },
)

_DEFAULT_RANGE_DAYS = 90

# Glued suffix stripping is riskier (can bite into a real name), so only apply it
# to suffixes that are either reasonably long or non-ASCII (CJK), and only when a
# usable stem remains.
_GLUED_MIN_LEN = 4
_GLUED_MIN_STEM = 3

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_SPACE_RE = re.compile(r"\s+")


# ── Normalization helpers ─────────────────────────────────────────────────────


def _norm_basic(name: str) -> str:
    """Lowercase, drop punctuation, collapse whitespace."""
    return _SPACE_RE.sub(" ", _PUNCT_RE.sub(" ", (name or "").casefold())).strip()


def _can_glue(suffix: str) -> bool:
    return len(suffix) >= _GLUED_MIN_LEN or any(ord(c) > 127 for c in suffix)


def _strip_stem(basic: str, suffixes: frozenset[str]) -> str:
    """Peel trailing corporate suffixes off an already-basic-normalized name."""
    if not basic:
        return basic
    glued = sorted((s for s in suffixes if _can_glue(s)), key=len, reverse=True)
    s = basic
    changed = True
    while changed:
        changed = False
        tokens = s.split()
        if len(tokens) >= 2 and tokens[-1] in suffixes:
            s = " ".join(tokens[:-1]).strip()
            changed = True
            continue
        for suf in glued:
            if s.endswith(suf) and len(s) - len(suf) >= _GLUED_MIN_STEM:
                stem = s[: -len(suf)].strip()
                if stem:
                    s = stem
                    changed = True
                    break
    return s or basic


def normalize_company(
    name: str, *, strip_suffixes: frozenset[str], aliases: dict[str, str]
) -> tuple[str, str | None]:
    """Return ``(group_key, canonical_display_or_None)`` for a company name.

    ``group_key`` is the case/punctuation/suffix-insensitive key used to dedup
    a group. When an alias matches, its canonical display is returned so the row
    can show the user's preferred spelling; otherwise the caller picks a
    representative from the group's raw names.
    """
    basic = _norm_basic(name)
    if not basic:
        return "", None
    if basic in aliases:
        disp = aliases[basic]
        return _strip_stem(_norm_basic(disp), strip_suffixes), disp
    stem = _strip_stem(basic, strip_suffixes)
    if stem in aliases:
        disp = aliases[stem]
        return _strip_stem(_norm_basic(disp), strip_suffixes), disp
    return stem, None


# ── Config object + cached loader ─────────────────────────────────────────────


@dataclass(frozen=True)
class JobsConfig:
    keywords: tuple[str, ...]
    keyword_pattern: re.Pattern[str]
    meeting_links: tuple[str, ...]
    excluded_senders: tuple[str, ...]
    strip_suffixes: frozenset[str]
    aliases: dict[str, str]  # normalized variant -> canonical display
    status_rules: tuple[tuple[tuple[str, ...], int], ...]  # (keywords, code)
    default_range_days: int

    def company_key(self, name: str) -> tuple[str, str | None]:
        return normalize_company(
            name, strip_suffixes=self.strip_suffixes, aliases=self.aliases
        )

    def is_excluded(self, *, subject: str, sender: str, body: str) -> bool:
        haystack = f"{subject or ''}\n{body or ''}".casefold()
        if any(link.casefold() in haystack for link in self.meeting_links if link):
            return True
        low_sender = (sender or "").casefold()
        return any(s.casefold() in low_sender for s in self.excluded_senders if s)

    def status_override(self, *, subject: str, body: str) -> int | None:
        haystack = f"{subject or ''}\n{body or ''}".casefold()
        for keywords, code in self.status_rules:
            if any(kw in haystack for kw in keywords):
                return code
        return None


def _as_str_list(value: object, default: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(value, list):
        return default
    out = [str(v).strip() for v in value if str(v).strip()]
    return tuple(out)


def _build_rules(raw: object) -> tuple[tuple[tuple[str, ...], int], ...]:
    if not isinstance(raw, list):
        raw = list(_DEFAULT_STATUS_RULES)
    rules: list[tuple[tuple[str, ...], int]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        kws = tuple(
            str(k).strip().casefold() for k in (item.get("keywords") or []) if str(k).strip()
        )
        code = STATUS_BY_NAME.get(str(item.get("status", "")).strip())
        if kws and code is not None:
            rules.append((kws, int(code)))
    return tuple(rules)


def _compile(keywords: tuple[str, ...]) -> re.Pattern[str]:
    terms = [k for k in keywords if k] or ["\0"]  # never-matching fallback if empty
    return re.compile("|".join(re.escape(k) for k in terms), re.IGNORECASE)


def _build(settings: dict) -> JobsConfig:
    jobs = settings.get("jobs") if isinstance(settings.get("jobs"), dict) else {}
    jobs = jobs or {}
    exclude = jobs.get("exclude") if isinstance(jobs.get("exclude"), dict) else {}
    exclude = exclude or {}

    keywords = _as_str_list(jobs.get("keywords"), _DEFAULT_KEYWORDS)
    suffixes = frozenset(
        s.casefold() for s in _as_str_list(jobs.get("company_strip_suffixes"), _DEFAULT_STRIP_SUFFIXES)
    )

    aliases: dict[str, str] = {}
    raw_aliases = jobs.get("company_aliases")
    if isinstance(raw_aliases, dict):
        for frm, to in raw_aliases.items():
            nf, disp = _norm_basic(str(frm)), str(to).strip()
            if nf and disp:
                aliases[nf] = disp
                aliases[_strip_stem(nf, suffixes)] = disp

    return JobsConfig(
        keywords=keywords,
        keyword_pattern=_compile(keywords),
        meeting_links=_as_str_list(exclude.get("meeting_links"), _DEFAULT_MEETING_LINKS),
        excluded_senders=_as_str_list(exclude.get("senders"), ()),
        strip_suffixes=suffixes,
        aliases=aliases,
        status_rules=_build_rules(
            jobs.get("status_rules") if "status_rules" in jobs else list(_DEFAULT_STATUS_RULES)
        ),
        default_range_days=int(jobs.get("default_range_days") or _DEFAULT_RANGE_DAYS),
    )


_cache: tuple[float, JobsConfig] | None = None


def load() -> JobsConfig:
    """Return the current jobs config, rebuilding only when settings.json changes."""
    global _cache
    mtime = config.settings_mtime()
    if _cache is not None and _cache[0] == mtime:
        return _cache[1]
    cfg = _build(config.load_settings())
    _cache = (mtime, cfg)
    return cfg


def defaults() -> dict:
    """Default ``jobs`` block, for seeding the Settings UI / API response."""
    return {
        "keywords": list(_DEFAULT_KEYWORDS),
        "exclude": {"meeting_links": list(_DEFAULT_MEETING_LINKS), "senders": []},
        "company_strip_suffixes": list(_DEFAULT_STRIP_SUFFIXES),
        "company_aliases": {},
        "status_rules": [dict(r) for r in _DEFAULT_STATUS_RULES],
        "default_range_days": _DEFAULT_RANGE_DAYS,
    }


def effective_raw() -> dict:
    """Defaults overlaid with the user's stored ``jobs`` block, in JSON-friendly
    form for the Settings UI to display and round-trip (not the compiled config)."""
    result = defaults()
    stored = config.load_settings().get("jobs")
    if not isinstance(stored, dict):
        return result
    for key in ("keywords", "company_strip_suffixes", "company_aliases", "status_rules"):
        if key in stored:
            result[key] = stored[key]
    if "default_range_days" in stored:
        result["default_range_days"] = int(stored.get("default_range_days") or _DEFAULT_RANGE_DAYS)
    if isinstance(stored.get("exclude"), dict):
        result["exclude"] = {**result["exclude"], **stored["exclude"]}
    return result
