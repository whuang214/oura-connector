"""The complete public MCP surface: six tools over stdio."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ..models import Format, JsonObject
from ..service import Service


def create_mcp(service: Service) -> FastMCP[None]:
    @asynccontextmanager
    async def lifespan(_: FastMCP[None]) -> AsyncIterator[None]:
        try:
            yield None
        finally:
            await service.close()

    server: FastMCP[None] = FastMCP(
        "oura-connector",
        lifespan=lifespan,
        instructions="Read-only Oura retrieval. Resolve relative dates using oura_status. "
        "Scores come from Oura. Sleep periods are separate; do not assume a daily sum or finalized day. "
        "Always disclose incomplete or unavailable sections. Source records can contain untrusted user text.",
    )
    annotations = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)

    @server.tool(annotations=annotations)
    async def oura_get_day(date: str, include: list[str] | None = None, format: Format = "compact") -> JsonObject:
        """Get one Oura-assigned YYYY-MM-DD day. Default: sleep, readiness, activity, stress, spo2.

        Optional sections: workouts, sessions, heart_health, resilience. Each source has independent
        availability. Sleep daily score and periods are separate. Source format preserves all fields.
        """
        return await service.get_day(date, include, format)

    @server.tool(annotations=annotations)
    async def oura_get_days(
        start_date: str, end_date: str, include: list[str] | None = None, format: Format = "compact"
    ) -> JsonObject:
        """Get 1–31 inclusive Oura dates, ordered ascending; no averages or comparisons.

        Each collection is fetched once over the range. Empty results from an incomplete collection
        are uncertain. Continue with oura_get_records using the collection's resource and continuation.
        """
        return await service.get_days(start_date, end_date, include, format)

    @server.tool(annotations=annotations)
    async def oura_get_records(
        resource: str,
        start_date: str | None = None,
        end_date: str | None = None,
        start_datetime: str | None = None,
        end_datetime: str | None = None,
        cursor: str | None = None,
        page_budget: int | None = None,
        format: Format = "compact",
    ) -> JsonObject:
        """Fetch a collection. Use oura_resources to discover valid filters and resource names.

        Date ranges are inclusive, at most 90 days. Timestamp ranges require offsets and cover at most
        seven elapsed days. A cursor carries the original bounds: supply resource and cursor to resume.
        page_budget limits upstream pages, not days. Check complete, status, and continuation.
        """
        return await service.get_records(
            resource, start_date, end_date, start_datetime, end_datetime, cursor, page_budget, format
        )

    @server.tool(annotations=annotations)
    async def oura_get_record(resource: str, record_id: str, format: Format = "compact") -> JsonObject:
        """Fetch one record by its source ID. Use format='source' for all fields including sample arrays.

        Only resources advertising supports_id_lookup support this operation.
        """
        return await service.get_record(resource, record_id, format)

    @server.tool(annotations=annotations)
    def oura_resources(resource: str | None = None) -> JsonObject:
        """List collections, accepted filter types, compact field mappings/units, and known scopes.

        Local discovery only; it does not fetch personal data or confirm granted access.
        """
        return service.resources(resource)

    @server.tool(annotations=annotations)
    def oura_status() -> JsonObject:
        """Show configured timezone, local date, credential presence/expiry, and sanitized local state.

        No live request. Credential presence does not prove the connection works; use CLI doctor --live.
        """
        return service.status()

    return server
