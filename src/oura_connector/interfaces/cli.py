"""Local setup, browser authorization, diagnostics, and transport launch."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import secrets
import socket
import sys
import time
import webbrowser
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Event
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..auth import (
    OAuthCallback,
    OAuthClient,
    OAuthSessionStore,
    TokenStore,
    code_challenge_for,
    validate_redirect_uri,
    write_protected_json,
)
from ..config import Settings, config_directory, load_settings
from ..errors import AuthenticationError, ConfigurationError, ConnectorError
from ..models import JsonObject
from ..service import Service


def setup(path: Path, client_id: str | None, timezone: str) -> None:
    if path.suffix.lower() != ".toml":
        raise ConfigurationError("Configuration must be a TOML file")
    if path.exists() or (path.parent / "credentials.json").exists():
        raise ConfigurationError("Setup files already exist; edit the existing config.toml instead")
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise ConfigurationError("timezone must be an IANA timezone") from None
    client_id = client_id or input("Oura OAuth client ID: ").strip()
    client_secret = getpass.getpass("Oura OAuth client secret (hidden): ").strip()
    if not client_id or not client_secret:
        raise ConfigurationError("Client ID and secret are required")
    write_protected_json(
        path.parent / "credentials.json", {"client_secret": client_secret, "http_token": secrets.token_urlsafe(32)}
    )
    # JSON string quoting is also valid for these TOML basic strings.
    with path.open("x", encoding="utf-8") as stream:
        stream.write(
            f"client_id = {json.dumps(client_id)}\ntimezone = {json.dumps(timezone)}\n"
            'redirect_uri = "http://localhost:8765/callback"\n'
            'default_sections = ["sleep", "readiness", "activity", "stress", "spo2"]\n'
        )
    print(f"Saved {path}. Credentials are protected beside it. Run login next.")


def browser_callback(
    settings: Settings, *, cancel: Event | None = None, on_url: Callable[[str], None] | None = None
) -> OAuthCallback:
    """Bind before opening the browser, reject forged callbacks, and never log URLs."""
    parsed = validate_redirect_uri(settings.redirect_uri, require_localhost=True)
    if parsed.scheme != "http":
        raise ConfigurationError("Local login requires an http://localhost redirect")
    store = OAuthSessionStore.from_settings(settings)
    callback: OAuthCallback | None = None
    denied = False
    created_session = False

    class CallbackServer(HTTPServer):
        def get_request(self) -> tuple[socket.socket, tuple[str, int]]:
            connection, address = super().get_request()
            connection.settimeout(5)
            return connection, address

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

        def do_GET(self) -> None:
            nonlocal callback, denied
            try:
                if self.headers.get("Host") != parsed.netloc or not self.path.startswith("/"):
                    raise AuthenticationError("Invalid callback origin")
                callback = store.consume_callback(f"{parsed.scheme}://{parsed.netloc}{self.path}")
                self.send_response(200)
                message = b"Authorization received. Return to your terminal."
            except ConnectorError:
                denied = not store.path.exists()
                self.send_response(400)
                message = b"Authorization rejected. Return to your terminal or finish the original login."
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(message)))
            self.end_headers()
            self.wfile.write(message)

    try:
        with CallbackServer(("127.0.0.1", parsed.port or 8765), Handler) as server:
            server.timeout = 1
            session = store.create(settings, use_pkce=True)
            created_session = True
            assert session.code_verifier is not None
            url = OAuthClient(settings).authorization_url(
                state=session.state, code_challenge=code_challenge_for(session.code_verifier)
            )
            if on_url is None:
                print("Opening Oura authorization. If the browser does not open, visit:\n" + url, file=sys.stderr)
            else:
                on_url(url)
            webbrowser.open(url)
            deadline = time.monotonic() + 180
            while callback is None and not denied and time.monotonic() < deadline and not (cancel and cancel.is_set()):
                server.handle_request()
    finally:
        if created_session:
            store.delete()
    if callback is None:
        raise AuthenticationError("Login was denied or timed out; run login again")
    return callback


async def exchange(settings: Settings, callback: OAuthCallback) -> None:
    async with TokenStore.from_settings(settings).exclusive_lock():
        await OAuthClient(settings).exchange_authorization_code(
            callback.code, code_verifier=callback.code_verifier, granted_scope=callback.granted_scope
        )


async def diagnostic(settings: Settings, live: bool) -> JsonObject:
    service = Service(settings)
    try:
        result = service.status()
        result["configuration_valid"] = True
        if live:
            date = result["local_date"]
            collection = await service.get_records("daily_sleep", date, date, page_budget=1)
            success = collection["complete"] and collection["status"] in {"ok", "empty"}
            result.update(
                live_connection_verified=success,
                live_probe={
                    "resource": "daily_sleep",
                    "status": collection["status"],
                    "error": collection.get("error"),
                },
            )
        return result
    finally:
        await service.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="oura-connector", description="Local Oura retrieval through MCP or HTTP")
    parser.add_argument("--config", type=Path, help="Non-secret TOML configuration path")
    commands = parser.add_subparsers(dest="command", required=True)
    setup_parser = commands.add_parser("setup", help="Create local settings and protected credentials")
    setup_parser.add_argument("--client-id")
    setup_parser.add_argument("--timezone", default="UTC")
    commands.add_parser("login", help="Authorize Oura in your browser")
    commands.add_parser("status", help="Show sanitized local status; no network request")
    doctor = commands.add_parser("doctor", help="Validate local configuration and optionally test Oura")
    doctor.add_argument("--live", action="store_true", help="Probe today's daily_sleep without printing health data")
    commands.add_parser("mcp", help="Run the six-tool stdio MCP server")
    commands.add_parser("serve", help="Run the authenticated loopback HTTP API")
    commands.add_parser("ui", help="Open the Oura Connect desktop login window")
    args = parser.parse_args()
    try:
        if args.command == "setup":
            setup(args.config or config_directory() / "config.toml", args.client_id, args.timezone)
            return
        if args.command == "ui":
            from .desktop import run_ui

            run_ui(args.config or config_directory() / "config.toml")
            return
        settings = load_settings(args.config)
        if args.command == "login":
            if not settings.oauth_client_configured:
                raise ConfigurationError("Run setup before login")
            asyncio.run(exchange(settings, browser_callback(settings)))
            print("Oura authorization saved. Run doctor --live to verify retrieval.")
        elif args.command in {"status", "doctor"}:
            live = args.command == "doctor" and args.live
            result = asyncio.run(diagnostic(settings, live))
            print(json.dumps(result, indent=2))
            if live and not result["live_connection_verified"]:
                raise SystemExit(1)
        elif args.command == "mcp":
            from .mcp import create_mcp

            create_mcp(Service(settings)).run(transport="stdio")
        elif args.command == "serve":
            import uvicorn

            from .http import create_app

            uvicorn.run(
                create_app(Service(settings)),
                host=settings.http_host,
                port=settings.http_port,
                access_log=False,
                log_level="warning",
            )
    except (ConnectorError, ValueError, OSError) as exc:
        # Domain errors are sanitized. OS errors may contain local paths, so keep them generic.
        message = (
            str(exc)
            if isinstance(exc, (ConnectorError, ValueError))
            else "Local operation failed; check paths and ports"
        )
        print(message, file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
