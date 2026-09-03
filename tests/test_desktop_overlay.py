"""Unit tests for Universal Desktop AI Overlay system."""

import os
import sys
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
from desktop_overlay.agent.tools.text_clean_tool import TextCleanTool
from desktop_overlay.agent.tools.screen_tool import ScreenTool
from desktop_overlay.agent.llm_provider import LLMProvider
from desktop_overlay.agent.engine import AgentEngine
from desktop_overlay.context.active_window import ActiveWindowTracker

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
        # Text with zero width space (\u200b) and Cyrillic 'а' (\u0430)
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

if __name__ == "__main__":
    unittest.main()
