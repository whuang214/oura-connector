"""Non-secret TOML settings; credentials live in a separate protected file."""

from __future__ import annotations

import os
import tomllib
from dataclasses import field
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import ConfigDict, Field, ValidationError
from pydantic.dataclasses import dataclass

from .errors import ConfigurationError


def config_directory() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "oura-connector"
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "oura-connector"


@dataclass(frozen=True, config=ConfigDict(extra="forbid"))
class Settings:
    timezone: str = "UTC"
    default_sections: tuple[str, ...] = ("sleep", "readiness", "activity", "stress", "spo2")
    compact_fields: dict[str, tuple[str, ...]] = field(default_factory=dict)
    client_id: str | None = None
    redirect_uri: str = "http://localhost:8765/callback"
    scopes: tuple[str, ...] = ("daily", "heartrate", "workout", "tag", "session", "spo2", "personal", "email")
    token_file: Path = field(default_factory=lambda: config_directory() / "tokens.json")
    client_secret: str | None = field(default=None, repr=False)
    access_token: str | None = field(default=None, repr=False)
    http_token: str | None = field(default=None, repr=False)
    authorize_url: str = "https://cloud.ouraring.com/oauth/authorize"
    token_url: str = "https://api.ouraring.com/oauth/token"
    timeout_seconds: float = Field(default=20, gt=0, le=120)
    operation_timeout_seconds: float = Field(default=90, gt=0, le=600)
    token_refresh_skew_seconds: int = Field(default=60, ge=0, le=600)
    max_retries: int = Field(default=2, ge=0, le=5)
    max_pages: int = Field(default=10, ge=1, le=100)
    max_records: int = Field(default=2000, ge=1, le=100000)
    max_page_bytes: int = Field(default=4_000_000, ge=1024, le=50_000_000)
    max_response_bytes: int = Field(default=8_000_000, ge=1024, le=100_000_000)
    concurrency: int = Field(default=3, ge=1, le=10)
    http_host: str = "127.0.0.1"
    http_port: int = Field(default=8766, ge=1024, le=65535)

    def __post_init__(self) -> None:
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("timezone must be an IANA timezone") from exc
        if self.http_host not in {"127.0.0.1", "::1", "localhost"}:
            raise ValueError("HTTP must bind to loopback")
        if not self.default_sections or len(set(self.default_sections)) != len(self.default_sections):
            raise ValueError("default_sections must be nonempty and unique")

    @property
    def oauth_client_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)


def load_settings(path: Path | None = None) -> Settings:
    """Read only config.toml and credentials.json, never environment files."""
    from .auth import read_protected_json

    path = path or config_directory() / "config.toml"
    # Avoid a user accidentally pointing --config at a secret environment file.
    if path.suffix.lower() != ".toml" or path.name.startswith(".env"):
        raise ConfigurationError("Configuration must be a TOML file")
    values: dict[str, Any] = {}
    try:
        if path.exists():
            with path.open("rb") as stream:
                values = tomllib.load(stream)
        forbidden = {"client_secret", "access_token", "http_token", "token_file", "authorize_url", "token_url"}
        if forbidden.intersection(values):
            raise ConfigurationError("Secrets and OAuth endpoint overrides are not allowed in config.toml")
        credentials = path.parent / "credentials.json"
        if credentials.exists():
            secrets = read_protected_json(credentials)
            if set(secrets) - {"client_secret", "http_token"}:
                raise ConfigurationError("Unknown credential fields")
            values.update(secrets)
        return Settings(**values, token_file=path.parent / "tokens.json")
    except (OSError, ValueError, TypeError, ValidationError) as exc:
        raise ConfigurationError("Invalid configuration; check config.toml and run doctor") from exc
