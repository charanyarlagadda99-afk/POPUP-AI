"""Audit Logging System with sensitive data redaction."""

from __future__ import annotations
import re
import time
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from desktop_overlay.config import CONFIG_DIR

AUDIT_LOG_FILE = CONFIG_DIR / "audit_log.jsonl"

@dataclass
class AuditEntry:
    timestamp: float
    action: str
    tool_name: str
    details: str
    status: str
    user_confirmed: bool

class AuditLogger:
    """Logs agent actions and tool calls with automated secret scrubbing."""
    
    SECRET_PATTERNS = [
        re.compile(r'(?i)(?:password|passwd|pwd|secret|token|api[_-]?key)\s*[:=]\s*["\']?([^"\'\s]+)'),
        re.compile(r'Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*'),
        re.compile(r'sk-[a-zA-Z0-9]{20,}')
    ]

    def __init__(self):
        self.entries: list[AuditEntry] = []
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def redact(self, text: str) -> str:
        if not text:
            return ""
        redacted = str(text)
        for pattern in self.SECRET_PATTERNS:
            redacted = pattern.sub(r'***REDACTED***', redacted)
        return redacted

    def log(self, action: str, tool_name: str = "", details: str = "", status: str = "success", user_confirmed: bool = False) -> None:
        entry = AuditEntry(
            timestamp=time.time(),
            action=action,
            tool_name=tool_name,
            details=self.redact(details),
            status=status,
            user_confirmed=user_confirmed
        )
        self.entries.append(entry)
        if len(self.entries) > 200:
            self.entries.pop(0)
            
        try:
            with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(entry)) + "\n")
        except Exception as e:
            print(f"[Audit] Failed to write log: {e}")

    def get_recent(self, count: int = 50) -> list[AuditEntry]:
        return self.entries[-count:]
