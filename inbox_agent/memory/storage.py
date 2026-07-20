"""
Abstract storage interface.

Every storage backend must implement these methods. ShortTermMemory and
LongTermMemory both now actually implement this interface (they didn't
fully before — `get()` was missing from both).
"""

from abc import ABC, abstractmethod

from .models import MemoryRecord


class MemoryStorage(ABC):

    @abstractmethod
    def save(self, memory: MemoryRecord):
        pass

    @abstractmethod
    def update(self, memory: MemoryRecord):
        pass

    @abstractmethod
    def delete(self, memory_id: str):
        pass

    @abstractmethod
    def get_all(self, user_id: str):
        pass

    @abstractmethod
    def get(self, user_id: str, key: str):
        pass
