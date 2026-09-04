"""Permission Center & Privacy Controls View."""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Callable
from desktop_overlay.config import THEMES
from desktop_overlay.security.permissions import PermissionManager, PermissionType, PrivacyMode

class PermissionCenter(tk.Frame):
    """Interactive permission dashboard with privacy mode selector."""
    
    def __init__(self, master, permissions: PermissionManager, on_close: Callable[[], None], theme_name: str = "Dark"):
        self.t = THEMES.get(theme_name, THEMES["Dark"])
        super().__init__(master, bg=self.t["bg"], padx=15, pady=15)
        self.permissions = permissions
        self.on_close = on_close
        
        # Header
        hdr = tk.Frame(self, bg=self.t["bg"])
        hdr.pack(fill=tk.X, pady=(0, 15))
        
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
        
        tk.Label(hdr, text="🔒 Privacy & Permission Center", bg=self.t["bg"], fg=self.t["accent"], font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
        tk.Button(hdr, text="✕ Close", command=self.on_close, bg=self.t["btn"], fg=self.t["btn_fg"], bd=0, padx=8, pady=2, cursor="hand2").pack(side=tk.RIGHT)
        
        # Privacy Mode Selector Card
        mode_card = tk.Frame(self, bg=self.t["card"], padx=12, pady=10)
        mode_card.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(mode_card, text="Active Privacy Profile:", bg=self.t["card"], fg=self.t["fg"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        
        mode_btns = tk.Frame(mode_card, bg=self.t["card"])
        mode_btns.pack(fill=tk.X, pady=(6, 0))
        
        for mode in PrivacyMode:
            btn = tk.Button(
                mode_btns,
                text=mode.value,
                command=lambda m=mode: self._set_mode(m),
                bg=self.t["accent"] if self.permissions.config.privacy_mode == mode.value else self.t["btn"],
                fg="#000000" if self.permissions.config.privacy_mode == mode.value else self.t["btn_fg"],
                bd=0,
                padx=8,
                pady=3,
                font=("Segoe UI", 9)
            )
            btn.pack(side=tk.LEFT, padx=(0, 6))
            
        # Granular Permission Toggles
        perm_card = tk.Frame(self, bg=self.t["card"], padx=12, pady=10)
        perm_card.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(perm_card, text="Granular Permissions:", bg=self.t["card"], fg=self.t["fg"], font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 8))
        
        self.check_vars = {}
        for p_type, info in self.permissions.get_all_status().items():
            row = tk.Frame(perm_card, bg=self.t["card"])
            row.pack(fill=tk.X, pady=3)
            
            var = tk.BooleanVar(value=info["granted"])
            self.check_vars[p_type] = var
            
            cb = tk.Checkbutton(
                row,
                text=info["name"],
                variable=var,
                command=lambda pt=p_type: self._toggle_perm(pt),
                bg=self.t["card"],
                fg=self.t["fg"],
                selectcolor=self.t["input_bg"],
                activebackground=self.t["card"],
                activeforeground=self.t["fg"],
                font=("Segoe UI", 9, "bold")
            )
            cb.pack(side=tk.LEFT)
            
            desc_lbl = tk.Label(row, text=f"({info['description']})", bg=self.t["card"], fg=self.t["fg_dim"], font=("Segoe UI", 8))
            desc_lbl.pack(side=tk.LEFT, padx=(5, 0))

    def _set_mode(self, mode: PrivacyMode) -> None:
        self.permissions.apply_privacy_mode(mode)
        # Refresh checkboxes
        for p_type, info in self.permissions.get_all_status().items():
            if p_type in self.check_vars:
                self.check_vars[p_type].set(info["granted"])

    def _toggle_perm(self, p_type_str: str) -> None:
        try:
            pt = PermissionType(p_type_str)
            val = self.check_vars[p_type_str].get()
            self.permissions.set_permission(pt, val)
        except Exception as e:
            print("[PermissionUI] Error toggling:", e)
