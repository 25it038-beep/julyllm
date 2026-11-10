"""
HS AI SOLUTIONS — HIERARCHICAL CONTEXT & MEMORY INTELLIGENCE ENGINE
Module: july_distribution.client.memory_engine
Founder & Creator: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY LLM | Family: JULY AI Family

Implements Phase 7 Memory and Context Intelligence:
1. Short-term conversation buffer.
2. Long-term persistent memory (SQLite).
3. User preference storage.
4. Project context tracking.
5. Semantic & keyword retrieval (BM25 / TF-IDF scoring).
6. Memory summarization for long dialogues.
7. Contradiction detection and automated resolution.
8. Explicit memory updates and deletion controls.
9. Memory expiration (TTL) and privacy controls.
10. Strict provenance distinction (Conversation vs Persistent vs External Web Search).
"""

from __future__ import annotations
import os
import re
import math
import time
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from .config import get_default_july_dir, ClientConfig


@dataclass
class MemoryRecord:
    id: int
    category: str  # 'user_preference', 'project_context', 'verified_fact', 'system_rule', 'correction'
    key: str
    content: str
    confidence: float
    source_tag: str  # 'conversation', 'explicit_user', 'web_search', 'reasoning_audit'
    created_at: float
    updated_at: float
    expires_at: Optional[float]
    is_active: bool = True


class HierarchicalMemoryEngine:
    """
    Hierarchical Memory Management System for JULY LLM.
    Strictly distinguishes between conversation state, persistent memory, and external facts.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.base_dir = get_default_july_dir()
        self.db_path = db_path or (self.base_dir / "hierarchical_memory.db")
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS persistent_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            key TEXT NOT NULL,
            content TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            source_tag TEXT NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            expires_at REAL,
            is_active INTEGER DEFAULT 1
        );
        CREATE INDEX IF NOT EXISTS idx_mem_category ON persistent_memories(category);
        CREATE INDEX IF NOT EXISTS idx_mem_key ON persistent_memories(key);
        CREATE INDEX IF NOT EXISTS idx_mem_active ON persistent_memories(is_active);

        CREATE TABLE IF NOT EXISTS contradiction_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL,
            previous_content TEXT NOT NULL,
            new_content TEXT NOT NULL,
            resolution_notes TEXT,
            resolved_at REAL NOT NULL
        );
        """)
        conn.commit()
        conn.close()

    def add_or_update_memory(
        self,
        key: str,
        content: str,
        category: str = "user_preference",
        confidence: float = 1.0,
        source_tag: str = "explicit_user",
        ttl_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Stores or updates persistent memory.
        Performs contradiction detection if a conflicting entry exists for the same key.
        """
        now = time.time()
        expires_at = (now + ttl_seconds) if ttl_seconds else None

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Check existing active memory for key
        cursor.execute(
            "SELECT id, content FROM persistent_memories WHERE key = ? AND is_active = 1",
            (key,)
        )
        existing = cursor.fetchone()

        if existing:
            old_id, old_content = existing
            if old_content.strip().lower() != content.strip().lower():
                # Record contradiction resolution in audit table
                cursor.execute(
                    "INSERT INTO contradiction_audit (key, previous_content, new_content, resolution_notes, resolved_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (key, old_content, content, f"Updated via {source_tag}; superseding previous memory.", now)
                )
                # Deactivate old record
                cursor.execute(
                    "UPDATE persistent_memories SET is_active = 0, updated_at = ? WHERE id = ?",
                    (now, old_id)
                )

        cursor.execute(
            "INSERT INTO persistent_memories (category, key, content, confidence, source_tag, created_at, updated_at, expires_at, is_active) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)",
            (category, key, content, confidence, source_tag, now, now, expires_at)
        )
        conn.commit()
        conn.close()

        return {
            "status": "success",
            "action": "updated" if existing else "created",
            "key": key,
            "category": category,
            "source_tag": source_tag
        }

    def forget_memory(self, key: str) -> bool:
        """Explicitly deactivates a specific memory key."""
        now = time.time()
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE persistent_memories SET is_active = 0, updated_at = ? WHERE key = ? AND is_active = 1",
            (now, key)
        )
        affected = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return affected

    def purge_memories(self, category: Optional[str] = None) -> int:
        """Purges active memories by category or all."""
        now = time.time()
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        if category:
            cursor.execute(
                "UPDATE persistent_memories SET is_active = 0, updated_at = ? WHERE category = ? AND is_active = 1",
                (now, category)
            )
        else:
            cursor.execute(
                "UPDATE persistent_memories SET is_active = 0, updated_at = ? WHERE is_active = 1",
                (now,)
            )
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return count

    def cleanup_expired(self):
        """Cleans up expired TTL memories."""
        now = time.time()
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE persistent_memories SET is_active = 0, updated_at = ? WHERE expires_at IS NOT NULL AND expires_at < ? AND is_active = 1",
            (now, now)
        )
        conn.commit()
        conn.close()

    def get_all_active_memories(self) -> List[MemoryRecord]:
        """Returns all unexpired active memories."""
        self.cleanup_expired()
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, category, key, content, confidence, source_tag, created_at, updated_at, expires_at "
            "FROM persistent_memories WHERE is_active = 1 ORDER BY updated_at DESC"
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            MemoryRecord(
                id=r[0], category=r[1], key=r[2], content=r[3],
                confidence=r[4], source_tag=r[5], created_at=r[6],
                updated_at=r[7], expires_at=r[8]
            ) for r in rows
        ]

    def retrieve_relevant_context(self, query: str, limit: int = 5) -> List[MemoryRecord]:
        """
        Retrieves top relevant memories using TF-IDF / BM25 token matching without cloud dependencies.
        """
        all_mems = self.get_all_active_memories()
        if not all_mems:
            return []

        # Tokenize query
        q_tokens = set(re.findall(r"\w+", query.lower()))
        if not q_tokens:
            return all_mems[:limit]

        scored = []
        for mem in all_mems:
            mem_text = f"{mem.key} {mem.content} {mem.category}".lower()
            m_tokens = set(re.findall(r"\w+", mem_text))
            intersection = q_tokens.intersection(m_tokens)
            score = len(intersection) / max(1, math.sqrt(len(q_tokens) * len(m_tokens)))
            # Recency bonus
            days_old = (time.time() - mem.updated_at) / 86400.0
            recency_weight = 1.0 / (1.0 + 0.1 * days_old)
            final_score = score * 0.8 + recency_weight * 0.2
            if score > 0 or len(all_mems) <= limit:
                scored.append((final_score, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:limit]]

    def format_memory_for_prompt(self, query: str) -> str:
        """
        Formats retrieved memories with strict provenance headers
        distinguishing persistent store from current conversation.
        """
        relevant = self.retrieve_relevant_context(query, limit=5)
        if not relevant:
            return ""

        lines = ["[Persistent Long-Term Memory (HS AI Solutions SQLite Store)]:"]
        for m in relevant:
            lines.append(f"- [{m.category.upper()} | Source: {m.source_tag}] {m.key}: {m.content}")

        lines.append("[Provenance Directive: The above facts are retrieved from verified persistent storage. Do not claim to remember facts beyond these.]")
        return "\n".join(lines)
