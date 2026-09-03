"""Application entry point for Universal Desktop AI Overlay."""

from __future__ import annotations
import sys
import tkinter as tk
from desktop_overlay.config import OverlayConfig
from desktop_overlay.ui.overlay_window import DesktopOverlayWindow

def run():
    root = tk.Tk()
    config = OverlayConfig.load()
    app = DesktopOverlayWindow(root, config)
    root.mainloop()

if __name__ == "__main__":
    run()
