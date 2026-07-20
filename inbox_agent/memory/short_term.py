"""
Short-Term Memory

In-process, per-session storage. Cleared when the process restarts or via
`clear()` / `remove_expired()`. Now fully implements MemoryStorage (added
`get()`; `delete()` was previously only reachable by MemoryManager poking
at the private `_memory` dict directly).
"""

from datetime import datetime

from .models import MemoryRecord
from .storage import MemoryStorage


class ShortTermMemory(MemoryStorage):

    def __init__(self):
        self._memory: dict[str, MemoryRecord] = {}

    def save(self, memory: MemoryRecord):
        self._memory[memory.id] = memory

    def update(self, memory: MemoryRecord):
        self._memory[memory.id] = memory

    def delete(self, memory_id: str):
        self._memory.pop(memory_id, None)

    def get_all(self, user_id: str) -> list[MemoryRecord]:
        return [m for m in self._memory.values() if m.user_id == user_id]

    def get(self, user_id: str, key: str) -> MemoryRecord | None:
        for m in self._memory.values():
            if m.user_id == user_id and m.key == key:
                return m
        return None

    def clear(self):
        self._memory.clear()

    def remove_expired(self):
        now = datetime.utcnow()
        expired = [k for k, v in self._memory.items() if v.expires_at and v.expires_at < now]
        for key in expired:
            del self._memory[key]
