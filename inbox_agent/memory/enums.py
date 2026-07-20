from enum import Enum


class MemoryType(str, Enum):
    """Type of memory."""

    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"


class MemoryCategory(str, Enum):
    """What kind of information is stored."""

    PREFERENCE = "preference"
    CONTACT = "contact"
    TASK = "task"
    CALENDAR = "calendar"
    SIGNATURE = "signature"
    LANGUAGE = "language"
    WORKFLOW = "workflow"
    OTHER = "other"
