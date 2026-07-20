"""
Memory Manager

Single entry point for all memory operations. Routes short-term vs
long-term storage based on MemoryRecord.memory_type.
"""

from __future__ import annotations

from .enums import MemoryCategory, MemoryType
from .extractor import MemoryCandidate
from .long_term import LongTermMemory
from .memory_guard import MemoryGuard
from .models import MemoryRecord
from .short_term import ShortTermMemory


class MemoryManager:

    def __init__(self):
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
        self.guard = MemoryGuard()

    # ---------------------------------
    # Store
    # ---------------------------------

    def store(self, memory: MemoryRecord):
        if memory.memory_type == MemoryType.SHORT_TERM:
            self.short_term.save(memory)
        else:
            self.long_term.save(memory)

    def store_candidate(
        self, candidate: MemoryCandidate, user_id: str
    ) -> MemoryRecord | None:
        """
        Convenience method combining MemoryGuard filtering + MemoryRecord
        creation + storage in one call. Returns the stored record, or None
        if the guard rejected it (blocked key, PII detected, or
        candidate.should_store was False).
        """
        if not candidate.should_store:
            return None

        record = self.guard.create_memory(
            user_id=user_id,
            key=candidate.key,
            value=candidate.value,
            category=candidate.category,
            memory_type=candidate.memory_type,
        )

        if record is None:
            return None  # guard blocked it (sensitive key/value)

        record.confidence = candidate.confidence
        record.source = "memory_extractor_agent"

        self.store(record)
        return record

    # ---------------------------------
    # Retrieve
    # ---------------------------------

    def retrieve(self, user_id: str) -> list[MemoryRecord]:
        short = self.short_term.get_all(user_id)
        long = self.long_term.get_all(user_id)
        return short + long

    def retrieve_by_category(
        self, user_id: str, category: MemoryCategory
    ) -> list[MemoryRecord]:
        return [m for m in self.retrieve(user_id) if m.category == category]

    # ---------------------------------
    # Delete
    # ---------------------------------

    def delete(self, memory_id: str):
        # Deletes from both backends via the proper interface method — no
        # more reaching into ShortTermMemory's private `_memory` dict.
        self.short_term.delete(memory_id)
        self.long_term.delete(memory_id)

    # ---------------------------------
    # Cleanup
    # ---------------------------------

    def cleanup(self):
        self.short_term.remove_expired()
