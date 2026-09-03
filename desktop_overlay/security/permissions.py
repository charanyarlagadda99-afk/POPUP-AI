"""Granular Permission Center and Privacy Modes."""

from __future__ import annotations
from enum import Enum
from typing import Dict
from desktop_overlay.config import OverlayConfig

class PermissionType(Enum):
    SCREEN_CAPTURE = "screen_capture"
    ACCESSIBILITY = "accessibility"
    INPUT_AUTOMATION = "input_automation"
    CLIPBOARD_READ = "clipboard_read"
    CLIPBOARD_WRITE = "clipboard_write"
    FILE_ACCESS = "file_access"
    NETWORK_AI = "network_ai"

class PrivacyMode(Enum):
    MAXIMUM_PRIVACY = "Maximum Privacy"
    BALANCED = "Balanced"
    AGENT_MODE = "Agent Mode"

class PermissionManager:
    """Manages dynamic runtime permissions and privacy profiles."""
    
    DESCRIPTIONS = {
        PermissionType.SCREEN_CAPTURE: "Allows analyzing visible screen regions when explicitly requested.",
        PermissionType.ACCESSIBILITY: "Allows reading accessible UI elements (buttons, inputs, labels).",
        PermissionType.INPUT_AUTOMATION: "Allows automated typing and mouse interactions upon confirmation.",
        PermissionType.CLIPBOARD_READ: "Allows reading copied text to provide instant context.",
        PermissionType.CLIPBOARD_WRITE: "Allows placing AI answers or cleaned text into the clipboard.",
        PermissionType.FILE_ACCESS: "Allows reading and exporting text documents locally.",
        PermissionType.NETWORK_AI: "Allows communicating with Ollama or local LLM server."
    }

    def __init__(self, config: OverlayConfig):
        self.config = config
        self._permissions: Dict[PermissionType, bool] = {
            PermissionType.SCREEN_CAPTURE: config.allow_screen_capture,
            PermissionType.ACCESSIBILITY: config.allow_accessibility,
            PermissionType.INPUT_AUTOMATION: config.allow_input_automation,
            PermissionType.CLIPBOARD_READ: config.allow_clipboard_read,
            PermissionType.CLIPBOARD_WRITE: config.allow_clipboard_write,
            PermissionType.FILE_ACCESS: config.allow_file_access,
            PermissionType.NETWORK_AI: True
        }
        self.apply_privacy_mode(PrivacyMode(config.privacy_mode))

    def is_granted(self, perm: PermissionType) -> bool:
        return self._permissions.get(perm, False)

    def set_permission(self, perm: PermissionType, granted: bool) -> None:
        self._permissions[perm] = granted
        # Sync to config
        if perm == PermissionType.SCREEN_CAPTURE: self.config.allow_screen_capture = granted
        elif perm == PermissionType.ACCESSIBILITY: self.config.allow_accessibility = granted
        elif perm == PermissionType.INPUT_AUTOMATION: self.config.allow_input_automation = granted
        elif perm == PermissionType.CLIPBOARD_READ: self.config.allow_clipboard_read = granted
        elif perm == PermissionType.CLIPBOARD_WRITE: self.config.allow_clipboard_write = granted
        elif perm == PermissionType.FILE_ACCESS: self.config.allow_file_access = granted
        self.config.save()

    def apply_privacy_mode(self, mode: PrivacyMode) -> None:
        self.config.privacy_mode = mode.value
        if mode == PrivacyMode.MAXIMUM_PRIVACY:
            self._permissions[PermissionType.SCREEN_CAPTURE] = False
            self._permissions[PermissionType.INPUT_AUTOMATION] = False
            self._permissions[PermissionType.ACCESSIBILITY] = False
        elif mode == PrivacyMode.BALANCED:
            self._permissions[PermissionType.SCREEN_CAPTURE] = True
            self._permissions[PermissionType.ACCESSIBILITY] = True
            self._permissions[PermissionType.INPUT_AUTOMATION] = True
        elif mode == PrivacyMode.AGENT_MODE:
            for k in self._permissions:
                self._permissions[k] = True
        self.config.save()

    def get_all_status(self) -> dict[str, dict]:
        return {
            perm.value: {
                "name": perm.name.replace("_", " ").title(),
                "granted": self.is_granted(perm),
                "description": self.DESCRIPTIONS.get(perm, "")
            }
            for perm in PermissionType
        }
