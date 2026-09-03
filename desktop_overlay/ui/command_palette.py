"""Command Palette for fast keyboard-driven AI actions."""

from __future__ import annotations
import tkinter as tk
from typing import Callable, List
from desktop_overlay.config import THEMES

class CommandPalette(tk.Frame):
    """Global fast action launcher with live filtering."""
    
    DEFAULT_ACTIONS = [
        {"id": "summarize", "title": "📄 Summarize Active Context", "desc": "Summarizes active window content or clipboard"},
        {"id": "clean_watermarks", "title": "🛡️ Clean Watermarks & Homoglyphs", "desc": "Strips invisible chars and zero-width spaces"},
        {"id": "explain_screen", "title": "👁️ Explain What I'm Seeing", "desc": "Captures window and explains UI / code / errors"},
        {"id": "rewrite_professional", "title": "✍️ Rewrite (Professional Tone)", "desc": "Improves clarity and tone of clipboard text"},
        {"id": "block_typer", "title": "⌨️ Open Sequential Block Typer", "desc": "Splits text into queued blocks for auto-typing"},
        {"id": "diagnostics", "title": "🔍 Open Diagnostics Panel", "desc": "Inspects active window and OS capabilities"},
        {"id": "permissions", "title": "🔒 Open Permission Center", "desc": "Manage privacy modes and access rights"}
    ]

    def __init__(self, master, on_action: Callable[[str], None], theme_name: str = "Dark"):
        self.t = THEMES.get(theme_name, THEMES["Dark"])
        super().__init__(master, bg=self.t["bg"], padx=12, pady=12)
        self.on_action = on_action
        
        # Search Entry Header
        hdr = tk.Frame(self, bg=self.t["card"], bd=1, relief=tk.SOLID)
        hdr.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(hdr, text="🔍", bg=self.t["card"], fg=self.t["accent"], font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=8)
        self.entry_var = tk.StringVar()
        self.entry_var.trace_add("write", self._filter_actions)
        
        self.entry = tk.Entry(
            hdr,
            textvariable=self.entry_var,
            bg=self.t["card"],
            fg=self.t["fg"],
            insertbackground=self.t["fg"],
            font=("Segoe UI", 11),
            bd=0
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        
        # Listbox for action items
        self.listbox = tk.Listbox(
            self,
            bg=self.t["card_alt"],
            fg=self.t["fg"],
            selectbackground=self.t["accent"],
            selectforeground="#000000",
            font=("Segoe UI", 10),
            bd=0,
            highlightthickness=0,
            activestyle="none"
        )
        self.listbox.pack(fill=tk.BOTH, expand=True)
        
        self.listbox.bind("<Double-Button-1>", lambda e: self._trigger_selected())
        self.entry.bind("<Return>", lambda e: self._trigger_selected())
        self.entry.bind("<Down>", lambda e: self._navigate_list(1))
        self.entry.bind("<Up>", lambda e: self._navigate_list(-1))
        
        self.filtered_actions = list(self.DEFAULT_ACTIONS)
        self._populate_listbox()

    def focus_entry(self) -> None:
        self.entry.focus_set()
        self.entry.select_range(0, tk.END)

    def _populate_listbox(self) -> None:
        self.listbox.delete(0, tk.END)
        for act in self.filtered_actions:
            self.listbox.insert(tk.END, f"  {act['title']}  —  {act['desc']}")
        if self.filtered_actions:
            self.listbox.selection_set(0)

    def _filter_actions(self, *args) -> None:
        query = self.entry_var.get().lower().strip()
        if not query:
            self.filtered_actions = list(self.DEFAULT_ACTIONS)
        else:
            self.filtered_actions = [
                act for act in self.DEFAULT_ACTIONS
                if query in act["title"].lower() or query in act["desc"].lower() or query in act["id"]
            ]
        self._populate_listbox()

    def _navigate_list(self, step: int) -> None:
        sel = self.listbox.curselection()
        if not sel:
            idx = 0
        else:
            idx = (sel[0] + step) % max(1, self.listbox.size())
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(idx)
        self.listbox.see(idx)

    def _trigger_selected(self) -> None:
        sel = self.listbox.curselection()
        if sel and sel[0] < len(self.filtered_actions):
            action_id = self.filtered_actions[sel[0]]["id"]
            self.on_action(action_id)
        elif self.entry_var.get().strip():
            # Treat custom search as direct prompt
            self.on_action(f"prompt:{self.entry_var.get().strip()}")
