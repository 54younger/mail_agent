"""On-demand translation for a single email, with result caching."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from .. import config
from ..db import get_session
from ..models import EmailMessage
from ..schemas.email import EmailDetail
from ..services import translation

router = APIRouter(prefix="/api/emails", tags=["translate"])


@router.post("/{email_id}/translate", response_model=EmailDetail)
async def translate_email(
    email_id: int, session: AsyncSession = Depends(get_session)
) -> EmailDetail:
    email = await session.get(EmailMessage, email_id)
    if email is None:
        raise HTTPException(status_code=404, detail="邮件不存在")

    # Serve cached translation if present.
    if email.translated_text is not None:
        return EmailDetail.model_validate(email)

    target = str(config.load_settings().get("translation_target", translation.DEFAULT_TARGET))
    service = translation.get_service()

    try:
        result = await run_in_threadpool(
            service.translate, email.body_text or "", target_lang=target
        )
    except translation.TranslationUnavailable as e:
        raise HTTPException(status_code=400, detail=e.message) from e

    email.translated_text = result.translated
    email.detected_lang = result.source_lang or None
    await session.flush()
    return EmailDetail.model_validate(email)
