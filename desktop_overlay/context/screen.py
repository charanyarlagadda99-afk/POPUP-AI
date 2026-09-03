"""Screen context extraction and OCR snapshot pipeline."""

from __future__ import annotations
import base64
import io
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

@dataclass
class ScreenContext:
    image_base64: Optional[str] = None
    width: int = 0
    height: int = 0
    region: Optional[tuple[int, int, int, int]] = None
    ocr_text: str = ""
    available: bool = False
    error: Optional[str] = None

class ScreenCaptureEngine:
    """Safely captures permitted screen regions and performs high-speed OCR text extraction."""
    
    def capture_fullscreen(self, run_ocr: bool = True) -> ScreenContext:
        if not HAS_PIL:
            return ScreenContext(available=False, error="Pillow (PIL) not installed")
        try:
            img = self._grab_screen_image()
            return self._image_to_context(img, run_ocr=run_ocr)
        except Exception as e:
            return ScreenContext(available=False, error=str(e))

    def capture_region(self, bbox: tuple[int, int, int, int], run_ocr: bool = True) -> ScreenContext:
        if not HAS_PIL:
            return ScreenContext(available=False, error="Pillow (PIL) not installed")
        try:
            full_img = self._grab_screen_image()
            img = full_img.crop(bbox)
            ctx = self._image_to_context(img, run_ocr=run_ocr)
            ctx.region = bbox
            return ctx
        except Exception as e:
            return ScreenContext(available=False, error=str(e))

    def _grab_screen_image(self) -> Image.Image:
        """Captures screen using PIL ImageGrab with safe multi-display and GDI fallback."""
        try:
            return ImageGrab.grab(all_screens=True)
        except Exception:
            pass
            
        try:
            return ImageGrab.grab()
        except Exception:
            pass
            
        # Robust Windows GDI BitBlt Capture fallback
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
                    raw_lines = [l["text"] for l in res.get("lines", []) if isinstance(l, dict) and "text" in l]
                    if raw_lines:
                        # Clean out obvious server URLs while preserving all text
                        cleaned = [line.strip() for line in raw_lines if line.strip() and not line.strip().startswith("http://localhost")]
                        ocr_text = "\n".join(cleaned) if cleaned else res.get("text", "").strip()
                    else:
                        ocr_text = res.get("text", "").strip()
            except Exception as e:
                print(f"[OCR] WinOCR Extraction Notice: {e}")

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
            ocr_text=ocr_text.strip(),
            available=True
        )
