"""Expanded Conversational Assistant View with Code Sandbox, Auto-Paste, Ghost Mode, and History."""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
from desktop_overlay.config import THEMES, OverlayConfig
from desktop_overlay.context.context_engine import ApplicationContext
from desktop_overlay.sandbox.code_runner import CodeSandboxEngine

class ExpandedAssistantView(tk.Frame):
    """Full desktop AI assistant with live context tags, streaming output, code runner sandbox, auto-paste, and history."""
    
    def __init__(
        self,
        master,
        config: OverlayConfig,
        on_send_prompt: Callable[[str, bool], None],
        on_scan_solve: Callable[[], None],
        on_snip_solve: Callable[[], None],
        on_stop: Callable[[], None],
        on_run_agent: Callable[[str], None],
        on_auto_paste: Callable[[], None],
        on_run_sandbox: Callable[[str], None],
        on_toggle_ghost: Callable[[], None],
        on_open_history: Callable[[], None],
        on_open_sandbox: Callable[[], None],
        on_open_palette: Callable[[], None],
        on_open_settings: Callable[[], None],
        on_open_permissions: Callable[[], None],
        on_open_diagnostics: Callable[[], None],
        on_open_editor: Callable[[], None],
        on_engine_change: Optional[Callable[[], None]] = None,
        theme_name: str = "Light"
    ):
        self.t = THEMES.get(theme_name, THEMES["Light"])
        super().__init__(master, bg=self.t["bg"], padx=10, pady=10)
        self.config = config
        self.on_send_prompt = on_send_prompt
        self.on_scan_solve = on_scan_solve
        self.on_snip_solve = on_snip_solve
        self.on_stop = on_stop
        self.on_run_agent = on_run_agent
        self.on_auto_paste = on_auto_paste
        self.on_run_sandbox = on_run_sandbox
        self.on_toggle_ghost = on_toggle_ghost
        self.on_open_history = on_open_history
        self.on_open_sandbox = on_open_sandbox
        self.on_open_palette = on_open_palette
        self.on_open_settings = on_open_settings
        self.on_open_permissions = on_open_permissions
        self.on_open_diagnostics = on_open_diagnostics
        self.on_open_editor = on_open_editor
        self.on_engine_change = on_engine_change
        self.is_generating = False
        
        # 1. TOP STATUS & CONTEXT TOOLBAR
        top_bar = tk.Frame(self, bg=self.t["bg"])
        top_bar.pack(side=tk.TOP, fill=tk.X, pady=(0, 6))
        
        # Engine Status Badge
        is_cloud = (self.config.ai_provider != "Ollama" and self.config.api_key.strip())
        badge_text = f"☁️ {self.config.ai_provider}" if is_cloud else "💻 Local"
        badge_bg = "#00AA44" if is_cloud else self.t["btn"]
        badge_fg = "#FFFFFF" if is_cloud else self.t["fg_dim"]
        
        self.lbl_badge = tk.Label(
            top_bar,
            text=badge_text,
            bg=badge_bg,
            fg=badge_fg,
            font=("Segoe UI", 8, "bold"),
            padx=6,
            pady=2,
            bd=0
        )
        self.lbl_badge.pack(side=tk.LEFT, padx=(0, 4))
        
        # Unified Model & Provider Selector
        self.model_var = tk.StringVar(value=self._get_current_model_label())
        choices = self._build_model_choices()
        self.model_menu = tk.OptionMenu(top_bar, self.model_var, *choices, command=self._on_model_select)
        self.model_menu.config(bg=self.t["btn"], fg=self.t["btn_fg"], bd=0, highlightthickness=0, font=("Segoe UI", 8, "bold"), activebackground=self.t["card"])
        self.model_menu.pack(side=tk.LEFT, padx=(0, 2))
        
        self.btn_refresh = tk.Button(
            top_bar,
            text="🔄",
            command=self.refresh_models,
            bg=self.t["btn"],
            fg=self.t["btn_fg"],
            bd=0,
            padx=4,
            pady=1,
            font=("Segoe UI", 8),
            cursor="hand2"
        )
        self.btn_refresh.pack(side=tk.LEFT, padx=(0, 6))
        
        # Quick Navigation Buttons Bar (Pill style)
        tk.Button(top_bar, text="⚙️ Settings", command=self.on_open_settings, bg=self.t["btn"], fg=self.t["btn_fg"], bd=0, padx=5, pady=2, font=("Segoe UI", 8), activebackground=self.t["accent"]).pack(side=tk.RIGHT, padx=1)
        tk.Button(top_bar, text="🔍 Actions", command=self.on_open_palette, bg=self.t["btn"], fg=self.t["btn_fg"], bd=0, padx=5, pady=2, font=("Segoe UI", 8), activebackground=self.t["accent"]).pack(side=tk.RIGHT, padx=1)
        tk.Button(top_bar, text="📜 History", command=self.on_open_history, bg=self.t["btn"], fg=self.t["btn_fg"], bd=0, padx=5, pady=2, font=("Segoe UI", 8, "bold"), activebackground=self.t["accent"]).pack(side=tk.RIGHT, padx=1)
        tk.Button(top_bar, text="🧩 Sandbox", command=self.on_open_sandbox, bg=self.t["btn"], fg=self.t["btn_fg"], bd=0, padx=5, pady=2, font=("Segoe UI", 8, "bold"), activebackground=self.t["accent"]).pack(side=tk.RIGHT, padx=1)
        tk.Button(top_bar, text="📝 Typer", command=self.on_open_editor, bg=self.t["btn"], fg=self.t["btn_fg"], bd=0, padx=5, pady=2, font=("Segoe UI", 8), activebackground=self.t["accent"]).pack(side=tk.RIGHT, padx=1)
        tk.Button(top_bar, text="🪟 Ghost", command=self.on_toggle_ghost, bg=self.t["btn"], fg=self.t["btn_fg"], bd=0, padx=5, pady=2, font=("Segoe UI", 8), activebackground=self.t["accent"]).pack(side=tk.RIGHT, padx=1)
        
        # 2. INPUT AREA & FIXED ACTION BAR (Packed at BOTTOM first to guarantee visibility)
        f_in = tk.Frame(self, bg=self.t["card"], bd=1, relief=tk.FLAT)
        f_in.pack(side=tk.BOTTOM, fill=tk.X)
        
        hdr_in = tk.Frame(f_in, bg=self.t["card"], padx=6, pady=4)
        hdr_in.pack(fill=tk.X)
        tk.Label(hdr_in, text="💬 Ask or Instruct (Ctrl+Enter to send):", bg=self.t["card"], fg=self.t["accent"], font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT)
        
        self.var_attach_screen = tk.BooleanVar(value=False)
        self.cb_screen = tk.Checkbutton(
            hdr_in,
            text="📷 Attach Screen Context",
            variable=self.var_attach_screen,
            bg=self.t["card"],
            fg=self.t["fg_dim"],
            selectcolor=self.t["input_bg"],
            activebackground=self.t["card"],
            activeforeground=self.t["fg"],
            font=("Segoe UI", 8)
        )
        self.cb_screen.pack(side=tk.RIGHT, padx=4)
        
        self.txt_input = tk.Text(
            f_in,
            height=3,
            wrap=tk.WORD,
            bg=self.t["input_bg"],
            fg=self.t["fg"],
            insertbackground=self.t["fg"],
            font=("Segoe UI", 10),
            bd=0,
            padx=8,
            pady=6
        )
        self.txt_input.pack(fill=tk.X, padx=6, pady=(0, 4))
        self.txt_input.bind("<Control-Return>", lambda e: self._submit_prompt())
        
        # FIXED ACTION BUTTONS BAR (ALWAYS VISIBLE)
        self.btn_bar = tk.Frame(f_in, bg=self.t["card"], padx=6, pady=5)
        self.btn_bar.pack(fill=tk.X)
        
        # 🎯 SNIP & SOLVE QUESTION
        self.btn_snip = tk.Button(
            self.btn_bar,
            text="🎯 Snip & Solve",
            command=self._submit_snip_solve,
            bg="#00AA44",
            fg="#FFFFFF",
            bd=0,
            padx=10,
            pady=4,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2"
        )
        self.btn_snip.pack(side=tk.LEFT, padx=(0, 5))
        
        # 📸 FULL SCREEN SCAN & SOLVE
        self.btn_scan = tk.Button(
            self.btn_bar,
            text="📸 Scan Screen",
            command=self._submit_scan_solve,
            bg="#268BD2",
            fg="#FFFFFF",
            bd=0,
            padx=9,
            pady=4,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2"
        )
        self.btn_scan.pack(side=tk.LEFT, padx=(0, 5))
        
        # ⚡ AUTO-PASTE SOLUTION (Ctrl+Shift+V)
        self.btn_auto_paste = tk.Button(
            self.btn_bar,
            text="⚡ Auto-Paste (Ctrl+Shift+V)",
            command=self.on_auto_paste,
            bg=self.t["btn"],
            fg=self.t["btn_fg"],
            bd=0,
            padx=8,
            pady=4,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2"
        )
        self.btn_auto_paste.pack(side=tk.LEFT)
        
        # Stop Generation Button (Hidden until AI starts generating)
        self.btn_stop = tk.Button(
            self.btn_bar,
            text="🛑 Stop Answer",
            command=self.on_stop,
            bg="#D20F39",
            fg="#FFFFFF",
            bd=0,
            padx=12,
            pady=4,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2"
        )
        
        # Send Prompt Button
        self.btn_send = tk.Button(
            self.btn_bar,
            text="🚀 Send Prompt",
            command=self._submit_prompt,
            bg=self.t["accent"],
            fg="#000000",
            bd=0,
            padx=14,
            pady=4,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2"
        )
        self.btn_send.pack(side=tk.RIGHT)
        
        # 3. OUTPUT RESPONSE DISPLAY (Takes all remaining middle space)
        f_out = tk.Frame(self, bg=self.t["card"], bd=1, relief=tk.FLAT)
        f_out.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 6))
        
        hdr_out = tk.Frame(f_out, bg=self.t["card"], padx=6, pady=4)
        hdr_out.pack(fill=tk.X)
        tk.Label(hdr_out, text="✦ AI Response & Solutions", bg=self.t["card"], fg=self.t["success"], font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        
        self.btn_copy_resp = tk.Button(hdr_out, text="📋 Copy", command=self.copy_output, bg=self.t["btn"], fg=self.t["btn_fg"], bd=0, padx=6, pady=1, font=("Segoe UI", 8))
        self.btn_copy_resp.pack(side=tk.RIGHT, padx=(2, 0))
        
        self.btn_run_sandbox_inline = tk.Button(
            hdr_out,
            text="▶ Run in Sandbox",
            command=self._run_code_in_sandbox,
            bg="#00AA44",
            fg="#FFFFFF",
            bd=0,
            padx=8,
            pady=1,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2"
        )
        self.btn_run_sandbox_inline.pack(side=tk.RIGHT, padx=4)
        
        self.txt_output = tk.Text(
            f_out,
            wrap=tk.WORD,
            bg=self.t["output_bg"],
            fg=self.t["fg"],
            insertbackground=self.t["fg"],
            font=("Segoe UI", 10),
            bd=0,
            padx=10,
            pady=8,
            exportselection=False
        )
        self.txt_output.pack(fill=tk.BOTH, expand=True)

    def set_generating(self, generating: bool) -> None:
        self.is_generating = generating
        if generating:
            self.btn_send.pack_forget()
            self.btn_stop.pack(side=tk.RIGHT)
            self.btn_snip.config(state=tk.DISABLED)
            self.btn_scan.config(state=tk.DISABLED)
            self.btn_auto_paste.config(state=tk.DISABLED)
        else:
            self.btn_stop.pack_forget()
            self.btn_send.pack(side=tk.RIGHT)
            self.btn_send.config(text="🚀 Send Prompt", state=tk.NORMAL)
            self.btn_snip.config(state=tk.NORMAL)
            self.btn_scan.config(state=tk.NORMAL)
            self.btn_auto_paste.config(state=tk.NORMAL)

    def set_output(self, text: str) -> None:
        self.txt_output.delete("1.0", tk.END)
        self.txt_output.insert("1.0", text)
        self.txt_output.see(tk.END)

    def append_output_stream(self, token: str) -> None:
        self.txt_output.insert(tk.END, token)
        self.txt_output.see(tk.END)

    def get_output_text(self) -> str:
        return self.txt_output.get("1.0", tk.END).strip()

    def copy_output(self) -> None:
        try:
            txt = self.get_output_text()
            if txt:
                self.clipboard_clear()
                self.clipboard_append(txt)
                self.btn_copy_resp.config(text="✓ Copied!")
                self.after(1500, lambda: self.btn_copy_resp.config(text="📋 Copy"))
        except Exception:
            pass

    def _run_code_in_sandbox(self) -> None:
        txt = self.get_output_text()
        clean_code = CodeSandboxEngine.extract_clean_code_or_answer(txt)
        self.on_run_sandbox(clean_code)

    def focus_input(self) -> None:
        self.txt_input.focus_set()
        self.txt_input.mark_set(tk.INSERT, tk.END)

    def _submit_prompt(self) -> None:
        if self.is_generating: return
        prompt = self.txt_input.get("1.0", tk.END).strip()
        if not prompt: return
        self.set_output("")
        self.set_generating(True)
        self.on_send_prompt(prompt, self.var_attach_screen.get())

    def _submit_snip_solve(self) -> None:
        if self.is_generating: return
        self.set_output("")
        self.on_snip_solve()

    def _submit_scan_solve(self) -> None:
        if self.is_generating: return
        self.set_output("")
        self.set_generating(True)
        self.on_scan_solve()

    def _build_model_choices(self) -> list[str]:
        choices = [
            "⚡ Grok (grok-beta)",
            "⚡ Groq (llama-3.3-70b-versatile)",
            "⚡ DeepSeek (deepseek-chat)",
            "⚡ OpenAI (gpt-4o-mini)",
        ]
        local_models = self.config.available_models or ["llama3.2:3b", "qwen2.5-coder:3b", "phi3:latest"]
        for m in local_models:
            choices.append(f"💻 {m}")
        return choices

    def _get_current_model_label(self) -> str:
        if self.config.ai_provider != "Ollama" and self.config.api_key.strip():
            return f"⚡ {self.config.ai_provider} ({self.config.api_model})"
        return f"💻 {self.config.ollama_model}"

    def _on_model_select(self, selection: str) -> None:
        if selection.startswith("⚡ Grok"):
            saved_key = self.config.get_api_key("Grok")
            self.config.set_provider("Grok", saved_key, "grok-beta", "https://api.x.ai/v1")
        elif selection.startswith("⚡ Groq"):
            saved_key = self.config.get_api_key("Groq")
            self.config.set_provider("Groq", saved_key, "llama-3.3-70b-versatile", "https://api.groq.com/openai/v1")
        elif selection.startswith("⚡ DeepSeek"):
            saved_key = self.config.get_api_key("DeepSeek")
            self.config.set_provider("DeepSeek", saved_key, "deepseek-chat", "https://api.deepseek.com")
        elif selection.startswith("⚡ OpenAI"):
            saved_key = self.config.get_api_key("OpenAI")
            self.config.set_provider("OpenAI", saved_key, "gpt-4o-mini", "https://api.openai.com/v1")
        elif selection.startswith("💻 "):
            model_name = selection.replace("💻 ", "").strip()
            self.config.set_provider("Ollama", "", model_name, "http://localhost:11434/api/generate")
            self.config.ollama_model = model_name
        self.config.save()
        self.refresh_engine_display()
        if self.on_engine_change:
            self.on_engine_change()

    def refresh_engine_display(self) -> None:
        """Updates the engine badge, selected model label, and dropdown menu choices."""
        is_cloud = (self.config.ai_provider != "Ollama" and self.config.api_key.strip())
        badge_text = f"☁️ {self.config.ai_provider}" if is_cloud else "💻 Local"
        badge_bg = "#00AA44" if is_cloud else self.t["btn"]
        badge_fg = "#FFFFFF" if is_cloud else self.t["fg_dim"]
        self.lbl_badge.config(text=badge_text, bg=badge_bg, fg=badge_fg)
        self.model_var.set(self._get_current_model_label())
        
        # Rebuild option menu
        menu = self.model_menu["menu"]
        menu.delete(0, "end")
        for choice in self._build_model_choices():
            menu.add_command(label=choice, command=lambda c=choice: self._on_model_select(c))

    def refresh_models(self) -> None:
        """Dynamically queries Ollama for newly downloaded models and updates dropdown menu."""
        from desktop_overlay.agent.llm_provider import LLMProvider
        installed = LLMProvider.get_installed_models()
        if installed:
            self.config.available_models = installed
            if self.config.ai_provider == "Ollama" and self.config.ollama_model not in installed:
                self.config.ollama_model = installed[0]
            self.config.save()
            self.refresh_engine_display()
            self.set_output(f"✓ Model list refreshed from Ollama:\n{', '.join(installed)}")
        else:
            self.refresh_engine_display()
