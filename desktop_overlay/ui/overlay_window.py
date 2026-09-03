"""Master Floating Overlay Window Manager with Permanent Dot, Recess/Extend, Settings, and Direct OCR Solving."""

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
from desktop_overlay.context.context_engine import ContextEngine, ApplicationContext
from desktop_overlay.agent.llm_provider import LLMProvider
from desktop_overlay.agent.engine import AgentEngine

from desktop_overlay.ui.compact_mode import CompactLauncher
from desktop_overlay.ui.expanded_mode import ExpandedAssistantView
from desktop_overlay.ui.agent_mode import AgentExecutionView
from desktop_overlay.ui.command_palette import CommandPalette
from desktop_overlay.ui.permission_ui import PermissionCenter
from desktop_overlay.ui.diagnostics_ui import DiagnosticsPanel
from desktop_overlay.ui.editor_view import EditorToolsView
from desktop_overlay.ui.settings_ui import SettingsPanel

class DesktopOverlayWindow:
    """Universal Desktop AI Overlay Window with permanent floating dot, Recess/Extend, and direct problem solver."""
    
    def __init__(self, root: tk.Tk, config: Optional[OverlayConfig] = None):
        self.root = root
        self.config = config or OverlayConfig.load()
        self.t = THEMES.get(self.config.theme, THEMES["Light"])
        
        # State
        self._cancel_stream = False
        self.is_recessed = False
        self._saved_height = max(520, self.config.overlay_height)
        
        # Core Subsystems
        self.capabilities = CapabilityMatrix()
        self.permissions = PermissionManager(self.config)
        self.audit = AuditLogger()
        self.context_engine = ContextEngine(self.permissions)
        self.llm = LLMProvider(self.config)
        self.agent = AgentEngine(self.llm, self.permissions, self.audit)
        
        # 1. PERMANENT FLOATING DOT (ROOT WINDOW)
        self.root.title("AI Dot")
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
        self.popup_win.title("Universal Desktop AI Assistant")
        self.popup_win.overrideredirect(True)
        self.popup_win.attributes("-topmost", self.config.always_on_top)
        self.popup_win.attributes("-alpha", self.config.opacity)
        self.popup_win.configure(bg=self.t["bg"])
        
        # Position assistant window centered
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w, h = max(600, self.config.overlay_width), max(520, self.config.overlay_height)
        pos_x = max(20, min(sw - w - 20, (sw - w) // 2))
        pos_y = max(20, min(sh - h - 20, (sh - h) // 2))
        self.popup_win.geometry(f"{w}x{h}+{pos_x}+{pos_y}")
        
        # Drag handle / Header
        self.hdr = tk.Frame(self.popup_win, bg=self.t["card"], height=30, cursor="fleur")
        self.hdr.pack(fill=tk.X)
        
        self.lbl_hdr_title = tk.Label(self.hdr, text="✦ Desktop AI Assistant", bg=self.t["card"], fg=self.t["fg_dim"], font=("Segoe UI", 9, "bold"))
        self.lbl_hdr_title.pack(side=tk.LEFT, padx=10)
        
        # Window controls: Close & Recess/Extend button
        self.btn_close = tk.Label(self.hdr, text="✕", bg=self.t["card"], fg=self.t["fg_dim"], font=("Segoe UI", 10), cursor="hand2")
        self.btn_close.pack(side=tk.RIGHT, padx=(4, 10))
        self.btn_close.bind("<Button-1>", lambda e: self.popup_win.withdraw())
        
        # RECESS / EXTEND BUTTON (Compress down to slim bar or decompress back up)
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
        
        # Views
        self.expanded_view = ExpandedAssistantView(
            self.view_frame,
            config=self.config,
            on_send_prompt=self.handle_prompt,
            on_scan_solve=self.handle_scan_and_solve,
            on_stop=self.cancel_generation,
            on_run_agent=self.handle_agent_task,
            on_open_palette=lambda: self.open_mode("palette"),
            on_open_settings=lambda: self.open_mode("settings"),
            on_open_permissions=lambda: self.open_mode("permissions"),
            on_open_diagnostics=lambda: self.open_mode("diagnostics"),
            on_open_editor=lambda: self.open_mode("editor"),
            theme_name=self.config.theme
        )
        
        self.agent_view = AgentExecutionView(
            self.view_frame,
            on_cancel=self.agent.cancel,
            on_confirm=self.agent.confirm_action,
            theme_name=self.config.theme
        )
        
        self.palette_view = CommandPalette(
            self.view_frame,
            on_action=self.handle_palette_action,
            theme_name=self.config.theme
        )
        
        self.settings_view = SettingsPanel(
            self.view_frame,
            config=self.config,
            on_opacity_change=self.apply_opacity,
            on_topmost_change=self.apply_topmost,
            on_theme_change=self.apply_theme,
            on_close=lambda: self.open_mode("expanded"),
            theme_name=self.config.theme
        )
        
        self.permission_view = PermissionCenter(
            self.view_frame,
            permissions=self.permissions,
            on_close=lambda: self.open_mode("expanded"),
            theme_name=self.config.theme
        )
        
        self.diagnostics_view = DiagnosticsPanel(
            self.view_frame,
            context_engine=self.context_engine,
            capabilities=self.capabilities,
            audit=self.audit,
            on_close=lambda: self.open_mode("expanded"),
            theme_name=self.config.theme
        )
        
        self.editor_view = EditorToolsView(
            self.view_frame,
            theme_name=self.config.theme
        )
        
        # Bottom-Right Resize Grip
        self.resize_grip = tk.Label(self.popup_win, text="⋰", bg=self.t["bg"], fg=self.t["fg_dim"], font=("Segoe UI", 9), cursor="size_nw_se")
        self.resize_grip.place(relx=1.0, rely=1.0, anchor="se", x=-2, y=-2)
        self.resize_grip.bind("<Button-1>", self._start_resize)
        self.resize_grip.bind("<B1-Motion>", self._do_resize)
        
        # Start withdrawn so only the dot is initially visible
        self.popup_win.withdraw()
        self.open_mode("expanded")

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
            # Compress / Recess
            self._saved_height = max(400, self.popup_win.winfo_height())
            self.view_frame.pack_forget()
            self.resize_grip.place_forget()
            w = self.popup_win.winfo_width()
            self.popup_win.geometry(f"{w}x32")
            self.btn_recess.config(text="▼ Extend", fg=self.t["accent"])
            self.is_recessed = True
        else:
            # Decompress / Extend
            w = self.popup_win.winfo_width()
            h = self._saved_height
            self.popup_win.geometry(f"{w}x{h}")
            self.view_frame.pack(fill=tk.BOTH, expand=True)
            self.resize_grip.place(relx=1.0, rely=1.0, anchor="se", x=-2, y=-2)
            self.btn_recess.config(text="▲ Recess", fg=self.t["fg_dim"])
            self.is_recessed = False

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
        # Update popup window background and controls
        self.popup_win.configure(bg=self.t["bg"])
        self.hdr.configure(bg=self.t["card"])
        self.lbl_hdr_title.configure(bg=self.t["card"], fg=self.t["fg_dim"])
        self.btn_close.configure(bg=self.t["card"], fg=self.t["fg_dim"])
        self.btn_recess.configure(bg=self.t["card"], fg=self.t["fg_dim"])
        self.resize_grip.configure(bg=self.t["bg"], fg=self.t["fg_dim"])

    def cancel_generation(self) -> None:
        """Immediately stops the AI generation stream."""
        self._cancel_stream = True
        self.expanded_view.set_generating(False)
        self.expanded_view.append_output_stream("\n\n[🛑 Generation stopped by user]")

    def _setup_hotkeys(self) -> None:
        try:
            import keyboard
            # Ctrl+H toggles popup appear/disappear/reappear
            keyboard.add_hotkey("ctrl+h", lambda: self.root.after(0, self.toggle_assistant))
            if self.config.hotkey_summon.lower() != "ctrl+h":
                keyboard.add_hotkey(self.config.hotkey_summon, lambda: self.root.after(0, self.toggle_assistant))
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
        app_ctx = self.context_engine.collect(self.root)
        self.open_mode("expanded")
        self.popup_win.deiconify()
        self.popup_win.lift()
        if self.is_recessed:
            self.toggle_recess()
        self.expanded_view.update_context_badge(app_ctx)
        self.expanded_view.focus_input()

    def open_mode(self, mode: str) -> None:
        for v in (self.expanded_view, self.agent_view, self.palette_view, self.settings_view, self.permission_view, self.diagnostics_view, self.editor_view):
            v.pack_forget()
            
        if mode == "expanded":
            self.expanded_view.pack(fill=tk.BOTH, expand=True)
            self.expanded_view.focus_input()
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
        """Handles streaming prompt request without blinking or hiding the popup window."""
        self._cancel_stream = False
        images = []
        is_screen_solve = False
        
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
                self.expanded_view.set_output(f"📷 Screen scanned ({ocr_len} characters extracted). Analyzing with {self.config.ollama_model}...\n\n")
                is_screen_solve = True
            else:
                self.expanded_view.set_output("⚠️ Screen text could not be extracted.\n\n")
        else:
            app_ctx = self.context_engine.collect(self.root, include_screen=False)
            
        context_prefix = app_ctx.to_prompt_context()
        system_prompt = "You are an intelligent desktop assistant. Provide direct, concise, and accurate answers with no fluff."
        if is_screen_solve:
            system_prompt = (
                "You are a direct question answering engine. "
                "Examine the extracted screen text. If there is a question or MCQ on the screen, "
                "identify the question and provide ONLY the direct answer/option without lengthy explanations or filler."
            )
            
        full_prompt = f"Desktop Context:\n{context_prefix}\n\nUser Request: {prompt}\nAnswer:" if context_prefix else prompt
        
        import threading
        def _stream():
            def on_token(t: str):
                self.root.after(0, lambda: self.expanded_view.append_output_stream(t))
                
            self.llm.generate_stream(
                full_prompt,
                system_prompt=system_prompt,
                images=images if images else None,
                on_token=on_token,
                cancel_check=lambda: self._cancel_stream
            )
            self.root.after(0, lambda: self.expanded_view.set_generating(False))
            
        threading.Thread(target=_stream, daemon=True).start()

    def handle_scan_and_solve(self) -> None:
        """One-click automated screen scanning and direct problem solving."""
        self._cancel_stream = False
        # Step aside to cleanly unblock the desktop for OCR
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
                "💡 Please make sure the question or window you want to solve is open and clearly visible on your monitor, then click '📸 Scan & Solve Screen' again."
            )
            self.expanded_view.set_generating(False)
            return
            
        ocr_len = len(ocr_text)
        self.expanded_view.set_output(f"✓ Screen scanned ({ocr_len} characters extracted via Windows OCR).\n🧠 Solving with {self.config.ollama_model}...\n\n")
        
        images = []
        if app_ctx.screen and app_ctx.screen.image_base64:
            images.append(app_ctx.screen.image_base64)
            
        system_prompt = (
            "You are an ultra-direct Question and MCQ answering engine.\n"
            "Analyze the provided screen text, find the primary question or multiple-choice question (MCQ), and output strictly:\n\n"
            "Question: <The exact question found on screen>\n"
            "Answer: <Direct Option and Answer ONLY>\n\n"
            "RULES:\n"
            "- If MCQ: Give ONLY the correct Option Letter and text (e.g. 'Answer: B) Paris' or 'Answer: Option A'). No explanation.\n"
            "- If open question: Give ONLY the direct concise answer. No explanation.\n"
            "- Ignore any terminal commands, file paths, or IDE menus.\n"
            "- Do not write reasoning or conversational preamble."
        )
        full_prompt = (
            f"Screen Text:\n"
            f"----------------------------------------\n"
            f"{ocr_text}\n"
            f"----------------------------------------\n\n"
            f"TASK: Find the question in the screen text above and provide the direct answer.\n"
        )
        
        import threading
        def _stream_solve():
            def on_token(t: str):
                self.root.after(0, lambda: self.expanded_view.append_output_stream(t))
                
            self.llm.generate_stream(
                full_prompt,
                system_prompt=system_prompt,
                images=images if images else None,
                on_token=on_token,
                cancel_check=lambda: self._cancel_stream
            )
            self.root.after(0, lambda: self.expanded_view.set_generating(False))
            
        threading.Thread(target=_stream_solve, daemon=True).start()

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
