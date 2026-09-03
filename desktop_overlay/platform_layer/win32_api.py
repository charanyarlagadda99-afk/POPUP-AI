"""Windows-specific ctypes bindings for active window detection, DPI, and display affinity."""

from __future__ import annotations
import sys
import ctypes
from ctypes import wintypes
from typing import Optional, Tuple

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi
    
    # Constants
    WDA_NONE = 0x00000000
    WDA_MONITOR = 0x00000001
    WDA_EXCLUDEFROMCAPTURE = 0x00000011  # Available on Win10 2004+
    
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    PROCESS_VM_READ = 0x0010
    
    # Set DPI awareness for crisp scaling on multi-monitor setups
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2) # Per monitor aware
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def get_foreground_window_info() -> dict:
    """Returns title, process_name, pid, and rect of currently focused window."""
    if not IS_WINDOWS:
        return {"title": "Unknown (Non-Windows)", "process_name": "unknown", "pid": 0, "rect": (0, 0, 0, 0)}
        
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return {"title": "", "process_name": "", "pid": 0, "rect": (0, 0, 0, 0)}
            
        # Get Window Title
        length = user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value
        
        # Get PID
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        
        # Get Process Name
        process_name = "unknown"
        h_process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, False, pid.value)
        if h_process:
            try:
                image_name_buf = ctypes.create_unicode_buffer(1024)
                size = wintypes.DWORD(1024)
                if kernel32.QueryFullProcessImageNameW(h_process, 0, image_name_buf, ctypes.byref(size)):
                    full_path = image_name_buf.value
                    process_name = full_path.split("\\")[-1]
            finally:
                kernel32.CloseHandle(h_process)
                
        # Get Window Rect
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        window_rect = (rect.left, rect.top, rect.right, rect.bottom)
        
        return {
            "hwnd": hwnd,
            "title": title,
            "process_name": process_name,
            "pid": pid.value,
            "rect": window_rect
        }
    except Exception as e:
        return {"title": f"Error: {e}", "process_name": "unknown", "pid": 0, "rect": (0, 0, 0, 0)}


def get_cursor_position() -> Tuple[int, int]:
    """Returns the current mouse cursor (x, y) coordinates."""
    if not IS_WINDOWS:
        return (0, 0)
    try:
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        return (pt.x, pt.y)
    except Exception:
        return (0, 0)


def set_window_capture_protection(hwnd: int, enable: bool) -> bool:
    """
    Applies or removes standard OS window display affinity protection.
    Uses SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE).
    Returns True if successfully set.
    """
    if not IS_WINDOWS or not hwnd:
        return False
    try:
        affinity = WDA_EXCLUDEFROMCAPTURE if enable else WDA_NONE
        res = user32.SetWindowDisplayAffinity(hwnd, affinity)
        if not res and enable:
            # Fallback to WDA_MONITOR for older Windows versions
            res = user32.SetWindowDisplayAffinity(hwnd, WDA_MONITOR)
        return bool(res)
    except Exception as e:
        print(f"[Win32] SetWindowDisplayAffinity failed: {e}")
        return False
