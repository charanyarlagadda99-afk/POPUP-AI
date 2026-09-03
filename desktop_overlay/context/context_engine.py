"""Normalized Context Engine Aggregator."""

from __future__ import annotations
import time
import tkinter as tk
from typing import Optional, List
from dataclasses import dataclass, field

from desktop_overlay.context.active_window import ActiveWindowTracker, WindowContext
from desktop_overlay.context.screen import ScreenCaptureEngine, ScreenContext
from desktop_overlay.context.clipboard import ClipboardManager
from desktop_overlay.context.accessibility import AccessibilityProvider, UIElement
from desktop_overlay.context.browser import BrowserBridge, BrowserTabContext
from desktop_overlay.platform_layer.win32_api import get_cursor_position
from desktop_overlay.security.permissions import PermissionManager, PermissionType

@dataclass
class ApplicationContext:
    timestamp: float
    window: WindowContext
    cursor_position: tuple[int, int]
    clipboard_text: str = ""
    screen: Optional[ScreenContext] = None
    accessible_elements: list[UIElement] = field(default_factory=list)
    browser_tab: Optional[BrowserTabContext] = None
    permissions_summary: dict[str, bool] = field(default_factory=dict)

    def to_prompt_context(self) -> str:
        """Converts collected context into a concise prompt prefix for AI models."""
        parts = []
        if self.window and self.window.title:
            parts.append(f"Active App: {self.window.process_name} (Title: '{self.window.title}') [Category: {self.window.app_category}]")
            
        if self.browser_tab and self.browser_tab.connected and self.browser_tab.url:
            parts.append(f"Browser URL: {self.browser_tab.url}")
            if self.browser_tab.selected_text:
                parts.append(f"Selected Page Text: \"{self.browser_tab.selected_text}\"")
                
        if self.clipboard_text:
            clip_snippet = self.clipboard_text.strip()
            if len(clip_snippet) > 400:
                clip_snippet = clip_snippet[:397] + "..."
            parts.append(f"Clipboard Content: \"{clip_snippet}\"")
            
        if self.accessible_elements:
            elem_names = [e.name for e in self.accessible_elements if e.name][:5]
            if elem_names:
                parts.append(f"Visible UI Controls: {', '.join(elem_names)}")
                
        if self.screen and self.screen.ocr_text:
            parts.append(f"Visible Screen Text / Questions:\n---\n{self.screen.ocr_text}\n---")
                
        return "\n".join(parts)

class ContextEngine:
    """Aggregates multi-source desktop context according to granted permissions."""
    
    def __init__(self, permission_manager: PermissionManager):
        self.permissions = permission_manager
        self.window_tracker = ActiveWindowTracker()
        self.screen_engine = ScreenCaptureEngine()
        self.clipboard_mgr = ClipboardManager()
        self.accessibility = AccessibilityProvider()
        self.browser_bridge = BrowserBridge()

    def collect(self, root: tk.Tk, include_screen: bool = False) -> ApplicationContext:
        # Active Window is collected
        win_ctx = self.window_tracker.get_current()
        cursor_pos = get_cursor_position()
        
        # Clipboard
        clip_text = ""
        if self.permissions.is_granted(PermissionType.CLIPBOARD_READ):
            clip_text = self.clipboard_mgr.get_current_text(root)
            
        # Screen snapshot (only when explicitly allowed & requested)
        screen_ctx = None
        if include_screen and self.permissions.is_granted(PermissionType.SCREEN_CAPTURE):
            # Capture full desktop screen for comprehensive question and text discovery
            screen_ctx = self.screen_engine.capture_fullscreen()
                
        # Accessibility UI elements
        elements = []
        if self.permissions.is_granted(PermissionType.ACCESSIBILITY) and win_ctx.pid:
            # win_ctx info includes hwnd in win32_api
            from desktop_overlay.platform_layer.win32_api import get_foreground_window_info
            info = get_foreground_window_info()
            hwnd = info.get("hwnd", 0)
            if hwnd:
                elements = self.accessibility.get_window_elements(hwnd)
                
        # Browser tab info
        browser_tab = self.browser_bridge.get_context()
        
        return ApplicationContext(
            timestamp=time.time(),
            window=win_ctx,
            cursor_position=cursor_pos,
            clipboard_text=clip_text,
            screen=screen_ctx,
            accessible_elements=elements,
            browser_tab=browser_tab,
            permissions_summary={k: v["granted"] for k, v in self.permissions.get_all_status().items()}
        )
