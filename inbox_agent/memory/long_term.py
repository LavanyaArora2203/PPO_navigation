"""
Long-Term Memory

Per memory_management.txt, long-term memory should be backed by
"SQLite / Vector DB". This implementation uses SQLite for durable
key-value storage of MemoryRecord objects, persisted across process
restarts (unlike the previous in-memory-dict version).

A vector DB backend (for semantic/similarity retrieval rather than exact
key lookups) is a natural follow-up — this class implements the same
MemoryStorage interface, so swapping backends later doesn't require
touching manager.py or the node functions in nodes.py.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .enums import MemoryCategory, MemoryType
from .models import MemoryRecord
from .storage import MemoryStorage

DEFAULT_DB_PATH = Path(__file__).parent / "long_term_memory.db"


class LongTermMemory(MemoryStorage):

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = str(db_path)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS long_term_memory (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                expires_at TEXT,
                metadata TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ltm_user_key ON long_term_memory(user_id, key)"
        )
        conn.commit()
        conn.close()

    # ------------------------------------------------------------
    # MemoryStorage interface
    # ------------------------------------------------------------

    def save(self, memory: MemoryRecord):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            INSERT OR REPLACE INTO long_term_memory
                (id, user_id, memory_type, category, key, value, confidence,
                 source, created_at, updated_at, expires_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._to_row(memory),
        )
        conn.commit()
        conn.close()

    def update(self, memory: MemoryRecord):
        memory.updated_at = datetime.utcnow()
        self.save(memory)

    def delete(self, memory_id: str):
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM long_term_memory WHERE id = ?", (memory_id,))
        conn.commit()
        conn.close()

    def get_all(self, user_id: str) -> list[MemoryRecord]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM long_term_memory WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
        conn.close()
        return [self._from_row(row) for row in rows]

    def get(self, user_id: str, key: str) -> MemoryRecord | None:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM long_term_memory WHERE user_id = ? AND key = ? "
            "ORDER BY updated_at DESC LIMIT 1",
            (user_id, key),
        ).fetchone()
        conn.close()
        return self._from_row(row) if row else None

    # ------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------

    def _to_row(self, memory: MemoryRecord) -> tuple:
        return (
            memory.id,
            memory.user_id,
            memory.memory_type.value,
            memory.category.value,
            memory.key,
            json.dumps(memory.value),
            memory.confidence,
            memory.source,
            memory.created_at.isoformat(),
            memory.updated_at.isoformat(),
            memory.expires_at.isoformat() if memory.expires_at else None,
            json.dumps(memory.metadata),
        )

    def _from_row(self, row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            id=row["id"],
            user_id=row["user_id"],
            memory_type=MemoryType(row["memory_type"]),
            category=MemoryCategory(row["category"]),
            key=row["key"],
            value=json.loads(row["value"]),
            confidence=row["confidence"],
            source=row["source"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            metadata=json.loads(row["metadata"]),
        )
