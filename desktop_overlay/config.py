"""Configuration schema and persistent settings."""

from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict

CONFIG_DIR = Path.home() / ".universal_overlay"
CONFIG_FILE = CONFIG_DIR / "settings.json"

@dataclass
class OverlayConfig:
    # Hotkeys
    hotkey_summon: str = "ctrl+h"
    hotkey_clean_clipboard: str = "ctrl+shift+c"
    hotkey_auto_type: str = "ctrl+shift+v"
    hotkey_next_block: str = "ctrl+shift+n"
    
    # UI Appearance
    theme: str = "Light"  # Default: "Light" for clean white translucent desktop blending
    opacity: float = 0.95
    always_on_top: bool = True
    remember_position: bool = True
    last_x: int = 100
    last_y: int = 100
    overlay_width: int = 680
    overlay_height: int = 560
    font_family: str = "Segoe UI"
    font_size: int = 10
    
    # Privacy & Protection
    privacy_mode: str = "Balanced"  # "Maximum Privacy", "Balanced", "Agent Mode"
    screen_capture_protection: bool = False  # SetWindowDisplayAffinity
    allow_screen_capture: bool = True
    allow_accessibility: bool = True
    allow_input_automation: bool = True
    allow_clipboard_read: bool = True
    allow_clipboard_write: bool = True
    allow_file_access: bool = True
    
    # AI Engine
    ai_provider: str = "Ollama"  # "Ollama", "CustomAPI"
    ollama_url: str = "http://localhost:11434/api/generate"
    ollama_model: str = "Qwen3.6:latest"
    available_models: list[str] = field(default_factory=lambda: ["Qwen3.6:latest", "phi3:latest", "phi3", "llama3.2", "llava", "qwen2.5:3b", "mistral"])
    streaming: bool = True
    temperature: float = 0.7
    max_tokens: int = 1500

    def save(self) -> None:
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=2)
        except Exception as e:
            print(f"[Config] Failed to save config: {e}")

    @classmethod
    def load(cls) -> "OverlayConfig":
        config = cls()
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    config = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except Exception as e:
                print(f"[Config] Failed to load config, using defaults: {e}")
                
        # Try dynamic local model discovery
        try:
            import urllib.request
            req = urllib.request.Request("http://localhost:11434/api/tags", headers={"User-Agent": "DesktopAI/1.0"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                installed = [m["name"] for m in data.get("models", []) if "name" in m]
                if installed:
                    for m in installed:
                        if m not in config.available_models:
                            config.available_models.insert(0, m)
                    if config.ollama_model not in installed:
                        config.ollama_model = installed[0]
        except Exception:
            pass
        return config

THEMES = {
    "Light": {
        "bg": "#FFFFFF",
        "card": "#F6F8FA",
        "card_alt": "#EAEEF2",
        "fg": "#1F2328",
        "fg_dim": "#59636E",
        "accent": "#0969DA",
        "accent_hover": "#218BFF",
        "success": "#1A7F37",
        "warning": "#9A6700",
        "error": "#CF222E",
        "btn": "#EBEFF4",
        "btn_fg": "#1F2328",
        "input_bg": "#FFFFFF",
        "output_bg": "#F8FAFC",
        "border": "#D0D7DE"
    },
    "Dark": {
        "bg": "#11111B",
        "card": "#181825",
        "card_alt": "#1E1E2E",
        "fg": "#CDD6F4",
        "fg_dim": "#A6ADC8",
        "accent": "#89B4FA",
        "accent_hover": "#B4BEFE",
        "success": "#A6E3A1",
        "warning": "#F9E2AF",
        "error": "#F38BA8",
        "btn": "#313244",
        "btn_fg": "#CDD6F4",
        "input_bg": "#1E1E2E",
        "output_bg": "#181825",
        "border": "#313244"
    }
}
