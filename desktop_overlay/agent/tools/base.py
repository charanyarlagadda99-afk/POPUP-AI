"""Abstract BaseTool interface for AI agent tools."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional
from desktop_overlay.security.permissions import PermissionType

@dataclass
class ToolResult:
    success: bool
    output: Any
    error: Optional[str] = None
    action_description: str = ""

class BaseTool(ABC):
    """Base class for all agent execution tools."""
    
    name: str = "base_tool"
    description: str = "Base tool description"
    required_permission: Optional[PermissionType] = None
    is_high_impact: bool = False  # If True, requires explicit user confirmation before execution
    
    @abstractmethod
    def execute(self, params: dict, context: Any = None) -> ToolResult:
        """Executes the tool with given parameters and returns ToolResult."""
        pass

    def get_confirmation_message(self, params: dict) -> str:
        """User-facing message shown in agent mode when confirmation is needed."""
        return f"Allow the assistant to perform action '{self.name}' with params: {params}?"
