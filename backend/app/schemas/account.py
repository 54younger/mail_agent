from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AccountIn(BaseModel):
    host: str = Field(min_length=1)
    port: int = Field(default=993, ge=1, le=65535)
    use_ssl: bool = True
    username: str = Field(min_length=1)
    # Auth code / password — used to test + stored in the secrets store, never persisted
    # to the DB nor returned by the API.
    password: str = Field(min_length=1)
    display_name: str = ""


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    host: str
    port: int
    use_ssl: bool
    username: str
    display_name: str
    last_sync_at: datetime | None = None
