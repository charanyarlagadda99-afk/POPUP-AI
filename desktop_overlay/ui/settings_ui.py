"""Settings & Appearance Control Panel with Live Opacity and Theme Sliders."""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Callable
from desktop_overlay.config import THEMES, OverlayConfig

class SettingsPanel(tk.Frame):
    """Interactive Settings panel for Live Opacity, Themes, Always on Top, and Model Preferences."""
    
    def __init__(
        self,
        master: tk.Widget,
        config: OverlayConfig,
        on_opacity_change: Callable[[float], None],
        on_topmost_change: Callable[[bool], None],
        on_theme_change: Callable[[str], None],
        on_close: Callable[[], None],
        theme_name: str = "Dark"
    ):
        self.t = THEMES.get(theme_name, THEMES["Dark"])
        super().__init__(master, bg=self.t["bg"], padx=15, pady=12)
        self.config = config
        self.on_opacity_change = on_opacity_change
        self.on_topmost_change = on_topmost_change
        self.on_theme_change = on_theme_change
        self.on_close = on_close
        
        # 1. HEADER
        hdr = tk.Frame(self, bg=self.t["bg"])
        hdr.pack(fill=tk.X, pady=(0, 12))
        tk.Label(hdr, text="⚙️ App Settings & Appearance", bg=self.t["bg"], fg=self.t["accent"], font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
        tk.Button(hdr, text="✕ Close", command=self.on_close, bg=self.t["btn"], fg=self.t["btn_fg"], bd=0, padx=8, pady=2, font=("Segoe UI", 9), activebackground=self.t["accent"]).pack(side=tk.RIGHT)
        
        # Scrollable / Organized Card
        card = tk.Frame(self, bg=self.t["card"], padx=14, pady=12, bd=1, relief=tk.FLAT)
        card.pack(fill=tk.BOTH, expand=True)
        
        # 2. OPACITY / TRANSPARENCY SLIDER
        tk.Label(card, text="Window Transparency & Opacity:", bg=self.t["card"], fg=self.t["fg"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        
        op_frame = tk.Frame(card, bg=self.t["card"])
        op_frame.pack(fill=tk.X, pady=(4, 12))
        
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
        
        # 3. WINDOW BEHAVIOR
        tk.Label(card, text="Window Behavior:", bg=self.t["card"], fg=self.t["fg"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        
        self.var_topmost = tk.BooleanVar(value=self.config.always_on_top)
        cb_top = tk.Checkbutton(
            card,
            text="Keep Assistant Always on Top",
            variable=self.var_topmost,
            command=self._on_topmost_toggle,
            bg=self.t["card"],
            fg=self.t["fg"],
            selectcolor=self.t["input_bg"],
            activebackground=self.t["card"],
            activeforeground=self.t["fg"],
            font=("Segoe UI", 9)
        )
        cb_top.pack(anchor="w", pady=(4, 12))
        
        # 4. THEME SELECTION
        tk.Label(card, text="Color Theme:", bg=self.t["card"], fg=self.t["fg"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        
        theme_frame = tk.Frame(card, bg=self.t["card"])
        theme_frame.pack(fill=tk.X, pady=(4, 12))
        
        self.theme_var = tk.StringVar(value=self.config.theme)
        for th in ["Dark", "Light"]:
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
            rb.pack(side=tk.LEFT, padx=(0, 15))
            
        # 5. OLLAMA SERVER & MODEL
        tk.Label(card, text="Ollama Endpoint URL:", bg=self.t["card"], fg=self.t["fg"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.entry_url = tk.Entry(card, bg=self.t["input_bg"], fg=self.t["fg"], insertbackground=self.t["fg"], font=("Consolas", 9), bd=0)
        self.entry_url.insert(0, self.config.ollama_url)
        self.entry_url.pack(fill=tk.X, pady=(4, 12), ipady=3)
        self.entry_url.bind("<FocusOut>", lambda e: self._save_url())
        
        # Save Button
        tk.Button(card, text="💾 Save Preferences", command=self._save_all, bg=self.t["accent"], fg="#000000", bd=0, padx=12, pady=4, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(5, 0))

    def _on_opacity_slider(self, val: str) -> None:
        opacity = float(val)
        self.lbl_opacity.config(text=f"{int(opacity * 100)}%")
        self.config.opacity = opacity
        self.on_opacity_change(opacity)

    def _on_topmost_toggle(self) -> None:
        top = self.var_topmost.get()
        self.config.always_on_top = top
        self.config.save()
        self.on_topmost_change(top)

    def _on_theme_select(self) -> None:
        th = self.theme_var.get()
        self.config.theme = th
        self.config.save()
        self.on_theme_change(th)

    def _save_url(self) -> None:
        url = self.entry_url.get().strip()
        if url:
            self.config.ollama_url = url
            self.config.save()

    def _save_all(self) -> None:
        self._save_url()
        self.config.save()
        self.on_close()
