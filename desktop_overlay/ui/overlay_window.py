"""Master Floating Overlay Window Manager with Code Sandbox, Auto-Paste, History, Ghost Mode, and Direct OCR Solving."""

from __future__ import annotations
import sys
import time
import tkinter as tk
from typing import Optional

from desktop_overlay.config import OverlayConfig, THEMES
from desktop_overlay.security.permissions import PermissionManager
from desktop_overlay.security.capture_guard import CaptureGuard
from desktop_overlay.security.audit import AuditLogger
from desktop_overlay.platform_layer.capability_matrix import CapabilityMatrix
from desktop_overlay.platform_layer.win32_api import set_click_through, paste_into_active_window
from desktop_overlay.context.context_engine import ContextEngine, ApplicationContext
from desktop_overlay.agent.llm_provider import LLMProvider
from desktop_overlay.agent.engine import AgentEngine
from desktop_overlay.history.history_manager import HistoryManager
from desktop_overlay.sandbox.code_runner import CodeSandboxEngine

from desktop_overlay.ui.compact_mode import CompactLauncher
from desktop_overlay.ui.expanded_mode import ExpandedAssistantView
from desktop_overlay.ui.agent_mode import AgentExecutionView
from desktop_overlay.ui.command_palette import CommandPalette
from desktop_overlay.ui.permission_ui import PermissionCenter
from desktop_overlay.ui.diagnostics_ui import DiagnosticsPanel
from desktop_overlay.ui.editor_view import EditorToolsView
from desktop_overlay.ui.settings_ui import SettingsPanel
from desktop_overlay.ui.history_view import HistoryView
from desktop_overlay.ui.sandbox_view import SandboxView
from desktop_overlay.ui.snipper import ScreenSnipper

