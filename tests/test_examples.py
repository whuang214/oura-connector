"""The public HTTP example must keep local credentials out of redirects and errors."""

import json
import runpy
import sys
from pathlib import Path

import httpx
import pytest

from oura_connector.config import Settings


@pytest.mark.parametrize("status", [200, 307, 401])
def test_http_example_uses_local_token_without_leaking_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], status: int
) -> None:
    example = Path(__file__).resolve().parents[1] / "examples" / "http-day.py"
    main = runpy.run_path(str(example))["main"]
    profile = tmp_path / "config.toml"
    token = "synthetic-local-token-do-not-print-123456"
    settings = Settings(http_token=token, http_port=9876, token_file=tmp_path / "tokens.json")
    requests: list[httpx.Request] = []

    def load(path: Path) -> Settings:
        assert path == profile
        return settings

    def response(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert str(request.url).startswith("http://127.0.0.1:9876/days/2026-09-27?")
        assert request.url.params.get_list("include") == ["sleep", "readiness"]
        assert request.url.params["format"] == "source"
        assert request.headers["Authorization"] == f"Bearer {token}"
        return httpx.Response(
            status,
            headers={"Location": "https://untrusted.example/"},
            json={"date": "2026-09-27"} if status == 200 else {"error": token},
        )

    original_client = httpx.Client

    def client(**kwargs: object) -> httpx.Client:
        assert kwargs["trust_env"] is False
        assert kwargs["follow_redirects"] is False
        return original_client(transport=httpx.MockTransport(response), **kwargs)

    monkeypatch.setitem(main.__globals__, "load_settings", load)
    monkeypatch.setattr(httpx, "Client", client)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(example),
            "2026-09-27",
            "--config",
            str(profile),
            "--include",
            "sleep",
            "--include",
            "readiness",
            "--format",
            "source",
        ],
    )
    assert main() == (0 if status == 200 else 1)
    captured = capsys.readouterr()
    assert token not in captured.out + captured.err
    assert len(requests) == 1
    if status == 200:
        assert json.loads(captured.out) == {"date": "2026-09-27"}
    else:
        assert captured.out == "" and f"HTTP {status}" in captured.err


def test_http_example_rejects_invalid_date_before_loading_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    main = runpy.run_path(str(Path(__file__).resolve().parents[1] / "examples" / "http-day.py"))["main"]

    def unexpected_load(_: object) -> None:
        raise AssertionError("Must validate before reading a profile")

    monkeypatch.setitem(main.__globals__, "load_settings", unexpected_load)
    monkeypatch.setattr(sys, "argv", ["http-day.py", "../not-a-date"])
    assert main() == 1
