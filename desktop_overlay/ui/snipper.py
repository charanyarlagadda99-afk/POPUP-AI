"""Interactive Screen Snipping / Region Selection Tool."""

from __future__ import annotations
import tkinter as tk
from typing import Callable, Optional
from PIL import Image, ImageTk
from desktop_overlay.context.screen import ScreenCaptureEngine

class ScreenSnipper(tk.Toplevel):
    """
    Crystal-clear fullscreen overlay for snipping questions and screen regions.
    Renders the exact desktop background with a dimmed spotlight effect and glowing green selection frame.
    """
    
    def __init__(
        self,
        master: tk.Widget,
        on_snip_completed: Callable[[Image.Image], None],
        on_cancel: Optional[Callable[[], None]] = None
    ):
        super().__init__(master)
        self.on_snip_completed = on_snip_completed
        self.on_cancel = on_cancel
        
        # 1. Capture pristine desktop screenshot before showing overlay
        engine = ScreenCaptureEngine()
        self.screen_img = engine._grab_screen_image()
        
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        
        # Ensure screenshot matches screen dimensions
        if self.screen_img.size != (sw, sh):
            self.screen_img = self.screen_img.resize((sw, sh), Image.Resampling.LANCZOS)
            
        # Create subtle darkened background (72% brightness) for clean spotlight contrast
        self.dark_img = self.screen_img.point(lambda p: int(p * 0.72))
        self.bg_photo = ImageTk.PhotoImage(self.dark_img)
        
        # 2. Window Properties
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.geometry(f"{sw}x{sh}+0+0")
        
        try:
            from desktop_overlay.platform_layer.win32_api import set_window_capture_protection
            self.update_idletasks()
            frame = self.wm_frame()
            if frame:
                set_window_capture_protection(int(frame, 16), True)
        except Exception:
            pass
            
        # 3. Canvas setup
        self.canvas = tk.Canvas(self, width=sw, height=sh, highlightthickness=0, cursor="cross", bg="#000000")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_image(0, 0, image=self.bg_photo, anchor="nw")
        
        # 4. Hint Badge
        hint_text = "🎯 Drag a box over your Question or MCQ to solve directly  •  Press ESC to cancel"
        self.canvas.create_rectangle(
            (sw // 2) - 290, 20, (sw // 2) + 290, 54,
            fill="#1E1E2E", outline="#00FF66", width=1.5
        )
        self.canvas.create_text(
            sw // 2, 37,
            text=hint_text,
            fill="#FFFFFF",
            font=("Segoe UI", 11, "bold")
        )
        
        self.start_x = 0
        self.start_y = 0
        self.rect_id: Optional[int] = None
        self.crop_img_id: Optional[int] = None
        self.crop_photo: Optional[ImageTk.PhotoImage] = None
        
        self.canvas.bind("<Button-1>", self._on_button_press)
        self.canvas.bind("<B1-Motion>", self._on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self._on_button_release)
        self.bind("<Escape>", self._on_escape)

    def _on_button_press(self, event) -> None:
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None
        if self.crop_img_id:
            self.canvas.delete(self.crop_img_id)
            self.crop_img_id = None

    def _on_move_press(self, event) -> None:
        cur_x, cur_y = event.x, event.y
        x1 = min(self.start_x, cur_x)
        y1 = min(self.start_y, cur_y)
        x2 = max(self.start_x, cur_x)
        y2 = max(self.start_y, cur_y)
        
        if (x2 - x1) > 4 and (y2 - y1) > 4:
            # Crop bright section from original screen image
            try:
                bright_crop = self.screen_img.crop((x1, y1, x2, y2))
                self.crop_photo = ImageTk.PhotoImage(bright_crop)
                if self.crop_img_id:
                    self.canvas.delete(self.crop_img_id)
                self.crop_img_id = self.canvas.create_image(x1, y1, image=self.crop_photo, anchor="nw")
            except Exception:
                pass
                
            if self.rect_id:
                self.canvas.delete(self.rect_id)
            self.rect_id = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                outline="#00FF66", width=2
            )

    def _on_button_release(self, event) -> None:
        end_x, end_y = event.x, event.y
        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)
        
        # Close overlay
        self.destroy()
        
        # If selection area is valid (at least 12x12)
        if (x2 - x1) > 12 and (y2 - y1) > 12:
            try:
                cropped = self.screen_img.crop((x1, y1, x2, y2))
                self.on_snip_completed(cropped)
            except Exception as e:
                print(f"[Snipper] Crop error: {e}")
                if self.on_cancel:
                    self.on_cancel()
        else:
            if self.on_cancel:
                self.on_cancel()

    def _on_escape(self, event=None) -> None:
        self.destroy()
        if self.on_cancel:
            self.on_cancel()
