"""Solution History and Search Panel."""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable, Optional
from desktop_overlay.config import THEMES
from desktop_overlay.history.history_manager import HistoryManager

class HistoryView(tk.Frame):
    """Searchable SQLite Solution Archive with live search, copy, and Markdown export."""
    
    def __init__(
        self,
        master,
        history_mgr: HistoryManager,
        on_back: Callable[[], None],
        theme_name: str = "Light"
    ):
        self.t = THEMES.get(theme_name, THEMES["Light"])
        super().__init__(master, bg=self.t["bg"], padx=12, pady=12)
        self.history_mgr = history_mgr
        self.on_back = on_back
        
        # 1. HEADER
        hdr = tk.Frame(self, bg=self.t["bg"])
        hdr.pack(fill=tk.X, pady=(0, 10))
        
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
            text="📜 Solution History & Archives",
            bg=self.t["bg"],
            fg=self.t["fg"],
            font=("Segoe UI", 11, "bold")
        ).pack(side=tk.LEFT, padx=12)
        
        tk.Button(
            hdr,
            text="🗑️ Clear All",
            command=self._clear_all,
            bg="#D20F39",
            fg="#FFFFFF",
            bd=0,
            padx=8,
            pady=3,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2"
        ).pack(side=tk.RIGHT, padx=4)
        
        tk.Button(
            hdr,
            text="📥 Export to Markdown",
            command=self._export_markdown,
            bg="#268BD2",
            fg="#FFFFFF",
            bd=0,
            padx=10,
            pady=3,
            font=("Segoe UI", 8, "bold"),
            cursor="hand2"
        ).pack(side=tk.RIGHT, padx=4)
        
        # 2. SEARCH BAR
        search_frame = tk.Frame(self, bg=self.t["card"], padx=8, pady=6)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            search_frame,
            text="🔍 Search:",
            bg=self.t["card"],
            fg=self.t["accent"],
            font=("Segoe UI", 9, "bold")
        ).pack(side=tk.LEFT, padx=(0, 6))
        
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self._on_search_change())
        
        self.search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            bg=self.t["input_bg"],
            fg=self.t["fg"],
            insertbackground=self.t["fg"],
            font=("Segoe UI", 9),
            bd=0
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        
        tk.Button(
            search_frame,
            text="✕",
            command=lambda: self.search_var.set(""),
            bg=self.t["btn"],
            fg=self.t["btn_fg"],
            bd=0,
            padx=6,
            pady=1,
            font=("Segoe UI", 8)
        ).pack(side=tk.RIGHT)
        
        # 3. SCROLLABLE RESULTS LIST
        list_container = tk.Frame(self, bg=self.t["card"])
        list_container.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(list_container, bg=self.t["card"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg=self.t["card"])
        
        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=self.canvas.winfo_width()))
        
        self.refresh()

    def refresh(self) -> None:
        """Loads entries from SQLite and displays them."""
        query = self.search_var.get().strip()
        entries = self.history_mgr.search(query)
        
        for w in self.scroll_frame.winfo_children():
            w.destroy()
            
        if not entries:
            tk.Label(
                self.scroll_frame,
                text="No solutions found in history." if query else "History is empty. Scanned questions will appear here automatically.",
                bg=self.t["card"],
                fg=self.t["fg_dim"],
                font=("Segoe UI", 10),
                pady=30
            ).pack(fill=tk.X)
            return
            
        for item in entries:
            self._render_card(item)

    def _render_card(self, item: dict) -> None:
        card = tk.Frame(self.scroll_frame, bg=self.t["bg"], bd=1, relief=tk.SOLID, padx=8, pady=8)
        card.pack(fill=tk.X, padx=6, pady=4)
        
        # Top Meta Row
        meta = tk.Frame(card, bg=self.t["bg"])
        meta.pack(fill=tk.X, pady=(0, 4))
        
        q_type = item.get("question_type", "Question").upper()
        type_color = "#268BD2" if "MCQ" in q_type else ("#00AA44" if "CODE" in q_type else self.t["accent"])
        
        tk.Label(
            meta,
            text=f"[{q_type}]",
            bg=self.t["bg"],
            fg=type_color,
            font=("Segoe UI", 8, "bold")
        ).pack(side=tk.LEFT)
        
        tk.Label(
            meta,
            text=f"🤖 {item.get('model', 'phi3')} • {item.get('created_at', '')}",
            bg=self.t["bg"],
            fg=self.t["fg_dim"],
            font=("Segoe UI", 8)
        ).pack(side=tk.LEFT, padx=8)
        
        # Action buttons
        tk.Button(
            meta,
            text="🗑️",
            command=lambda i=item["id"]: self._delete_item(i),
            bg=self.t["bg"],
            fg="#D20F39",
            bd=0,
            font=("Segoe UI", 8),
            cursor="hand2"
        ).pack(side=tk.RIGHT, padx=2)
        
        tk.Button(
            meta,
            text="📋 Copy Solution",
            command=lambda t=item["answer_text"]: self._copy_text(t),
            bg=self.t["btn"],
            fg=self.t["btn_fg"],
            bd=0,
            padx=6,
            pady=1,
            font=("Segoe UI", 8),
            cursor="hand2"
        ).pack(side=tk.RIGHT, padx=4)
        
        # Question snippet (if available)
        q_text = item.get("question_text", "").strip()
        if q_text:
            if len(q_text) > 120:
                q_text = q_text[:117] + "..."
            tk.Label(
                card,
                text=f"Q: {q_text}",
                bg=self.t["bg"],
                fg=self.t["fg_dim"],
                font=("Segoe UI", 8, "italic"),
                anchor="w",
                justify=tk.LEFT
            ).pack(fill=tk.X, pady=(0, 2))
            
        # Answer preview
        a_text = item.get("answer_text", "").strip()
        preview = a_text[:250] + ("..." if len(a_text) > 250 else "")
        tk.Label(
            card,
            text=preview,
            bg=self.t["bg"],
            fg=self.t["fg"],
            font=("Segoe UI", 9),
            anchor="w",
            justify=tk.LEFT,
            wraplength=560
        ).pack(fill=tk.X)

    def _on_search_change(self) -> None:
        self.refresh()

    def _copy_text(self, text: str) -> None:
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            messagebox.showinfo("Copied", "Solution copied to clipboard!")
        except Exception:
            pass

    def _delete_item(self, entry_id: int) -> None:
        self.history_mgr.delete_entry(entry_id)
        self.refresh()

    def _clear_all(self) -> None:
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to delete all solution history?"):
            self.history_mgr.clear_all()
            self.refresh()

    def _export_markdown(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown Files", "*.md"), ("All Files", "*.*")],
            title="Export Solution History to Markdown"
        )
        if path:
            ok = self.history_mgr.export_markdown(path)
            if ok:
                messagebox.showinfo("Export Successful", f"History exported successfully to:\n{path}")
            else:
                messagebox.showwarning("Export Failed", "No history entries found to export.")
