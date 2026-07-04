"""Unit tests for the job-config layer: company normalization/aliases, meeting
exclusion, and status-override rules. Pure functions — no DB or network."""

from __future__ import annotations

from app.services import job_config


def _cfg(jobs: dict | None = None):
    return job_config._build({"jobs": jobs} if jobs is not None else {})


def test_normalize_merges_suffix_variants():
    cfg = _cfg()

    def key(name: str) -> str:
        return cfg.company_key(name)[0]

    assert key("Sana") == key("Sanalabs") == key("Sana Labs")


def test_normalize_keeps_distinct_companies():
    cfg = _cfg()
    assert cfg.company_key("Apple")[0] != cfg.company_key("Apple Bank")[0]


def test_cjk_suffix_stripped():
    cfg = _cfg()
    assert cfg.company_key("字节跳动科技有限公司")[0] == cfg.company_key("字节跳动")[0]


def test_alias_maps_to_canonical_display():
    cfg = _cfg({"company_aliases": {"bytedance": "字节跳动"}})
    key, disp = cfg.company_key("ByteDance Inc")
    assert key == cfg.company_key("字节跳动")[0]
    assert disp == "字节跳动"


def test_meeting_link_excluded():
    cfg = _cfg()
    assert cfg.is_excluded(
        subject="Interview", sender="hr@x.com", body="Join https://meet.google.com/abc-def"
    )
    assert not cfg.is_excluded(subject="Interview", sender="hr@x.com", body="no link here")


def test_excluded_sender():
    cfg = _cfg({"exclude": {"senders": ["noreply@calendar"]}})
    assert cfg.is_excluded(subject="x", sender="noreply@calendar.google.com", body="")


def test_status_override_ai_interview():
    cfg = _cfg()
    assert cfg.status_override(subject="AI面试邀请", body="") == job_config.STATUS_BY_NAME["online_test"]
    assert cfg.status_override(subject="Onsite interview", body="normal invite") is None


def test_build_overlays_defaults():
    cfg = job_config._build({"jobs": {"default_range_days": 30}})
    assert cfg.default_range_days == 30
    # unspecified fields still fall back to defaults
    assert cfg.company_key("Sanalabs")[0] == cfg.company_key("Sana")[0]
