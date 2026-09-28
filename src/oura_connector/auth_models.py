"""Private OAuth persistence models; never returned by public API routes."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OAuthTokenSet(BaseModel):
    """Validated rotating token state stored only in the protected token file."""

    model_config = ConfigDict(extra="forbid")

    access_token: str = Field(min_length=1, repr=False)
    token_type: str = "Bearer"
    expires_at: datetime | None = None
    refresh_token: str | None = Field(default=None, repr=False)
    scope: str | None = None
    obtained_at: datetime

    @field_validator("expires_at", "obtained_at")
    @classmethod
    def require_offset(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("OAuth timestamps must include a UTC offset")
        return value
