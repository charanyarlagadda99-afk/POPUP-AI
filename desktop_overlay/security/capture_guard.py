"""Screen Capture Protection Manager."""

from __future__ import annotations
import sys
from desktop_overlay.platform_layer.win32_api import set_window_capture_protection, IS_WINDOWS

class CaptureGuard:
    """
    Manages OS-level display affinity protection for the overlay window.
    Applies official Windows SetWindowDisplayAffinity APIs when enabled by the user.
    """
    
    def __init__(self, hwnd: int = 0, initial_state: bool = False):
        self.hwnd = hwnd
        self.is_active = False
        if hwnd and initial_state:
            self.set_protection(True)

    def set_hwnd(self, hwnd: int) -> None:
        self.hwnd = hwnd
        if self.is_active:
            self.set_protection(True)

    def set_protection(self, enable: bool) -> bool:
        if not IS_WINDOWS or not self.hwnd:
            self.is_active = False
            return False
            
        success = set_window_capture_protection(self.hwnd, enable)
        if success or not enable:
            self.is_active = enable
            return True
        return False

    def toggle(self) -> bool:
        return self.set_protection(not self.is_active)
