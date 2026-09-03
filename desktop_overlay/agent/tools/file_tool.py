"""Local safe file operations tool for AI agent."""

from __future__ import annotations
import os
from pathlib import Path
from typing import Any
from desktop_overlay.agent.tools.base import BaseTool, ToolResult
from desktop_overlay.security.permissions import PermissionType

class FileTool(BaseTool):
    name = "file_operations"
    description = "Safely reads or writes text files locally."
    required_permission = PermissionType.FILE_ACCESS
    is_high_impact = True  # Modifying files requires confirmation

    def get_confirmation_message(self, params: dict) -> str:
        action = params.get("action", "read")
        path = params.get("filepath", "")
        if action == "write":
            return f"Save/overwrite file at path: '{path}'?"
        return f"Read file from '{path}'?"

    def execute(self, params: dict, context: Any = None) -> ToolResult:
        action = params.get("action", "read")
        filepath = params.get("filepath", "")
        
        if not filepath:
            return ToolResult(success=False, output=None, error="No filepath specified")
            
        p = Path(filepath)
        
        if action == "read":
            if not p.exists():
                return ToolResult(success=False, output=None, error=f"File not found: {filepath}")
            try:
                content = p.read_text(encoding="utf-8")
                return ToolResult(success=True, output=content, action_description=f"Read file: {p.name}")
            except Exception as e:
                return ToolResult(success=False, output=None, error=str(e))
                
        elif action == "write":
            content = params.get("content", "")
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
                return ToolResult(success=True, output=f"Saved {len(content)} bytes to {p.name}", action_description=f"Saved file: {p.name}")
            except Exception as e:
                return ToolResult(success=False, output=None, error=str(e))
                
        return ToolResult(success=False, output=None, error=f"Unknown file action: {action}")
