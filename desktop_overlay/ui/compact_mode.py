"""Compact Mode: Minimalist adaptive floating dot widget."""

from __future__ import annotations
import sys
import tkinter as tk
from typing import Callable, Optional
from desktop_overlay.config import THEMES

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import ctypes
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

try:
    from PIL import ImageGrab, ImageStat
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

class CompactLauncher(tk.Frame):
    """Minimal floating dot widget with high-precision background luminance detection."""
    
    def __init__(
        self,
        master: tk.Widget,
        on_expand: Callable[[], None],
        on_palette: Optional[Callable[[], None]] = None,
        on_clean: Optional[Callable[[], None]] = None,
        theme_name: str = "Dark",
        dot_size: int = 48
    ):
        self.t = THEMES.get(theme_name, THEMES["Dark"])
        super().__init__(master, bg=self.t["bg"], bd=0)
        self.on_expand = on_expand
        self.on_palette = on_palette
        self.on_clean = on_clean
        self.dot_size = dot_size
        
        # Adaptive Theme State
        self.is_dark_bg = True
        
        # Transparent background setup
        self.TRANS_COLOR = "#000001"
        try:
            top = master.winfo_toplevel()
            top.config(bg=self.TRANS_COLOR)
            top.attributes("-transparentcolor", self.TRANS_COLOR)
            self.configure(bg=self.TRANS_COLOR)
        except Exception:
            pass
            
        self.canvas = tk.Canvas(
            self,
            width=self.dot_size,
            height=self.dot_size,
            bg=self.TRANS_COLOR,
            highlightthickness=0,
            cursor="hand2"
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Center and Radius
        self._center = self.dot_size // 2
        self._dot_radius = 9
        self._render_dot(hover=False)
        
        # Drag and click tracking
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._offset_x = 0
        self._offset_y = 0
        
        self.canvas.bind("<Button-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._do_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Enter>", lambda e: self._render_dot(hover=True))
        self.canvas.bind("<Leave>", lambda e: self._render_dot(hover=False))
        self.canvas.bind("<Button-3>", self._show_menu)
        
        # Start periodic adaptive background color sampling
        self.after(300, self._sample_background_color)

    def _sample_background_color(self) -> None:
        """Samples the desktop background pixels surrounding the dot."""
        try:
            top = self.winfo_toplevel()
            x = top.winfo_x()
            y = top.winfo_y()
            
            if IS_WINDOWS:
                hdc = user32.GetDC(0)
                if hdc:
                    try:
                        # Sample 4 surrounding points just outside the dot window to read true background
                        points = [
                            (max(0, x - 8), max(0, y + 24)),
                            (x + self.dot_size + 8, max(0, y + 24)),
                            (max(0, x + 24), max(0, y - 8)),
                            (max(0, x + 24), y + self.dot_size + 8)
                        ]
                        lums = []
                        for px, py in points:
                            col = gdi32.GetPixel(hdc, px, py)
                            if col != -1:
                                r = col & 0xFF
                                g = (col >> 8) & 0xFF
                                b = (col >> 16) & 0xFF
                                lums.append(0.299 * r + 0.587 * g + 0.114 * b)
                        if lums:
                            avg_lum = sum(lums) / len(lums)
                            new_dark = (avg_lum < 140)
                            if new_dark != self.is_dark_bg:
                                self.is_dark_bg = new_dark
                                self._render_dot(hover=False)
                    finally:
                        user32.ReleaseDC(0, hdc)
            elif HAS_PIL and x > 0 and y > 0:
                img = ImageGrab.grab(bbox=(x - 5, y - 5, x, y))
                stat = ImageStat.Stat(img)
                avg = stat.mean
                lum = 0.299 * avg[0] + 0.587 * avg[1] + 0.114 * avg[2]
                self.is_dark_bg = (lum < 140)
                self._render_dot(hover=False)
        except Exception:
            pass
            
        # Re-check every 2 seconds
        self.after(2000, self._sample_background_color)

    def _render_dot(self, hover: bool = False) -> None:
        self.canvas.delete("all")
        c = self._center
        r = self._dot_radius + (2 if hover else 0)
        
        if hover:
            # Active hover glow
            self.canvas.create_oval(
                c - r - 4, c - r - 4, c + r + 4, c + r + 4,
                fill="", outline=self.t["accent"], width=1
            )
            fill_color = self.t["accent"]
            outline_color = "#FFFFFF"
        else:
            if self.is_dark_bg:
                # Dark background: rich dark dot with subtle light outline so it is detectable
                fill_color = "#1E1E2E"
                outline_color = "#585B70"
            else:
                # White/Light background: white dot with subtle darker outline so it is detectable
                fill_color = "#FFFFFF"
                outline_color = "#7C7F93"
                
        # Render the minimalist adaptive dot
        self.canvas.create_oval(
            c - r, c - r, c + r, c + r,
            fill=fill_color, outline=outline_color, width=1.5
        )

    def _start_drag(self, event) -> None:
        self._offset_x = event.x
        self._offset_y = event.y
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root

    def _do_drag(self, event) -> None:
        top = self.winfo_toplevel()
        new_x = top.winfo_x() + (event.x - self._offset_x)
        new_y = top.winfo_y() + (event.y - self._offset_y)
        top.geometry(f"+{new_x}+{new_y}")

    def _on_release(self, event) -> None:
        # If clicked without dragging more than 4px, expand!
        if abs(event.x_root - self._drag_start_x) < 5 and abs(event.y_root - self._drag_start_y) < 5:
            self.on_expand()
        else:
            # Re-sample background color immediately at new position
            self.after(80, self._sample_background_color)

    def _show_menu(self, event) -> None:
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="✦ Toggle AI Assistant (Ctrl+Z)", command=self.on_expand)
        if self.on_palette:
            menu.add_command(label="🔍 Quick Actions", command=self.on_palette)
        if self.on_clean:
            menu.add_command(label="🛡️ Clean Clipboard (Ctrl+Shift+C)", command=self.on_clean)
        menu.add_separator()
        menu.add_command(label="✕ Exit", command=self.winfo_toplevel().destroy)
        menu.tk_popup(event.x_root, event.y_root)
