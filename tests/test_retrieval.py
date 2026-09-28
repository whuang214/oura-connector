from dataclasses import replace

import httpx
import pytest

from oura_connector.client import OuraClient
from oura_connector.config import Settings
from oura_connector.models import Cursor, Query

DAY = "2026-09-27"
QUERY = Query(resource="sleep", start_date=DAY, end_date=DAY)


def settings(**kwargs: object) -> Settings:
    return replace(Settings(access_token="synthetic", max_retries=0), **kwargs)


@pytest.mark.anyio
async def test_mid_page_record_limit_resumes_without_skips_or_duplicates() -> None:
    rows = [{"id": str(i), "day": DAY} for i in range(5)]
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"data": rows, "next_token": None}))
    ) as http:
        client = OuraClient(settings(max_records=2), http=http)
        result = await client.collect(QUERY)
        collected = list(result.records)
        assert result.status == "partial"
        while result.continuation:
            result = await client.collect(QUERY, cursor=result.continuation)
            collected.extend(result.records)
        assert [r["id"] for r in collected] == ["0", "1", "2", "3", "4"]
        assert result.complete


@pytest.mark.anyio
async def test_page_budget_and_empty_intermediate_page() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(dict(request.url.params))
        token = request.url.params.get("next_token")
        return httpx.Response(
            200,
            json={
                "data": [] if token is None else [{"id": "x", "day": DAY}],
                "next_token": "next" if token is None else None,
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = OuraClient(settings(), http=http)
        first = await client.collect(QUERY, page_budget=1)
        assert first.status == "partial" and not first.complete
        assert first.continuation
        last = await client.collect(QUERY, cursor=first.continuation)
        assert last.complete and last.records[0]["id"] == "x"
        assert calls[0] == {"start_date": DAY, "end_date": "2026-09-28"}
        assert calls[1]["next_token"] == "next"


@pytest.mark.anyio
async def test_changed_page_is_reported_instead_of_skipping_records() -> None:
    rows = [{"id": str(i), "day": DAY} for i in range(3)]
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"data": rows}))
    ) as http:
        client = OuraClient(settings(max_records=1), http=http)
        first = await client.collect(QUERY)
        rows.reverse()
        result = await client.collect(QUERY, cursor=first.continuation)
        assert result.status == "error"
        assert result.error and "changed" in result.error["message"]
        assert not result.records


@pytest.mark.anyio
async def test_denied_and_empty_are_different() -> None:
    for code in (200, 403):
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(code, json={"data": []}))
        ) as http:
            result = await OuraClient(settings(), http=http).collect(QUERY)
            assert result.status == ("empty" if code == 200 else "unavailable")
            assert result.complete == (code == 200)


@pytest.mark.anyio
async def test_next_page_failure_keeps_earlier_records_and_retry_position() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "next_token" in request.url.params:
            return httpx.Response(503, text="secret must not leak")
        return httpx.Response(200, json={"data": [{"day": DAY}], "next_token": "page-two"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await OuraClient(settings(), http=http).collect(QUERY)
        assert result.status == "partial" and len(result.records) == 1
        assert result.continuation and Cursor.decode(result.continuation).next_token == "page-two"
        assert "secret" not in result.model_dump_json()


@pytest.mark.anyio
async def test_repeated_cursor_is_bounded() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"data": [{"day": DAY}], "next_token": "again"})
        )
    ) as http:
        result = await OuraClient(settings(), http=http).collect(QUERY)
        assert not result.complete and result.error
        assert result.pages_fetched == 2


@pytest.mark.anyio
async def test_page_size_and_record_size_limits() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"data": [{"day": DAY, "large": "x" * 2000}]}))
    ) as http:
        for limits in ({"max_page_bytes": 1024}, {"max_response_bytes": 1024}):
            result = await OuraClient(settings(**limits), http=http).collect(QUERY)
            assert result.status == "error" and result.error
            assert result.error["code"] == "LimitError"


@pytest.mark.anyio
async def test_source_assigned_day_is_authoritative() -> None:
    rows = [{"day": DAY, "bedtime_start": "2026-09-26T21:00:00-04:00"}, {"day": "2026-09-28"}]
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"data": rows}))
    ) as http:
        result = await OuraClient(settings(), http=http).collect(QUERY)
        assert result.records == rows[:1]


