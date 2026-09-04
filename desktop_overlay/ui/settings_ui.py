"""Settings & Appearance Control Panel with Live Opacity, Cloud API Keys, and Provider Config."""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable
from desktop_overlay.config import THEMES, OverlayConfig

PROVIDER_PRESETS = {
    "Local Ollama": {
        "provider": "Ollama",
        "url": "http://localhost:11434/api/generate",
        "model": "phi3:latest",
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
    """Interactive Settings panel for Live Opacity, Themes, Cloud API Keys, and Model Providers."""
    
    def __init__(
        self,
        master: tk.Widget,
        config: OverlayConfig,
        on_opacity_change: Callable[[float], None],
        on_topmost_change: Callable[[bool], None],
        on_theme_change: Callable[[str], None],
        on_close: Callable[[], None],
        theme_name: str = "Light"
    ):
        self.t = THEMES.get(theme_name, THEMES["Light"])
        super().__init__(master, bg=self.t["bg"], padx=12, pady=10)
        self.config = config
        self.on_opacity_change = on_opacity_change
        self.on_topmost_change = on_topmost_change
        self.on_theme_change = on_theme_change
        self.on_close = on_close
        
        # 1. HEADER
        hdr = tk.Frame(self, bg=self.t["bg"])
        hdr.pack(fill=tk.X, pady=(0, 8))
        tk.Label(hdr, text="⚙️ Pop-up AI Settings & API Keys", bg=self.t["bg"], fg=self.t["accent"], font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        tk.Button(hdr, text="✕ Close", command=self.on_close, bg=self.t["btn"], fg=self.t["btn_fg"], bd=0, padx=8, pady=2, font=("Segoe UI", 8, "bold"), activebackground=self.t["accent"], cursor="hand2").pack(side=tk.RIGHT)
        
        # Scrollable container for settings
        canvas = tk.Canvas(self, bg=self.t["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=self.t["bg"])
        
        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_win = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.bind("<Configure>", lambda e: canvas.itemconfig(canvas_win, width=canvas.winfo_width()))
        
        # CARD 1: AI PROVIDER & CLOUD API KEYS
        card_ai = tk.Frame(scroll_frame, bg=self.t["card"], padx=12, pady=10, bd=1, relief=tk.FLAT)
        card_ai.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(card_ai, text="🤖 AI Engine & Provider:", bg=self.t["card"], fg=self.t["accent"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        
        # Preset Provider Dropdown
        prov_row = tk.Frame(card_ai, bg=self.t["card"])
        prov_row.pack(fill=tk.X, pady=(4, 6))
        
        current_preset = "Local Ollama"
        for k, v in PROVIDER_PRESETS.items():
            if v["provider"] == self.config.ai_provider:
                current_preset = k
                break
                
        self.provider_var = tk.StringVar(value=current_preset)
        self.prov_menu = tk.OptionMenu(prov_row, self.provider_var, *PROVIDER_PRESETS.keys(), command=self._on_preset_change)
        self.prov_menu.config(bg=self.t["btn"], fg=self.t["btn_fg"], bd=0, font=("Segoe UI", 9, "bold"))
        self.prov_menu.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # API Key Field
        self.key_frame = tk.Frame(card_ai, bg=self.t["card"])
        self.key_frame.pack(fill=tk.X, pady=(4, 6))
        
        tk.Label(self.key_frame, text="🔑 API Key (Grok / Groq / DeepSeek / OpenAI):", bg=self.t["card"], fg=self.t["fg"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
        
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
        self.key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        
        self.btn_toggle_key = tk.Button(
            key_input_row,
            text="👁️ Show",
            command=self._toggle_key_visibility,
            bg=self.t["btn"],
            fg=self.t["btn_fg"],
            bd=0,
            padx=6,
            pady=1,
            font=("Segoe UI", 8)
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
        self.url_entry.pack(fill=tk.X, pady=(2, 4))
        
        tk.Label(url_row, text="Model Name (e.g. llama-3.3-70b-versatile, grok-2-latest, deepseek-chat):", bg=self.t["card"], fg=self.t["fg_dim"], font=("Segoe UI", 8)).pack(anchor="w")
        self.model_entry = tk.Entry(
            url_row,
            bg=self.t["input_bg"],
            fg=self.t["fg"],
            insertbackground=self.t["fg"],
            font=("Consolas", 8),
            bd=0
        )
        self.model_entry.insert(0, self.config.api_model if self.config.ai_provider != "Ollama" else self.config.ollama_model)
        self.model_entry.pack(fill=tk.X, pady=(2, 4))
        
        tk.Button(
            card_ai,
            text="💾 Save API Settings",
            command=self._save_ai_settings,
            bg="#00AA44",
            fg="#FFFFFF",
            bd=0,
            padx=10,
            pady=3,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2"
        ).pack(anchor="e", pady=(4, 0))
        
        # CARD 2: APPEARANCE & WINDOW CONTROLS
        card_app = tk.Frame(scroll_frame, bg=self.t["card"], padx=12, pady=10, bd=1, relief=tk.FLAT)
        card_app.pack(fill=tk.X)
        
        tk.Label(card_app, text="🎨 Window Appearance & Opacity:", bg=self.t["card"], fg=self.t["accent"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        
        # Opacity Slider
        op_frame = tk.Frame(card_app, bg=self.t["card"])
        op_frame.pack(fill=tk.X, pady=(4, 8))
        
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
        
        # Always on Top
        self.var_topmost = tk.BooleanVar(value=self.config.always_on_top)
        cb_top = tk.Checkbutton(
            card_app,
            text="Keep Pop-up AI Always on Top",
            variable=self.var_topmost,
            command=self._on_topmost_toggle,
            bg=self.t["card"],
            fg=self.t["fg"],
            selectcolor=self.t["input_bg"],
            activebackground=self.t["card"],
            activeforeground=self.t["fg"],
            font=("Segoe UI", 8)
        )
        cb_top.pack(anchor="w", pady=(2, 6))
        
        # Theme Selection
        theme_frame = tk.Frame(card_app, bg=self.t["card"])
        theme_frame.pack(fill=tk.X, pady=(2, 0))
        
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
                font=("Segoe UI", 8)
            )
            rb.pack(side=tk.LEFT, padx=(0, 15))

    def _on_preset_change(self, preset_name: str) -> None:
        preset = PROVIDER_PRESETS.get(preset_name)
        if not preset: return
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, preset["url"])
        self.model_entry.delete(0, tk.END)
        self.model_entry.insert(0, preset["model"])

    def _toggle_key_visibility(self) -> None:
        self.key_show = not self.key_show
        self.key_entry.config(show="" if self.key_show else "*")
        self.btn_toggle_key.config(text="🙈 Hide" if self.key_show else "👁️ Show")

    def _save_ai_settings(self) -> None:
        preset_name = self.provider_var.get()
        preset = PROVIDER_PRESETS.get(preset_name, PROVIDER_PRESETS["Local Ollama"])
        
        prov = preset["provider"]
        self.config.ai_provider = prov
        self.config.api_key = self.key_entry.get().strip()
        
        if prov == "Ollama":
            self.config.ollama_url = self.url_entry.get().strip()
            self.config.ollama_model = self.model_entry.get().strip()
        else:
            self.config.api_base_url = self.url_entry.get().strip()
            self.config.api_model = self.model_entry.get().strip()
            
        self.config.save()
        messagebox.showinfo("Saved", f"AI Provider set to '{prov}' with model '{self.model_entry.get().strip()}'!")

    def _on_opacity_slider(self, val: str) -> None:
        f_val = float(val)
        self.lbl_opacity.config(text=f"{int(f_val * 100)}%")
        self.on_opacity_change(f_val)

    def _on_topmost_toggle(self) -> None:
        self.on_topmost_change(self.var_topmost.get())

    def _on_theme_select(self) -> None:
        self.on_theme_change(self.theme_var.get())
