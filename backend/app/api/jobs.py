"""求职看板 API — list, background extraction (+progress), manual add/edit, moves.

Status changes and manual edits set manually_edited=True and append to the
timeline. The 3-stage extraction pipeline runs in the background (see
``job_extract_manager``); this router only triggers it and reports progress.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import EmailMessage, JobApplication, JobStatus
from ..schemas.job import (
    ApplicationSummary,
    ExtractStatus,
    FunnelStage,
    JobApplicationOut,
    JobEdit,
    JobStats,
    JobStatusUpdate,
    ManualJobIn,
    SummaryRecord,
    TimelineEntry,
    TrendPoint,
)
from ..services import job_extract_manager

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timeline(job: JobApplication) -> list[dict]:
    try:
        return json.loads(job.timeline_json or "[]")
    except json.JSONDecodeError:
        return []


def _append_timeline(job: JobApplication, status_code: int) -> None:
    tl = _timeline(job)
    tl.append({"status": status_code, "ts": _now_iso()})
    job.timeline_json = json.dumps(tl)


def _to_dto(job: JobApplication, subject: str | None = None) -> JobApplicationOut:
    return JobApplicationOut(
        id=job.id,
        company=job.company,
        position=job.position or "",
        applied_at=job.applied_at,
        status_code=job.status_code,
        email_id=job.email_id,
        manually_edited=job.manually_edited,
        timeline=[TimelineEntry(**e) for e in _timeline(job)],
        source_subject=subject,
    )


async def _subjects_for(session: AsyncSession, jobs: list[JobApplication]) -> dict[int, str]:
    ids = [j.email_id for j in jobs if j.email_id]
    if not ids:
        return {}
    rows = await session.execute(
        select(EmailMessage.id, EmailMessage.subject).where(EmailMessage.id.in_(ids))
    )
    return {eid: subj for eid, subj in rows.all()}


@router.get("", response_model=list[JobApplicationOut])
async def list_jobs(session: AsyncSession = Depends(get_session)) -> list[JobApplicationOut]:
    jobs = (
        await session.execute(select(JobApplication).order_by(JobApplication.applied_at.desc()))
    ).scalars().all()
    subjects = await _subjects_for(session, jobs)
    return [_to_dto(j, subjects.get(j.email_id)) for j in jobs]


# ── Deduped summary (one row per company+position) + dashboard stats ──────────


def _aware(dt: datetime) -> datetime:
    """SQLite hands back naive datetimes; treat them as UTC so aware/naive values
    (e.g. parsed timeline timestamps) stay comparable."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _parse_ts(ts: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return _aware(dt)


def _group_key(job: JobApplication) -> tuple[str, str]:
    """Case/space-insensitive (company, position) key that dedups a group."""
    return (job.company.strip().casefold(), (job.position or "").strip().casefold())


def _group_jobs(jobs: list[JobApplication]) -> list[list[JobApplication]]:
    groups: dict[tuple[str, str], list[JobApplication]] = {}
    for j in jobs:
        groups.setdefault(_group_key(j), []).append(j)
    return list(groups.values())


def _reached_statuses(records: list[JobApplication]) -> set[int]:
    """Every status a group has ever been in (union of timelines + current)."""
    seen: set[int] = set()
    for r in records:
        seen.add(r.status_code)
        for e in _timeline(r):
            seen.add(int(e.get("status", JobStatus.UNKNOWN)))
    return seen


def _summarize(records: list[JobApplication], subjects: dict[int, str]) -> ApplicationSummary:
    ordered = sorted(records, key=lambda r: r.applied_at)
    first = ordered[0]

    # Walk every timeline event to find the newest one (its status is "current")
    # and the latest update time; the record holding it is the status-edit target.
    latest_ts: datetime | None = None
    latest_status = ordered[-1].status_code
    primary = ordered[-1]
    last_update = max(_aware(r.applied_at) for r in records)
    for r in records:
        for e in _timeline(r):
            ts = _parse_ts(e.get("ts", ""))
            if ts is None:
                continue
            if ts > last_update:
                last_update = ts
            if latest_ts is None or ts > latest_ts:
                latest_ts = ts
                latest_status = int(e.get("status", r.status_code))
                primary = r

    return ApplicationSummary(
        company=first.company or "",
        position=first.position or "",
        applied_at=_aware(first.applied_at),
        status_code=int(latest_status),
        last_update=last_update,
        count=len(records),
        manually_edited=any(r.manually_edited for r in records),
        primary_id=primary.id,
        records=[
            SummaryRecord(
                id=r.id,
                email_id=r.email_id,
                source_subject=subjects.get(r.email_id),
                status_code=r.status_code,
                applied_at=r.applied_at,
                timeline=[TimelineEntry(**e) for e in _timeline(r)],
            )
            for r in ordered
        ],
    )


@router.get("/summary", response_model=list[ApplicationSummary])
async def list_summary(session: AsyncSession = Depends(get_session)) -> list[ApplicationSummary]:
    jobs = (await session.execute(select(JobApplication))).scalars().all()
    subjects = await _subjects_for(session, jobs)
    summaries = [_summarize(g, subjects) for g in _group_jobs(jobs)]
    summaries.sort(key=lambda s: s.last_update, reverse=True)
    return summaries