def test_date_limits_and_dst_elapsed_time() -> None:
    with pytest.raises(ValueError):
        Query(resource="sleep", start_date=DAY, end_date="2027-01-01").parameters()
    with pytest.raises(ValueError):
        Query(resource="heartrate", start_datetime="2026-09-01T00:00", end_datetime="2026-09-02T00:00").parameters()
    # Seven local dates spanning fall-back exceed seven elapsed days.
    with pytest.raises(ValueError):
        Query(
            resource="heartrate", start_datetime="2026-10-29T00:00:00-04:00", end_datetime="2026-11-05T00:00:00-05:00"
        ).parameters()
    assert Query(
        resource="heartrate", start_datetime="2026-11-01T01:00:00-04:00", end_datetime="2026-11-01T01:00:00-05:00"
    ).parameters()


@pytest.mark.anyio
async def test_invalid_query_never_reaches_network() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        pytest.fail("Invalid queries must fail before network access")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = OuraClient(settings(), http=http)
        with pytest.raises(ValueError):
            await client.collect(Query(resource="unknown"))
        with pytest.raises(ValueError):
            await client.collect(QUERY, cursor="bad")
        with pytest.raises(ValueError):
            await client.record("sleep", "../personal_info")
        with pytest.raises(ValueError):
            await client.record("heartrate", "abc")


@pytest.mark.anyio
async def test_rate_limit_retry_and_transport_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    waits = []
    calls = 0

    async def sleep(delay: float) -> None:
        waits.append(delay)

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "3"})
        if calls == 2:
            raise httpx.ConnectError("secret upstream diagnostics")
        return httpx.Response(200, json={"data": []})

    monkeypatch.setattr("oura_connector.client.asyncio.sleep", sleep)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await OuraClient(settings(max_retries=2), http=http).collect(QUERY)
        assert result.status == "empty"
        assert calls == 3 and waits == [3, 2]


@pytest.mark.anyio
async def test_401_refresh_once_and_never_follow_redirects() -> None:
    class Auth:
        calls = 0

        async def access_token(self, **kwargs: object) -> str:
            self.calls += 1
            return "replacement" if kwargs.get("force_refresh") else "first"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers["authorization"] == "Bearer first":
            return httpx.Response(401)
        return httpx.Response(302, headers={"Location": "https://attacker.example"})

    auth = Auth()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True) as http:
        result = await OuraClient(settings(), http=http, auth=auth).collect(QUERY)
        assert auth.calls == 2
        assert result.status == "error" and result.error
        assert "302" in result.error["message"]


@pytest.mark.anyio
async def test_singleton_and_record_lookup_preserve_source() -> None:
    expected = {"id": "abc", "unknown_future_field": {"value": 1}}
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=expected))) as http:
        client = OuraClient(settings(), http=http)
        singleton = await client.collect(Query(resource="personal_info"))
        record = await client.record("sleep", "abc")
        assert singleton.records == [expected] and singleton.complete
        assert record == expected


@pytest.mark.anyio
async def test_timestamp_filter_preserves_offsets_and_rejects_invalid_source() -> None:
    rows = [
        {"timestamp": "2026-11-01T01:30:00-04:00", "bpm": 50},
        {"timestamp": "2026-11-01T01:30:00-05:00", "bpm": 55},
    ]
    query = Query(
        resource="heartrate", start_datetime="2026-11-01T01:00:00-04:00", end_datetime="2026-11-01T01:00:00-05:00"
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"data": rows}))
    ) as http:
        client = OuraClient(settings(), http=http)
        result = await client.collect(query)
        assert result.records == rows[:1]
        rows[1] = {"timestamp": "invalid"}
        result = await client.collect(query)
        assert result.status == "partial" and len(result.records) == 1
        assert result.continuation and Cursor.decode(result.continuation).offset == 1


@pytest.mark.anyio
async def test_time_budget_returns_partial_instead_of_losing_records() -> None:
    import asyncio

    async def handler(request: httpx.Request) -> httpx.Response:
        if "next_token" in request.url.params:
            await asyncio.sleep(1)
        return httpx.Response(200, json={"data": [{"day": DAY}], "next_token": "two"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await OuraClient(settings(operation_timeout_seconds=0.05), http=http).collect(QUERY)
        assert result.status == "partial" and len(result.records) == 1
        assert result.error and result.error["code"] == "TimeoutError"
