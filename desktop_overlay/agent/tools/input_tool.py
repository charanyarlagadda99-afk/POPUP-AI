"""Input automation tool (Keyboard & Mouse) for AI agent."""

from __future__ import annotations
import time
from typing import Any
from desktop_overlay.agent.tools.base import BaseTool, ToolResult
from desktop_overlay.security.permissions import PermissionType

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

class InputTool(BaseTool):
    name = "input_automation"
    description = "Synthesizes keyboard typing, key combinations, or mouse clicks."
    required_permission = PermissionType.INPUT_AUTOMATION
    is_high_impact = True  # Requires confirmation before typing into external windows

    def get_confirmation_message(self, params: dict) -> str:
        action = params.get("action", "type")
        if action == "type":
            txt = params.get("text", "")
            preview = (txt[:30] + "...") if len(txt) > 30 else txt
            return f"Type '{preview}' ({len(txt)} chars) into the active window?"
        elif action == "click":
            x, y = params.get("x", 0), params.get("y", 0)
            return f"Click mouse at coordinates ({x}, {y})?"
        elif action == "hotkey":
            keys = params.get("keys", [])
            return f"Send keyboard shortcut: {' + '.join(keys)}?"
        return f"Perform input automation ({action})?"

    def execute(self, params: dict, context: Any = None) -> ToolResult:
        if not HAS_PYAUTOGUI:
            return ToolResult(success=False, output=None, error="PyAutoGUI not installed")
            
        action = params.get("action", "type")
        
        try:
            if action == "type":
                text = params.get("text", "")
                delay = params.get("delay", 0.005)
                # Sleep briefly to ensure window focus
                time.sleep(0.5)
                pyautogui.write(text, interval=delay)
                return ToolResult(success=True, output=f"Typed {len(text)} characters", action_description=f"Auto-typed text into target window")
                
            elif action == "click":
                x = params.get("x", 0)
                y = params.get("y", 0)
                pyautogui.click(x, y)
                return ToolResult(success=True, output=f"Clicked at ({x}, {y})", action_description=f"Clicked coordinates ({x}, {y})")
                
            elif action == "hotkey":
                keys = params.get("keys", [])
                if keys:
                    pyautogui.hotkey(*keys)
                    return ToolResult(success=True, output=f"Triggered hotkey {'+'.join(keys)}", action_description=f"Sent hotkey {'+'.join(keys)}")
                    
            return ToolResult(success=False, output=None, error=f"Unsupported input action: {action}")
        except Exception as e:
            return ToolResult(success=False, output=None, error=f"Input automation failed: {e}")
