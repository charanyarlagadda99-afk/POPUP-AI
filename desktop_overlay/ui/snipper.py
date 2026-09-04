"""Interactive Screen Snipping / Region Selection Tool."""

from __future__ import annotations
import tkinter as tk
from typing import Callable, Optional
from PIL import Image, ImageGrab

class ScreenSnipper(tk.Toplevel):
    """Fullscreen semi-transparent overlay that allows dragging a box over any question on screen."""
    
    def __init__(self, master: tk.Widget, on_snip_completed: Callable[[tuple[int, int, int, int]], None]):
        super().__init__(master)
        self.on_snip_completed = on_snip_completed
        
        # Frameless, topmost fullscreen overlay
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.28)
        self.configure(bg="#000000", cursor="cross")
        
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{sw}x{sh}+0+0")
        
        try:
            from desktop_overlay.platform_layer.win32_api import set_window_capture_protection
            self.update_idletasks()
            frame = self.wm_frame()
            if frame:
                set_window_capture_protection(int(frame, 16), True)
        except Exception:
            pass
        
        # Canvas for drawing the selection rectangle
        self.canvas = tk.Canvas(self, bg="#000000", highlightthickness=0, cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Hint label
        self.canvas.create_text(
            sw // 2, 40,
            text="🎯 Drag a box over your Question or MCQ to solve it directly (Press ESC to cancel)",
            fill="#FFFFFF",
            font=("Segoe UI", 13, "bold")
        )
        
        self.start_x = 0
        self.start_y = 0
        self.rect_id: Optional[int] = None
        
        self.canvas.bind("<Button-1>", self._on_button_press)
        self.canvas.bind("<B1-Motion>", self._on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self._on_button_release)
        self.bind("<Escape>", lambda e: self.destroy())

    def _on_button_press(self, event) -> None:
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="#00FF66", width=2, fill="#FFFFFF"
        )

    def _on_move_press(self, event) -> None:
        cur_x, cur_y = event.x, event.y
        if self.rect_id:
            self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)

    def _on_button_release(self, event) -> None:
        end_x, end_y = event.x, event.y
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)
        
        # Close overlay first
        self.destroy()
        
        # If selection area is large enough (at least 15x15)
        if (x2 - x1) > 15 and (y2 - y1) > 15:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            self.on_snip_completed((x1, y1, x2, y2, sw, sh))
