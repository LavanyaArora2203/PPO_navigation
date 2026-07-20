"""
Memory Guard

Determines whether information should be stored as memory. This is the
"Is there anything worth remembering?" decision point in
memory_management.txt.

Two layers:
1. should_store() — blocked-key check (unchanged) + a lightweight PII scan
   over the value itself, since a value can contain sensitive data even
   under an innocuous key (e.g. key="note", value="card is 4111 1111...").
2. create_memory() — builds the MemoryRecord if should_store() passes.
"""

from __future__ import annotations

import re

from .enums import MemoryCategory, MemoryType
from .models import MemoryRecord

# Reuses the same pattern intent as guardrails/pii_guard.py, kept minimal
# and independent here since memory/ shouldn't depend on guardrails/.
_PII_PATTERNS = [
    r"\b\d{4}\s?\d{4}\s?\d{4}\s?\d{0,4}\b",  # card-like number sequences
    r"password\s*[:=]\s*\S+",
    r"\bOTP\b.*?\b\d{4,8}\b",
    r"AKIA[0-9A-Z]{16}",  # AWS key
]


class MemoryGuard:
    """Filters unsafe or useless memories before storage."""

    BLOCKED_KEYS = {
        "password",
        "otp",
        "api_key",
        "credit_card",
        "bank_account",
        "aadhaar",
        "pan",
    }

    def should_store(self, key: str, value) -> bool:
        """Basic rule engine: blocked key names, plus a PII scan on the value."""
        if key.lower() in self.BLOCKED_KEYS:
            return False

        text_value = str(value)
        for pattern in _PII_PATTERNS:
            if re.search(pattern, text_value, flags=re.IGNORECASE):
                return False

        return True

    def create_memory(
        self,
        user_id: str,
        key: str,
        value,
        category: MemoryCategory,
        memory_type: MemoryType,
    ) -> MemoryRecord | None:
        if not self.should_store(key, value):
            return None

        return MemoryRecord(
            user_id=user_id,
            key=key,
            value=value,
            category=category,
            memory_type=memory_type,
        )
