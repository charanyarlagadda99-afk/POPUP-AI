"""Agent Planning, Tool Selection, and Reasoning Execution Loop."""

from __future__ import annotations
import threading
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass

from desktop_overlay.agent.tools.base import BaseTool, ToolResult
from desktop_overlay.agent.tools.screen_tool import ScreenTool
from desktop_overlay.agent.tools.clipboard_tool import ClipboardTool
from desktop_overlay.agent.tools.uia_tool import UIAutomationTool
from desktop_overlay.agent.tools.input_tool import InputTool
from desktop_overlay.agent.tools.file_tool import FileTool
from desktop_overlay.agent.tools.text_clean_tool import TextCleanTool
from desktop_overlay.agent.llm_provider import LLMProvider
from desktop_overlay.security.permissions import PermissionManager
from desktop_overlay.security.audit import AuditLogger
from desktop_overlay.context.context_engine import ApplicationContext

@dataclass
class AgentStep:
    step_num: int
    description: str
    tool_name: Optional[str] = None
    params: Optional[dict] = None
    status: str = "pending"  # "pending", "running", "waiting_confirmation", "done", "failed"
    result: Optional[str] = None

class AgentEngine:
    """Coordinates intent detection, task planning, permission checks, and step-by-step tool execution."""
    
    def __init__(self, llm: LLMProvider, permissions: PermissionManager, audit: AuditLogger):
        self.llm = llm
        self.permissions = permissions
        self.audit = audit
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()
        self._cancelled = False
        self._confirm_event = threading.Event()
        self._confirm_granted = False

    def _register_default_tools(self) -> None:
        tools = [
            ScreenTool(),
            ClipboardTool(),
            UIAutomationTool(),
            InputTool(),
            FileTool(),
            TextCleanTool()
        ]
        for t in tools:
            self._tools[t.name] = t

    def register_tool(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def cancel(self) -> None:
        self._cancelled = True
        self._confirm_granted = False
        self._confirm_event.set()

    def confirm_action(self, allow: bool) -> None:
        self._confirm_granted = allow
        self._confirm_event.set()

    def run_agent_task(
        self,
        task_prompt: str,
        app_context: ApplicationContext,
        on_step_update: Callable[[list[AgentStep]], None],
        on_confirm_needed: Callable[[str], None],
        on_complete: Callable[[str], None],
        gui_root: Any = None
    ) -> None:
        """Executes an agent task asynchronously with step-by-step trace and safety confirmations."""
        self._cancelled = False
        
        def _worker():
            context_prefix = app_context.to_prompt_context()
            
            # 1. Intent & Planning Phase
            plan_steps = self._plan_task(task_prompt, context_prefix)
            on_step_update(plan_steps)
            
            final_summary = []
            
            for step in plan_steps:
                if self._cancelled:
                    step.status = "failed"
                    step.result = "Task cancelled by user"
                    break
                    
                step.status = "running"
                on_step_update(plan_steps)
                
                # Execute tool step if tool specified
                if step.tool_name and step.tool_name in self._tools:
                    tool = self._tools[step.tool_name]
                    params = step.params or {}
                    if "root" not in params and gui_root:
                        params["root"] = gui_root
                        
                    # Check permission
                    if tool.required_permission and not self.permissions.is_granted(tool.required_permission):
                        step.status = "failed"
                        step.result = f"Permission '{tool.required_permission.value}' denied"
                        self.audit.log("tool_blocked", tool.name, step.result, status="blocked")
                        on_step_update(plan_steps)
                        break
                        
                    # Check if high impact requires confirmation
                    if tool.is_high_impact and self.permissions.config.privacy_mode == "Agent Mode":
                        step.status = "waiting_confirmation"
                        on_step_update(plan_steps)
                        
                        self._confirm_event.clear()
                        confirm_msg = tool.get_confirmation_message(params)
                        on_confirm_needed(confirm_msg)
                        
                        self._confirm_event.wait()
                        if not self._confirm_granted or self._cancelled:
                            step.status = "failed"
                            step.result = "User declined action confirmation"
                            self.audit.log("tool_declined", tool.name, confirm_msg, status="declined")
                            on_step_update(plan_steps)
                            break
                            
                    # Execute tool
                    tool_res = tool.execute(params, context=app_context)
                    if tool_res.success:
                        step.status = "done"
                        step.result = str(tool_res.output)[:120]
                        final_summary.append(tool_res.action_description or str(tool_res.output))
                        self.audit.log("tool_exec", tool.name, str(params), status="success", user_confirmed=tool.is_high_impact)
                    else:
                        step.status = "failed"
                        step.result = tool_res.error or "Execution error"
                        self.audit.log("tool_exec", tool.name, tool_res.error or "", status="failed")
                else:
                    # Pure reasoning / AI step
                    step_prompt = f"Context:\n{context_prefix}\n\nTask: {task_prompt}\nStep: {step.description}\n\nProvide the direct outcome or answer for this step:"
                    out = self.llm.generate_sync(step_prompt)
                    step.status = "done"
                    step.result = out[:120]
                    final_summary.append(out)
                    
                on_step_update(plan_steps)
                
            summary_text = "\n".join(final_summary) if final_summary else "Task complete."
            on_complete(summary_text)

        threading.Thread(target=_worker, daemon=True).start()

    def _plan_task(self, prompt: str, context_str: str) -> list[AgentStep]:
        """Simple rule/heuristic + LLM task decomposition."""
        p_lower = prompt.lower()
        
        # Rule-based fast paths
        if "clean" in p_lower and ("watermark" in p_lower or "clipboard" in p_lower or "text" in p_lower):
            return [
                AgentStep(1, "Read clipboard text", "clipboard_action", {"action": "read"}),
                AgentStep(2, "Remove hidden watermarks and normalize Unicode", "clean_watermarks", {}),
                AgentStep(3, "Write cleaned text back to clipboard", "clipboard_action", {"action": "write"})
            ]
            
        if "type" in p_lower or "write this" in p_lower or "auto-type" in p_lower:
            return [
                AgentStep(1, "Inspect active target window", "uia_inspect", {}),
                AgentStep(2, "Synthesize keyboard input into target application", "input_automation", {"action": "type", "text": prompt})
            ]
            
        if "screen" in p_lower or "what am i seeing" in p_lower or "explain this" in p_lower:
            return [
                AgentStep(1, "Capture active window region", "screen_inspect", {}),
                AgentStep(2, "Analyze visual elements and text", None, {})
            ]
            
        # Default 2-step reasoning plan
        return [
            AgentStep(1, "Analyze active application context and user intent", None, {}),
            AgentStep(2, "Generate comprehensive solution", None, {})
        ]
