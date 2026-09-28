"""Bounded HTTPS retrieval. No cache, analytics, or persistent health data."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from .auth import AuthManager
from .config import Settings
from .errors import ApiError, AuthenticationError, ConnectorError, LimitError
from .models import Collection, Cursor, JsonObject, Query, aware_datetime, iso_date, json_size
from .resources import get_resource

API_ROOT = "https://api.ouraring.com/v2/usercollection/"


class OuraClient:
    def __init__(self, settings: Settings, *, http: httpx.AsyncClient | None = None,
                 auth: AuthManager | None = None) -> None:
        self.settings = settings
        self.auth = auth or AuthManager(settings)
        self.http = http or httpx.AsyncClient(timeout=settings.timeout_seconds, trust_env=False, follow_redirects=False)
        self._owns_http = http is None

    async def close(self) -> None:
        if self._owns_http:
            await self.http.aclose()

    async def request(self, path: str, params: dict[str, str]) -> JsonObject:
        token = await self.auth.access_token()
        refreshed = False
        attempt = 0
        while True:
            delay = min(2 ** attempt, 8)
            try:
                async with self.http.stream("GET", API_ROOT + path, params=params,
                                            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                                            follow_redirects=False) as response:
                    status = response.status_code
                    if status == 401 and not refreshed:
                        token = await self.auth.access_token(force_refresh=True, rejected_token=token)
                        refreshed = True
                        continue
                    if status in {408, 429, 500, 502, 503, 504} and attempt < self.settings.max_retries:
                        retry = response.headers.get("retry-after", "")
                        try:
                            delay = max(0, min(float(retry), 30))
                        except ValueError:
                            try:
                                delay = max(0, min((parsedate_to_datetime(retry) -
                                                   datetime.now(timezone.utc)).total_seconds(), 30))
                            except (ValueError, TypeError, OverflowError):
                                pass
                    elif status != 200:
                        raise ApiError(f"Oura request failed with HTTP {status}", status_code=status)
                    else:
                        chunks = bytearray()
                        async for chunk in response.aiter_bytes(chunk_size=65536):
                            chunks.extend(chunk)
                            if len(chunks) > self.settings.max_page_bytes:
                                raise LimitError("Oura page exceeds max_page_bytes; narrow the interval or raise the limit")
                        try:
                            body = json.loads(chunks)
                            json_size(body)
                        except (ValueError, UnicodeError):
                            raise ApiError("Oura returned invalid JSON") from None
                        if not isinstance(body, dict):
                            raise ApiError("Oura returned an invalid object")
                        return body
            except httpx.HTTPError:
                if attempt >= self.settings.max_retries:
                    raise ApiError("Oura could not be reached within the retry limit") from None
            attempt += 1
            await asyncio.sleep(delay)

    async def record(self, resource: str, record_id: str) -> JsonObject:
        spec = get_resource(resource)
        if not spec.lookup:
            raise ValueError("This resource does not support lookup by record ID")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,512}", record_id):
            raise ValueError("Invalid record ID")
        async with asyncio.timeout(self.settings.operation_timeout_seconds):
            return await self.request(f"{resource}/{record_id}", {})

    async def collect(self, query: Query, *, cursor: str | None = None,
                      page_budget: int | None = None) -> Collection:
        params = query.parameters()
        budget = self.settings.max_pages if page_budget is None else page_budget
        if type(budget) is not int or not 1 <= budget <= self.settings.max_pages:
            raise ValueError("page_budget must be between 1 and configured max_pages")
        state = Cursor.decode(cursor) if cursor else Cursor(query=query)
        if state.query != query:
            raise ValueError("Cursor belongs to a different query")
        spec = get_resource(query.resource)
        result = Collection(resource=query.resource)
        used_bytes = 0
        try:
            async with asyncio.timeout(self.settings.operation_timeout_seconds):
                for _ in range(budget):
                    page_params = dict(params)
                    if state.next_token is not None:
                        page_params["next_token"] = state.next_token
                    body = await self.request(query.resource, page_params)
                    result.pages_fetched += 1
                    raw: Any
                    next_token: Any
                    if spec.filters == "singleton":
                        raw, next_token = [body], None
                    else:
                        raw, next_token = body.get("data"), body.get("next_token")
                    if not isinstance(raw, list) or any(not isinstance(row, dict) for row in raw):
                        raise ApiError("Oura returned invalid collection records")
                    if next_token is not None and (not isinstance(next_token, str) or len(next_token) > 8192):
                        raise ApiError("Oura returned an invalid continuation token")
                    fingerprint = hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()
                    if state.offset and (state.page_hash != fingerprint or state.offset > len(raw)):
                        raise ApiError("Oura page changed since continuation; restart this query")
                    for index in range(state.offset, len(raw)):
                        row = raw[index]
                        if not self._in_range(query, row):
                            state.offset, state.page_hash = index + 1, fingerprint
                            continue
                        size = json_size(row)
                        if size > self.settings.max_response_bytes:
                            raise LimitError("One source record exceeds max_response_bytes; raise the limit")
                        if len(result.records) >= self.settings.max_records or used_bytes + size > self.settings.max_response_bytes:
                            state.offset, state.page_hash = index, fingerprint
                            return self._partial(result, state)
                        result.records.append(row)
                        used_bytes += size
                        state.offset, state.page_hash = index + 1, fingerprint
                    if not next_token:
                        result.status = "ok" if result.records else "empty"
                        return result
                    token_hash = hashlib.sha256(next_token.encode()).hexdigest()
                    if token_hash in state.seen or next_token == state.next_token:
                        raise ApiError("Oura repeated a continuation token; restart this query")
                    if len(state.seen) >= 1000:
                        raise LimitError("Continuation chain limit reached; narrow the query")
                    state = Cursor(query=query, next_token=next_token, seen=[*state.seen, token_hash])
                return self._partial(result, state)
        except (ConnectorError, TimeoutError) as exc:
            result.complete = False
            result.continuation = state.encode()
            result.status = "partial" if result.records else "error"
            if isinstance(exc, AuthenticationError) or isinstance(exc, ApiError) and exc.status_code in {401, 403}:
                result.status = "partial" if result.records else "unavailable"
            result.error = {"code": type(exc).__name__, "message": str(exc) or "Operation timed out; retry continuation"}
            return result

    @staticmethod
    def _partial(result: Collection, state: Cursor) -> Collection:
        result.complete, result.status, result.continuation = False, "partial", state.encode()
        return result

    @staticmethod
    def _in_range(query: Query, row: dict[str, Any]) -> bool:
        spec = get_resource(query.resource)
        if spec.filters == "date" and spec.day_field:
            day = row.get(spec.day_field)
            if not isinstance(day, str):
                raise ApiError("Oura returned a record without its assigned day")
            try:
                iso_date(day)
            except ValueError:
                raise ApiError("Oura returned an invalid assigned day") from None
            assert query.start_date and query.end_date
            return query.start_date <= day <= query.end_date
        if spec.filters == "datetime":
            try:
                timestamp = aware_datetime(row["timestamp"])
                assert query.start_datetime and query.end_datetime
                return aware_datetime(query.start_datetime) <= timestamp <= aware_datetime(query.end_datetime)
            except (ValueError, KeyError, TypeError):
                raise ApiError("Oura returned an invalid timestamp") from None
        return True
