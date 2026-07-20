"""
AuditLogger

Same public interface as before (`.log(...)`, `.records`, `.export()`) so
guardrails/audit_guard.py works unchanged. Records are still kept in memory
on `self.records`, but are now also persisted to a local SQLite database by
default, so audit history survives a process restart.

Pass `persist=False` to keep the old in-memory-only behavior (e.g. in tests).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .models import AuditRecord

DEFAULT_DB_PATH = Path(__file__).parent / "audit_log.db"


class AuditLogger:

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH, persist: bool = True):
        self.records: list[AuditRecord] = []
        self.persist = persist
        self.db_path = str(db_path)

        if self.persist:
            self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                workflow TEXT NOT NULL,
                email_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                component TEXT NOT NULL,
                decision TEXT NOT NULL,
                status TEXT NOT NULL,
                duration_ms REAL,
                metadata TEXT,
                error TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    def log(
        self,
        workflow,
        email_id,
        stage,
        component,
        decision,
        status,
        duration_ms=None,
        metadata=None,
        error=None,
    ):
        record = AuditRecord(
            timestamp=datetime.utcnow(),
            workflow=workflow,
            email_id=email_id,
            stage=stage,
            component=component,
            decision=decision,
            status=status,
            duration_ms=duration_ms,
            metadata=metadata or {},
            error=error,
        )

        self.records.append(record)

        if self.persist:
            self._persist(record)

        return record

    def _persist(self, record: AuditRecord):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            INSERT INTO audit_records
                (timestamp, workflow, email_id, stage, component, decision,
                 status, duration_ms, metadata, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.timestamp.isoformat(),
                record.workflow,
                record.email_id,
                record.stage,
                record.component,
                record.decision,
                record.status,
                record.duration_ms,
                json.dumps(record.metadata),
                record.error,
            ),
        )
        conn.commit()
        conn.close()

    def export(self) -> list[AuditRecord]:
        """In-memory records from this process only."""
        return self.records

    def query(self, email_id: str | None = None, limit: int = 100) -> list[dict]:
        """Query persisted records from SQLite (survives restarts)."""
        if not self.persist:
            return []

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        if email_id:
            rows = conn.execute(
                "SELECT * FROM audit_records WHERE email_id = ? ORDER BY id DESC LIMIT ?",
                (email_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM audit_records ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()

        conn.close()
        return [dict(row) for row in rows]
