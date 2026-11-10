"""
HS AI SOLUTIONS — UNIVERSAL CONVERSATION & DATA STORE
Module: hs_ecosystem.storage.conversation_store
Founder: Harshan Seliyan | Organization: HS AI Solutions
Product: HS AI ECOSYSTEM (JULY LLM & GRAVITY LLM)

Manages local-first conversations with model-specific isolation (July vs Gravity),
history filtering, and JSON/Markdown export/import.
"""

from __future__ import annotations
import os
import sqlite3
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class ConversationSession:
    id: str
    title: str
    model_id: str  # "july" or "gravity"
    created_at: float
    updated_at: float
    system_prompt_snapshot: str


@dataclass
class ChatMessage:
    id: int
    session_id: str
    role: str
    content: str
    model_id: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class UniversalConversationStore:
    """SQLite-backed conversation manager enforcing model identity boundaries."""

    def __init__(self, db_path: Optional[Path] = None):
        self.repo_root = Path(__file__).resolve().parent.parent.parent
        self.db_path = db_path or (self.repo_root / "ecosystem_conversations.db")
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            model_id TEXT NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            system_prompt_snapshot TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_model ON sessions(model_id);

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            model_id TEXT NOT NULL,
            timestamp REAL NOT NULL,
            metadata_json TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );
        CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
        """)
        conn.commit()
        conn.close()

    def create_session(self, session_id: str, title: str, model_id: str, system_prompt: str = "") -> ConversationSession:
        now = time.time()
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO sessions (id, title, model_id, created_at, updated_at, system_prompt_snapshot) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, title, model_id.lower(), now, now, system_prompt)
        )
        conn.commit()
        conn.close()
        return ConversationSession(session_id, title, model_id.lower(), now, now, system_prompt)

    def log_message(self, session_id: str, role: str, content: str, model_id: str, metadata: Optional[Dict[str, Any]] = None):
        now = time.time()
        meta_str = json.dumps(metadata or {})
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute(
            "INSERT INTO messages (session_id, role, content, model_id, timestamp, metadata_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, role, content, model_id.lower(), now, meta_str)
        )
        c.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
        conn.commit()
        conn.close()

    def list_sessions(self, model_filter: Optional[str] = None) -> List[ConversationSession]:
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        if model_filter and model_filter.lower() in ("july", "gravity"):
            c.execute("SELECT id, title, model_id, created_at, updated_at, system_prompt_snapshot FROM sessions WHERE model_id = ? ORDER BY updated_at DESC", (model_filter.lower(),))
        else:
            c.execute("SELECT id, title, model_id, created_at, updated_at, system_prompt_snapshot FROM sessions ORDER BY updated_at DESC")
        rows = c.fetchall()
        conn.close()
        return [ConversationSession(*r) for r in rows]

    def get_messages(self, session_id: str) -> List[ChatMessage]:
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("SELECT id, session_id, role, content, model_id, timestamp, metadata_json FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
        rows = c.fetchall()
        conn.close()
        return [ChatMessage(r[0], r[1], r[2], r[3], r[4], r[5], json.loads(r[6] or "{}")) for r in rows]

    def export_session_markdown(self, session_id: str) -> str:
        messages = self.get_messages(session_id)
        if not messages:
            return ""
        model_name = messages[0].model_id.upper()
        lines = [
            f"# Conversation Export: {session_id}",
            f"**Model**: {model_name} LLM | **Platform**: HS AI Solutions",
            "---\n"
        ]
        for m in messages:
            sender = "User" if m.role == "user" else f"{m.model_id.upper()} LLM"
            lines.append(f"### {sender} ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(m.timestamp))}):")
            lines.append(m.content)
            lines.append("")
        return "\n".join(lines)
