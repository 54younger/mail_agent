"""Email listing (paginated, newest first) + lazy body fetch on open."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import secrets_store
from ..db import get_session
from ..models import Account, EmailMessage
from ..schemas.email import EmailDetail, EmailListItem, EmailPage
from ..services import imap_sync

router = APIRouter(prefix="/api/emails", tags=["emails"])

_MAX_SIZE = 200


@router.get("", response_model=EmailPage)
async def list_emails(
    page: int = Query(0, ge=0),
    size: int = Query(100, ge=1),
    session: AsyncSession = Depends(get_session),
) -> EmailPage:
    size = min(size, _MAX_SIZE)
    total = (await session.execute(select(func.count()).select_from(EmailMessage))).scalar_one()
    page_count = max(1, (total + size - 1) // size) if total else 1
    page = min(page, page_count - 1)

    rows = (
        await session.execute(
            select(EmailMessage)
            .order_by(EmailMessage.date.desc())
            .offset(page * size)
            .limit(size)
        )
    ).scalars().all()

    return EmailPage(
        items=[EmailListItem.model_validate(r) for r in rows],
        total=total,
        page=page,
        size=size,
        page_count=page_count,
    )


@router.get("/{email_id}", response_model=EmailDetail)
async def get_email(
    email_id: int, session: AsyncSession = Depends(get_session)
) -> EmailDetail:
    email = await session.get(EmailMessage, email_id)
    if email is None:
        raise HTTPException(status_code=404, detail="邮件不存在")

    # Lazy body fetch on first open; cache into the row.
    if not email.body_text:
        acc = (await session.execute(select(Account).limit(1))).scalar_one_or_none()
        if acc is not None:
            password = await run_in_threadpool(
                secrets_store.get_imap_password, acc.credential_key
            )
            if password:
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
                    await session.flush()

    return EmailDetail.model_validate(email)
