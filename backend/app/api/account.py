"""Account binding for one or more mailboxes. Passwords are tested, stored in
the secrets store, and never persisted to the DB or returned.

Multiple accounts are supported: POST adds (or updates the same username@host)
without removing the others; DELETE removes a single account together with its
credential, its emails, and any jobs extracted from those emails."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import secrets_store
from ..core.errors import ImapErrorInfo
from ..db import get_session
from ..models import Account, EmailMessage, JobApplication
from ..schemas.account import AccountIn, AccountOut
from ..services import imap_sync

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def _imap_error_response(info: ImapErrorInfo) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"message": info.message, "hint": info.hint, "kind": info.kind.value},
    )


@router.get("", response_model=list[AccountOut])
async def list_accounts(session: AsyncSession = Depends(get_session)) -> list[AccountOut]:
    rows = (await session.execute(select(Account).order_by(Account.id))).scalars().all()
    return [AccountOut.model_validate(a) for a in rows]


@router.post("", response_model=AccountOut)
async def add_account(payload: AccountIn, session: AsyncSession = Depends(get_session)):
    # 1) Probe the connection (selects INBOX → surfaces 163 "Unsafe Login" etc.).
    info = await run_in_threadpool(
        imap_sync.test_connection,
        payload.host,
        payload.port,
        payload.use_ssl,
        payload.username,
        payload.password,
    )
    if info is not None:
        return _imap_error_response(info)

    # 2) Store the password in the secrets store.
    cred_key = await run_in_threadpool(
        secrets_store.set_imap_password, payload.username, payload.host, payload.password
    )

    # 3) Add, or update the matching mailbox (same username@host) in place.
    existing = (
        await session.execute(
            select(Account).where(
                Account.username == payload.username, Account.host == payload.host
            )
        )
    ).scalar_one_or_none()

    if existing is not None:
        existing.port = payload.port
        existing.use_ssl = payload.use_ssl
        existing.credential_key = cred_key
        existing.display_name = payload.display_name or payload.username
        acc = existing
    else:
        acc = Account(
            host=payload.host,
            port=payload.port,
            use_ssl=payload.use_ssl,
            username=payload.username,
            credential_key=cred_key,
            display_name=payload.display_name or payload.username,
        )
        session.add(acc)

    await session.flush()
    await session.refresh(acc)
    return AccountOut.model_validate(acc)


@router.delete("/{account_id}", status_code=204)
async def delete_account(
    account_id: int, session: AsyncSession = Depends(get_session)
) -> None:
    acc = await session.get(Account, account_id)
    if acc is None:
        raise HTTPException(status_code=404, detail="Account not found")

    # Remove jobs extracted from this account's emails, then the emails.
    email_ids = (
        await session.execute(
            select(EmailMessage.id).where(EmailMessage.account_id == account_id)
        )
    ).scalars().all()
    if email_ids:
        await session.execute(
            delete(JobApplication).where(JobApplication.email_id.in_(email_ids))
        )
    await session.execute(
        delete(EmailMessage).where(EmailMessage.account_id == account_id)
    )

    if acc.credential_key:
        await run_in_threadpool(secrets_store.delete_imap_password, acc.credential_key)
    await session.delete(acc)
