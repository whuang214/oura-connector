from pathlib import Path

import pytest
from pydantic import ValidationError

from oura_connector.auth import write_protected_json
from oura_connector.config import Settings, load_settings
from oura_connector.errors import ConfigurationError


def test_toml_and_protected_credentials_are_separate(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text('timezone = "America/New_York"\nclient_id = "example"\n')
    write_protected_json(tmp_path / "credentials.json", {"client_secret": "synthetic-secret"})
    settings = load_settings(config)
    assert settings.oauth_client_configured
    assert settings.timezone == "America/New_York"
    assert "synthetic-secret" not in repr(settings)
    assert settings.token_file == tmp_path / "tokens.json"


def test_no_config_is_a_safe_disconnected_state(tmp_path: Path) -> None:
    settings = load_settings(tmp_path / "config.toml")
    assert not settings.oauth_client_configured


@pytest.mark.parametrize("content", ['client_secret = "bad"', "max_pages = 0", "typo = true"])
def test_invalid_settings_fail_closed(tmp_path: Path, content: str) -> None:
    config = tmp_path / "config.toml"
    config.write_text(content)
    with pytest.raises(ConfigurationError):
        load_settings(config)


def test_config_extension_is_checked_before_read(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="TOML"):
        load_settings(tmp_path / "wrong.txt")


@pytest.mark.parametrize("values", [{"http_host": "0.0.0.0"}, {"timezone": "bad"}, {"concurrency": 0}])
def test_invalid_runtime_limits(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Settings(**values)
