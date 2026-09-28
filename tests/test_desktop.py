import gc
import time
import tkinter as tk
from pathlib import Path
from threading import Event

import pytest

from oura_connector.connection import Connection
from oura_connector.errors import AuthenticationError
from oura_connector.interfaces.desktop import ConnectWindow


class FakeConnection(Connection):
    saved = False
    secret_seen = ""

    def snapshot(self):
        return {
            "oauth_client_configured": self.saved,
            "credential_present": self.saved,
            "state": "credentials_present" if self.saved else "not_authorized",
            "timezone": "UTC",
        }

    def prepare(self):
        return self.snapshot()

    def save_app(self, client_id, secret, timezone):
        self.secret_seen = secret

    def connect(self, cancel, on_url):
        on_url("https://cloud.ouraring.com/oauth/authorize?state=synthetic")
        self.saved = True
        return self.snapshot()

    def check(self):
        return {**self.snapshot(), "live_connection_verified": True}

    def disconnect(self):
        self.saved = False
        return self.snapshot()


def settle(root, window):
    deadline = time.monotonic() + 5
    while window.busy and time.monotonic() < deadline:
        root.update()
        time.sleep(0.01)
    assert not window.busy
    root.update()


@pytest.fixture(scope="module")
def interpreter():
    # One Tk interpreter per process; use Toplevels for independent windows.
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("No desktop display")
    root.withdraw()
    yield root
    root.destroy()


def test_native_ui_setup_save_check_and_disconnect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, interpreter
) -> None:
    root = tk.Toplevel(interpreter)
    root.withdraw()
    try:
        connection = FakeConnection(tmp_path / "config.toml")
        window = ConnectWindow(root, connection)
        settle(root, window)
        assert window.mode == "setup"
        window.client_id.set("synthetic-client")
        window.secret.set("synthetic-secret")
        assert window.secret_entry.cget("show")
        window.activate()
        settle(root, window)
        assert connection.secret_seen == "synthetic-secret"
        assert window.secret.get() == ""
        assert window.mode == "saved"
        assert window.connection_label.cget("text") == "Sign-in saved"
        window.activate()
        settle(root, window)
        assert window.connection_label.cget("text") == "Connected to Oura"
        monkeypatch.setattr("oura_connector.interfaces.desktop.messagebox.askyesno", lambda *a, **k: True)
        window.secondary_action()
        settle(root, window)
        assert not connection.saved
    finally:
        root.destroy()
        gc.collect()


def test_close_waits_for_pending_work(tmp_path: Path, interpreter) -> None:
    root = tk.Toplevel(interpreter)
    root.withdraw()
    try:
        window = ConnectWindow(root, FakeConnection(tmp_path / "config.toml"))
        settle(root, window)
        release = Event()

        def work():
            release.wait(2)
            return {}

        window.run_work(work, "Synthetic pending operation")
        window.close()
        assert window.closing and window.cancel.is_set()
        assert root.winfo_exists()
        release.set()
        assert window.worker
        window.worker.join(3)
        assert not window.worker.is_alive()
    finally:
        root.destroy()
        gc.collect()


def test_declined_browser_login_keeps_app_setup_and_hides_raw_errors(tmp_path, interpreter, monkeypatch):
    root = tk.Toplevel(interpreter)
    root.withdraw()

    def decline(*args, **kwargs):
        raise AuthenticationError("synthetic-sensitive-error-marker")

    monkeypatch.setattr(Connection, "connect", decline)
    try:
        window = ConnectWindow(root, Connection(tmp_path / "config.toml"))
        settle(root, window)
        window.client_id.set("synthetic-client")
        window.secret.set("synthetic-secret")
        window.activate()
        settle(root, window)
        assert window.mode == "ready"
        assert window.primary.cget("text") == "Connect with Oura"
        assert "synthetic-sensitive" not in window.status.cget("text")
        assert not window.secret.get()
    finally:
        root.destroy()
        gc.collect()
