"""SQLite-backed Solution History and Markdown Export Engine."""

from __future__ import annotations
import sqlite3
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

HISTORY_DIR = Path.home() / ".universal_overlay"
DB_PATH = HISTORY_DIR / "history.db"

class HistoryManager:
    """Manages persistent SQLite storage of all scanned questions, generated code, and solutions."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._init_db()

    def _init_db(self) -> None:
        """Initializes the SQLite schema and indexes."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS solutions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    model TEXT NOT NULL,
                    question_type TEXT NOT NULL,
                    question_text TEXT,
                    answer_text TEXT NOT NULL,
                    duration_ms INTEGER DEFAULT 0
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON solutions(created_at DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_question_type ON solutions(question_type)")
            conn.commit()

    def add_entry(
        self,
        model: str,
        question_type: str,
        question_text: str,
        answer_text: str,
        duration_ms: int = 0
    ) -> int:
        """Saves a new question and solution entry to SQLite."""
        if not answer_text.strip():
            return -1
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO solutions (model, question_type, question_text, answer_text, duration_ms)
                VALUES (?, ?, ?, ?, ?)
            """, (model, question_type, question_text.strip(), answer_text.strip(), duration_ms))
            conn.commit()
            return cursor.lastrowid

    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetches recent solution entries."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, created_at, model, question_type, question_text, answer_text, duration_ms
                FROM solutions
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def search(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Performs full-text keyword search across question and answer bodies."""
        if not query.strip():
            return self.get_recent(limit)
        pattern = f"%{query.strip()}%"
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, created_at, model, question_type, question_text, answer_text, duration_ms
                FROM solutions
                WHERE question_text LIKE ? OR answer_text LIKE ? OR question_type LIKE ? OR model LIKE ?
                ORDER BY id DESC
                LIMIT ?
            """, (pattern, pattern, pattern, pattern, limit))
            return [dict(row) for row in cursor.fetchall()]

    def delete_entry(self, entry_id: int) -> bool:
        """Deletes a single entry by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM solutions WHERE id = ?", (entry_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_all(self) -> bool:
        """Clears entire history."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM solutions")
            conn.commit()
            return True

    def export_markdown(self, filepath: Path | str) -> bool:
        """Exports all history items to a clean, structured Markdown document."""
        entries = self.get_recent(limit=500)
        if not entries:
            return False
            
        md_lines = [
            "# Desktop AI Overlay - Solution History Export",
            f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Entries: {len(entries)}\n",
            "---",
            ""
        ]
        
        for idx, item in enumerate(entries, 1):
            md_lines.append(f"## {idx}. [{item['question_type'].upper()}] {item['created_at']} (Model: {item['model']})")
            if item.get("question_text"):
                md_lines.append("### Question / Screen Context:")
                md_lines.append(f"```\n{item['question_text']}\n```")
            md_lines.append("### Solution / Answer:")
            md_lines.append(f"{item['answer_text']}\n")
            md_lines.append("---\n")
            
        Path(filepath).write_text("\n".join(md_lines), encoding="utf-8")
        return True
