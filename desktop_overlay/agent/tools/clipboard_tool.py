"""Clipboard interaction tool for AI agent."""

from __future__ import annotations
from typing import Any
import tkinter as tk
from desktop_overlay.agent.tools.base import BaseTool, ToolResult
from desktop_overlay.security.permissions import PermissionType

class ClipboardTool(BaseTool):
    name = "clipboard_action"
    description = "Reads from or writes text to the system clipboard."
    required_permission = PermissionType.CLIPBOARD_READ
    is_high_impact = False

    def execute(self, params: dict, context: Any = None) -> ToolResult:
        action = params.get("action", "read") # "read" or "write"
        root = params.get("root") # Tk instance
        
        if not root:
            return ToolResult(success=False, output=None, error="No GUI root context available for clipboard")
            
        if action == "read":
            try:
                txt = root.clipboard_get()
                return ToolResult(success=True, output=txt, action_description="Read text from clipboard")
            except Exception as e:
                return ToolResult(success=False, output="", error=f"Clipboard read failed: {e}")
                
        elif action == "write":
            text = params.get("text", "")
            try:
                root.clipboard_clear()
                root.clipboard_append(text)
                return ToolResult(success=True, output=f"Copied {len(text)} characters", action_description=f"Wrote text to clipboard ({len(text)} chars)")
            except Exception as e:
                return ToolResult(success=False, output=None, error=f"Clipboard write failed: {e}")
                
        return ToolResult(success=False, output=None, error=f"Unknown clipboard action: {action}")
