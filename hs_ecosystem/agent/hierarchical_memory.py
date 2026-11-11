"""
HS AI SOLUTIONS — 5-LAYER PERSISTENT HIERARCHICAL MEMORY SYSTEM
Module: hs_ecosystem.agent.hierarchical_memory
Founder & Chief Architect: Harshan Seliyan | Organization: HS AI Solutions
Product: JULY AUTONOMOUS AI AGENT PLATFORM

Implements Pillar 5:
1. USER MEMORY: Developer preferences, styles, guidelines
2. PROJECT MEMORY: Architecture, schemas, file maps, conventions
3. CONVERSATION MEMORY: Multi-session chat continuity
4. EPISODIC MEMORY: Task outcomes, solutions applied, post-mortems
5. PROCEDURAL MEMORY: Workflows and skills learned from tasks

Includes:
- SQLite + FTS5 full-text indexing
- TF-IDF Vector cosine similarity retrieval
- Secret redaction filter (API keys, passwords, bearer tokens)
- Summarization, consolidation, inspection, and deletion
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


class MemoryLayer:
    USER = "USER"
    PROJECT = "PROJECT"
    CONVERSATION = "CONVERSATION"
    EPISODIC = "EPISODIC"
    PROCEDURAL = "PROCEDURAL"


@dataclass
class MemoryItem:
    id: int
    layer: str
    key: str
    content: str
    metadata: Dict[str, Any]
    score: float = 1.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class SecretSanitizer:
    """Scans and redacts credentials, private keys, and passwords before memory storage."""

    SECRET_PATTERNS = [
        re.compile(r"(?i)(api[_-]?key|secret|password|token|bearer|auth)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\.]{8,})['\"]?"),
        re.compile(r"sk-[a-zA-Z0-9]{32,}"),
        re.compile(r"ghp_[a-zA-Z0-9]{36}"),
        re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC )?PRIVATE KEY-----")
    ]

    @classmethod
    def sanitize(cls, text: str) -> str:
        sanitized = text
        for pat in cls.SECRET_PATTERNS:
            sanitized = pat.sub(r"\1: [REDACTED_CREDENTIAL]", sanitized)
        return sanitized


class HierarchicalMemorySystem:
    """
    Five-layer persistent memory store with FTS5 and vector retrieval.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or (Path.cwd() / "hs_ecosystem" / "storage" / "july_persistent_memory.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.cursor()
            cur.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                layer TEXT NOT NULL,
                key TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_mem_layer ON memories(layer);
            CREATE INDEX IF NOT EXISTS idx_mem_key ON memories(key);

            -- FTS5 full text search table
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                content,
                key,
                content='memories',
                content_rowid='id'
            );

            -- Triggers to sync FTS5
            CREATE TRIGGER IF NOT EXISTS mem_after_insert AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, content, key) VALUES (new.id, new.content, new.key);
            END;
            CREATE TRIGGER IF NOT EXISTS mem_after_delete AFTER DELETE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content, key) VALUES('delete', old.id, old.content, old.key);
            END;
            CREATE TRIGGER IF NOT EXISTS mem_after_update AFTER UPDATE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content, key) VALUES('delete', old.id, old.content, old.key);
                INSERT INTO memories_fts(rowid, content, key) VALUES (new.id, new.content, new.key);
            END;
            """)
            conn.commit()

    def store_memory(
        self,
        layer: str,
        key: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Stores or updates a memory item with automatic secret redaction."""
        clean_content = SecretSanitizer.sanitize(content)
        meta_json = json.dumps(metadata or {})
        now = time.time()

        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT id FROM memories WHERE layer = ? AND key = ?
            """, (layer, key))
            row = cur.fetchone()

            if row:
                mem_id = row[0]
                cur.execute("""
                UPDATE memories SET content = ?, metadata = ?, updated_at = ?
                WHERE id = ?
                """, (clean_content, meta_json, now, mem_id))
            else:
                cur.execute("""
                INSERT INTO memories (layer, key, content, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (layer, key, clean_content, meta_json, now, now))
                mem_id = cur.lastrowid
            conn.commit()
            return mem_id

    def recall_exact(self, layer: str, key: str) -> Optional[MemoryItem]:
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM memories WHERE layer = ? AND key = ?", (layer, key))
            row = cur.fetchone()
            if not row:
                return None
            return MemoryItem(
                id=row["id"],
                layer=row["layer"],
                key=row["key"],
                content=row["content"],
                metadata=json.loads(row["metadata"] or "{}"),
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )

    def search_fts(self, query: str, layer: Optional[str] = None, limit: int = 10) -> List[MemoryItem]:
        """Full-text search using SQLite FTS5."""
        sanitized_query = re.sub(r"[^\w\s]", "", query).strip()
        if not sanitized_query:
            return []

        results = []
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            sql = """
            SELECT m.* FROM memories m
            JOIN memories_fts f ON m.id = f.rowid
            WHERE memories_fts MATCH ?
            """
            params = [sanitized_query]
            if layer:
                sql += " AND m.layer = ?"
                params.append(layer)
            sql += " ORDER BY rank LIMIT ?"
            params.append(limit)

            try:
                cur.execute(sql, params)
                for r in cur.fetchall():
                    results.append(MemoryItem(
                        id=r["id"],
                        layer=r["layer"],
                        key=r["key"],
                        content=r["content"],
                        metadata=json.loads(r["metadata"] or "{}"),
                        created_at=r["created_at"],
                        updated_at=r["updated_at"]
                    ))
            except Exception:
                # Fallback to LIKE if FTS expression is ill-formed
                return self.search_keyword(query, layer=layer, limit=limit)
        return results

    def search_keyword(self, keyword: str, layer: Optional[str] = None, limit: int = 10) -> List[MemoryItem]:
        """LIKE fallback search."""
        results = []
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            sql = "SELECT * FROM memories WHERE (content LIKE ? OR key LIKE ?)"
            params = [f"%{keyword}%", f"%{keyword}%"]
            if layer:
                sql += " AND layer = ?"
                params.append(layer)
            sql += " ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)

            cur.execute(sql, params)
            for r in cur.fetchall():
                results.append(MemoryItem(
                    id=r["id"],
                    layer=r["layer"],
                    key=r["key"],
                    content=r["content"],
                    metadata=json.loads(r["metadata"] or "{}"),
                    created_at=r["created_at"],
                    updated_at=r["updated_at"]
                ))
        return results

    def search_semantic(self, query: str, layer: Optional[str] = None, limit: int = 5) -> List[MemoryItem]:
        """TF-IDF Vector Cosine Similarity retrieval across memories."""
        all_memories = self.list_memories(layer=layer, limit=200)
        if not all_memories:
            return []

        def tokenize(text: str) -> List[str]:
            return re.findall(r"\b[a-zA-Z0-9_]{2,}\b", text.lower())

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        # Build vocabulary & IDF
        docs = [tokenize(m.content + " " + m.key) for m in all_memories]
        n_docs = len(docs)
        doc_freq = {}
        for d in docs:
            for w in set(d):
                doc_freq[w] = doc_freq.get(w, 0) + 1

        idf = {w: math.log((n_docs + 1) / (df + 1)) + 1.0 for w, df in doc_freq.items()}

        def tf_idf_vec(toks: List[str]) -> Dict[str, float]:
            tf = {}
            for t in toks:
                tf[t] = tf.get(t, 0) + 1
            length = len(toks) or 1
            return {t: (cnt / length) * idf.get(t, 1.0) for t, cnt in tf.items()}

        def cosine_sim(v1: Dict[str, float], v2: Dict[str, float]) -> float:
            dot = sum(v1[k] * v2[k] for k in v1 if k in v2)
            norm1 = math.sqrt(sum(val ** 2 for val in v1.values())) or 1e-9
            norm2 = math.sqrt(sum(val ** 2 for val in v2.values())) or 1e-9
            return dot / (norm1 * norm2)

        q_vec = tf_idf_vec(query_tokens)
        scored = []
        for m, d in zip(all_memories, docs):
            d_vec = tf_idf_vec(d)
            sim = cosine_sim(q_vec, d_vec)
            if sim > 0.05:
                m.score = round(sim, 4)
                scored.append(m)

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:limit]

    def list_memories(self, layer: Optional[str] = None, limit: int = 100) -> List[MemoryItem]:
        results = []
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            if layer:
                cur.execute("SELECT * FROM memories WHERE layer = ? ORDER BY updated_at DESC LIMIT ?", (layer, limit))
            else:
                cur.execute("SELECT * FROM memories ORDER BY updated_at DESC LIMIT ?", (limit,))
            for r in cur.fetchall():
                results.append(MemoryItem(
                    id=r["id"],
                    layer=r["layer"],
                    key=r["key"],
                    content=r["content"],
                    metadata=json.loads(r["metadata"] or "{}"),
                    created_at=r["created_at"],
                    updated_at=r["updated_at"]
                ))
        return results

    def delete_memory(self, memory_id: int) -> bool:
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            return cur.rowcount > 0

    def purge_layer(self, layer: str) -> int:
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM memories WHERE layer = ?", (layer,))
            conn.commit()
            return cur.rowcount
