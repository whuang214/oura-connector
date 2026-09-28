"""Render only synthetic desktop previews; never load a user's configuration."""

import argparse
import tempfile
import tkinter as tk
from pathlib import Path

from PIL import ImageGrab

from oura_connector.connection import Connection
from oura_connector.interfaces.desktop import ConnectWindow

parser = argparse.ArgumentParser()
parser.add_argument("--state", choices=("setup", "saved"), default="setup")
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()

with tempfile.TemporaryDirectory(prefix="oura-preview-") as directory:
    root = tk.Tk()
    window = ConnectWindow(root, Connection(Path(directory) / "config.toml"), preview=args.state)
    root.attributes("-topmost", True)
    root.update()

    def capture() -> None:
        import win32gui

        handle = win32gui.GetAncestor(root.winfo_id(), 2)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        ImageGrab.grab(window=handle).save(args.output)
        root.destroy()

    root.after(400, capture)
    root.mainloop()
