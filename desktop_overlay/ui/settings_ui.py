"""Settings & Appearance Control Panel with Live Opacity, Cloud API Keys, and Provider Config."""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request
import json
import threading
from typing import Callable
from desktop_overlay.config import THEMES, OverlayConfig

PROVIDER_PRESETS = {
    "Local Ollama": {
        "provider": "Ollama",
        "url": "http://localhost:11434/api/generate",
        "model": "llama3.2:3b",
        "key_required": False
    },
    "Groq (Free & Fast)": {
        "provider": "Groq",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "llama-3.3-70b-versatile",
        "key_required": True
    },
    "Grok (xAI)": {
        "provider": "Grok",
        "url": "https://api.x.ai/v1/chat/completions",
        "model": "grok-2-latest",
        "key_required": True
    },
    "DeepSeek": {
        "provider": "DeepSeek",
        "url": "https://api.deepseek.com/v1/chat/completions",
        "model": "deepseek-chat",
        "key_required": True
    },
    "OpenAI": {
        "provider": "OpenAI",
        "url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4o-mini",
        "key_required": True
    },
    "OpenRouter": {
        "provider": "OpenRouter",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "model": "deepseek/deepseek-chat",
        "key_required": True
    },
    "Custom API": {
        "provider": "CustomAPI",
        "url": "https://api.example.com/v1/chat/completions",
        "model": "custom-model",
        "key_required": True
    }
}

