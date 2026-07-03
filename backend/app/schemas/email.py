from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EmailListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uid: str
    folder: str
    from_address: str
    subject: str
    date: datetime


class EmailPage(BaseModel):
    items: list[EmailListItem]
    total: int
    page: int
    size: int
    page_count: int


class EmailDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uid: str
    folder: str
    from_address: str
    to_addresses: str
    subject: str
    date: datetime
    body_text: str
    translated_text: str | None = None
    detected_lang: str | None = None
