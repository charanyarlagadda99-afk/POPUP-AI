"""Agent Execution Mode View: Step-by-step trace & Confirmation."""

from __future__ import annotations
import tkinter as tk
from typing import Callable, List
from desktop_overlay.config import THEMES
from desktop_overlay.agent.engine import AgentStep

class AgentExecutionView(tk.Frame):
    """Visualizes multi-step agent reasoning, tool calls, and confirmations."""
    
    def __init__(self, master, on_cancel: Callable[[], None], on_confirm: Callable[[bool], None], theme_name: str = "Dark"):
        self.t = THEMES.get(theme_name, THEMES["Dark"])
        super().__init__(master, bg=self.t["bg"], padx=15, pady=12)
        self.on_cancel = on_cancel
        self.on_confirm = on_confirm
        
        # Header
        hdr = tk.Frame(self, bg=self.t["bg"])
        hdr.pack(fill=tk.X, pady=(0, 10))
        
        self.lbl_task_title = tk.Label(hdr, text="⚡ Agent Task in Progress...", bg=self.t["bg"], fg=self.t["accent"], font=("Segoe UI", 11, "bold"))
        self.lbl_task_title.pack(side=tk.LEFT)
        
        self.btn_cancel = tk.Button(hdr, text="🛑 Cancel Task", command=self.on_cancel, bg=self.t["error"], fg="#FFFFFF", bd=0, padx=8, pady=3, font=("Segoe UI", 9, "bold"))
        self.btn_cancel.pack(side=tk.RIGHT)
        
        # Confirmation bar (hidden by default)
        self.confirm_frame = tk.Frame(self, bg=self.t["card"], bd=1, relief=tk.SOLID, padx=10, pady=8)
        self.lbl_confirm_msg = tk.Label(self.confirm_frame, text="", bg=self.t["card"], fg=self.t["warning"], wraplength=450, justify=tk.LEFT, font=("Segoe UI", 9, "bold"))
        self.lbl_confirm_msg.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Button(self.confirm_frame, text="✓ Allow", command=lambda: self._handle_confirm(True), bg=self.t["success"], fg="#000000", bd=0, padx=10, pady=3, font=("Segoe UI", 9, "bold")).pack(side=tk.RIGHT, padx=4)
        tk.Button(self.confirm_frame, text="✕ Decline", command=lambda: self._handle_confirm(False), bg=self.t["btn"], fg=self.t["btn_fg"], bd=0, padx=8, pady=3, font=("Segoe UI", 9)).pack(side=tk.RIGHT)
        
        # Steps container list
        self.steps_container = tk.Frame(self, bg=self.t["card_alt"], padx=10, pady=10)
        self.steps_container.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

    def update_steps(self, steps: list[AgentStep]) -> None:
        for w in self.steps_container.winfo_children():
            w.destroy()
            
        for step in steps:
            row = tk.Frame(self.steps_container, bg=self.t["card_alt"])
            row.pack(fill=tk.X, pady=3)
            
            # Status Badge
            if step.status == "done":
                badge = ("✓", self.t["success"])
            elif step.status == "running":
                badge = ("⏳", self.t["accent"])
            elif step.status == "waiting_confirmation":
                badge = ("⚠️", self.t["warning"])
            elif step.status == "failed":
                badge = ("✗", self.t["error"])
            else:
                badge = ("○", self.t["fg_dim"])
                
            tk.Label(row, text=badge[0], bg=self.t["card_alt"], fg=badge[1], font=("Segoe UI", 10, "bold"), width=3).pack(side=tk.LEFT)
            
            # Step description
            desc_text = f"{step.step_num}. {step.description}"
            if step.tool_name:
                desc_text += f" [{step.tool_name}]"
            tk.Label(row, text=desc_text, bg=self.t["card_alt"], fg=self.t["fg"], font=("Segoe UI", 9, "bold" if step.status == "running" else "normal")).pack(side=tk.LEFT, padx=4)
            
            # Step result summary
            if step.result:
                res_lbl = tk.Label(row, text=f"→ {step.result}", bg=self.t["card_alt"], fg=self.t["fg_dim"], font=("Segoe UI", 8))
                res_lbl.pack(side=tk.RIGHT, padx=6)

    def request_confirmation(self, message: str) -> None:
        self.lbl_confirm_msg.config(text=message)
        self.confirm_frame.pack(fill=tk.X, after=self.lbl_task_title.master, pady=(5, 0))

    def _handle_confirm(self, allow: bool) -> None:
        self.confirm_frame.pack_forget()
        self.on_confirm(allow)
