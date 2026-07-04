"""Settings API: the new jobs-config block and per-role LLM advanced fields
(max_tokens / temperature / prompt) round-trip through PUT then GET."""

from __future__ import annotations


async def test_settings_exposes_jobs_defaults(app_client):
    body = (await app_client.get("/api/settings")).json()
    assert body["jobs"]["default_range_days"] == 90
    assert "meet.google.com" in body["jobs"]["exclude"]["meeting_links"]
    names = {o["name"] for o in body["job_status_options"]}
    assert {"applied", "online_test", "interview", "offer"} <= names


async def test_jobs_config_round_trip(app_client):
    r = await app_client.put(
        "/api/settings/jobs",
        json={
            "company_aliases": {"sanalabs": "Sana"},
            "default_range_days": 30,
            "exclude": {"meeting_links": ["meet.google.com", "zoom.us"]},
            "status_rules": [{"keywords": ["ai面试"], "status": "online_test"}],
        },
    )
    assert r.status_code == 200
    jobs = r.json()["jobs"]
    assert jobs["default_range_days"] == 30
    assert jobs["company_aliases"] == {"sanalabs": "Sana"}
    assert "zoom.us" in jobs["exclude"]["meeting_links"]
    # A partial follow-up update must not wipe previously saved fields.
    r = await app_client.put("/api/settings/jobs", json={"default_range_days": 60})
    jobs = r.json()["jobs"]
    assert jobs["default_range_days"] == 60
    assert jobs["company_aliases"] == {"sanalabs": "Sana"}


async def test_jobs_config_rejects_unknown_status(app_client):
    r = await app_client.put(
        "/api/settings/jobs",
        json={"status_rules": [{"keywords": ["x"], "status": "bogus"}]},
    )
    assert r.status_code == 400


async def test_llm_role_advanced_round_trip(app_client):
    r = await app_client.put(
        "/api/settings/llm/extract",
        json={
            "provider": "anthropic",
            "model": "claude-sonnet-5",
            "base_url": "",
            "max_tokens": 2048,
            "temperature": 0.3,
            "prompt": "Custom {subject}",
        },
    )
    assert r.status_code == 200
    roles = {x["role"]: x for x in r.json()["llm"]}
    assert roles["extract"]["max_tokens"] == 2048
    assert roles["extract"]["temperature"] == 0.3
    assert roles["extract"]["prompt"] == "Custom {subject}"
    # Omitting advanced fields on a later basic save keeps the stored prompt.
    r = await app_client.put(
        "/api/settings/llm/extract",
        json={"provider": "anthropic", "model": "claude-sonnet-5", "base_url": ""},
    )
    roles = {x["role"]: x for x in r.json()["llm"]}
    assert roles["extract"]["prompt"] == "Custom {subject}"
    assert roles["extract"]["max_tokens"] == 2048