class DesktopOverlayWindow:
    """Universal Desktop AI Overlay Window with permanent floating dot, Sandbox, Auto-Paste, Ghost Mode, and History."""
    
    def __init__(self, root: tk.Tk, config: Optional[OverlayConfig] = None):
        self.root = root
        self.config = config or OverlayConfig.load()
        self.t = THEMES.get(self.config.theme, THEMES["Light"])
        
        # State
        self._cancel_stream = False
        self.is_recessed = False
        self.is_ghost_mode = False
        self.is_boss_hidden = False
        self._saved_height = max(520, self.config.overlay_height)
        
        # Core Subsystems
        self.capabilities = CapabilityMatrix()
        self.permissions = PermissionManager(self.config)
        self.audit = AuditLogger()
        self.context_engine = ContextEngine(self.permissions)
        self.llm = LLMProvider(self.config)
        self.agent = AgentEngine(self.llm, self.permissions, self.audit)
        self.history_mgr = HistoryManager()
        
        # 1. PERMANENT FLOATING DOT (ROOT WINDOW)
        self.root.title("Pop-up AI Dot")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", self.config.always_on_top)
        
        # Transparent background for the dot
        self.TRANS_COLOR = "#000001"
        try:
            self.root.config(bg=self.TRANS_COLOR)
            self.root.attributes("-transparentcolor", self.TRANS_COLOR)
        except Exception:
            self.root.config(bg=self.t["bg"])
            
        self.dot_size = 48
        self._position_floating_dot()
        
        # Floating Dot Widget
        self.compact_launcher = CompactLauncher(
            self.root,
            on_expand=self.toggle_assistant,
            on_palette=lambda: self.open_mode("palette"),
            on_clean=self.quick_clean_clipboard,
            theme_name=self.config.theme,
            dot_size=self.dot_size
        )
        self.compact_launcher.pack(fill=tk.BOTH, expand=True)
        
        # 2. ASSISTANT POPUP WINDOW (TOPLEVEL)
        self.popup_win: Optional[tk.Toplevel] = None
        self._create_assistant_window()
        
        # Register global hotkeys
        self._setup_hotkeys()

    def _position_floating_dot(self) -> None:
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        init_x = self.config.last_x if (self.config.remember_position and self.config.last_x) else (sw - 100)
        init_y = self.config.last_y if (self.config.remember_position and self.config.last_y) else (sh - 140)
        self.root.geometry(f"{self.dot_size}x{self.dot_size}+{init_x}+{init_y}")

    def _create_assistant_window(self) -> None:
        self.popup_win = tk.Toplevel(self.root)
        self.popup_win.title("Pop-up AI")
        self.popup_win.overrideredirect(True)
        self.popup_win.attributes("-topmost", self.config.always_on_top)
        self.popup_win.attributes("-alpha", self.config.opacity)
        self.popup_win.configure(bg=self.t["bg"])
        
        # Position assistant window centered
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = max(640, self.config.overlay_width), max(520, self.config.overlay_height)
        pos_x = max(20, min(sw - w - 20, (sw - w) // 2))
        pos_y = max(20, min(sh - h - 20, (sh - h) // 2))
        self.popup_win.geometry(f"{w}x{h}+{pos_x}+{pos_y}")
        
        # Drag handle / Header
        self.hdr = tk.Frame(self.popup_win, bg=self.t["card"], height=30, cursor="fleur")
        self.hdr.pack(fill=tk.X)
        
        self.lbl_hdr_title = tk.Label(self.hdr, text="✦ Pop-up AI", bg=self.t["card"], fg=self.t["fg_dim"], font=("Segoe UI", 9, "bold"))
        self.lbl_hdr_title.pack(side=tk.LEFT, padx=10)
        
        # Ghost mode badge (hidden by default)
        self.lbl_ghost_badge = tk.Label(self.hdr, text="🪟 GHOST MODE ACTIVE (Press Ctrl+Shift+G to disable)", bg="#D20F39", fg="#FFFFFF", font=("Segoe UI", 8, "bold"), padx=6, pady=1)
        
        # Window controls: Close & Recess/Extend button
        self.btn_close = tk.Label(self.hdr, text="✕", bg=self.t["card"], fg=self.t["fg_dim"], font=("Segoe UI", 10), cursor="hand2")
        self.btn_close.pack(side=tk.RIGHT, padx=(4, 10))
        self.btn_close.bind("<Button-1>", lambda e: self.popup_win.withdraw())
        
        # RECESS / EXTEND BUTTON
        self.btn_recess = tk.Label(self.hdr, text="▲ Recess", bg=self.t["card"], fg=self.t["fg_dim"], font=("Segoe UI", 8, "bold"), cursor="hand2")
        self.btn_recess.pack(side=tk.RIGHT, padx=6)
        self.btn_recess.bind("<Button-1>", lambda e: self.toggle_recess())
        
        # Dragging state for popup
        self._popup_drag_x = 0
        self._popup_drag_y = 0
        for w_elem in (self.hdr, self.lbl_hdr_title):
            w_elem.bind("<Button-1>", self._start_popup_drag)
            w_elem.bind("<B1-Motion>", self._do_popup_drag)
            
        # Views Frame
        self.view_frame = tk.Frame(self.popup_win, bg=self.t["bg"])
        self.view_frame.pack(fill=tk.BOTH, expand=True)
        
        # Subviews container
        self._current_mode = "expanded"
        self._create_subviews(self.config.theme)
        
        # Bottom-Right Resize Grip
        self.resize_grip = tk.Label(self.popup_win, text="⋰", bg=self.t["bg"], fg=self.t["fg_dim"], font=("Segoe UI", 9), cursor="size_nw_se")
        self.resize_grip.place(relx=1.0, rely=1.0, anchor="se", x=-2, y=-2)
        self.resize_grip.bind("<Button-1>", self._start_resize)
        self.resize_grip.bind("<B1-Motion>", self._do_resize)
        
        # Start withdrawn so only the dot is initially visible
        self.popup_win.withdraw()
        self.open_mode("expanded")

    def _create_subviews(self, theme_name: str) -> None:
        # 1. Main Assistant View
        self.expanded_view = ExpandedAssistantView(
            self.view_frame,
            config=self.config,
            on_send_prompt=self.handle_prompt,
            on_scan_solve=self.handle_scan_and_solve,
            on_snip_solve=self.start_snip_and_solve,
            on_stop=self.cancel_generation,
            on_run_agent=self.handle_agent_task,
            on_auto_paste=self.handle_auto_paste,
            on_run_sandbox=self.run_in_sandbox,
            on_toggle_ghost=self.toggle_ghost_mode,
            on_open_history=lambda: self.open_mode("history"),
            on_open_sandbox=lambda: self.open_mode("sandbox"),
            on_open_palette=lambda: self.open_mode("palette"),
            on_open_settings=lambda: self.open_mode("settings"),
            on_open_permissions=lambda: self.open_mode("permissions"),
            on_open_diagnostics=lambda: self.open_mode("diagnostics"),
            on_open_editor=lambda: self.open_mode("editor"),
            theme_name=theme_name
        )
        
        # 2. History View
        self.history_view = HistoryView(
            self.view_frame,
            history_mgr=self.history_mgr,
            on_back=lambda: self.open_mode("expanded"),
            theme_name=theme_name
        )
        
        # 3. Sandbox View
        self.sandbox_view = SandboxView(
            self.view_frame,
            on_back=lambda: self.open_mode("expanded"),
            theme_name=theme_name
        )
        
        # 4. Auxiliary Panels
        self.agent_view = AgentExecutionView(
            self.view_frame,
            on_cancel=self.agent.cancel,
            on_confirm=self.agent.confirm_action,
            theme_name=theme_name
        )
        
        self.palette_view = CommandPalette(
            self.view_frame,
            on_action=self.handle_palette_action,
            theme_name=theme_name
        )
        
        self.settings_view = SettingsPanel(
            self.view_frame,
            config=self.config,
            on_opacity_change=self.apply_opacity,
            on_topmost_change=self.apply_topmost,
            on_theme_change=self.apply_theme,
            on_close=lambda: self.open_mode("expanded"),
            theme_name=theme_name
        )
        
        self.permission_view = PermissionCenter(
            self.view_frame,
            permissions=self.permissions,
            on_close=lambda: self.open_mode("expanded"),
            theme_name=theme_name
        )
        
        self.diagnostics_view = DiagnosticsPanel(
            self.view_frame,
            context_engine=self.context_engine,
            capabilities=self.capabilities,
            audit=self.audit,
            on_close=lambda: self.open_mode("expanded"),
            theme_name=theme_name
        )
        
        self.editor_view = EditorToolsView(
            self.view_frame,
            theme_name=theme_name
        )

    def _start_popup_drag(self, event) -> None:
        self._popup_drag_x = event.x
        self._popup_drag_y = event.y

    def _do_popup_drag(self, event) -> None:
        new_x = self.popup_win.winfo_x() + (event.x - self._popup_drag_x)
        new_y = self.popup_win.winfo_y() + (event.y - self._popup_drag_y)
        self.popup_win.geometry(f"+{new_x}+{new_y}")

    def _start_resize(self, event) -> None:
        self._resize_start_x = event.x_root
        self._resize_start_y = event.y_root
        self._resize_start_w = self.popup_win.winfo_width()
        self._resize_start_h = self.popup_win.winfo_height()

    def _do_resize(self, event) -> None:
        if self.is_recessed: return
        dx = event.x_root - self._resize_start_x
        dy = event.y_root - self._resize_start_y
        new_w = max(500, self._resize_start_w + dx)
        new_h = max(400, self._resize_start_h + dy)
        self.popup_win.geometry(f"{new_w}x{new_h}")
        self.config.overlay_width = new_w
        self.config.overlay_height = new_h
        self.config.save()

    def toggle_recess(self, event=None) -> None:
        """Compresses/recesses the window into a slim title bar or decompresses/extends it back up."""
        if not self.is_recessed:
            self._saved_height = max(400, self.popup_win.winfo_height())
            self.view_frame.pack_forget()
            self.resize_grip.place_forget()
            w = self.popup_win.winfo_width()
            self.popup_win.geometry(f"{w}x32")
            self.btn_recess.config(text="▼ Extend", fg=self.t["accent"])
            self.is_recessed = True
        else:
            w = self.popup_win.winfo_width()
            h = self._saved_height
            self.popup_win.geometry(f"{w}x{h}")
            self.view_frame.pack(fill=tk.BOTH, expand=True)
            self.resize_grip.place(relx=1.0, rely=1.0, anchor="se", x=-2, y=-2)
            self.btn_recess.config(text="▲ Recess", fg=self.t["fg_dim"])
            self.is_recessed = False

    def toggle_ghost_mode(self) -> None:
        """Toggles click-through 'Ghost Mode' using WS_EX_TRANSPARENT."""
        self.is_ghost_mode = not self.is_ghost_mode
        try:
            hwnd = int(self.popup_win.wm_frame(), 16) if hasattr(self.popup_win, 'wm_frame') else self.popup_win.winfo_id()
            set_click_through(hwnd, self.is_ghost_mode)
            if self.is_ghost_mode:
                self.lbl_ghost_badge.pack(side=tk.LEFT, padx=10)
                self.expanded_view.set_output("🪟 GHOST MODE ENABLED:\nMouse clicks now pass directly through this window to whatever is behind it!\n\nTo disable Ghost Mode anytime, press: Ctrl + Shift + G")
            else:
                self.lbl_ghost_badge.pack_forget()
        except Exception as e:
            print(f"[GhostMode] Error: {e}")

    def toggle_boss_key(self) -> None:
        """Emergency Boss Key: instantly hides or restores all UI without a trace."""
        if not self.is_boss_hidden:
            self.popup_win.withdraw()
            self.root.withdraw()
            self.is_boss_hidden = True
        else:
            self.root.deiconify()
            self.is_boss_hidden = False

    def handle_auto_paste(self) -> None:
        """Instantly auto-pastes the clean solution or code into the user's active window."""
        text = self.expanded_view.get_output_text()
        if not text: return
        clean_text = CodeSandboxEngine.extract_clean_code_or_answer(text)
        
        # Step aside, focus target window, and inject paste event
        self.popup_win.withdraw()
        self.root.update()
        time.sleep(0.08)
        paste_into_active_window(clean_text)
        time.sleep(0.10)
        self.popup_win.deiconify()
        self.popup_win.lift()

    def run_in_sandbox(self, code_text: str) -> None:
        """Loads code into Sandbox and executes it."""
        self.open_mode("sandbox")
        self.sandbox_view.load_code(code_text)
        self.sandbox_view.run_code()

    def apply_opacity(self, opacity: float) -> None:
        try:
            op = max(0.10, min(1.0, opacity))
            self.popup_win.attributes("-alpha", op)
            self.config.opacity = op
            self.config.save()
        except Exception:
            pass

    def apply_topmost(self, topmost: bool) -> None:
        try:
            self.popup_win.attributes("-topmost", topmost)
            self.config.always_on_top = topmost
            self.config.save()
        except Exception:
            pass

    def apply_theme(self, theme_name: str) -> None:
        self.config.theme = theme_name
        self.config.save()
        self.t = THEMES.get(theme_name, THEMES["Light"])
        self.popup_win.configure(bg=self.t["bg"])
        self.hdr.configure(bg=self.t["card"])
        self.lbl_hdr_title.configure(bg=self.t["card"], fg=self.t["fg_dim"])
        self.btn_close.configure(bg=self.t["card"], fg=self.t["fg_dim"])
        self.btn_recess.configure(bg=self.t["card"], fg=self.t["fg_dim"])
        self.resize_grip.configure(bg=self.t["bg"], fg=self.t["fg_dim"])
        self.view_frame.configure(bg=self.t["bg"])
        
        # Destroy and recreate subviews with new theme
        current_mode = self._current_mode if hasattr(self, "_current_mode") else "expanded"
        for v in (self.expanded_view, self.history_view, self.sandbox_view, self.agent_view, self.palette_view, self.settings_view, self.permission_view, self.diagnostics_view, self.editor_view):
            v.destroy()
        self._create_subviews(theme_name)
        self.open_mode(current_mode)

    def _get_active_model_name(self) -> str:
        if self.config.ai_provider != "Ollama" and self.config.api_key.strip():
            return f"{self.config.ai_provider}:{self.config.api_model}"
        return self.config.ollama_model

    def cancel_generation(self) -> None:
        """Immediately stops the AI generation stream."""
        self._cancel_stream = True
        self.expanded_view.set_generating(False)
        self.expanded_view.append_output_stream("\n\n[🛑 Generation stopped by user]")

    def _setup_hotkeys(self) -> None:
        try:
            import keyboard
            keyboard.add_hotkey("ctrl+h", lambda: self.root.after(0, self.toggle_assistant))
            keyboard.add_hotkey("ctrl+shift+v", lambda: self.root.after(0, self.handle_auto_paste))
            keyboard.add_hotkey("ctrl+shift+g", lambda: self.root.after(0, self.toggle_ghost_mode))
            keyboard.add_hotkey("f1", lambda: self.root.after(0, self.toggle_boss_key))
            keyboard.add_hotkey(self.config.hotkey_clean_clipboard, self.quick_clean_clipboard)
            keyboard.add_hotkey(self.config.hotkey_next_block, self.editor_view.type_next_now)
        except Exception as e:
            print(f"[Overlay] Global hotkey registration note: {e}")

    def toggle_assistant(self) -> None:
        """Toggles the assistant popup appear, disappear, and reappear with Ctrl+H."""
        if self.popup_win and self.popup_win.winfo_viewable():
            self.popup_win.withdraw()
        else:
            self.summon_overlay()

    def summon_overlay(self) -> None:
        """Summons assistant popup near active cursor/focus and refreshes context."""
        self.root.after(0, self._do_summon)

    def _do_summon(self) -> None:
        self.open_mode("expanded")
        self.popup_win.deiconify()
        self.popup_win.lift()
        if self.is_recessed:
            self.toggle_recess()
        self.expanded_view.focus_input()

    def open_mode(self, mode: str) -> None:
        self._current_mode = mode
        for v in (self.expanded_view, self.history_view, self.sandbox_view, self.agent_view, self.palette_view, self.settings_view, self.permission_view, self.diagnostics_view, self.editor_view):
            v.pack_forget()
            
        if mode == "expanded":
            self.expanded_view.pack(fill=tk.BOTH, expand=True)
            self.expanded_view.focus_input()
        elif mode == "history":
            self.history_view.pack(fill=tk.BOTH, expand=True)
            self.history_view.refresh()
        elif mode == "sandbox":
            self.sandbox_view.pack(fill=tk.BOTH, expand=True)
        elif mode == "agent":
            self.agent_view.pack(fill=tk.BOTH, expand=True)
        elif mode == "palette":
            self.palette_view.pack(fill=tk.BOTH, expand=True)
            self.palette_view.focus_entry()
        elif mode == "settings":
            self.settings_view.pack(fill=tk.BOTH, expand=True)
        elif mode == "permissions":
            self.permission_view.pack(fill=tk.BOTH, expand=True)
        elif mode == "diagnostics":
            self.diagnostics_view.pack(fill=tk.BOTH, expand=True)
            self.diagnostics_view.refresh()
        elif mode == "editor":
            self.editor_view.pack(fill=tk.BOTH, expand=True)

    def handle_prompt(self, prompt: str, attach_screen: bool = False) -> None:
        """Handles streaming prompt request."""
        self._cancel_stream = False
        images = []
        
        if attach_screen:
            self.expanded_view.set_output("")
            self.popup_win.withdraw()
            self.root.update()
            time.sleep(0.12)
            app_ctx = self.context_engine.collect(self.root, include_screen=True)
            self.popup_win.deiconify()
            self.popup_win.lift()
                
            if app_ctx.screen and app_ctx.screen.ocr_text:
                ocr_len = len(app_ctx.screen.ocr_text)
                self.expanded_view.set_output(f"📷 Screen context attached ({ocr_len} characters extracted). Thinking with {self._get_active_model_name()}...\n\n")
                if app_ctx.screen.image_base64:
                    images.append(app_ctx.screen.image_base64)
                full_prompt = f"Screen Text:\n{app_ctx.screen.ocr_text}\n\nUser Question:\n{prompt}"
            else:
                self.expanded_view.set_output("⚠️ Screen text could not be extracted.\n\n")
                full_prompt = prompt
        else:
            full_prompt = prompt
            
        system_prompt = "You are a helpful, intelligent desktop AI assistant. Answer the user's questions, requests, and coding tasks accurately, directly, and clearly. If writing code, provide clean, complete, working code."
        
        import threading
        def _stream():
            start_t = time.perf_counter()
            full_out = []
            def on_token(t: str):
                full_out.append(t)
                self.root.after(0, lambda: self.expanded_view.append_output_stream(t))
                
            self.llm.generate_stream(
                full_prompt,
                system_prompt=system_prompt,
                images=images if images else None,
                on_token=on_token,
                cancel_check=lambda: self._cancel_stream
            )
            duration_ms = int((time.perf_counter() - start_t) * 1000)
            self.root.after(0, lambda: self.expanded_view.set_generating(False))
            # Save to SQLite history
            self.history_mgr.add_entry(
                model=self._get_active_model_name(),
                question_type="Prompt",
                question_text=prompt,
                answer_text="".join(full_out),
                duration_ms=duration_ms
            )
            
        threading.Thread(target=_stream, daemon=True).start()

    def handle_scan_and_solve(self) -> None:
        """One-click automated screen scanning and direct problem solving."""
        self._cancel_stream = False
        self.expanded_view.set_output("")
        self.popup_win.withdraw()
        self.root.update()
        time.sleep(0.12)
        app_ctx = self.context_engine.collect(self.root, include_screen=True)
        self.popup_win.deiconify()
        self.popup_win.lift()
        
        ocr_text = app_ctx.screen.ocr_text.strip() if (app_ctx.screen and app_ctx.screen.ocr_text) else ""
        if not ocr_text and app_ctx.clipboard_text:
            ocr_text = app_ctx.clipboard_text.strip()
            
        if not ocr_text:
            self.expanded_view.set_output(
                "⚠️ No readable text was detected on your screen.\n\n"
                "💡 Please make sure the question or window you want to solve is open and clearly visible on your monitor, then click '📸 Scan Screen' again."
            )
            self.expanded_view.set_generating(False)
            return
            
        ocr_len = len(ocr_text)
        self.expanded_view.set_output(f"✓ Screen scanned ({ocr_len} characters extracted via Windows OCR).\n🧠 Solving with {self._get_active_model_name()}...\n\n")
        
        images = []
        if app_ctx.screen and app_ctx.screen.image_base64:
            images.append(app_ctx.screen.image_base64)
            
        system_prompt = "You are an intelligent desktop assistant. Analyze the screen text and provide direct, accurate answers or working code solutions."
        full_prompt = f"Screen Text:\n{ocr_text}\n\nProvide the direct answer or solution."
        
        import threading
        def _stream_solve():
            start_t = time.perf_counter()
            full_out = []
            def on_token(t: str):
                full_out.append(t)
                self.root.after(0, lambda: self.expanded_view.append_output_stream(t))
                
            self.llm.generate_stream(
                full_prompt,
                system_prompt=system_prompt,
                images=images if images else None,
                on_token=on_token,
                cancel_check=lambda: self._cancel_stream
            )
            duration_ms = int((time.perf_counter() - start_t) * 1000)
            self.root.after(0, lambda: self.expanded_view.set_generating(False))
            # Save to SQLite history
            self.history_mgr.add_entry(
                model=self._get_active_model_name(),
                question_type="Screen Scan",
                question_text=ocr_text,
                answer_text="".join(full_out),
                duration_ms=duration_ms
            )
            
        threading.Thread(target=_stream_solve, daemon=True).start()

    def start_snip_and_solve(self) -> None:
        """Opens interactive green box snipper so user can select their exact question."""
        self._cancel_stream = False
        self.popup_win.withdraw()
        self.root.update()
        time.sleep(0.08)
        ScreenSnipper(self.root, on_snip_completed=self.handle_region_solve)

    def handle_region_solve(self, bbox: tuple) -> None:
        """Extracts OCR text from selected screen rectangle and solves the question directly."""
        self._cancel_stream = False
        self.popup_win.deiconify()
        self.popup_win.lift()
        self.expanded_view.set_output("🎯 Analyzing selected question region...\n")
        self.expanded_view.set_generating(True)
        
        screen_ctx = self.context_engine.screen_engine.capture_region(bbox, run_ocr=True)
        ocr_text = screen_ctx.ocr_text.strip() if screen_ctx else ""
        
        if not ocr_text:
            self.expanded_view.set_output("⚠️ No readable text detected in the selected box. Please drag a slightly larger box around the question.")
            self.expanded_view.set_generating(False)
            return
            
        ocr_len = len(ocr_text)
        self.expanded_view.set_output(f"✓ Question captured ({ocr_len} characters).\n🧠 Solving with {self._get_active_model_name()}...\n\n")
        
        system_prompt = "You are an intelligent desktop assistant. Analyze the captured question or coding problem and provide the direct, accurate answer or solution."
        full_prompt = ocr_text
        
        import threading
        def _stream_snip():
            start_t = time.perf_counter()
            full_out = []
            def on_token(t: str):
                full_out.append(t)
                self.root.after(0, lambda: self.expanded_view.append_output_stream(t))
                
            self.llm.generate_stream(
                full_prompt,
                system_prompt=system_prompt,
                on_token=on_token,
                cancel_check=lambda: self._cancel_stream
            )
            duration_ms = int((time.perf_counter() - start_t) * 1000)
            self.root.after(0, lambda: self.expanded_view.set_generating(False))
            # Save to SQLite history
            self.history_mgr.add_entry(
                model=self._get_active_model_name(),
                question_type="Snip & Solve",
                question_text=ocr_text,
                answer_text="".join(full_out),
                duration_ms=duration_ms
            )
            
        threading.Thread(target=_stream_snip, daemon=True).start()

    def handle_agent_task(self, prompt: str) -> None:
        """Handles agent multi-step execution."""
        self.open_mode("agent")
        app_ctx = self.context_engine.collect(self.root, include_screen=True)
        
        def on_step_update(steps):
            self.root.after(0, lambda: self.agent_view.update_steps(steps))
            
        def on_confirm_needed(msg):
            self.root.after(0, lambda: self.agent_view.request_confirmation(msg))
            
        def on_complete(summary):
            self.root.after(0, lambda: self.expanded_view.set_output(f"⚡ Task Completed:\n{summary}"))
            
        self.agent.run_agent_task(
            task_prompt=prompt,
            app_context=app_ctx,
            on_step_update=on_step_update,
            on_confirm_needed=on_confirm_needed,
            on_complete=on_complete,
            gui_root=self.root
        )

    def handle_palette_action(self, action_id: str) -> None:
        if action_id == "summarize":
            self.open_mode("expanded")
            self.handle_prompt("Summarize the active context and any copied text.")
        elif action_id == "clean_watermarks":
            self.quick_clean_clipboard()
            self.open_mode("expanded")
            self.expanded_view.set_output("✓ Clipboard cleaned! All invisible chars and homoglyphs normalized.")
        elif action_id == "explain_screen":
            self.open_mode("expanded")
            self.handle_scan_and_solve()
        elif action_id == "rewrite_professional":
            self.open_mode("expanded")
            self.handle_prompt("Rewrite the text in my clipboard to sound highly professional, crisp, and clean.")
        elif action_id == "block_typer":
            self.open_mode("editor")
            self.editor_view.start_block_typer()
        elif action_id == "history":
            self.open_mode("history")
        elif action_id == "sandbox":
            self.open_mode("sandbox")
        elif action_id == "settings":
            self.open_mode("settings")
        elif action_id == "diagnostics":
            self.open_mode("diagnostics")
        elif action_id == "permissions":
            self.open_mode("permissions")
        elif action_id.startswith("prompt:"):
            query = action_id.split("prompt:", 1)[1]
            self.open_mode("expanded")
            self.handle_prompt(query)

    def quick_clean_clipboard(self) -> None:
        tool = self.agent._tools.get("clean_watermarks")
        if tool:
            try:
                raw = self.root.clipboard_get()
                res = tool.execute({"text": raw})
                if res.success and res.output.get("cleaned_text"):
                    self.root.clipboard_clear()
                    self.root.clipboard_append(res.output["cleaned_text"])
            except Exception:
                pass
