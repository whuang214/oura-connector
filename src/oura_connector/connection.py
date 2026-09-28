"""Local desktop connection operations. Never return secrets to the view."""

from __future__ import annotations

import asyncio
import os
import secrets
import tempfile
import tomllib
from collections.abc import Callable
from pathlib import Path
from threading import Event

import tomli_w

from .auth import InterProcessFileLock, TokenStore, read_protected_json, write_protected_json
from .config import Settings, load_settings
from .errors import AuthenticationError, ConfigurationError
from .interfaces.cli import browser_callback, diagnostic, exchange
from .models import JsonObject


class Connection:
    def __init__(self, path: Path) -> None:
        if path.suffix.lower() != ".toml" or path.name.startswith(".env"):
            raise ConfigurationError("Choose a non-secret config.toml file")
        self.path = path

    def snapshot(self) -> JsonObject:
        settings = load_settings(self.path)
        result = asyncio.run(diagnostic(settings, False))
        result.update(
            client_id=settings.client_id or "",
            redirect_uri=settings.redirect_uri,
            directory=str(self.path.parent),
            encrypted=os.name == "nt",
        )
        return result

    def prepare(self) -> JsonObject:
        """Upgrade protected plaintext saves from the earlier CLI, under locks."""

        async def upgrade() -> None:
            if os.name != "nt" or not self.path.parent.exists():
                return
            async with InterProcessFileLock(self.path.parent / "settings.lock"):
                settings = load_settings(self.path)
                credentials = self.path.parent / "credentials.json"
                if credentials.exists():
                    write_protected_json(credentials, read_protected_json(credentials))
                store = TokenStore.from_settings(settings)
                async with store.exclusive_lock():
                    if store.path.exists():
                        store.save(store.load())

        asyncio.run(upgrade())
        return self.snapshot()

    def save_app(self, client_id: str, secret: str, timezone: str) -> None:
        """Preserve advanced settings while changing only the setup form fields."""

        async def save() -> None:
            async with InterProcessFileLock(self.path.parent / "settings.lock"):
                existing = load_settings(self.path)
                if existing.token_file.exists() and existing.client_id != client_id.strip():
                    raise ConfigurationError("Disconnect locally before changing the Oura application")
                if existing.client_id != client_id.strip() and not secret.strip():
                    raise ConfigurationError("Enter the client secret for the new Oura application")
                selected_secret = secret.strip() or existing.client_secret
                if not client_id.strip() or not selected_secret:
                    raise ConfigurationError("Enter an Oura application client ID and client secret")
                values = tomllib.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
                values.update(client_id=client_id.strip(), timezone=timezone.strip())
                Settings(**values, client_secret=selected_secret)
                text = tomli_w.dumps(values)
                descriptor, temporary_name = tempfile.mkstemp(prefix=".oura-settings-", dir=self.path.parent)
                temporary = Path(temporary_name)
                try:
                    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                        stream.write(text)
                        stream.flush()
                        os.fsync(stream.fileno())
                    write_protected_json(
                        self.path.parent / "credentials.json",
                        {
                            "client_secret": selected_secret,
                            "http_token": existing.http_token or secrets.token_urlsafe(32),
                        },
                    )
                    os.replace(temporary, self.path)
                finally:
                    temporary.unlink(missing_ok=True)

        asyncio.run(save())

    def connect(self, cancel: Event, on_url: Callable[[str], None]) -> JsonObject:
        if cancel.is_set():
            raise AuthenticationError("Sign-in was cancelled")
        settings = load_settings(self.path)
        if not settings.oauth_client_configured:
            raise ConfigurationError("Complete the app setup first")
        callback = browser_callback(settings, cancel=cancel, on_url=on_url)
        if cancel.is_set():
            raise AuthenticationError("Sign-in was cancelled")
        asyncio.run(exchange(settings, callback))
        return self.snapshot()

    def check(self) -> JsonObject:
        return asyncio.run(diagnostic(load_settings(self.path), True))

    def disconnect(self) -> JsonObject:
        """Remove only this connector's saved OAuth grant; keep app setup."""
        settings = load_settings(self.path)

        async def forget() -> None:
            store = TokenStore.from_settings(settings)
            async with store.exclusive_lock():
                store.delete()

        asyncio.run(forget())
        return self.snapshot()
