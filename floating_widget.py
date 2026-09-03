#!/usr/bin/env python3
"""
Universal Desktop AI Overlay & Watermark Remover.
Main Entry Point.
"""

from __future__ import annotations
import sys
import tkinter as tk
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from desktop_overlay.ui.overlay_window import DesktopOverlayWindow
from desktop_overlay.config import OverlayConfig

def main():
    try:
        root = tk.Tk()
        config = OverlayConfig.load()
        app = DesktopOverlayWindow(root, config)
        root.mainloop()
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == "__main__":
    main()
