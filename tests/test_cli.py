import asyncio
import json
import socket
import sys
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from oura_connector.auth import OAuthSessionStore
from oura_connector.config import Settings
from oura_connector.interfaces import cli


def test_browser_callback_rejects_forged_state_then_accepts_real_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    settings = Settings(
        client_id="synthetic-client",
        client_secret="synthetic-secret",
        redirect_uri=f"http://localhost:{port}/callback",
        token_file=tmp_path / "tokens.json",
    )
    threads = []
    statuses = []
    queries = []

    def open_browser(url: str) -> bool:
        query = parse_qs(urlsplit(url).query)
        queries.append(query)

        def send_callbacks() -> None:
            with httpx.Client(trust_env=False) as http:
                for state in ("forged-state", query["state"][0]):
                    response = http.get(
                        f"http://127.0.0.1:{port}/callback",
                        headers={"Host": f"localhost:{port}"},
                        params={"code": "synthetic-code", "state": state},
                    )
                    statuses.append(response.status_code)

        thread = Thread(target=send_callbacks)
        thread.start()
        threads.append(thread)
        return True

    monkeypatch.setattr(cli.webbrowser, "open", open_browser)
    callback = cli.browser_callback(settings)
    for thread in threads:
        thread.join(timeout=10)
        assert not thread.is_alive()
    assert callback.code == "synthetic-code" and callback.code_verifier
    assert statuses == [400, 200]
    assert queries[0]["code_challenge_method"] == ["S256"]
    assert not OAuthSessionStore.from_settings(settings).path.exists()


def test_busy_login_port_preserves_existing_session(tmp_path: Path) -> None:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        settings = Settings(
            client_id="synthetic", redirect_uri=f"http://localhost:{port}/callback", token_file=tmp_path / "tokens.json"
        )
        store = OAuthSessionStore.from_settings(settings)
        original = store.create(settings, use_pkce=True)
        with pytest.raises(OSError):
            cli.browser_callback(settings)
        assert store.load().state == original.state


@pytest.mark.parametrize("command", ["status", "doctor"])
def test_cli_local_diagnostics(
    command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["oura-connector", "--config", str(tmp_path / "config.toml"), command])
    cli.main()
    output = json.loads(capsys.readouterr().out)
    assert not output["live_connection_verified"]
    assert output["state"] == "not_authorized"


def test_cli_live_probe_reports_failed_exit_without_secrets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["oura-connector", "--config", str(tmp_path / "config.toml"), "doctor", "--live"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 1
    output = json.loads(capsys.readouterr().out)
    assert not output["live_connection_verified"]
    assert output["live_probe"]["error"]["code"] == "ConfigurationError"


def test_cli_login_without_setup_is_actionable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["oura-connector", "--config", str(tmp_path / "config.toml"), "login"])
    with pytest.raises(SystemExit):
        cli.main()
    assert "Run setup" in capsys.readouterr().err


def test_live_diagnostic_discards_health_records(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def records(*args: object, **kwargs: object) -> dict[str, object]:
        return {"complete": True, "status": "ok", "records": [{"private_health_field": 99}]}

    monkeypatch.setattr(cli.Service, "get_records", records)
    result = asyncio.run(cli.diagnostic(Settings(token_file=tmp_path / "tokens.json"), True))
    assert result["live_connection_verified"]
    assert "private_health_field" not in json.dumps(result)
