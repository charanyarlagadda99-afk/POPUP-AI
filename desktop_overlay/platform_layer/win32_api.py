"""Windows-specific ctypes bindings for active window detection, DPI, click-through ghost mode, and display affinity."""

from __future__ import annotations
import sys
import time
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
    
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020
    
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    PROCESS_VM_READ = 0x0010
    
    # Set DPI awareness for crisp scaling on multi-monitor setups
    try:
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
        return {"title": "Unknown (Non-Windows)", "process_name": "unknown", "pid": 0, "rect": (0, 0, 0, 0), "hwnd": 0}
        
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return {"title": "", "process_name": "", "pid": 0, "rect": (0, 0, 0, 0), "hwnd": 0}
            
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
        return {"title": f"Error: {e}", "process_name": "unknown", "pid": 0, "rect": (0, 0, 0, 0), "hwnd": 0}


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
    """Hides the window from screen capture tools (Win10 2004+)."""
    if not IS_WINDOWS or not hwnd:
        return False
    try:
        affinity = WDA_EXCLUDEFROMCAPTURE if enable else WDA_NONE
        res = user32.SetWindowDisplayAffinity(hwnd, affinity)
        return bool(res)
    except Exception:
        return False


def set_click_through(hwnd: int, enable: bool) -> bool:
    """Enables or disables click-through 'Ghost Mode' using WS_EX_TRANSPARENT."""
    if not IS_WINDOWS or not hwnd:
        return False
    try:
        # Get current window ex-style
        GetWindowLong = user32.GetWindowLongW if ctypes.sizeof(ctypes.c_void_p) == 4 else user32.GetWindowLongPtrW
        SetWindowLong = user32.SetWindowLongW if ctypes.sizeof(ctypes.c_void_p) == 4 else user32.SetWindowLongPtrW
        
        style = GetWindowLong(hwnd, GWL_EXSTYLE)
        if enable:
            new_style = style | WS_EX_TRANSPARENT | WS_EX_LAYERED
        else:
            new_style = (style & ~WS_EX_TRANSPARENT) | WS_EX_LAYERED
            
        SetWindowLong(hwnd, GWL_EXSTYLE, new_style)
        return True
    except Exception as e:
        print(f"[Win32] Failed to toggle click-through: {e}")
        return False


def switch_to_window(hwnd: int) -> bool:
    """Brings the target window to the foreground."""
    if not IS_WINDOWS or not hwnd:
        return False
    try:
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False


def paste_into_active_window(text: str) -> bool:
    """Pastes text directly into the currently active target window using Windows key events."""
    if not IS_WINDOWS:
        return False
    try:
        import tkinter as tk
        # Put text in clipboard
        r = tk.Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(text)
        r.update()
        r.destroy()
        
        time.sleep(0.06)
        
        # Simulate Ctrl + V
        VK_CONTROL = 0x11
        VK_V = 0x56
        KEYEVENTF_KEYUP = 0x0002
        
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_V, 0, 0, 0)
        time.sleep(0.02)
        user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        return True
    except Exception as e:
        print(f"[Win32] Failed to paste into active window: {e}")
        return False
