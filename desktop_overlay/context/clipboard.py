"""Dedicated Clipboard Manager and Local History."""

from __future__ import annotations
import time
import tkinter as tk
from dataclasses import dataclass

@dataclass
class ClipboardItem:
    text: str
    timestamp: float
    char_count: int
    preview: str

class ClipboardManager:
    """Monitors and provides access to local clipboard contents."""
    
    def __init__(self, max_history: int = 30):
        self.max_history = max_history
        self.history: list[ClipboardItem] = []
        self._last_text: str = ""

    def get_current_text(self, root: tk.Tk) -> str:
        try:
            txt = root.clipboard_get()
            if txt and txt != self._last_text:
                self._record(txt)
            return txt
        except Exception:
            return ""

    def set_text(self, root: tk.Tk, text: str) -> bool:
        try:
            root.clipboard_clear()
            root.clipboard_append(text)
            self._record(text)
            return True
        except Exception:
            return False

    def _record(self, text: str) -> None:
        self._last_text = text
        preview = text.strip().replace("\n", " ")
        if len(preview) > 60:
            preview = preview[:57] + "..."
            
        item = ClipboardItem(
            text=text,
            timestamp=time.time(),
            char_count=len(text),
            preview=preview
        )
        self.history.insert(0, item)
        if len(self.history) > self.max_history:
            self.history.pop()

    def get_history(self) -> list[ClipboardItem]:
        return list(self.history)
