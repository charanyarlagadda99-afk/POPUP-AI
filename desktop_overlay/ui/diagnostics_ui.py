"""Developer Diagnostics & Observability Dashboard."""

from __future__ import annotations
import tkinter as tk
from typing import Callable
from desktop_overlay.config import THEMES
from desktop_overlay.context.context_engine import ContextEngine
from desktop_overlay.platform_layer.capability_matrix import CapabilityMatrix
from desktop_overlay.security.audit import AuditLogger

class DiagnosticsPanel(tk.Frame):
    """Real-time observability dashboard for active context and security audit."""
    
    def __init__(self, master, context_engine: ContextEngine, capabilities: CapabilityMatrix, audit: AuditLogger, on_close: Callable[[], None], theme_name: str = "Dark"):
        self.t = THEMES.get(theme_name, THEMES["Dark"])
        super().__init__(master, bg=self.t["bg"], padx=15, pady=15)
        self.context_engine = context_engine
        self.capabilities = capabilities
        self.audit = audit
        self.on_close = on_close
        
        # Header
        hdr = tk.Frame(self, bg=self.t["bg"])
        hdr.pack(fill=tk.X, pady=(0, 10))
        
        tk.Button(
            hdr,
            text="← Back to Assistant",
            command=self.on_close,
            bg=self.t["btn"],
            fg=self.t["btn_fg"],
            bd=0,
            padx=10,
            pady=3,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Label(hdr, text="🔍 System Diagnostics & Observability", bg=self.t["bg"], fg=self.t["accent"], font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
        tk.Button(hdr, text="↻ Refresh", command=self.refresh, bg=self.t["btn"], fg=self.t["btn_fg"], bd=0, padx=8, pady=2, cursor="hand2").pack(side=tk.LEFT, padx=10)
        tk.Button(hdr, text="✕ Close", command=self.on_close, bg=self.t["btn"], fg=self.t["btn_fg"], bd=0, padx=8, pady=2, cursor="hand2").pack(side=tk.RIGHT)
        
        # Diagnostics Text Display
        self.txt = tk.Text(
            self,
            bg=self.t["card_alt"],
            fg=self.t["fg"],
            insertbackground=self.t["fg"],
            font=("Consolas", 9),
            bd=0,
            padx=10,
            pady=10
        )
        self.txt.pack(fill=tk.BOTH, expand=True)
        self.refresh()

    def refresh(self) -> None:
        ctx = self.context_engine.collect(self.winfo_toplevel())
        caps = self.capabilities.get_details()
        recent_audit = self.audit.get_recent(10)
        
        lines = []
        lines.append("=== ACTIVE APPLICATION CONTEXT ===")
        lines.append(f"Process Name  : {ctx.window.process_name} (PID: {ctx.window.pid})")
        lines.append(f"Window Title  : {ctx.window.title}")
        lines.append(f"Window Rect   : {ctx.window.rect}")
        lines.append(f"App Category  : {ctx.window.app_category}")
        lines.append(f"Cursor Pos    : {ctx.cursor_position}")
        lines.append(f"Clipboard Len : {len(ctx.clipboard_text)} chars")
        lines.append("")
        
        lines.append("=== OS CAPABILITIES MATRIX ===")
        for name, cap in caps.items():
            status_sym = "✓" if cap.supported else "✗"
            lines.append(f"[{status_sym}] {cap.name:<30} : {cap.status_detail}")
        lines.append("")
        
        lines.append("=== RECENT AUDIT LOGS (SANITIZED) ===")
        if not recent_audit:
            lines.append("(No agent tool actions recorded yet)")
        for a in recent_audit:
            lines.append(f"• [{a.status.upper()}] {a.action} ({a.tool_name}) -> {a.details}")
            
        self.txt.config(state=tk.NORMAL)
        self.txt.delete("1.0", tk.END)
        self.txt.insert("1.0", "\n".join(lines))
        self.txt.config(state=tk.DISABLED)
