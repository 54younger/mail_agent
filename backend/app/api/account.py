"""Account binding / rebinding. Password is tested, stored in the secrets store,
and never persisted to the DB or returned."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import secrets_store
from ..core.errors import ImapErrorInfo
from ..db import get_session
from ..models import Account
from ..schemas.account import AccountIn, AccountOut
from ..services import imap_sync

router = APIRouter(prefix="/api/account", tags=["account"])


def _imap_error_response(info: ImapErrorInfo) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"message": info.message, "hint": info.hint, "kind": info.kind.value},
    )


@router.get("", response_model=AccountOut | None)
async def get_account(session: AsyncSession = Depends(get_session)) -> AccountOut | None:
    acc = (await session.execute(select(Account).limit(1))).scalar_one_or_none()
    return AccountOut.model_validate(acc) if acc else None


@router.post("", response_model=AccountOut)
async def bind_account(payload: AccountIn, session: AsyncSession = Depends(get_session)):
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

    # 3) Single-user rebind: drop any previous account (+ its secret) first.
    for old in (await session.execute(select(Account))).scalars().all():
        if old.credential_key and old.credential_key != cred_key:
            await run_in_threadpool(secrets_store.delete_imap_password, old.credential_key)
        await session.delete(old)
    await session.flush()

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


@router.delete("", status_code=204)
async def unbind_account(session: AsyncSession = Depends(get_session)) -> None:
    for acc in (await session.execute(select(Account))).scalars().all():
        if acc.credential_key:
            await run_in_threadpool(secrets_store.delete_imap_password, acc.credential_key)
        await session.delete(acc)