class SettingsPanel(tk.Frame):
    """Interactive Settings panel for Live Opacity, Themes, Cloud API Keys, Model Providers, and Hotkeys."""
    
    def __init__(
        self,
        master: tk.Widget,
        config: OverlayConfig,
        on_opacity_change: Callable[[float], None],
        on_topmost_change: Callable[[bool], None],
        on_theme_change: Callable[[str], None],
        on_close: Callable[[], None],
        on_save_config: Optional[Callable[[], None]] = None,
        theme_name: str = "Light"
    ):
        self.t = THEMES.get(theme_name, THEMES["Light"])
        super().__init__(master, bg=self.t["bg"], padx=12, pady=10)
        self.config = config
        self.on_opacity_change = on_opacity_change
        self.on_topmost_change = on_topmost_change
        self.on_theme_change = on_theme_change
        self.on_close = on_close
        self.on_save_config = on_save_config
        
        # 1. HEADER WITH PROMINENT BACK BUTTON
        hdr = tk.Frame(self, bg=self.t["bg"])
        hdr.pack(fill=tk.X, pady=(0, 8))
        
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
            activebackground=self.t["accent"],
            cursor="hand2"
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Label(
            hdr,
            text="⚙️ Pop-up AI Settings & API Keys",
            bg=self.t["bg"],
            fg=self.t["accent"],
            font=("Segoe UI", 11, "bold")
        ).pack(side=tk.LEFT)
        
        tk.Button(
            hdr,
            text="✕ Close",
            command=self.on_close,
            bg=self.t["btn"],
            fg=self.t["btn_fg"],
            bd=0,
            padx=10,
            pady=3,
            font=("Segoe UI", 9, "bold"),
            activebackground=self.t["accent"],
            cursor="hand2"
        ).pack(side=tk.RIGHT)
        
        # 2. SCROLLABLE CONTAINER
        scroll_container = tk.Frame(self, bg=self.t["bg"])
        scroll_container.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(scroll_container, bg=self.t["bg"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(scroll_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg=self.t["bg"])
        
        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_win = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw", width=620)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Responsively resize inner frame to match canvas width
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_win, width=max(e.width - 6, 460)))
        
        # Mousewheel scrolling
        self._bind_mousewheel(self.canvas)
        self._bind_mousewheel(self.scroll_frame)
        
        # CARD 1: AI PROVIDER & CLOUD API KEYS
        card_ai = tk.Frame(self.scroll_frame, bg=self.t["card"], padx=14, pady=12, bd=1, relief=tk.FLAT)
        card_ai.pack(fill=tk.X, pady=(0, 10))
        self._bind_mousewheel(card_ai)
        
        tk.Label(card_ai, text="🤖 AI Engine & Provider", bg=self.t["card"], fg=self.t["accent"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        
        # Preset Provider Dropdown
        prov_row = tk.Frame(card_ai, bg=self.t["card"])
        prov_row.pack(fill=tk.X, pady=(6, 6))
        
        current_preset = "Local Ollama"
        for k, v in PROVIDER_PRESETS.items():
            if v["provider"] == self.config.ai_provider:
                current_preset = k
                break
                
        self.provider_var = tk.StringVar(value=current_preset)
        self.prov_menu = tk.OptionMenu(prov_row, self.provider_var, *PROVIDER_PRESETS.keys(), command=self._on_preset_change)
        self.prov_menu.config(bg=self.t["btn"], fg=self.t["btn_fg"], bd=0, font=("Segoe UI", 9, "bold"), activebackground=self.t["card"])
        self.prov_menu.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # API Key Field
        self.key_frame = tk.Frame(card_ai, bg=self.t["card"])
        self.key_frame.pack(fill=tk.X, pady=(4, 6))
        
        tk.Label(self.key_frame, text="🔑 API Key (Groq / Grok / DeepSeek / OpenAI / OpenRouter):", bg=self.t["card"], fg=self.t["fg"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        
        key_input_row = tk.Frame(self.key_frame, bg=self.t["card"])
        key_input_row.pack(fill=tk.X, pady=(2, 0))
        
        self.key_show = False
        self.key_entry = tk.Entry(
            key_input_row,
            show="*",
            bg=self.t["input_bg"],
            fg=self.t["fg"],
            insertbackground=self.t["fg"],
            font=("Consolas", 9),
            bd=0
        )
        self.key_entry.insert(0, self.config.api_key)
        self.key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6), ipady=3)
        
        self.btn_toggle_key = tk.Button(
            key_input_row,
            text="👁️ Show",
            command=self._toggle_key_visibility,
            bg=self.t["btn"],
            fg=self.t["btn_fg"],
            bd=0,
            padx=8,
            pady=2,
            font=("Segoe UI", 8),
            cursor="hand2"
        )
        self.btn_toggle_key.pack(side=tk.RIGHT)
        
        # API Base URL & Model Name
        url_row = tk.Frame(card_ai, bg=self.t["card"])
        url_row.pack(fill=tk.X, pady=(4, 6))
        
        tk.Label(url_row, text="Endpoint URL / Local Ollama URL:", bg=self.t["card"], fg=self.t["fg_dim"], font=("Segoe UI", 8)).pack(anchor="w")
        self.url_entry = tk.Entry(
            url_row,
            bg=self.t["input_bg"],
            fg=self.t["fg"],
            insertbackground=self.t["fg"],
            font=("Consolas", 8),
            bd=0
        )
        self.url_entry.insert(0, self.config.api_base_url if self.config.ai_provider != "Ollama" else self.config.ollama_url)
        self.url_entry.pack(fill=tk.X, pady=(2, 6), ipady=2)
        
        tk.Label(url_row, text="Model Name (e.g. llama3.2:3b, qwen2.5-coder:3b, llama-3.3-70b-versatile, grok-2-latest):", bg=self.t["card"], fg=self.t["fg_dim"], font=("Segoe UI", 8)).pack(anchor="w")
        self.model_entry = tk.Entry(
            url_row,
            bg=self.t["input_bg"],
            fg=self.t["fg"],
            insertbackground=self.t["fg"],
            font=("Consolas", 8),
            bd=0
        )
        self.model_entry.insert(0, self.config.api_model if self.config.ai_provider != "Ollama" else self.config.ollama_model)
        self.model_entry.pack(fill=tk.X, pady=(2, 6), ipady=2)
        
        # Action Buttons Row
        ai_btns = tk.Frame(card_ai, bg=self.t["card"])
        ai_btns.pack(fill=tk.X, pady=(4, 0))
        
        self.lbl_conn_status = tk.Label(ai_btns, text="", bg=self.t["card"], fg=self.t["fg_dim"], font=("Segoe UI", 8))
        self.lbl_conn_status.pack(side=tk.LEFT)
        
        tk.Button(
            ai_btns,
            text="⚡ Test Connection",
            command=self._test_connection,
            bg=self.t["btn"],
            fg=self.t["btn_fg"],
            bd=0,
            padx=10,
            pady=3,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2"
        ).pack(side=tk.RIGHT, padx=(6, 0))
        
        tk.Button(
            ai_btns,
            text="💾 Save API Settings",
            command=self._save_ai_settings,
            bg="#00AA44",
            fg="#FFFFFF",
            bd=0,
            padx=12,
            pady=3,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2"
        ).pack(side=tk.RIGHT)
        
        # CARD 2: APPEARANCE & WINDOW CONTROLS
        card_app = tk.Frame(self.scroll_frame, bg=self.t["card"], padx=14, pady=12, bd=1, relief=tk.FLAT)
        card_app.pack(fill=tk.X, pady=(0, 10))
        self._bind_mousewheel(card_app)
        
        tk.Label(card_app, text="🎨 Window Appearance & Opacity", bg=self.t["card"], fg=self.t["accent"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        
        # Opacity Slider
        op_frame = tk.Frame(card_app, bg=self.t["card"])
        op_frame.pack(fill=tk.X, pady=(6, 8))
        
        self.lbl_opacity = tk.Label(op_frame, text=f"{int(self.config.opacity * 100)}%", bg=self.t["card"], fg=self.t["accent"], font=("Segoe UI", 9, "bold"), width=5)
        self.lbl_opacity.pack(side=tk.RIGHT)
        
        self.opacity_scale = ttk.Scale(
            op_frame,
            from_=0.10,
            to=1.0,
            value=self.config.opacity,
            command=self._on_opacity_slider
        )
        self.opacity_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        
        # Always on Top & Theme Row
        opts_row = tk.Frame(card_app, bg=self.t["card"])
        opts_row.pack(fill=tk.X, pady=(2, 0))
        
        self.var_topmost = tk.BooleanVar(value=self.config.always_on_top)
        cb_top = tk.Checkbutton(
            opts_row,
            text="Keep Pop-up AI Always on Top",
            variable=self.var_topmost,
            command=self._on_topmost_toggle,
            bg=self.t["card"],
            fg=self.t["fg"],
            selectcolor=self.t["input_bg"],
            activebackground=self.t["card"],
            activeforeground=self.t["fg"],
            font=("Segoe UI", 9)
        )
        cb_top.pack(side=tk.LEFT)
        
        # Theme Selection
        theme_frame = tk.Frame(opts_row, bg=self.t["card"])
        theme_frame.pack(side=tk.RIGHT)
        
        self.theme_var = tk.StringVar(value=self.config.theme)
        for th in ["Light", "Dark"]:
            rb = tk.Radiobutton(
                theme_frame,
                text=f"{th} Mode",
                variable=self.theme_var,
                value=th,
                command=self._on_theme_select,
                bg=self.t["card"],
                fg=self.t["fg"],
                selectcolor=self.t["input_bg"],
                activebackground=self.t["card"],
                activeforeground=self.t["fg"],
                font=("Segoe UI", 9)
            )
            rb.pack(side=tk.LEFT, padx=(6, 0))
            
        # CARD 3: GLOBAL HOTKEYS & SHORTCUTS CHEAT SHEET
        card_hk = tk.Frame(self.scroll_frame, bg=self.t["card"], padx=14, pady=12, bd=1, relief=tk.FLAT)
        card_hk.pack(fill=tk.X, pady=(0, 10))
        self._bind_mousewheel(card_hk)
        
        tk.Label(card_hk, text="⌨️ Global Hotkeys & Shortcuts", bg=self.t["card"], fg=self.t["accent"], font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))
        
        shortcuts = [
            ("Ctrl + Z", "Summon / Hide Pop-up AI Assistant"),
            ("Ctrl + Shift + V", "Auto-Paste Clean Solution directly into Active App"),
            ("Ctrl + Shift + G", "Toggle Ghost Mode (Click-Through Transparent Overlay)"),
            ("F1", "Boss Key (Emergency Stealth Instant Hide)"),
            ("Ctrl + Shift + C", "Clean Invisible Watermarks & Homoglyphs from Clipboard"),
            ("Ctrl + Shift + N", "Auto-Type Next Block in Sequential Typer Queue"),
            ("Ctrl + Enter", "Send Prompt / Execute Sandbox Code"),
            ("Esc", "Cancel Snip & Solve Region Selection")
        ]
        
        for key, desc in shortcuts:
            row = tk.Frame(card_hk, bg=self.t["card"])
            row.pack(fill=tk.X, pady=2)
            self._bind_mousewheel(row)
            
            k_badge = tk.Label(row, text=f" {key} ", bg=self.t["btn"], fg=self.t["accent"], font=("Consolas", 8, "bold"), bd=1, relief=tk.FLAT)
            k_badge.pack(side=tk.LEFT)
            self._bind_mousewheel(k_badge)
            
            d_lbl = tk.Label(row, text=f" — {desc}", bg=self.t["card"], fg=self.t["fg_dim"], font=("Segoe UI", 8))
            d_lbl.pack(side=tk.LEFT, padx=(4, 0))
            self._bind_mousewheel(d_lbl)

    def _bind_mousewheel(self, widget: tk.Widget) -> None:
        def _on_wheel(e):
            self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        widget.bind("<MouseWheel>", _on_wheel)

    def _on_preset_change(self, preset_name: str) -> None:
        preset = PROVIDER_PRESETS.get(preset_name)
        if not preset: return
        prov = preset["provider"]
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, preset["url"])
        
        # Load saved model or default preset model
        saved_model = self.config.provider_models.get(prov, preset["model"])
        self.model_entry.delete(0, tk.END)
        self.model_entry.insert(0, saved_model)
        
        # Automatically load saved API key for this provider
        saved_key = self.config.get_api_key(prov)
        self.key_entry.delete(0, tk.END)
        self.key_entry.insert(0, saved_key)
        
        if prov == "Ollama":
            self.lbl_conn_status.config(text="Local Ollama selected (No API Key required)", fg=self.t["success"])
        else:
            status_text = f"✓ Saved {prov} API Key loaded" if saved_key else f"Please enter your {prov} API key above"
            status_fg = self.t["success"] if saved_key else self.t["accent"]
            self.lbl_conn_status.config(text=status_text, fg=status_fg)

    def _toggle_key_visibility(self) -> None:
        self.key_show = not self.key_show
        self.key_entry.config(show="" if self.key_show else "*")
        self.btn_toggle_key.config(text="🙈 Hide" if self.key_show else "👁️ Show")

    def _save_ai_settings(self) -> None:
        preset_name = self.provider_var.get()
        preset = PROVIDER_PRESETS.get(preset_name, PROVIDER_PRESETS["Local Ollama"])
        
        prov = preset["provider"]
        key = self.key_entry.get().strip()
        url = self.url_entry.get().strip()
        model = self.model_entry.get().strip()
        
        self.config.set_provider(prov, key=key, model=model, base_url=url)
        if self.on_save_config:
            self.on_save_config()
            
        self.lbl_conn_status.config(text=f"✓ Active Engine: {prov} ({model})", fg=self.t["success"])
        messagebox.showinfo(
            "Settings Saved",
            f"AI Engine successfully switched to:\n{prov} • Model: {model}\n\nYour active model has been updated on the main assistant toolbar!"
        )

    def _test_connection(self) -> None:
        preset_name = self.provider_var.get()
        preset = PROVIDER_PRESETS.get(preset_name, PROVIDER_PRESETS["Local Ollama"])
        prov = preset["provider"]
        
        self.lbl_conn_status.config(text="⏳ Testing connection...", fg=self.t["accent"])
        
        def _test():
            try:
                if prov == "Ollama":
                    url = self.url_entry.get().strip().replace("/api/generate", "/api/tags")
                    req = urllib.request.Request(url, headers={"User-Agent": "PopUpAI/1.0"})
                    with urllib.request.urlopen(req, timeout=4) as resp:
                        if resp.status == 200:
                            self.after(0, lambda: self.lbl_conn_status.config(text="✓ Local Ollama is connected & running!", fg=self.t["success"]))
                        else:
                            self.after(0, lambda: self.lbl_conn_status.config(text=f"⚠️ Ollama returned HTTP {resp.status}", fg=self.t["warning"]))
                else:
                    api_key = self.key_entry.get().strip()
                    if not api_key:
                        self.after(0, lambda: self.lbl_conn_status.config(text="⚠️ Please enter an API key to test", fg=self.t["error"]))
                        return
                    url = self.url_entry.get().strip()
                    model = self.model_entry.get().strip()
                    payload = {
                        "model": model,
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 5
                    }
                    data = json.dumps(payload).encode("utf-8")
                    req = urllib.request.Request(
                        url,
                        data=data,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {api_key}",
                            "User-Agent": "PopUpAI/1.0"
                        }
                    )
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        if resp.status == 200:
                            self.after(0, lambda: self.lbl_conn_status.config(text=f"✓ {prov} API connection verified!", fg=self.t["success"]))
                        else:
                            self.after(0, lambda: self.lbl_conn_status.config(text=f"⚠️ API returned HTTP {resp.status}", fg=self.t["warning"]))
            except Exception as e:
                err_str = str(e)
                if len(err_str) > 40: err_str = err_str[:37] + "..."
                self.after(0, lambda err=err_str: self.lbl_conn_status.config(text=f"✗ Error: {err}", fg=self.t["error"]))
                
        threading.Thread(target=_test, daemon=True).start()

    def _on_opacity_slider(self, val: str) -> None:
        f_val = float(val)
        self.lbl_opacity.config(text=f"{int(f_val * 100)}%")
        self.on_opacity_change(f_val)

    def _on_topmost_toggle(self) -> None:
        self.on_topmost_change(self.var_topmost.get())

    def _on_theme_select(self) -> None:
        self.on_theme_change(self.theme_var.get())

