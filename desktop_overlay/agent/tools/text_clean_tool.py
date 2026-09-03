"""Text cleaning & watermark removal tool for AI agent."""

from __future__ import annotations
import sys
from pathlib import Path
from typing import Any
from desktop_overlay.agent.tools.base import BaseTool, ToolResult

# Import clean_text from service scripts if available
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "service" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from text_unicode import clean_text
except ImportError:
    try:
        from service.scripts.text_unicode import clean_text
    except ImportError:
        def clean_text(text, **kwargs):
            return text, {"removed_count": 0, "replaced_count": 0, "input_length": len(text), "output_length": len(text)}

class TextCleanTool(BaseTool):
    name = "clean_watermarks"
    description = "Removes hidden zero-width spaces, invisible characters, and Unicode homoglyphs from text."
    required_permission = None
    is_high_impact = False

    def execute(self, params: dict, context: Any = None) -> ToolResult:
        text = params.get("text", "")
        if not text:
            return ToolResult(success=False, output="", error="No text provided to clean")
            
        try:
            cleaned, stats = clean_text(text, nfkc=True, aggressive_homoglyphs=True)
            rem = stats.get("removed_count", 0)
            rep = stats.get("replaced_count", 0)
            return ToolResult(
                success=True,
                output={"cleaned_text": cleaned, "stats": stats},
                action_description=f"Removed {rem} hidden chars and normalized {rep} homoglyphs"
            )
        except Exception as e:
            return ToolResult(success=False, output=text, error=str(e))
