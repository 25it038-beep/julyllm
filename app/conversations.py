"""
HS AI SOLUTIONS - JULY CONVERSATION STORAGE
SQLite-Backed Multi-Session Persistent Memory
Founder: Harshan Seliyan
"""

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.config import settings


class ConversationManager:
    """
    Manages persistent multi-turn conversations stored in SQLite.
    Safely separated from model weights and ephemeral container storage.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.CONVERSATION_DB_PATH
        # Ensure parent directory exists
        db_dir = os.path.dirname(os.path.abspath(self.db_path))
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
            except Exception:
                pass
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TEXT,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id)")
            conn.commit()

    def create_conversation(self, conversation_id: Optional[str] = None, title: Optional[str] = None) -> str:
        cid = conversation_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO conversations (conversation_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (cid, title or f"Conversation {cid[:8]}", now, now)
            )
            conn.commit()
        return cid

    def add_message(self, conversation_id: str, role: str, content: str) -> None:
        self.create_conversation(conversation_id)
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO messages (conversation_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (conversation_id, role, content, now)
            )
            cursor.execute(
                "UPDATE conversations SET updated_at = ? WHERE conversation_id = ?",
                (now, conversation_id)
            )
            conn.commit()

    def get_messages(self, conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content, timestamp FROM messages WHERE conversation_id = ? ORDER BY id ASC LIMIT ?",
                (conversation_id, limit)
            )
            rows = cursor.fetchall()
            return [{"role": r["role"], "content": r["content"], "timestamp": r["timestamp"]} for r in rows]

    def list_conversations(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.conversation_id, c.title, c.created_at, c.updated_at, COUNT(m.id) as message_count
                FROM conversations c
                LEFT JOIN messages m ON c.conversation_id = m.conversation_id
                GROUP BY c.conversation_id
                ORDER BY c.updated_at DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [
                {
                    "conversation_id": r["conversation_id"],
                    "title": r["title"],
                    "message_count": r["message_count"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"]
                }
                for r in rows
            ]

    def delete_conversation(self, conversation_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            cursor.execute("DELETE FROM conversations WHERE conversation_id = ?", (conversation_id,))
            conn.commit()
            return cursor.rowcount > 0


conversation_manager = ConversationManager()
