"""Browser Integration & Native Messaging Bridge Abstraction."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class BrowserTabContext:
    url: str
    title: str
    selected_text: Optional[str] = None
    page_text_summary: Optional[str] = None
    connected: bool = False

class BrowserBridge:
    """Provides structured communication with browser extensions via standard native messaging."""
    
    def __init__(self):
        self._current_context: Optional[BrowserTabContext] = None

    def update_tab_context(self, url: str, title: str, selected_text: Optional[str] = None, page_text: Optional[str] = None) -> None:
        self._current_context = BrowserTabContext(
            url=url,
            title=title,
            selected_text=selected_text,
            page_text_summary=page_text[:1000] if page_text else None,
            connected=True
        )

    def get_context(self) -> BrowserTabContext:
        if self._current_context:
            return self._current_context
        return BrowserTabContext(url="", title="", connected=False)
