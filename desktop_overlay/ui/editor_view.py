"""Preserved Text Editor, Watermark Remover, and Upgraded Sequential Block Typer View."""

from __future__ import annotations
import re
import difflib
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional
from desktop_overlay.config import THEMES

# Import clean_text from service scripts if available
import sys
from pathlib import Path
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "service" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from text_unicode import clean_text
except ImportError:
    try:
        from service.scripts.text_unicode import clean_text
    except ImportError:
        def clean_text(text, **kwargs):
            return text, {"removed_count": 0, "replaced_count": 0, "input_length": len(text), "output_length": len(text)}

class EditorToolsView(tk.Frame):
    """Integrates Unicode watermark cleaner, diff viewer, and upgraded sequential block typer."""
    
    def __init__(self, master, on_close: Optional[Callable[[], None]] = None, theme_name: str = "Dark"):
        self.t = THEMES.get(theme_name, THEMES["Dark"])
        super().__init__(master, bg=self.t["bg"], padx=10, pady=10)
        self.on_close = on_close
        
        self.custom_regex = tk.StringVar(value="")
        self.block_queue: list[str] = []
        self.current_block_idx = 0
        self.block_win: Optional[tk.Toplevel] = None
        self._is_typing = False
        
        # 0. Top Header with Back Button
        if self.on_close:
            hdr_top = tk.Frame(self, bg=self.t["bg"])
            hdr_top.pack(fill=tk.X, pady=(0, 6))
            
            tk.Button(
                hdr_top,
                text="← Back to Assistant",
                command=self.on_close,
                bg=self.t["btn"],
                fg=self.t["btn_fg"],
                bd=0,
                padx=10,
                pady=3,
                font=("Segoe UI", 9, "bold"),
                cursor="hand2"
            ).pack(side=tk.LEFT)
            
            tk.Label(
                hdr_top,
                text="📝 Watermark Cleaner & Typer",
                bg=self.t["bg"],
                fg=self.t["accent"],
                font=("Segoe UI", 11, "bold")
            ).pack(side=tk.LEFT, padx=10)
            
            tk.Button(
                hdr_top,
                text="✕ Close",
                command=self.on_close,
                bg=self.t["btn"],
                fg=self.t["btn_fg"],
                bd=0,
                padx=8,
                pady=2,
                cursor="hand2"
            ).pack(side=tk.RIGHT)
        
        # Split input and output panes
        paned = tk.PanedWindow(self, orient=tk.VERTICAL, bg=self.t["bg"], bd=0)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # 1. Input Box
        f_in = tk.Frame(paned, bg=self.t["card"])
        hdr_in = tk.Frame(f_in, bg=self.t["card"])
        hdr_in.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(hdr_in, text="Raw Text / Input:", bg=self.t["card"], fg=self.t["accent"], font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        
        tk.Button(hdr_in, text="🛡️ Clean Watermarks", command=self.clean_input, bg=self.t["accent"], fg="#000000", bd=0, padx=6, pady=2, font=("Segoe UI", 8, "bold")).pack(side=tk.RIGHT, padx=2)
        tk.Button(hdr_in, text="📋 Paste", command=self.paste_input, bg=self.t["btn"], fg=self.t["btn_fg"], bd=0, padx=6, pady=2, font=("Segoe UI", 8)).pack(side=tk.RIGHT, padx=2)
        
        self.txt_in = tk.Text(f_in, height=6, bg=self.t["input_bg"], fg=self.t["fg"], insertbackground=self.t["fg"], font=("Consolas", 10), exportselection=False)
        self.txt_in.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        self.txt_in.bind("<KeyRelease>", lambda e: self.clean_input())
        paned.add(f_in, minsize=100)
        
        # 2. Output Box
        f_out = tk.Frame(paned, bg=self.t["card"])
        hdr_out = tk.Frame(f_out, bg=self.t["card"])
        hdr_out.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(hdr_out, text="Cleaned Text / Output:", bg=self.t["card"], fg=self.t["success"], font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        
        self.lbl_stats = tk.Label(hdr_out, text="Ready", bg=self.t["card"], fg=self.t["fg_dim"], font=("Segoe UI", 8))
        self.lbl_stats.pack(side=tk.LEFT, padx=10)
        
        tk.Button(hdr_out, text="⌨️ Start Sequential Block Typer", command=self.start_block_typer, bg="#268BD2", fg="#FFFFFF", bd=0, padx=8, pady=2, font=("Segoe UI", 8, "bold")).pack(side=tk.RIGHT, padx=2)
        tk.Button(hdr_out, text="📋 Copy", command=self.copy_output, bg=self.t["btn"], fg=self.t["btn_fg"], bd=0, padx=6, pady=2, font=("Segoe UI", 8)).pack(side=tk.RIGHT, padx=2)
        
        self.txt_out = tk.Text(f_out, height=8, bg=self.t["output_bg"], fg=self.t["fg"], insertbackground=self.t["fg"], font=("Consolas", 10), exportselection=False)
        self.txt_out.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        paned.add(f_out, minsize=100)

    def paste_input(self) -> None:
        try:
            txt = self.clipboard_get()
            self.txt_in.delete("1.0", tk.END)
            self.txt_in.insert("1.0", txt)
            self.clean_input()
        except Exception:
            pass

    def copy_output(self) -> None:
        try:
            txt = self.txt_out.get("1.0", tk.END).rstrip("\n")
            if txt:
                self.clipboard_clear()
                self.clipboard_append(txt)
                self.lbl_stats.config(text="✓ Copied to clipboard!")
        except Exception:
            pass

    def clean_input(self) -> None:
        raw = self.txt_in.get("1.0", tk.END).rstrip("\n")
        if not raw:
            self.txt_out.delete("1.0", tk.END)
            self.lbl_stats.config(text="Ready.")
            return
            
        try:
            cleaned, stats = clean_text(raw, nfkc=True, aggressive_homoglyphs=True)
            self.txt_out.delete("1.0", tk.END)
            self.txt_out.insert("1.0", cleaned)
            
            rem = stats.get("removed_count", 0)
            rep = stats.get("replaced_count", 0)
            self.lbl_stats.config(text=f"-{rem} hidden chars | ~{rep} homoglyphs normalized")
        except Exception as e:
            self.lbl_stats.config(text=f"Error: {e}")

    def start_block_typer(self) -> None:
        # Check for highlighted text first, else full output
        txt = ""
        try:
            txt = self.txt_out.selection_get().strip()
        except Exception:
            pass
        if not txt:
            try:
                txt = self.txt_in.selection_get().strip()
            except Exception:
                pass
        if not txt:
            txt = self.txt_out.get("1.0", tk.END).strip()
        if not txt:
            txt = self.txt_in.get("1.0", tk.END).strip()
            
        if not txt:
            messagebox.showinfo("Block Typer", "No text found to split into typing blocks!")
            return
            
        # Split by double newlines or single newlines
        blocks = re.split(r'\n\s*\n', txt)
        if len(blocks) <= 1:
            blocks = txt.splitlines()
        self.block_queue = [b.strip() for b in blocks if b.strip()]
        self.current_block_idx = 0
        
        self.open_block_typer_window()

    def open_block_typer_window(self) -> None:
        if self.block_win and tk.Toplevel.winfo_exists(self.block_win):
            self.block_win.deiconify()
            self.block_win.lift()
            self._update_block_ui()
            return
            
        self.block_win = tk.Toplevel(self)
        self.block_win.title("Sequential Block Typer Queue")
        self.block_win.geometry("450x200")
        self.block_win.configure(bg=self.t["bg"])
        self.block_win.attributes("-topmost", True)
        
        # Header Status
        self.lbl_block_status = tk.Label(self.block_win, text=f"Block 1 of {len(self.block_queue)}", bg=self.t["bg"], fg=self.t["accent"], font=("Segoe UI", 11, "bold"))
        self.lbl_block_status.pack(pady=(10, 4))
        
        # Preview Box
        self.lbl_block_preview = tk.Label(self.block_win, text="", bg=self.t["card"], fg=self.t["fg"], wraplength=410, justify=tk.LEFT, height=3, padx=8, pady=4)
        self.lbl_block_preview.pack(fill=tk.X, padx=12, pady=4)
        
        # Buttons Bar
        btn_f = tk.Frame(self.block_win, bg=self.t["bg"])
        btn_f.pack(pady=8)
        
        self.btn_type_delayed = tk.Button(btn_f, text="⚡ Type Next (3s Countdown)", command=self.type_next_delayed, bg=self.t["accent"], fg="#000000", bd=0, padx=10, pady=4, font=("Segoe UI", 9, "bold"))
        self.btn_type_delayed.pack(side=tk.LEFT, padx=4)
        
        self.btn_paste_next = tk.Button(btn_f, text="📋 Paste Next Block", command=self.paste_next_block, bg=self.t["btn"], fg=self.t["btn_fg"], bd=0, padx=8, pady=4, font=("Segoe UI", 9))
        self.btn_paste_next.pack(side=tk.LEFT, padx=4)
        
        tk.Button(btn_f, text="↻ Reset", command=self.reset_block_queue, bg=self.t["btn"], fg=self.t["btn_fg"], bd=0, padx=8, pady=4, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=4)
        
        # Hotkey hint
        tk.Label(self.block_win, text="Tip: Press Ctrl+Shift+N anywhere to type the next block instantly!", bg=self.t["bg"], fg=self.t["fg_dim"], font=("Segoe UI", 8)).pack(pady=(2, 5))
        
        self._update_block_ui()

    def _update_block_ui(self) -> None:
        if not self.block_win or not tk.Toplevel.winfo_exists(self.block_win): return
        if self.current_block_idx >= len(self.block_queue):
            self.lbl_block_status.config(text="✅ All blocks typed successfully!", fg=self.t["success"])
            self.lbl_block_preview.config(text="Queue is empty. Click Reset to start over.")
            self.btn_type_delayed.config(state=tk.DISABLED)
            self.btn_paste_next.config(state=tk.DISABLED)
            return
            
        self.btn_type_delayed.config(state=tk.NORMAL, text="⚡ Type Next (3s Countdown)")
        self.btn_paste_next.config(state=tk.NORMAL)
        self.lbl_block_status.config(text=f"Block {self.current_block_idx + 1} of {len(self.block_queue)}", fg=self.t["accent"])
        preview = self.block_queue[self.current_block_idx].replace("\n", " ")
        if len(preview) > 140: preview = preview[:137] + "..."
        self.lbl_block_preview.config(text=preview)

    def type_next_delayed(self) -> None:
        if self._is_typing or self.current_block_idx >= len(self.block_queue): return
        self._is_typing = True
        
        def _countdown():
            for sec in [3, 2, 1]:
                self.btn_type_delayed.config(text=f"Click target window ({sec}s)...", state=tk.DISABLED)
                time.sleep(1.0)
            self.type_next_now()
            self._is_typing = False
            self.after(0, self._update_block_ui)
            
        threading.Thread(target=_countdown, daemon=True).start()

    def type_next_now(self) -> None:
        if self.current_block_idx >= len(self.block_queue): return
        txt = self.block_queue[self.current_block_idx]
        try:
            import pyautogui
            pyautogui.write(txt, interval=0.005)
        except Exception:
            try:
                import keyboard
                keyboard.write(txt, delay=0.005)
            except Exception as e:
                print("Typing error:", e)
        self.current_block_idx += 1

    def paste_next_block(self) -> None:
        if self.current_block_idx >= len(self.block_queue): return
        txt = self.block_queue[self.current_block_idx]
        try:
            self.clipboard_clear()
            self.clipboard_append(txt)
            import pyautogui
            pyautogui.hotkey('ctrl', 'v')
        except Exception:
            pass
        self.current_block_idx += 1
        self._update_block_ui()

    def reset_block_queue(self) -> None:
        self.current_block_idx = 0
        self._update_block_ui()
