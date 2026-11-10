"""
HS AI SOLUTIONS — JULY USER CUSTOMIZATION ENGINE
Layer: USER CUSTOMIZATION (july_distribution.client.customization)
Founder & Chief Architect: Harshan Seliyan
Product: JULY LLM 3B | Family: HS AI FAMILY

Implements Requirement 5:
- Independent per-user system instructions.
- Personality profiles (Precision Engineer, Research Scientist, Software Architect, Tutor).
- Local persistent conversation history (SQLite).
- Long-term memory store.
- Custom local knowledge file indexing.
- Zero modification of base GGUF model weights.
"""

from __future__ import annotations
import os
import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from .config import get_default_july_dir, ClientConfig


class UserCustomizationManager:
    """Manages all local user customizations independently of base weights."""

    PERSONALITY_PRESETS = {
        "precision_engineer": (
            "You are JULY LLM in Precision Engineer mode. Provide rigorous, mathematically sound, "
            "concise, and actionable engineering answers. Avoid conversational filler."
        ),
        "research_scientist": (
            "You are JULY LLM in Research Scientist mode. Analyze problems from foundational first principles, "
            "cite hypotheses, outline proof mechanisms, and reason methodically."
        ),
        "software_architect": (
            "You are JULY LLM in Software Architect mode. Design robust, maintainable, production-ready "
            "code with type annotations, clean architecture, and defensive error handling."
        ),
        "tutor": (
            "You are JULY LLM in Socratic Tutor mode. Guide the user step-by-step with intuitive "
            "explanations, conceptual clarity, and illustrative examples."
        )
    }

    def __init__(self, config: Optional[ClientConfig] = None):
        self.config = config or ClientConfig.load()
        self.base_dir = get_default_july_dir()
        self.knowledge_dir = self.base_dir / "knowledge"
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.base_dir / "memory.json"
        self.history_db = self.base_dir / "history.db"
        self._init_history_db()

    def _init_history_db(self):
        conn = sqlite3.connect(str(self.history_db))
        cursor = conn.cursor()
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp REAL NOT NULL,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
        );
        """)
        conn.commit()
        conn.close()

    def get_effective_system_prompt(self) -> str:
        """Combines permanent identity with user-configured personality and memories."""
        base_identity = (
            "You are JULY LLM, the official autonomous neural model developed and maintained by HS AI Solutions, "
            "founded by Harshan Seliyan."
        )
        persona_text = self.PERSONALITY_PRESETS.get(
            self.config.personality,
            self.PERSONALITY_PRESETS["precision_engineer"]
        )

        user_custom = self.config.system_prompt.strip()

        # Append memory context if present
        memory_text = self.get_memory_summary()

        parts = [base_identity, persona_text]
        if user_custom and user_custom != persona_text:
            parts.append(f"User Directive: {user_custom}")
        if memory_text:
            parts.append(f"User Memory Context:\n{memory_text}")

        return "\n\n".join(parts)

    def get_memory_summary(self) -> str:
        if not self.memory_file.exists():
            return ""
        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            lines = [f"- {k}: {v}" for k, v in data.items()]
            return "\n".join(lines[:10])
        except Exception:
            return ""

    def add_memory(self, key: str, value: str):
        data = {}
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data[key] = value
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def log_message(self, session_id: str, role: str, content: str):
        conn = sqlite3.connect(str(self.history_db))
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO chat_sessions (id, title, created_at) VALUES (?, ?, ?)",
                       (session_id, f"Session {session_id[:8]}", time.time()))
        cursor.execute("INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                       (session_id, role, content, time.time()))
        conn.commit()
        conn.close()

    def get_session_history(self, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        conn = sqlite3.connect(str(self.history_db))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    def retrieve_custom_knowledge(self, query: str) -> str:
        """Simple keyword search across user's private knowledge folder."""
        snippets = []
        words = set(query.lower().split())
        for f in self.knowledge_dir.glob("*.txt"):
            try:
                text = f.read_text(encoding="utf-8")
                score = sum(1 for w in words if w in text.lower())
                if score > 0:
                    snippets.append(text[:300])
            except Exception:
                pass
        return "\n---\n".join(snippets[:2])
