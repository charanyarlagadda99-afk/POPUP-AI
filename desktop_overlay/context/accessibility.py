"""Accessibility and UI Automation inspection provider."""

from __future__ import annotations
import sys
from typing import Optional
from dataclasses import dataclass

@dataclass
class UIElement:
    name: str
    control_type: str
    rect: tuple[int, int, int, int]
    is_enabled: bool = True
    value: Optional[str] = None

class AccessibilityProvider:
    """Inspects native accessible UI elements (buttons, inputs, labels) using standard OS interfaces."""
    
    def __init__(self):
        self.is_windows = sys.platform == "win32"

    def get_window_elements(self, hwnd: int) -> list[UIElement]:
        """Inspects accessible elements for given window."""
        if not self.is_windows or not hwnd:
            return []
            
        elements = []
        try:
            # Using pywinauto or fallback ctypes if available
            import pywinauto
            from pywinauto import Desktop
            
            app = Desktop(backend="uia")
            win = app.window(handle=hwnd)
            for child in win.children()[:20]: # Limit to avoid sluggishness
                try:
                    rect = child.rectangle()
                    elements.append(UIElement(
                        name=child.window_text(),
                        control_type=child.element_info.control_type or "Unknown",
                        rect=(rect.left, rect.top, rect.right, rect.bottom),
                        is_enabled=child.is_enabled()
                    ))
                except Exception:
                    pass
        except Exception:
            # Fallback lightweight placeholder
            pass
            
        return elements
