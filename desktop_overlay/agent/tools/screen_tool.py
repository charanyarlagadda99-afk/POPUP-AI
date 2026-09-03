"""Screen inspection tool for AI agent."""

from __future__ import annotations
from typing import Any
from desktop_overlay.agent.tools.base import BaseTool, ToolResult
from desktop_overlay.security.permissions import PermissionType
from desktop_overlay.context.screen import ScreenCaptureEngine

class ScreenTool(BaseTool):
    name = "screen_inspect"
    description = "Captures and analyzes a region of the screen or active window."
    required_permission = PermissionType.SCREEN_CAPTURE
    is_high_impact = False

    def __init__(self):
        self.engine = ScreenCaptureEngine()

    def execute(self, params: dict, context: Any = None) -> ToolResult:
        region = params.get("region") # (left, top, right, bottom)
        if region and len(region) == 4:
            res = self.engine.capture_region(tuple(region))
        else:
            res = self.engine.capture_fullscreen()
            
        if not res.available:
            return ToolResult(success=False, output=None, error=res.error or "Screen capture failed")
            
        return ToolResult(
            success=True,
            output={"width": res.width, "height": res.height, "has_image": bool(res.image_base64)},
            action_description=f"Captured screen region ({res.width}x{res.height})"
        )
