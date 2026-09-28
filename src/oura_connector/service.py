"""Shared application logic used directly by MCP, HTTP, and CLI."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .auth import TokenStore
from .client import OuraClient
from .config import Settings
from .errors import ConfigurationError, LimitError, TokenStoreError
from .formatting import IDENTITY_FIELDS, format_collection, format_record
from .models import Collection, Cursor, Format, JsonObject, Query, iso_date, json_size
from .resources import FIELD_LABELS, RESOURCES, SECTIONS, get_resource


class Service:
    def __init__(self, settings: Settings, client: OuraClient | None = None) -> None:
        self.settings = settings
        self._sections(list(settings.default_sections))
        for name, fields in settings.compact_fields.items():
            get_resource(name)
            if not fields or any(not field or len(field) > 128 for field in fields):
                raise ConfigurationError("compact_fields must contain nonempty source field names")
        self.client = client or OuraClient(settings)
        self._semaphore = asyncio.Semaphore(settings.concurrency)

    async def close(self) -> None:
        await self.client.close()

    @staticmethod
    def _format(format: str) -> Format:
        if format not in {"compact", "source"}:
            raise ValueError("format must be compact or source")
        return "compact" if format == "compact" else "source"

    def _bounded(self, value: JsonObject) -> JsonObject:
        if json_size(value) > self.settings.max_response_bytes:
            raise LimitError("Response exceeds max_response_bytes; select fewer sections, narrow the range, "
                             "lower page_budget, or raise the configured limit")
        return value

    @staticmethod
    def _sections(include: list[str]) -> list[str]:
        if not include or len(set(include)) != len(include) or any(name not in SECTIONS for name in include):
            raise ValueError("include must be a nonempty list of unique names from: " + ", ".join(SECTIONS))
        return include

    async def get_day(self, date: str, include: list[str] | None = None, format: str = "compact") -> JsonObject:
        return (await self.get_days(date, date, include, format))["days"][0]  # type: ignore[no-any-return]

    async def get_days(self, start_date: str, end_date: str, include: list[str] | None = None,
                       format: str = "compact") -> JsonObject:
        output_format = self._format(format)
        start, end = iso_date(start_date), iso_date(end_date)
        if not 0 <= (end - start).days < 31:
            raise ValueError("Day bundles must cover 1–31 inclusive days")
        sections = self._sections(list(self.settings.default_sections) if include is None else include)
        resources = list(dict.fromkeys(name for section in sections for name in SECTIONS[section].values()))
        queries = [Query(resource=name, start_date=start_date, end_date=end_date) for name in resources]
        # Validate all bounds before starting any request.
        for query in queries:
            query.parameters()

        async def fetch(query: Query) -> Collection:
            async with self._semaphore:
                return await self.client.collect(query)

        collections = dict(zip(resources, await asyncio.gather(*(fetch(query) for query in queries)), strict=True))
        retrieved_at = datetime.now(timezone.utc).isoformat()
        days: list[JsonObject] = []
        for offset in range((end - start).days + 1):
            day = (start + timedelta(days=offset)).isoformat()
            day_sections: JsonObject = {}
            for section in sections:
                parts: JsonObject = {}
                for key, name in SECTIONS[section].items():
                    collection = collections[name].model_copy(deep=True)
                    collection.records = [row for row in collection.records if row.get("day") == day]
                    # Partial collection means absence on this day is uncertain.
                    if not collection.complete and collection.status not in {"unavailable", "error"}:
                        collection.status = "partial"
                    formatted = format_collection(collection, output_format, self.settings.compact_fields.get(name))
                    parts[key] = formatted.model_dump(exclude_none=True)
                day_sections[section] = parts
            days.append({"date": day, "format": output_format, "retrieved_at": retrieved_at, "sections": day_sections})
        return self._bounded({"start_date": start_date, "end_date": end_date, "format": output_format,
                              "retrieved_at": retrieved_at, "days": days})

    async def get_records(self, resource: str, start_date: str | None = None, end_date: str | None = None,
                          start_datetime: str | None = None, end_datetime: str | None = None,
                          cursor: str | None = None, page_budget: int | None = None,
                          format: str = "compact") -> JsonObject:
        output_format = self._format(format)
        get_resource(resource)
        query = Query(resource=resource, start_date=start_date, end_date=end_date,
                      start_datetime=start_datetime, end_datetime=end_datetime)
        if cursor:
            original = Cursor.decode(cursor).query
            # A continuation carries its bounds. Supplied bounds must match.
            if original.resource != resource or any(value is not None and getattr(original, name) != value
                for name, value in query.model_dump(exclude={"resource"}).items()):
                raise ValueError("Cursor belongs to a different query")
            query = original
        async with self._semaphore:
            collection = await self.client.collect(query, cursor=cursor, page_budget=page_budget)
        output = format_collection(collection, output_format, self.settings.compact_fields.get(resource))
        return self._bounded({**output.model_dump(exclude_none=True), "format": output_format,
                              "query": query.model_dump(exclude_none=True),
                              "retrieved_at": datetime.now(timezone.utc).isoformat()})

    async def get_record(self, resource: str, record_id: str, format: str = "compact") -> JsonObject:
        output_format = self._format(format)
        async with self._semaphore:
            record = await self.client.record(resource, record_id)
        return self._bounded({"resource": resource, "format": output_format,
                              "record": format_record(resource, record, output_format,
                                                      self.settings.compact_fields.get(resource)),
                              "retrieved_at": datetime.now(timezone.utc).isoformat()})

    def resources(self, resource: str | None = None) -> JsonObject:
        specs = [get_resource(resource)] if resource is not None else list(RESOURCES.values())
        return {"sections": dict(SECTIONS), "defaults": list(self.settings.default_sections), "resources": [{
            "name": spec.name, "filters": spec.filters, "supports_id_lookup": spec.lookup,
            "known_scopes": list(spec.scopes),
            "access_note": "Availability also depends on Oura permissions, device, and data availability",
            "compact_fields": {name: {"output": FIELD_LABELS.get(name, (name, ""))[0],
                                      "unit": FIELD_LABELS.get(name, (name, None))[1]}
                               for name in dict.fromkeys((*IDENTITY_FIELDS,
                                   *self.settings.compact_fields.get(spec.name, spec.fields)))},
        } for spec in specs]}

    def status(self) -> JsonObject:
        now = datetime.now(ZoneInfo(self.settings.timezone))
        result: JsonObject = {"timezone": self.settings.timezone, "local_date": now.date().isoformat(),
                              "oauth_client_configured": self.settings.oauth_client_configured,
                              "credential_present": self.settings.token_file.exists(),
                              "live_connection_verified": False, "state": "not_authorized"}
        if result["credential_present"]:
            try:
                token = TokenStore.from_settings(self.settings).load()
                result.update(state="credentials_present", expires_at=token.expires_at.isoformat()
                              if token.expires_at else None, scopes=token.scope)
            except TokenStoreError:
                result["state"] = "credential_store_unavailable"
        return result
