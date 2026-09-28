import json
from pathlib import Path

import httpx
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from oura_connector.auth import read_protected_json
from oura_connector.client import OuraClient
from oura_connector.config import Settings, load_settings
from oura_connector.errors import ConfigurationError
from oura_connector.interfaces.cli import diagnostic, setup
from oura_connector.interfaces.http import create_app
from oura_connector.interfaces.mcp import create_mcp
from oura_connector.service import Service


@pytest.mark.anyio
async def test_http_and_mcp_share_data_and_errors(tmp_path: Path) -> None:
    settings = Settings(access_token="synthetic", http_token="a" * 32, token_file=tmp_path / "tokens.json")
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"data": [{"id": "one", "day": "2026-09-27", "score": 82}]})
        )
    ) as upstream:
        service = Service(settings, OuraClient(settings, http=upstream))
        app = create_app(service)
        server = create_mcp(service)
        tools = await server.list_tools()
        assert {tool.name for tool in tools} == {
            "oura_get_day",
            "oura_get_days",
            "oura_get_records",
            "oura_get_record",
            "oura_resources",
            "oura_status",
        }
        assert all(tool.annotations and tool.annotations.readOnlyHint for tool in tools)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://127.0.0.1") as api:
            assert (await api.get("/health")).json() == {"status": "ok"}
            assert (await api.get("/status")).status_code == 401
            api.headers["Authorization"] = "Bearer " + "a" * 32
            assert (await api.get("/status")).json()["live_connection_verified"] is False
            response = await api.get("/days/2026-09-27", params={"include": "readiness"})
            assert response.status_code == 200
            result = await server.call_tool("oura_get_day", {"date": "2026-09-27", "include": ["readiness"]})
            # SDK structured tools return both text and structured output.
            if isinstance(result, tuple):
                tool_data = result[1]
            elif isinstance(result, dict):
                tool_data = result
            else:
                tool_data = json.loads(result[0].text)
            assert response.json()["sections"] == tool_data["sections"]
            assert response.headers["cache-control"] == "no-store"
            assert (await api.get("/days/bad")).status_code == 422
            assert (await api.get("/records/sleep", params={"page_budget": "bad"})).status_code == 422
            assert (await api.get("/status", headers={"Origin": "https://attacker.example"})).status_code == 403
            assert (await api.get("/status", headers={"Host": "attacker.example"})).status_code == 400


@pytest.mark.anyio
async def test_stdio_starts_and_advertises_six_tools_without_http(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    params = StdioServerParameters(
        command="uv",
        args=[
            "run",
            "--no-sync",
            "--directory",
            str(root),
            "python",
            "-m",
            "oura_connector",
            "--config",
            str(tmp_path / "config.toml"),
            "mcp",
        ],
        env={"PYTHONPATH": str(root / "src")},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listing = await session.list_tools()
            assert len(listing.tools) == 6
            status = await session.call_tool("oura_status", {})
            assert not status.isError and status.structuredContent
            assert status.structuredContent["state"] == "not_authorized"
            invalid = await session.call_tool("oura_get_day", {"date": "invalid"})
            assert invalid.isError


def test_setup_and_protected_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("getpass.getpass", lambda _: "synthetic-secret")
    config = tmp_path / "settings" / "config.toml"
    setup(config, "example-client", "America/New_York")
    assert "synthetic-secret" not in config.read_text()
    credentials = read_protected_json(config.parent / "credentials.json")
    assert len(credentials["http_token"]) >= 32
    assert load_settings(config).oauth_client_configured
    with pytest.raises(ConfigurationError, match="already exist"):
        setup(config, "new", "UTC")


@pytest.mark.anyio
async def test_offline_diagnostics_and_http_requires_auth(tmp_path: Path) -> None:
    settings = Settings(token_file=tmp_path / "tokens.json")
    result = await diagnostic(settings, False)
    assert not result["live_connection_verified"] and result["configuration_valid"]
    service = Service(settings)
    try:
        with pytest.raises(ConfigurationError):
            create_app(service)
    finally:
        await service.close()
