"""Optional loopback HTTP transport, sharing the MCP service contract."""

import secrets
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import Response

from ..errors import ApiError, AuthenticationError, ConfigurationError, ConnectorError, LimitError
from ..models import Format, JsonObject
from ..service import Service


def create_app(service: Service) -> FastAPI:
    bearer = service.settings.http_token
    if not bearer or len(bearer) < 32:
        raise ConfigurationError("HTTP requires a protected bearer token of at least 32 characters; run setup")

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await service.close()

    app = FastAPI(title="Oura Connector", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def authorize(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if request.headers.get("origin"):
            return JSONResponse({"error": "Browser-origin requests are not supported"}, status_code=403)
        if request.url.path != "/health":
            supplied = request.headers.get("authorization", "")
            if not secrets.compare_digest(supplied.encode(), f"Bearer {bearer}".encode()):
                return JSONResponse(
                    {"error": "Bearer authentication required"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer", "Cache-Control": "no-store"},
                )
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]"])

    @app.exception_handler(ConnectorError)
    async def connector_error(_: Request, exc: ConnectorError) -> JSONResponse:
        code = 413 if isinstance(exc, LimitError) else 502 if isinstance(exc, ApiError) else 503
        if isinstance(exc, AuthenticationError):
            code = 503
        return JSONResponse({"error": {"code": type(exc).__name__, "message": str(exc)}}, status_code=code)

    @app.exception_handler(ValueError)
    async def invalid_query(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse({"error": {"code": "invalid_request", "message": str(exc)}}, status_code=422)

    @app.exception_handler(RequestValidationError)
    async def invalid_shape(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            {"error": {"code": "invalid_request", "message": "Invalid query parameters"}}, status_code=422
        )

    @app.exception_handler(TimeoutError)
    async def timeout(_: Request, exc: TimeoutError) -> JSONResponse:
        return JSONResponse({"error": {"code": "timeout", "message": "Operation timed out"}}, status_code=504)

    @app.get("/health")
    async def health() -> JsonObject:
        return {"status": "ok"}

    @app.get("/status")
    async def status() -> JsonObject:
        return service.status()

    @app.get("/resources")
    async def resources(resource: str | None = None) -> JsonObject:
        return service.resources(resource)

    @app.get("/days/{date}")
    async def day(
        date: str, include: Annotated[list[str] | None, Query()] = None, format: Format = "compact"
    ) -> JsonObject:
        return await service.get_day(date, include, format)

    @app.get("/days")
    async def days(
        start_date: str, end_date: str, include: Annotated[list[str] | None, Query()] = None, format: Format = "compact"
    ) -> JsonObject:
        return await service.get_days(start_date, end_date, include, format)

    @app.get("/records/{resource}/{record_id}")
    async def record(resource: str, record_id: str, format: Format = "compact") -> JsonObject:
        return await service.get_record(resource, record_id, format)

    @app.get("/records/{resource}")
    async def records(
        resource: str,
        start_date: str | None = None,
        end_date: str | None = None,
        start_datetime: str | None = None,
        end_datetime: str | None = None,
        cursor: str | None = None,
        page_budget: int | None = None,
        format: Format = "compact",
    ) -> JsonObject:
        return await service.get_records(
            resource, start_date, end_date, start_datetime, end_datetime, cursor, page_budget, format
        )

    return app