@router.get("/stats", response_model=JobStats)
async def job_stats(session: AsyncSession = Depends(get_session)) -> JobStats:
    jobs = (await session.execute(select(JobApplication))).scalars().all()
    groups = _group_jobs(jobs)
    units = [_summarize(g, {}) for g in groups]
    total = len(units)

    by_status: dict[int, int] = {}
    trend_map: dict[str, int] = {}
    for u in units:
        by_status[u.status_code] = by_status.get(u.status_code, 0) + 1
        day = u.applied_at.date().isoformat()
        trend_map[day] = trend_map.get(day, 0) + 1

    # Funnel: how many application units ever reached each stage. "Applied" is the
    # base (every tracked application implies an application), so its count = total.
    reached = {code: 0 for code in (JobStatus.ONLINE_TEST, JobStatus.INTERVIEW, JobStatus.OFFER)}
    for g in groups:
        seen = _reached_statuses(g)
        for code in reached:
            if code in seen:
                reached[code] += 1

    funnel = [
        FunnelStage(status_code=int(JobStatus.APPLIED), count=total),
        FunnelStage(status_code=int(JobStatus.ONLINE_TEST), count=reached[JobStatus.ONLINE_TEST]),
        FunnelStage(status_code=int(JobStatus.INTERVIEW), count=reached[JobStatus.INTERVIEW]),
        FunnelStage(status_code=int(JobStatus.OFFER), count=reached[JobStatus.OFFER]),
    ]
    return JobStats(
        total=total,
        by_status=by_status,
        trend=[TrendPoint(date=d, count=c) for d, c in sorted(trend_map.items())],
        funnel=funnel,
        interview_rate=(reached[JobStatus.INTERVIEW] / total) if total else 0.0,
        offer_rate=(reached[JobStatus.OFFER] / total) if total else 0.0,
    )


def _extract_status(s: job_extract_manager.ExtractState) -> ExtractStatus:
    return ExtractStatus(
        running=s.running,
        phase=s.phase,
        total=s.total,
        current=s.current,
        stage=s.stage,
        created=s.created,
        done=s.done,
        error=s.error,
        hint=s.hint,
        detail=s.detail,
    )


@router.post("/extract", response_model=ExtractStatus)
async def extract_jobs(
    since: datetime | None = None, until: datetime | None = None
) -> ExtractStatus:
    # Kick off the background pipeline over the [since, until] window (no-op if one
    # is already running); the client polls /extract/status for progress.
    await job_extract_manager.start_extract(since, until)
    return _extract_status(job_extract_manager.get_state())


@router.get("/extract/status", response_model=ExtractStatus)
async def extract_status() -> ExtractStatus:
    return _extract_status(job_extract_manager.get_state())


@router.post("", response_model=JobApplicationOut)
async def create_job(
    payload: ManualJobIn, session: AsyncSession = Depends(get_session)
) -> JobApplicationOut:
    applied = payload.applied_at or datetime.now(timezone.utc)
    job = JobApplication(
        company=payload.company,
        position=payload.position,
        applied_at=applied,
        status_code=payload.status_code,
        email_id=0,
        manually_edited=True,
        timeline_json=json.dumps([{"status": payload.status_code, "ts": applied.isoformat()}]),
    )
    session.add(job)
    await session.flush()
    return _to_dto(job)


async def _get_or_404(session: AsyncSession, job_id: int) -> JobApplication:
    job = await session.get(JobApplication, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="求职记录不存在")
    return job


@router.patch("/{job_id}/status", response_model=JobApplicationOut)
async def update_status(
    job_id: int, payload: JobStatusUpdate, session: AsyncSession = Depends(get_session)
) -> JobApplicationOut:
    job = await _get_or_404(session, job_id)
    job.status_code = payload.status_code
    job.manually_edited = True
    _append_timeline(job, payload.status_code)
    await session.flush()
    subjects = await _subjects_for(session, [job])
    return _to_dto(job, subjects.get(job.email_id))


@router.patch("/{job_id}", response_model=JobApplicationOut)
async def edit_job(
    job_id: int, payload: JobEdit, session: AsyncSession = Depends(get_session)
) -> JobApplicationOut:
    job = await _get_or_404(session, job_id)
    if payload.company is not None:
        job.company = payload.company
    if payload.position is not None:
        job.position = payload.position
    if payload.applied_at is not None:
        job.applied_at = payload.applied_at
    if payload.status_code is not None and payload.status_code != job.status_code:
        job.status_code = payload.status_code
        _append_timeline(job, payload.status_code)
    job.manually_edited = True
    await session.flush()
    subjects = await _subjects_for(session, [job])
    return _to_dto(job, subjects.get(job.email_id))


@router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: int, session: AsyncSession = Depends(get_session)) -> None:
    job = await _get_or_404(session, job_id)
    await session.delete(job)
