import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event

import pytest

from oura_connector import auth
from oura_connector.auth import OAuthCallback, TokenStore, read_protected_json, write_protected_json
from oura_connector.auth_models import OAuthTokenSet
from oura_connector.config import load_settings
from oura_connector.connection import Connection
from oura_connector.errors import AuthenticationError, ConfigurationError, TokenStoreError


def token() -> OAuthTokenSet:
    return OAuthTokenSet(
        access_token="synthetic-access",
        refresh_token="synthetic-refresh",
        obtained_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )


@pytest.mark.skipif(os.name != "nt", reason="Windows encryption")
def test_dpapi_round_trip_no_plaintext_and_tamper_rejected(tmp_path: Path) -> None:
    path = tmp_path / "credentials.json"
    write_protected_json(path, {"client_secret": "synthetic-test-secret"})
    serialized = path.read_text(encoding="utf-8")
    assert "synthetic-test-secret" not in serialized
    assert json.loads(serialized)["protection"] == "windows-dpapi-current-user"
    assert read_protected_json(path) == {"client_secret": "synthetic-test-secret"}
    envelope = json.loads(serialized)
    envelope["ciphertext"] = "invalid"
    path.write_text(json.dumps(envelope), encoding="utf-8")
    with pytest.raises(TokenStoreError, match="decrypt"):
        read_protected_json(path)


def test_save_preserves_settings_and_secret_and_restores_session(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('max_pages = 4\n[compact_fields]\nsleep = ["average_hrv"]\n', encoding="utf-8")
    connection = Connection(path)
    connection.save_app("synthetic-client", "synthetic-secret", "America/New_York")
    settings = load_settings(path)
    assert settings.max_pages == 4 and settings.compact_fields["sleep"] == ("average_hrv",)
    assert "synthetic-secret" not in path.read_text(encoding="utf-8")
    TokenStore.from_settings(settings).save(token())
    connection.save_app("synthetic-client", "", "UTC")
    restored = Connection(path).prepare()
    assert restored["state"] == "credentials_present"
    assert restored["timezone"] == "UTC"
    assert "synthetic-secret" not in json.dumps(restored)
    assert "synthetic-access" not in json.dumps(restored)
    assert load_settings(path).client_secret == "synthetic-secret"


def test_disconnect_only_removes_local_oauth_token(tmp_path: Path) -> None:
    connection = Connection(tmp_path / "config.toml")
    connection.save_app("synthetic-client", "synthetic-secret", "UTC")
    settings = load_settings(connection.path)
    TokenStore.from_settings(settings).save(token())
    state = connection.disconnect()
    assert not settings.token_file.exists()
    assert state["oauth_client_configured"] and not state["credential_present"]
    with pytest.raises(ConfigurationError):
        asyncio.run(auth.AuthManager(settings).access_token())


def test_cannot_switch_apps_while_signed_in_or_reuse_another_apps_secret(tmp_path: Path) -> None:
    connection = Connection(tmp_path / "config.toml")
    connection.save_app("first", "synthetic", "UTC")
    settings = load_settings(connection.path)
    TokenStore.from_settings(settings).save(token())
    with pytest.raises(ConfigurationError, match="Disconnect"):
        connection.save_app("second", "new-secret", "UTC")
    connection.disconnect()
    with pytest.raises(ConfigurationError, match="new Oura"):
        connection.save_app("second", "", "UTC")


def test_cancelled_login_does_not_open_browser(tmp_path: Path) -> None:
    cancel = Event()
    cancel.set()
    with pytest.raises(AuthenticationError):
        Connection(tmp_path / "config.toml").connect(cancel, lambda _: pytest.fail("Browser opened"))


def test_browser_grant_is_saved_and_returned_as_sanitized_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    connection = Connection(tmp_path / "config.toml")
    connection.save_app("synthetic-client", "synthetic-secret", "UTC")
    monkeypatch.setattr(
        "oura_connector.connection.browser_callback",
        lambda *a, **k: OAuthCallback(code="synthetic-code", granted_scope="daily", code_verifier="test"),
    )

    async def exchange(settings, callback):
        assert callback.code == "synthetic-code"
        TokenStore.from_settings(settings).save(token())

    monkeypatch.setattr("oura_connector.connection.exchange", exchange)
    state = connection.connect(Event(), lambda _: None)
    assert state["state"] == "credentials_present"
    assert "synthetic-access" not in json.dumps(state)


@pytest.mark.skipif(os.name != "nt", reason="Windows encryption upgrade")
def test_existing_protected_plaintext_is_upgraded_without_losing_session(tmp_path: Path) -> None:
    connection = Connection(tmp_path / "config.toml")
    connection.save_app("synthetic-client", "synthetic-secret", "UTC")
    settings = load_settings(connection.path)
    store = TokenStore.from_settings(settings)
    store.save(token())
    for path in (tmp_path / "credentials.json", settings.token_file):
        plaintext = read_protected_json(path)
        # Synthetic earlier-format file; keep the private ACL.
        path.write_text(json.dumps(plaintext), encoding="utf-8")
    assert connection.prepare()["credential_present"]
    assert store.load().access_token == "synthetic-access"
    for path in (tmp_path / "credentials.json", settings.token_file):
        envelope = json.loads(path.read_text(encoding="utf-8"))
        assert envelope["protection"] == "windows-dpapi-current-user"
