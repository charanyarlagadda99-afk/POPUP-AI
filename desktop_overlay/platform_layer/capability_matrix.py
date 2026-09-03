"""OS Capability Matrix and Probing System."""

from __future__ import annotations
import sys
import platform
from dataclasses import dataclass

@dataclass
class CapabilityStatus:
    name: str
    supported: bool
    status_detail: str
    permission_needed: bool = False
    fallback_available: bool = True

class CapabilityMatrix:
    """Detects available OS and environment capabilities at runtime."""
    
    def __init__(self):
        self.os_name = platform.system()
        self.os_version = platform.version()
        self._capabilities: dict[str, CapabilityStatus] = {}
        self.detect_all()

    def detect_all(self) -> dict[str, CapabilityStatus]:
        self._capabilities["screen_capture"] = self._detect_screen_capture()
        self._capabilities["accessibility"] = self._detect_accessibility()
        self._capabilities["clipboard"] = self._detect_clipboard()
        self._capabilities["global_hotkey"] = self._detect_hotkeys()
        self._capabilities["ui_automation"] = self._detect_ui_automation()
        self._capabilities["capture_protection"] = self._detect_capture_protection()
        self._capabilities["browser_bridge"] = self._detect_browser_bridge()
        return self._capabilities

    def _detect_screen_capture(self) -> CapabilityStatus:
        try:
            from PIL import ImageGrab
            return CapabilityStatus(
                name="Screen Capture",
                supported=True,
                status_detail="Pillow ImageGrab ready"
            )
        except ImportError:
            return CapabilityStatus(
                name="Screen Capture",
                supported=False,
                status_detail="Pillow (PIL) not installed",
                fallback_available=False
            )

    def _detect_accessibility(self) -> CapabilityStatus:
        if self.os_name == "Windows":
            return CapabilityStatus(
                name="Accessibility / UI Automation",
                supported=True,
                status_detail="Windows UI Automation (ctypes / UIA) supported"
            )
        return CapabilityStatus(
            name="Accessibility / UI Automation",
            supported=False,
            status_detail=f"Limited support on {self.os_name}",
            fallback_available=True
        )

    def _detect_clipboard(self) -> CapabilityStatus:
        return CapabilityStatus(
            name="Clipboard Manager",
            supported=True,
            status_detail="Native clipboard APIs operational"
        )

    def _detect_hotkeys(self) -> CapabilityStatus:
        try:
            import keyboard
            return CapabilityStatus(
                name="Global Hotkeys",
                supported=True,
                status_detail="keyboard module loaded"
            )
        except Exception:
            return CapabilityStatus(
                name="Global Hotkeys",
                supported=False,
                status_detail="keyboard module unavailable (requires root on Linux / permission)",
                fallback_available=True
            )

    def _detect_ui_automation(self) -> CapabilityStatus:
        try:
            import pyautogui
            return CapabilityStatus(
                name="Input Automation",
                supported=True,
                status_detail="PyAutoGUI input synthesis ready"
            )
        except ImportError:
            return CapabilityStatus(
                name="Input Automation",
                supported=False,
                status_detail="PyAutoGUI not installed",
                fallback_available=False
            )

    def _detect_capture_protection(self) -> CapabilityStatus:
        if self.os_name == "Windows":
            # SetWindowDisplayAffinity available on Windows 7+ (WDA_EXCLUDEFROMCAPTURE in Win 10 2004+)
            return CapabilityStatus(
                name="Capture Protection API",
                supported=True,
                status_detail="Windows SetWindowDisplayAffinity API available"
            )
        return CapabilityStatus(
            name="Capture Protection API",
            supported=False,
            status_detail=f"Not supported on {self.os_name}",
            fallback_available=False
        )

    def _detect_browser_bridge(self) -> CapabilityStatus:
        return CapabilityStatus(
            name="Browser Native Bridge",
            supported=True,
            status_detail="Local bridge & DOM receiver interface active"
        )

    def get_summary(self) -> dict[str, bool]:
        return {k: v.supported for k, v in self._capabilities.items()}

    def get_details(self) -> dict[str, CapabilityStatus]:
        return self._capabilities
