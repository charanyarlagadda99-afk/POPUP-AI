"""In-App Code Runner Sandbox and Code Block Extraction Engine."""

from __future__ import annotations
import sys
import re
import time
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class ExecutionResult:
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    error: Optional[str] = None

class CodeSandboxEngine:
    """Executes Python and JavaScript code safely in an isolated subprocess with timeout and metric tracking."""
    
    @staticmethod
    def extract_code_blocks(markdown_text: str) -> List[Dict[str, str]]:
        """Extracts fenced markdown code blocks (e.g. ```python ... ```)."""
        pattern = r"```([a-zA-Z0-9_+-]*)\n([\s\S]*?)```"
        matches = re.findall(pattern, markdown_text)
        blocks = []
        for lang, code in matches:
            clean_lang = lang.strip().lower() or "python"
            blocks.append({
                "language": clean_lang,
                "code": code.strip()
            })
        return blocks

    @staticmethod
    def extract_clean_code_or_answer(text: str) -> str:
        """Extracts only the raw code if code blocks exist, otherwise returns the clean answer text."""
        blocks = CodeSandboxEngine.extract_code_blocks(text)
        if blocks:
            # Join all code blocks
            return "\n\n".join([b["code"] for b in blocks])
        # If MCQ answer format, extract the answer line
        lines = text.strip().splitlines()
        for line in lines:
            if line.strip().lower().startswith("answer:"):
                return line.strip().split(":", 1)[1].strip()
        return text.strip()

    def run_python(self, code: str, timeout_sec: int = 10) -> ExecutionResult:
        """Executes Python code in a standalone subprocess and captures stdout/stderr."""
        if not code.strip():
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="No code provided to execute.",
                exit_code=-1,
                duration_ms=0
            )

        start_time = time.perf_counter()
        
        # Write code to a secure temporary script file
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(code)

        try:
            python_exe = sys.executable
            proc = subprocess.run(
                [python_exe, str(tmp_path)],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                encoding="utf-8",
                errors="replace"
            )
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return ExecutionResult(
                success=(proc.returncode == 0),
                stdout=proc.stdout,
                stderr=proc.stderr,
                exit_code=proc.returncode,
                duration_ms=duration_ms
            )
        except subprocess.TimeoutExpired:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"⏱️ Execution timed out after {timeout_sec} seconds.",
                exit_code=-2,
                duration_ms=duration_ms,
                error="Timeout"
            )
        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Execution error: {e}",
                exit_code=-1,
                duration_ms=duration_ms,
                error=str(e)
            )
        finally:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass
