from dataclasses import replace

import httpx
import pytest

from oura_connector.client import OuraClient
from oura_connector.config import Settings
from oura_connector.errors import LimitError
from oura_connector.formatting import format_record
from oura_connector.service import Service


def make_service(handler: object, **changes: object) -> tuple[Service, httpx.AsyncClient]:
    settings = replace(Settings(access_token="synthetic", max_retries=0), **changes)
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return Service(settings, OuraClient(settings, http=http)), http


@pytest.mark.anyio
async def test_seven_days_fetch_each_resource_once_and_keep_score_separate() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        name = request.url.path.rsplit("/", 1)[1]
        calls.append(name)
        rows = [{"day": "2026-09-27", "score": 80}]
        if name == "sleep":
            rows = [
                {"day": "2026-09-27", "id": "night", "type": "long_sleep", "total_sleep_duration": 27000},
                {"day": "2026-09-27", "id": "nap", "type": "late_nap", "total_sleep_duration": 1800},
            ]
        return httpx.Response(200, json={"data": rows})

    service, http = make_service(handler)
    async with http:
        result = await service.get_days("2026-09-21", "2026-09-27")
        assert len(calls) == len(set(calls)) == 6
        assert len(result["days"]) == 7
        sleep = result["days"][-1]["sections"]["sleep"]
        assert sleep["daily"]["records"][0]["score"] == 80
        assert len(sleep["periods"]["records"]) == 2
        assert "score" not in sleep["periods"]["records"][0]
        assert sleep["periods"]["records"][0]["total_sleep_display"] == "7h 30m"
        assert result["days"][0]["sections"]["sleep"]["daily"]["status"] == "empty"


@pytest.mark.anyio
async def test_sleep_filtering_nulls_unknown_types_and_source_mode() -> None:
    rows = [
        {
            "id": "a",
            "day": "2026-09-27",
            "type": "sleep",
            "total_sleep_duration": None,
            "time_in_bed": 8000,
            "average_hrv": 0,
            "heart_rate": {"items": [1, 2]},
        },
        {"id": "b", "day": "2026-09-27", "type": "rest"},
        {"id": "c", "day": "2026-09-27", "type": "deleted"},
        {"id": "d", "day": "2026-09-27", "type": "future_type"},
    ]
    service, http = make_service(lambda _: httpx.Response(200, json={"data": rows}))
    async with http:
        compact = await service.get_records("sleep", "2026-09-27", "2026-09-27")
        source = await service.get_records("sleep", "2026-09-27", "2026-09-27", format="source")
        assert source["records"] == rows
        assert compact["omitted_records"] == {"rest": 1, "deleted": 1}
        assert compact["warnings"] and len(compact["records"]) == 2
        period = compact["records"][0]
        assert period["total_sleep_seconds"] is None and period["total_sleep_display"] is None
        assert period["average_hrv_ms"] == 0
        assert period["omitted_fields"] == ["heart_rate"]


@pytest.mark.anyio
async def test_one_failed_sleep_source_does_not_erase_periods() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("daily_sleep"):
            return httpx.Response(403)
        return httpx.Response(200, json={"data": [{"day": "2026-09-27", "type": "sleep"}]})

    service, http = make_service(handler)
    async with http:
        sleep = (await service.get_day("2026-09-27", ["sleep"]))["sections"]["sleep"]
        assert sleep["daily"]["status"] == "unavailable"
        assert sleep["periods"]["status"] == "ok"


@pytest.mark.anyio
async def test_missing_day_in_partial_collection_is_not_empty_and_cursor_resumes() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        more = "next_token" not in request.url.params
        return httpx.Response(
            200,
            json={"data": [] if more else [{"day": "2026-09-27", "score": 70}], "next_token": "next" if more else None},
        )

    service, http = make_service(handler, max_pages=1)
    async with http:
        result = await service.get_day("2026-09-27", ["readiness"])
        daily = result["sections"]["readiness"]["daily"]
        assert daily["status"] == "partial" and not daily["complete"]
        resumed = await service.get_records("daily_readiness", cursor=daily["continuation"])
        assert resumed["complete"] and resumed["records"][0]["score"] == 70


def test_field_selection_preserves_identity_and_offsets() -> None:
    row = {
        "id": "x",
        "day": "2026-09-27",
        "bedtime_start": "2026-09-26T22:00:00-04:00",
        "average_hrv": None,
        "efficiency": 81,
    }
    formatted = format_record("sleep", row, "compact", ("average_hrv",))
    assert formatted["bedtime_start"] == row["bedtime_start"]
    assert formatted["average_hrv_ms"] is None
    assert "efficiency" not in formatted


@pytest.mark.anyio
async def test_bad_sections_and_oversized_response() -> None:
    service, http = make_service(lambda _: httpx.Response(200, json={"data": []}), max_response_bytes=1024)
    async with http:
        with pytest.raises(ValueError):
            await service.get_day("2026-09-27", [])
        with pytest.raises(ValueError):
            await service.get_day("2026-09-27", ["fake"])
        with pytest.raises(LimitError):
            await service.get_days("2026-09-01", "2026-09-27")
