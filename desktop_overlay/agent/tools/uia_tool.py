"""UI Automation interaction tool for AI agent."""

from __future__ import annotations
from typing import Any
from desktop_overlay.agent.tools.base import BaseTool, ToolResult
from desktop_overlay.security.permissions import PermissionType
from desktop_overlay.context.accessibility import AccessibilityProvider

class UIAutomationTool(BaseTool):
    name = "uia_inspect"
    description = "Inspects accessible controls and elements in the active window."
    required_permission = PermissionType.ACCESSIBILITY
    is_high_impact = False

    def __init__(self):
        self.provider = AccessibilityProvider()

    def execute(self, params: dict, context: Any = None) -> ToolResult:
        hwnd = params.get("hwnd", 0)
        elements = self.provider.get_window_elements(hwnd)
        
        elem_list = [
            {"name": e.name, "control_type": e.control_type, "rect": e.rect, "enabled": e.is_enabled}
            for e in elements
        ]
        return ToolResult(
            success=True,
            output=elem_list,
            action_description=f"Inspected {len(elem_list)} accessible UI controls"
        )
