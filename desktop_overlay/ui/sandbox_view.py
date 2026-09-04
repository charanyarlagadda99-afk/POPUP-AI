"""In-App Code Runner Sandbox UI."""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Callable, Optional
from desktop_overlay.config import THEMES
from desktop_overlay.sandbox.code_runner import CodeSandboxEngine

class SandboxView(tk.Frame):
    """Interactive Code Runner Sandbox with live stdout/stderr console and execution metrics."""
    
    def __init__(
        self,
        master,
        on_back: Callable[[], None],
        theme_name: str = "Light"
    ):
        self.t = THEMES.get(theme_name, THEMES["Light"])
        super().__init__(master, bg=self.t["bg"], padx=12, pady=12)
        self.on_back = on_back
        self.runner = CodeSandboxEngine()
        self.is_running = False
        
        # 1. HEADER
        hdr = tk.Frame(self, bg=self.t["bg"])
        hdr.pack(fill=tk.X, pady=(0, 8))
        
        tk.Button(
            hdr,
            text="← Back to Assistant",
            command=self.on_back,
            bg=self.t["btn"],
            fg=self.t["btn_fg"],
            bd=0,
            padx=8,
            pady=3,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2"
        ).pack(side=tk.LEFT)
        
        tk.Label(
            hdr,
            text="🧩 In-App Code Sandbox (Python)",
            bg=self.t["bg"],
            fg=self.t["fg"],
            font=("Segoe UI", 11, "bold")
        ).pack(side=tk.LEFT, padx=12)
        
        self.lbl_metric = tk.Label(
            hdr,
            text="Ready",
            bg=self.t["card"],
            fg=self.t["fg_dim"],
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=2
        )
        self.lbl_metric.pack(side=tk.RIGHT, padx=4)
        
        # 2. CODE EDITOR SECTION
        ed_frame = tk.Frame(self, bg=self.t["card"], padx=8, pady=6)
        ed_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        
        ed_hdr = tk.Frame(ed_frame, bg=self.t["card"])
        ed_hdr.pack(fill=tk.X, pady=(0, 4))
        
        tk.Label(
            ed_hdr,
            text="📝 Python Code Editor (Ctrl+Enter to Run):",
            bg=self.t["card"],
            fg=self.t["accent"],
            font=("Segoe UI", 9, "bold")
        ).pack(side=tk.LEFT)
        
        tk.Button(
            ed_hdr,
            text="📋 Paste from Clipboard",
            command=self._paste_clipboard,
            bg=self.t["btn"],
            fg=self.t["btn_fg"],
            bd=0,
            padx=6,
            pady=1,
            font=("Segoe UI", 8),
            cursor="hand2"
        ).pack(side=tk.RIGHT, padx=4)
        
        tk.Button(
            ed_hdr,
            text="🗑️ Clear",
            command=lambda: self.txt_code.delete("1.0", tk.END),
            bg=self.t["btn"],
            fg=self.t["btn_fg"],
            bd=0,
            padx=6,
            pady=1,
            font=("Segoe UI", 8),
            cursor="hand2"
        ).pack(side=tk.RIGHT)
        
        self.txt_code = tk.Text(
            ed_frame,
            wrap=tk.NONE,
            bg=self.t["input_bg"],
            fg=self.t["fg"],
            insertbackground=self.t["fg"],
            font=("Consolas", 10),
            bd=0,
            padx=8,
            pady=6,
            height=10
        )
        self.txt_code.pack(fill=tk.BOTH, expand=True)
        self.txt_code.bind("<Control-Return>", lambda e: self.run_code())
        
        # Sample code by default
        default_code = (
            "# Test Python algorithms or calculations here\n"
            "def solve():\n"
            "    data = [x**2 for x in range(1, 11)]\n"
            "    print('Computed squares:', data)\n"
            "    return sum(data)\n\n"
            "print('Result:', solve())\n"
        )
        self.txt_code.insert("1.0", default_code)
        
        # 3. ACTION BAR
        btn_bar = tk.Frame(self, bg=self.t["bg"])
        btn_bar.pack(fill=tk.X, pady=(0, 6))
        
        self.btn_run = tk.Button(
            btn_bar,
            text="▶ Run Code (Ctrl+Enter)",
            command=self.run_code,
            bg="#00AA44",
            fg="#FFFFFF",
            bd=0,
            padx=14,
            pady=5,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2"
        )
        self.btn_run.pack(side=tk.LEFT)
        
        # 4. TERMINAL OUTPUT SECTION
        out_frame = tk.Frame(self, bg=self.t["card"], padx=8, pady=6)
        out_frame.pack(fill=tk.BOTH, expand=True)
        
        out_hdr = tk.Frame(out_frame, bg=self.t["card"])
        out_hdr.pack(fill=tk.X, pady=(0, 4))
        
        tk.Label(
            out_hdr,
            text="💻 Execution Terminal Output:",
            bg=self.t["card"],
            fg=self.t["success"],
            font=("Segoe UI", 9, "bold")
        ).pack(side=tk.LEFT)
        
        self.txt_output = tk.Text(
            out_frame,
            wrap=tk.WORD,
            bg="#1E1E1E",
            fg="#00FF66",
            insertbackground="#FFFFFF",
            font=("Consolas", 9),
            bd=0,
            padx=8,
            pady=6,
            height=6
        )
        self.txt_output.pack(fill=tk.BOTH, expand=True)

    def load_code(self, code_text: str) -> None:
        """Loads code string into editor."""
        self.txt_code.delete("1.0", tk.END)
        self.txt_code.insert("1.0", code_text.strip())
        self.txt_output.delete("1.0", tk.END)
        self.lbl_metric.config(text="Code Loaded", fg=self.t["accent"])

    def run_code(self) -> None:
        """Runs the code in editor using sandbox subprocess."""
        if self.is_running: return
        code = self.txt_code.get("1.0", tk.END).strip()
        if not code: return
        
        self.is_running = True
        self.btn_run.config(text="⏳ Running...", state=tk.DISABLED, bg=self.t["btn"])
        self.txt_output.delete("1.0", tk.END)
        self.txt_output.insert("1.0", "⏳ Executing in sandbox environment...\n")
        self.lbl_metric.config(text="Executing...", fg=self.t["accent"])
        
        def _exec():
            res = self.runner.run_python(code, timeout_sec=10)
            self.after(0, lambda: self._on_exec_done(res))
            
        threading.Thread(target=_exec, daemon=True).start()

    def _on_exec_done(self, res) -> None:
        self.is_running = False
        self.btn_run.config(text="▶ Run Code (Ctrl+Enter)", state=tk.NORMAL, bg="#00AA44")
        self.txt_output.delete("1.0", tk.END)
        
        if res.stdout:
            self.txt_output.insert(tk.END, res.stdout)
        if res.stderr:
            self.txt_output.insert(tk.END, f"\n[Errors / Warnings]:\n{res.stderr}")
        if not res.stdout and not res.stderr:
            self.txt_output.insert(tk.END, "✓ Script finished with no output.")
            
        status = "✓ Success" if res.success else f"✗ Error (code {res.exit_code})"
        status_fg = "#00FF66" if res.success else "#FF5555"
        self.lbl_metric.config(text=f"{status} • {res.duration_ms}ms", fg=status_fg)

    def _paste_clipboard(self) -> None:
        try:
            txt = self.clipboard_get()
            if txt:
                self.load_code(txt)
        except Exception:
            pass
