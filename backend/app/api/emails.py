"""Email listing (paginated, newest first, optional per-account filter) + lazy
body fetch on open (via the email's own account)."""

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
    account_id: int | None = Query(None, description="Filter to one account; omit for all"),
    session: AsyncSession = Depends(get_session),
) -> EmailPage:
    size = min(size, _MAX_SIZE)

    count_q = select(func.count()).select_from(EmailMessage)
    rows_q = select(EmailMessage).order_by(EmailMessage.date.desc())
    if account_id is not None:
        count_q = count_q.where(EmailMessage.account_id == account_id)
        rows_q = rows_q.where(EmailMessage.account_id == account_id)

    total = (await session.execute(count_q)).scalar_one()
    page_count = max(1, (total + size - 1) // size) if total else 1
    page = min(page, page_count - 1)

    rows = (
        await session.execute(rows_q.offset(page * size).limit(size))
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
        raise HTTPException(status_code=404, detail="Email not found")

    # Lazy body fetch on first open, via the email's own account.
    if not email.body_text:
        acc = await _account_for(session, email.account_id)
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


async def _account_for(session: AsyncSession, account_id: int) -> Account | None:
    """The email's own account, falling back to the first account for legacy
    rows written before multi-account (account_id == 0)."""
    if account_id:
        acc = await session.get(Account, account_id)
        if acc is not None:
            return acc
    return (
        await session.execute(select(Account).order_by(Account.id).limit(1))
    ).scalar_one_or_none()
