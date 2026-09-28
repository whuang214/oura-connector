"""Shared retrieval contracts and bounded continuation state."""

from __future__ import annotations

import base64
import json
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .resources import get_resource

JsonObject = dict[str, Any]
Format = Literal["compact", "source"]


def iso_date(value: str) -> date:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Dates must use YYYY-MM-DD")
    return date.fromisoformat(value)


def aware_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Timestamps must include a UTC offset")
    return parsed.astimezone(timezone.utc)


class Query(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    resource: str
    start_date: str | None = None
    end_date: str | None = None
    start_datetime: str | None = None
    end_datetime: str | None = None

    def parameters(self) -> dict[str, str]:
        spec = get_resource(self.resource)
        dates = (self.start_date, self.end_date)
        times = (self.start_datetime, self.end_datetime)
        if spec.filters == "date":
            if any(v is not None for v in times) or any(v is None for v in dates):
                raise ValueError("This resource requires only start_date and end_date")
            assert self.start_date is not None and self.end_date is not None
            start, end = iso_date(self.start_date), iso_date(self.end_date)
            if not 0 <= (end - start).days < 90:
                raise ValueError("Date ranges must cover 1–90 inclusive days")
            # These four timestamp-backed collections use an exclusive upper
            # date. Keep the public range inclusive and filter by source day.
            # See docs/reference/data.md for evidence and the outstanding live check.
            if spec.exclusive_end:
                if end == date.max:
                    raise ValueError("end_date is too large for the upstream interval")
                end += timedelta(days=1)
            return {"start_date": self.start_date, "end_date": end.isoformat()}
        if spec.filters == "datetime":
            if any(v is not None for v in dates) or any(v is None for v in times):
                raise ValueError("This resource requires only start_datetime and end_datetime")
            assert self.start_datetime is not None and self.end_datetime is not None
            elapsed = (aware_datetime(self.end_datetime) - aware_datetime(self.start_datetime)).total_seconds()
            if not 0 < elapsed <= 7 * 86400:
                raise ValueError("Timestamp ranges must be positive and at most seven elapsed days")
            return {"start_datetime": self.start_datetime, "end_datetime": self.end_datetime}
        if any(v is not None for v in (*dates, *times)):
            raise ValueError("This resource does not accept date or timestamp filters")
        return {}


class Cursor(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    version: Literal[1] = 1
    query: Query
    next_token: str | None = Field(default=None, max_length=8192)
    offset: int = Field(default=0, ge=0, le=100000)
    page_hash: str | None = Field(default=None, max_length=64)
    seen: list[str] = Field(default_factory=list, max_length=1000)

    def encode(self) -> str:
        return base64.urlsafe_b64encode(self.model_dump_json().encode()).decode()

    @classmethod
    def decode(cls, value: str) -> Cursor:
        try:
            if not value or len(value) > 150000:
                raise ValueError()
            state = cls.model_validate_json(base64.b64decode(value, altchars=b"-_", validate=True))
            state.query.parameters()
            if state.offset and not state.page_hash:
                raise ValueError()
            return state
        except (ValueError, ValidationError):
            raise ValueError("Invalid continuation cursor; restart the query") from None


class Collection(BaseModel):
    resource: str
    status: Literal["ok", "empty", "partial", "unavailable", "error"] = "empty"
    records: list[JsonObject] = Field(default_factory=list)
    complete: bool = True
    continuation: str | None = None
    error: JsonObject | None = None
    pages_fetched: int = 0
    omitted_records: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


def json_size(value: object) -> int:
    return len(json.dumps(value, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode())
