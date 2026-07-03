"""求职看板 API — list, Claude extraction, manual add/edit, status moves.

Status changes and manual edits set manually_edited=True and append to the
timeline. Extraction never creates a second record for an email that already has
one, and never modifies manually-edited rows.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import secrets_store
from ..db import get_session
from ..models import Account, EmailMessage, JobApplication
from ..schemas.job import (
    ExtractResult,
    JobApplicationOut,
    JobEdit,
    JobStatusUpdate,
    ManualJobIn,
    TimelineEntry,
)
from ..services import imap_sync
from ..services.job_extractor import JobExtractionUnavailable, get_extractor

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

_EXTRACT_LIMIT = 25


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(s: str) -> datetime | None:
    if not s:
        return None
    txt = s.strip().replace("Z", "+00:00")
    for candidate in (txt, f"{txt}T00:00:00"):
        try:
            dt = datetime.fromisoformat(candidate)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


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


@router.post("/extract", response_model=ExtractResult)
async def extract_jobs(session: AsyncSession = Depends(get_session)) -> ExtractResult:
    extractor = get_extractor()
    if not extractor.is_configured:
        raise HTTPException(status_code=400, detail=JobExtractionUnavailable().message)

    # Candidate emails: newest first, not already linked to a job.
    linked = select(JobApplication.email_id).where(JobApplication.email_id != 0)
    emails = (
        await session.execute(
            select(EmailMessage)
            .where(EmailMessage.id.notin_(linked))
            .order_by(EmailMessage.date.desc())
            .limit(_EXTRACT_LIMIT)
        )
    ).scalars().all()

    acc = (await session.execute(select(Account).limit(1))).scalar_one_or_none()
    password = (
        await run_in_threadpool(secrets_store.get_imap_password, acc.credential_key)
        if acc
        else None
    )

    created = 0
    for email in emails:
        body = email.body_text
        if not body and acc and password:
            body = await run_in_threadpool(
                imap_sync.fetch_body,
                acc.host,
                acc.port,
                acc.use_ssl,
                acc.username,
                password,
                email.uid,
            )
            if body:
                email.body_text = body

        try:
            res = await run_in_threadpool(
                extractor.extract,
                subject=email.subject,
                sender=email.from_address,
                body=body or "",
            )
        except JobExtractionUnavailable as e:
            raise HTTPException(status_code=400, detail=e.message) from e

        if res.is_job and res.company:
            applied = _parse_iso(res.applied_date) or email.date
            job = JobApplication(
                company=res.company,
                applied_at=applied,
                status_code=res.status_code,
                email_id=email.id,
                manually_edited=False,
                timeline_json=json.dumps([{"status": res.status_code, "ts": applied.isoformat()}]),
            )
            session.add(job)
            created += 1

    await session.flush()
    return ExtractResult(created=created, scanned=len(emails))


@router.post("", response_model=JobApplicationOut)
async def create_job(
    payload: ManualJobIn, session: AsyncSession = Depends(get_session)
) -> JobApplicationOut:
    applied = payload.applied_at or datetime.now(timezone.utc)
    job = JobApplication(
        company=payload.company,
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
