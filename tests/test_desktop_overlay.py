"""Unit tests for Universal Desktop AI Overlay system."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from desktop_overlay.config import OverlayConfig
from desktop_overlay.platform_layer.capability_matrix import CapabilityMatrix
from desktop_overlay.security.permissions import PermissionManager, PermissionType, PrivacyMode
from desktop_overlay.security.audit import AuditLogger
from desktop_overlay.agent.tools.text_clean_tool import TextCleanTool, extract_code_blocks, extract_clean_code_or_answer
from desktop_overlay.agent.tools.screen_tool import ScreenTool
from desktop_overlay.agent.llm_provider import LLMProvider
from desktop_overlay.agent.engine import AgentEngine
from desktop_overlay.context.active_window import ActiveWindowTracker
from desktop_overlay.history.history_manager import HistoryManager
from desktop_overlay.ui.overlay_window import CHAT_SYSTEM_PROMPT, SOLVER_SYSTEM_PROMPT

class TestDesktopOverlay(unittest.TestCase):
    
    def setUp(self):
        self.config = OverlayConfig()
        self.permissions = PermissionManager(self.config)
        self.audit = AuditLogger()
        self.llm = LLMProvider(self.config)
        self.agent = AgentEngine(self.llm, self.permissions, self.audit)

    def test_capability_matrix(self):
        matrix = CapabilityMatrix()
        summary = matrix.get_summary()
        self.assertIn("clipboard", summary)
        self.assertIn("screen_capture", summary)
        self.assertTrue(summary["clipboard"])

    def test_permission_manager_modes(self):
        # Default Balanced
        self.assertTrue(self.permissions.is_granted(PermissionType.SCREEN_CAPTURE))
        
        # Max Privacy
        self.permissions.apply_privacy_mode(PrivacyMode.MAXIMUM_PRIVACY)
        self.assertFalse(self.permissions.is_granted(PermissionType.SCREEN_CAPTURE))
        self.assertFalse(self.permissions.is_granted(PermissionType.INPUT_AUTOMATION))
        
        # Agent Mode
        self.permissions.apply_privacy_mode(PrivacyMode.AGENT_MODE)
        self.assertTrue(self.permissions.is_granted(PermissionType.INPUT_AUTOMATION))
        self.assertTrue(self.permissions.is_granted(PermissionType.SCREEN_CAPTURE))

    def test_audit_logger_redaction(self):
        secret_msg = "api_key=sk-1234567890abcdef12345678 password=SuperSecretPassword123"
        redacted = self.audit.redact(secret_msg)
        self.assertNotIn("SuperSecretPassword123", redacted)
        self.assertIn("***REDACTED***", redacted)

    def test_text_clean_tool(self):
        tool = TextCleanTool()
        dirty_text = "Hello\u200b world \u0430pple"
        res = tool.execute({"text": dirty_text})
        self.assertTrue(res.success)
        cleaned = res.output["cleaned_text"]
        self.assertNotIn("\u200b", cleaned)
        self.assertEqual(cleaned, "Hello world apple")

    def test_active_window_tracker(self):
        tracker = ActiveWindowTracker()
        ctx = tracker.get_current()
        self.assertIsNotNone(ctx.process_name)
        self.assertIsNotNone(ctx.app_category)

    def test_agent_task_planning(self):
        steps = self.agent._plan_task("clean watermark in clipboard", "")
        self.assertGreaterEqual(len(steps), 2)
        tool_names = [s.tool_name for s in steps]
        self.assertIn("clean_watermarks", tool_names)

    def test_history_manager_crud_and_export(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "test_history.db"
            hm = HistoryManager(db_path)
            
            # 1. Insert entries
            id1 = hm.add_entry(
                model="Qwen3.6:latest",
                question_type="MCQ",
                question_text="What is the capital of France?",
                answer_text="Answer: B) Paris",
                duration_ms=450
            )
            id2 = hm.add_entry(
                model="phi3",
                question_type="Coding",
                question_text="Reverse a string in Python",
                answer_text="```python\ndef rev(s): return s[::-1]\n```",
                duration_ms=800
            )
            self.assertGreater(id1, 0)
            self.assertGreater(id2, 0)
            
            # 2. Search
            results = hm.search("Paris")
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["model"], "Qwen3.6:latest")
            
            # 3. Export to Markdown
            export_file = Path(tmp_dir) / "export.md"
            ok = hm.export_markdown(export_file)
            self.assertTrue(ok)
            self.assertTrue(export_file.exists())
            content = export_file.read_text(encoding="utf-8")
            self.assertIn("Solution History Export", content)
            self.assertIn("Paris", content)

    def test_code_and_answer_extraction(self):
        # Test 1: Code block extraction
        md = "Here is the code:\n```python\nprint('hello')\n```\nAnd done."
        blocks = extract_code_blocks(md)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["code"], "print('hello')")
        
        # Test 2: Clean code/answer extractor for code block
        clean = extract_clean_code_or_answer(md)
        self.assertEqual(clean, "print('hello')")
        
        # Test 3: Clean answer extractor for MCQ
        mcq_ans = "**Answer: B) Stack**"
        clean_mcq = extract_clean_code_or_answer(mcq_ans)
        self.assertIn("B) Stack", clean_mcq)

    def test_system_prompts_separation(self):
        # Ensure CHAT_SYSTEM_PROMPT is conversational and doesn't force MCQ formatting
        self.assertIn("ChatGPT", CHAT_SYSTEM_PROMPT)
        self.assertNotIn("**Answer:", CHAT_SYSTEM_PROMPT)
        
        # Ensure SOLVER_SYSTEM_PROMPT includes explicit instructions for MCQs and open-ended questions
        self.assertIn("MULTIPLE CHOICE", SOLVER_SYSTEM_PROMPT)
        self.assertIn("OPEN-ENDED", SOLVER_SYSTEM_PROMPT)

    def test_settings_and_history_ui_instantiation(self):
        import tkinter as tk
        from desktop_overlay.ui.settings_ui import SettingsPanel
        from desktop_overlay.ui.history_view import HistoryView
        
        root = tk.Tk()
        root.withdraw()
        try:
            # 1. Test SettingsPanel
            settings = SettingsPanel(
                root,
                config=self.config,
                on_opacity_change=lambda o: None,
                on_topmost_change=lambda t: None,
                on_theme_change=lambda th: None,
                on_close=lambda: None
            )
            settings.pack(fill=tk.BOTH, expand=True)
            root.update_idletasks()
            
            # Verify canvas window width is positive and not collapsed
            self.assertGreaterEqual(settings.canvas.winfo_width(), 0)
            self.assertIsNotNone(settings.provider_var.get())
            self.assertIsNotNone(settings.key_entry.get())
            
            # 2. Test HistoryView
            history_v = HistoryView(
                root,
                history_mgr=HistoryManager(),
                on_back=lambda: None
            )
            history_v.pack(fill=tk.BOTH, expand=True)
            root.update_idletasks()
            self.assertGreaterEqual(history_v.canvas.winfo_width(), 0)
        finally:
            root.destroy()

    def test_cloud_provider_config(self):
        cfg = OverlayConfig()
        cfg.ai_provider = "Groq"
        cfg.api_key = "gsk_test123456789"
        cfg.api_model = "llama-3.3-70b-versatile"
        
        llm = LLMProvider(cfg)
        self.assertEqual(llm.config.ai_provider, "Groq")
        self.assertEqual(llm.config.api_key, "gsk_test123456789")

if __name__ == "__main__":
    unittest.main()

