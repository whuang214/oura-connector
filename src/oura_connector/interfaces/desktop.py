"""Native Oura Connect window. Network and disk work stay off the Tk thread."""

from __future__ import annotations

import hashlib
import os
import queue
import tkinter as tk
import webbrowser
from collections.abc import Callable
from pathlib import Path
from threading import Event, Thread
from tkinter import messagebox, ttk
from typing import Any

from ..connection import Connection
from ..errors import AuthenticationError, ConfigurationError, TokenStoreError
from ..models import JsonObject

BLUE = "#175DDC"
INK = "#17243B"
MUTED = "#54657B"
CARD = "#F2F6FC"
GREEN = "#167044"
PORTAL = "https://cloud.ouraring.com/oauth/applications"


class ConnectWindow:
    def __init__(self, root: tk.Tk, connection: Connection, *, preview: str | None = None) -> None:
        self.root, self.connection = root, connection
        self.state: JsonObject = {}
        self.busy = False
        self.closing = False
        self.cancel = Event()
        self.events: queue.Queue[tuple[str, JsonObject | str]] = queue.Queue()
        self.worker: Thread | None = None
        self.auth_url: str | None = None
        self.mode = "setup"
        self.primary: tk.Button
        self.preview = preview
        root.title("Oura Connect")
        root.configure(bg="white")
        root.geometry("600x820")
        root.minsize(600, 820)
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.bind("<Escape>", lambda _: self.close())
        root.bind("<Return>", lambda _: self.primary.invoke() if not self.busy else None)
        root.report_callback_exception = self._callback_error
        style = ttk.Style(root)
        style.configure("Oura.TEntry", padding=8, font=("Segoe UI", 11))
        style.configure("Oura.TCombobox", padding=7, font=("Segoe UI", 11))

        self.shell = tk.Frame(root, bg="white", padx=32, pady=28)
        self.shell.pack(fill="both", expand=True)
        self._label(self.shell, "LOCAL OURA CONNECTION", size=9, color=BLUE).pack(anchor="w")
        self.heading = self._label(self.shell, "Connect to Oura", size=25, bold=True)
        self.heading.pack(anchor="w", pady=(16, 6))
        self._label(self.shell, "Sign in once. Keep your tools connected.", size=11, color=MUTED).pack(anchor="w")
        self.body = tk.Frame(self.shell, bg="white")
        self.body.pack(fill="both", expand=True, pady=(26, 16))
        self.form = tk.Frame(self.body, bg="white")
        self._label(self.form, "First, add your Oura app", size=14, bold=True).pack(anchor="w")
        self._label(
            self.form, "Create a free developer app, then enter its details below.", color=MUTED, wrap=530
        ).pack(anchor="w", pady=(6, 12))
        links = tk.Frame(self.form, bg="white")
        links.pack(fill="x", pady=(0, 14))
        self._link(links, "Open Oura developer portal", lambda: webbrowser.open(PORTAL)).pack(side="left")
        self._link(links, "Copy callback URL", self.copy_callback).pack(side="right")
        self._label(self.form, "Client ID").pack(anchor="w")
        self.client_id = tk.StringVar()
        self.client_entry = ttk.Entry(self.form, textvariable=self.client_id, style="Oura.TEntry")
        self.client_entry.pack(fill="x", pady=(5, 14))
        self.secret_label = self._label(self.form, "Client secret")
        self.secret_label.pack(anchor="w")
        self.secret = tk.StringVar()
        self.secret_entry = ttk.Entry(self.form, textvariable=self.secret, show="•", style="Oura.TEntry")
        self.secret_entry.pack(fill="x", pady=(5, 6))
        self.show_secret = tk.BooleanVar(value=False)
        self.show = tk.Checkbutton(
            self.form,
            text="Show secret",
            variable=self.show_secret,
            command=lambda: self.secret_entry.configure(show="" if self.show_secret.get() else "•"),
            bg="white",
            activebackground="white",
            fg=MUTED,
            font=("Segoe UI", 9),
            highlightthickness=0,
        )
        self.show.pack(anchor="w", pady=(0, 12))
        self._label(self.form, "Your timezone").pack(anchor="w")
        self.timezone = tk.StringVar(value="America/New_York")
        self.zone_entry = ttk.Combobox(
            self.form,
            textvariable=self.timezone,
            style="Oura.TCombobox",
            values=(
                "America/New_York",
                "America/Chicago",
                "America/Denver",
                "America/Los_Angeles",
                "Europe/London",
                "UTC",
            ),
        )
        self.zone_entry.pack(fill="x", pady=(5, 0))

        self.dashboard = tk.Frame(self.body, bg=CARD, padx=22, pady=22)
        self._label(self.dashboard, "YOUR CONNECTION", size=9, color=MUTED, bg=CARD).pack(anchor="w")
        self.connection_label = self._label(self.dashboard, "Ready to connect", size=19, bold=True, bg=CARD)
        self.connection_label.pack(anchor="w", pady=(14, 14))
        self.detail = self._label(self.dashboard, "", color=MUTED, wrap=470, bg=CARD)
        self.detail.pack(anchor="w")
        self.time_label = self._label(self.dashboard, "", bg=CARD)
        self.time_label.pack(anchor="w", pady=(24, 12))
        self._label(
            self.dashboard, "Closing this window keeps your sign-in saved.", size=10, color=MUTED, wrap=470, bg=CARD
        ).pack(anchor="w", pady=(16, 0))

        actions = tk.Frame(self.shell, bg="white")
        actions.pack(fill="x")
        self.primary = tk.Button(
            actions,
            text="Save & connect with Oura",
            command=self.activate,
            bg=BLUE,
            fg="white",
            disabledforeground="white",
            activebackground="#124CB5",
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=14,
            pady=12,
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
        )
        self.primary.pack(side="left", fill="x", expand=True)
        self.secondary = tk.Button(
            actions,
            text="Close",
            command=self.secondary_action,
            bg="white",
            fg=INK,
            activebackground=CARD,
            relief="solid",
            bd=1,
            padx=16,
            pady=11,
            font=("Segoe UI", 10),
            cursor="hand2",
        )
        self.secondary.pack(side="right", padx=(12, 0))
        self.progress = ttk.Progressbar(self.shell, mode="indeterminate")
        self.status = self._label(self.shell, "", size=10, color=MUTED, wrap=530)
        self.status.configure(height=3, anchor="nw")
        self.status.pack(fill="x", pady=(14, 0))
        self.browser_link = self._link(self.shell, "Open sign-in page again", self.reopen_browser)
        bottom = tk.Frame(self.shell, bg="white")
        bottom.pack(fill="x", pady=(8, 0))
        self._link(bottom, "App settings", self.edit_settings).pack(side="left")
        self._link(bottom, "Open local folder", self.open_folder).pack(side="right")
        privacy = (
            "Credentials encrypted for your Windows account."
            if os.name == "nt"
            else "Credentials saved in owner-only local files."
        )
        self._label(self.shell, privacy, size=9, color=MUTED).pack(anchor="w", pady=(16, 0))
        self._display({})
        if preview:
            self._display(
                {
                    "oauth_client_configured": preview == "saved",
                    "credential_present": preview == "saved",
                    "state": "credentials_present" if preview == "saved" else "not_authorized",
                    "timezone": "America/New_York",
                    "client_id": "example-oura-app",
                }
            )
            self.primary.configure(state="disabled")
            self.secondary.configure(state="disabled")
            self.status.configure(text="Example screen. No account or credentials accessed.")
        else:
            self.run_work(connection.prepare, "Checking your saved connection…")
        self.root.after(80, self.poll)

    @staticmethod
    def _label(
        parent: tk.Misc,
        text: str,
        *,
        size: int = 11,
        color: str = INK,
        bold: bool = False,
        wrap: int = 0,
        bg: str = "white",
    ) -> tk.Label:
        return tk.Label(
            parent,
            text=text,
            bg=bg,
            fg=color,
            justify="left",
            wraplength=wrap,
            font=("Segoe UI", size, "bold" if bold else "normal"),
        )

    @staticmethod
    def _link(parent: tk.Misc, text: str, action: Callable[[], object]) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=action,
            bg="white",
            fg=BLUE,
            relief="flat",
            bd=0,
            activebackground="white",
            activeforeground=BLUE,
            cursor="hand2",
            font=("Segoe UI", 9),
        )

    def _display(self, state: JsonObject) -> None:
        self.state = state
        self.form.pack_forget()
        self.dashboard.pack_forget()
        self.client_id.set(state.get("client_id", ""))
        self.timezone.set(state.get("timezone", "America/New_York"))
        self.secret.set("")
        saved = state.get("state") == "credentials_present"
        configured = state.get("oauth_client_configured", False)
        self.mode = "saved" if saved else "ready" if configured else "setup"
        self.primary.configure(
            text="Check connection" if saved else "Connect with Oura" if configured else "Save & connect with Oura"
        )
        self.secondary.configure(text="Disconnect" if saved else "Close")
        if self.mode == "setup":
            self.form.pack(fill="x")
            self.heading.configure(text="Connect to Oura")
        else:
            self.dashboard.pack(fill="x")
            self.heading.configure(text="Your Oura connection")
            self.connection_label.configure(
                text="Sign-in saved" if saved else "App setup saved", fg=GREEN if saved else INK
            )
            self.detail.configure(
                text="Your sign-in is saved on this PC. Check the connection to verify Oura access."
                if saved
                else "Continue in your browser to authorize access to your Oura data."
            )
            self.time_label.configure(text="Timezone: " + self.timezone.get())
        self.secret_label.configure(text="Client secret · leave blank to keep saved" if configured else "Client secret")
        if state.get("live_connection_verified"):
            self.connection_label.configure(text="Connected to Oura", fg=GREEN)
            self.detail.configure(text="Connection checked successfully. Your local MCP tools can retrieve Oura data.")

    def run_work(self, action: Callable[[], JsonObject], message: str) -> None:
        if self.busy or self.preview:
            return
        self.busy = True
        self.cancel.clear()
        self.primary.configure(state="disabled")
        self.secondary.configure(text="Cancel")
        for field in (self.client_entry, self.secret_entry, self.zone_entry, self.show):
            field.configure(state="disabled")
        self.status.configure(text=message, fg=MUTED)
        self.progress.start(12)
        self.progress.pack(before=self.status, fill="x", pady=(12, 0))

        def work() -> None:
            try:
                self.events.put(("done", action()))
            except Exception as exc:
                if self.cancel.is_set():
                    message = "Sign-in cancelled. You can connect again when ready."
                elif isinstance(exc, TokenStoreError):
                    message = (
                        "Could not open or save the local credentials for this Windows account. Check the local folder."
                    )
                elif isinstance(exc, AuthenticationError):
                    message = "Oura sign-in was declined or timed out. Check your app's callback URL and try again."
                elif isinstance(exc, ConfigurationError):
                    message = str(exc)
                else:
                    message = (
                        "Could not complete the request. Check your app details, timezone, and internet connection."
                    )
                try:
                    snapshot = self.connection.snapshot()
                except Exception:
                    snapshot = self.state
                self.events.put(("error", {"message": message, "snapshot": snapshot}))

        self.worker = Thread(target=work, name="oura-connection", daemon=False)
        self.worker.start()

    def poll(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "browser":
                    self.auth_url = str(payload)
                    self.browser_link.pack(before=self.status, anchor="w")
                    self.status.configure(
                        text="Finish signing in on Oura's website. This window will update automatically."
                    )
                    continue
                self.busy = False
                self.progress.stop()
                self.progress.pack_forget()
                self.auth_url = None
                self.browser_link.pack_forget()
                for field in (self.client_entry, self.secret_entry, self.zone_entry, self.show):
                    field.configure(state="normal")
                self.primary.configure(state="normal")
                if kind == "done" and isinstance(payload, dict):
                    # A live probe omits setup metadata; retain it from the local snapshot.
                    self._display({**self.state, **payload})
                    probe = payload.get("live_probe")
                    self.status.configure(
                        text="Connection verified."
                        if payload.get("live_connection_verified")
                        else "Oura could not verify access. Your saved sign-in is kept; try reconnecting."
                        if probe
                        else "Your connection is saved locally."
                        if self.mode == "saved"
                        else "Ready when you are.",
                        fg=MUTED,
                    )
                else:
                    draft_id, draft_zone = self.client_id.get(), self.timezone.get()
                    failure: JsonObject = (
                        payload if isinstance(payload, dict) else {"message": str(payload), "snapshot": self.state}
                    )
                    self._display(failure["snapshot"])
                    if self.mode == "setup":
                        self.client_id.set(draft_id)
                        self.timezone.set(draft_zone)
                    self.status.configure(text=failure["message"], fg="#AB3333")
                if self.closing:
                    self.root.destroy()
                    return
        except queue.Empty:
            pass
        self.root.after(80, self.poll)

    def activate(self) -> None:
        if self.mode == "saved":
            self.run_work(self.connection.check, "Checking your Oura connection…")
            return
        client_id, secret, timezone = self.client_id.get(), self.secret.get(), self.timezone.get()
        mode = self.mode
        self.secret.set("")

        def connect() -> JsonObject:
            if mode == "setup":
                self.connection.save_app(client_id, secret, timezone)
            return self.connection.connect(self.cancel, lambda url: self.events.put(("browser", url)))

        self.run_work(connect, "Preparing secure sign-in…")

    def secondary_action(self) -> None:
        if self.busy:
            self.cancel.set()
            self.status.configure(text="Finishing safely…")
        elif self.mode == "saved":
            if messagebox.askyesno(
                "Disconnect Oura",
                "Remove this app's saved sign-in from this PC?\n\nYour Oura data and app setup will stay.",
                parent=self.root,
            ):
                self.run_work(self.connection.disconnect, "Removing the saved sign-in…")
        else:
            self.close()

    def edit_settings(self) -> None:
        if self.busy or self.preview:
            return
        self.dashboard.pack_forget()
        self.form.pack(fill="x")
        self.mode = "setup"
        self.heading.configure(text="Your Oura app")
        self.primary.configure(text="Save & connect with Oura")
        self.secondary.configure(text="Close")
        self.status.configure(
            text="Advanced settings are kept. Restart an existing MCP connection after changing app details."
        )

    def copy_callback(self) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(self.state.get("redirect_uri", "http://localhost:8765/callback"))
        self.status.configure(text="Callback URL copied. Register this exact URL in your Oura developer app.")

    def reopen_browser(self) -> None:
        if self.auth_url:
            webbrowser.open(self.auth_url)

    def open_folder(self) -> None:
        if os.name == "nt" and self.connection.path.parent.exists() and not self.preview:
            os.startfile(self.connection.path.parent)

    def close(self) -> None:
        self.secret.set("")
        if self.busy:
            self.closing = True
            self.cancel.set()
            self.status.configure(text="Finishing safely before closing…")
        else:
            self.root.destroy()

    def _callback_error(self, *args: Any) -> None:
        self.status.configure(text="The window could not complete that action. Please try again.", fg="#AB3333")


def run_ui(path: Path) -> None:
    mutex = None
    if os.name == "nt":
        import win32api
        import win32event
        import win32gui

        name = "Local\\OuraConnect-" + hashlib.sha256(str(path.resolve()).casefold().encode()).hexdigest()[:24]
        mutex = win32event.CreateMutex(None, False, name)
        if win32api.GetLastError() == 183:
            window = win32gui.FindWindow(None, "Oura Connect")
            if window:
                win32gui.ShowWindow(window, 9)
                try:
                    win32gui.SetForegroundWindow(window)
                except Exception:
                    pass
            win32api.CloseHandle(mutex)
            return
    try:
        root = tk.Tk()
        ConnectWindow(root, Connection(path))
        root.after(100, root.deiconify)
        root.mainloop()
    finally:
        if mutex is not None:
            win32api.CloseHandle(mutex)
