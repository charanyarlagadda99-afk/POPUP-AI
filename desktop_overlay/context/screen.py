"""Screen context extraction, smart noise filtering, and OCR snapshot pipeline."""

from __future__ import annotations
import base64
import io
import re
import ctypes
from typing import Optional
from dataclasses import dataclass

try:
    from PIL import ImageGrab, Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import winocr
    HAS_WINOCR = True
except ImportError:
    HAS_WINOCR = False

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

@dataclass
class ScreenContext:
    image_base64: Optional[str] = None
    width: int = 0
    height: int = 0
    region: Optional[tuple[int, int, int, int]] = None
    ocr_text: str = ""
    available: bool = False
    error: Optional[str] = None

def filter_screen_text(raw_text: str) -> str:
    """Intelligently filters out terminal prompts, IDE menus, and self-referencing assistant status messages."""
    if not raw_text:
        return ""
        
    noise_phrases = [
        "are you sure you want to paste",
        "windows powershell",
        "command prompt",
        "desktop ai assistant",
        "ai response & solutions",
        "scan & solve screen",
        "run agent task",
        "send prompt",
        "ask or instruct",
        "file edit selection view",
        "visual studio code",
        "powershell.exe",
        "python.exe",
        "attach screen context",
        "copyright (c) microsoft",
        "all rights reserved",
        "copy response",
        "start sequential block typer",
        "http://localhost",
        "no readable text was detected",
        "no readable text",
        "please make sure the question or window",
        "screen scanned",
        "characters extracted via windows ocr",
        "solving with phi3",
        "solving with",
        "generation stopped by user",
        "antigravity",
        "drag a box over your question"
    ]
    
    clean_lines = []
    for l in raw_text.splitlines():
        line = l.strip()
        if not line or len(line) < 2:
            continue
        line_lower = line.lower()
        if any(noise in line_lower for noise in noise_phrases):
            continue
        # Strip shell paths and prompts
        if line.startswith("PS ") or line.startswith(">>>") or line.startswith("C:\\") or line.startswith("D:\\"):
            continue
        clean_lines.append(line)
        
    return "\n".join(clean_lines) if clean_lines else ""

class ScreenCaptureEngine:
    """Safely captures permitted screen regions and performs high-speed OCR text extraction."""
    
    def capture_fullscreen(self, run_ocr: bool = True) -> ScreenContext:
        if not HAS_PIL and not HAS_MSS:
            return ScreenContext(available=False, error="Screenshot library not available")
        try:
            img = self._grab_screen_image()
            return self._image_to_context(img, run_ocr=run_ocr)
        except Exception as e:
            return ScreenContext(available=False, error=str(e))

    def capture_region(self, bbox: tuple, run_ocr: bool = True) -> ScreenContext:
        if not HAS_PIL and not HAS_MSS:
            return ScreenContext(available=False, error="Screenshot library not available")
        try:
            full_img = self._grab_screen_image()
            if len(bbox) == 6:
                x1, y1, x2, y2, sw, sh = bbox
                if sw > 0 and sh > 0:
                    scale_x = full_img.width / sw
                    scale_y = full_img.height / sh
                    crop_box = (
                        max(0, int(x1 * scale_x)),
                        max(0, int(y1 * scale_y)),
                        min(full_img.width, int(x2 * scale_x)),
                        min(full_img.height, int(y2 * scale_y))
                    )
                else:
                    crop_box = bbox[:4]
            else:
                crop_box = bbox[:4]
                
            img = full_img.crop(crop_box)
            ctx = self._image_to_context(img, run_ocr=run_ocr)
            ctx.region = crop_box
            return ctx
        except Exception as e:
            return ScreenContext(available=False, error=str(e))

    def _grab_screen_image(self) -> Image.Image:
        """Captures desktop screen using robust multi-engine fallback."""
        # Engine 1: PIL ImageGrab
        if HAS_PIL:
            try:
                return ImageGrab.grab(all_screens=True)
            except Exception:
                pass
            try:
                return ImageGrab.grab()
            except Exception:
                pass
                
        # Engine 2: MSS Hardware-accelerated screenshot
        if HAS_MSS:
            try:
                with mss.MSS() as sct:
                    monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                    sct_img = sct.grab(monitor)
                    return Image.frombytes('RGB', sct_img.size, sct_img.bgra, 'raw', 'BGRX')
            except Exception:
                pass
                
        # Engine 3: Native Windows GDI BitBlt
        try:
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32
            w = user32.GetSystemMetrics(0)
            h = user32.GetSystemMetrics(1)
            hdc_screen = user32.GetDC(0)
            hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
            hbm = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
            gdi32.SelectObject(hdc_mem, hbm)
            gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, 0, 0, 0x00CC0020)
            
            from ctypes import wintypes, Structure, c_long, byref, sizeof
            class BITMAPINFOHEADER(Structure):
                _fields_ = [
                    ('biSize', wintypes.DWORD), ('biWidth', c_long), ('biHeight', c_long),
                    ('biPlanes', wintypes.WORD), ('biBitCount', wintypes.WORD),
                    ('biCompression', wintypes.DWORD), ('biSizeImage', wintypes.DWORD),
                    ('biXPelsPerMeter', c_long), ('biYPelsPerMeter', c_long),
                    ('biClrUsed', wintypes.DWORD), ('biClrImportant', wintypes.DWORD)
                ]
            bmi = BITMAPINFOHEADER()
            bmi.biSize = sizeof(BITMAPINFOHEADER)
            bmi.biWidth = w
            bmi.biHeight = -h
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            bmi.biCompression = 0
            
            buf = ctypes.create_string_buffer(w * h * 4)
            gdi32.GetDIBits(hdc_mem, hbm, 0, h, buf, byref(bmi), 0)
            gdi32.DeleteObject(hbm)
            gdi32.DeleteDC(hdc_mem)
            user32.ReleaseDC(0, hdc_screen)
            return Image.frombuffer('RGBA', (w, h), buf, 'raw', 'BGRA', 0, 1).convert('RGB')
        except Exception as e:
            raise RuntimeError(f"All screen capture methods failed: {e}")

    def _image_to_context(self, img: Image.Image, run_ocr: bool = True) -> ScreenContext:
        # 1. OCR Extraction using Windows Native OCR Engine
        ocr_text = ""
        if run_ocr and HAS_WINOCR:
            try:
                res = winocr.recognize_pil_sync(img, "en")
                if isinstance(res, dict):
                    text_val = res.get("text", "").strip()
                    lines_val = [l.get("text", "").strip() for l in res.get("lines", []) if isinstance(l, dict) and l.get("text")]
                    if lines_val:
                        ocr_text = "\n".join(lines_val)
                    elif text_val:
                        ocr_text = text_val
                elif hasattr(res, "text"):
                    ocr_text = str(res.text).strip()
            except Exception as e:
                print(f"[OCR] WinOCR Extraction Notice: {e}")

        # Filter out noise to isolate real questions
        filtered_text = filter_screen_text(ocr_text)

        # 2. Resize thumbnail for vision payload
        max_dim = 1280
        img_thumb = img.copy()
        if img_thumb.width > max_dim or img_thumb.height > max_dim:
            img_thumb.thumbnail((max_dim, max_dim))
            
        buf = io.BytesIO()
        img_thumb.save(buf, format="JPEG", quality=80)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        
        return ScreenContext(
            image_base64=b64,
            width=img.width,
            height=img.height,
            ocr_text=filtered_text.strip(),
            available=True
        )
