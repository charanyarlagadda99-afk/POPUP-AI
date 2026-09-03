"""Active window context provider."""

from __future__ import annotations
from dataclasses import dataclass
from desktop_overlay.platform_layer.win32_api import get_foreground_window_info

@dataclass
class WindowContext:
    title: str
    process_name: str
    pid: int
    rect: tuple[int, int, int, int]
    is_browser: bool
    app_category: str

class ActiveWindowTracker:
    """Retrieves metadata regarding the currently focused foreground window."""
    
    BROWSER_PROCESSES = {
        "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", 
        "opera.exe", "vivaldi.exe", "arc.exe"
    }
    
    DEV_PROCESSES = {
        "code.exe", "devenv.exe", "pycharm64.exe", "windowsterminal.exe",
        "powershell.exe", "cmd.exe", "sublime_text.exe", "idea64.exe"
    }

    def get_current(self) -> WindowContext:
        info = get_foreground_window_info()
        proc = info.get("process_name", "").lower()
        title = info.get("title", "")
        
        is_browser = proc in self.BROWSER_PROCESSES
        
        category = "General"
        if is_browser:
            category = "Web Browser"
        elif proc in self.DEV_PROCESSES:
            category = "Development"
        elif "word" in proc or "notepad" in proc or "writer" in proc:
            category = "Document / Writing"
            
        return WindowContext(
            title=title,
            process_name=info.get("process_name", "unknown"),
            pid=info.get("pid", 0),
            rect=info.get("rect", (0, 0, 0, 0)),
            is_browser=is_browser,
            app_category=category
        )
