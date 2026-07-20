"""
Shared configuration for all guardrails.

IMPORTANT: ALLOWED_ACTIONS / TOOL_REGISTRY / HUMAN_APPROVAL_ACTIONS here are
the single source of truth for the action vocabulary. They MUST match the
`ActionType` Literal defined in agents/planner.py. If planner.py's action
vocabulary changes, update it here too — every guard imports from this file
rather than hardcoding its own copy, specifically to prevent the vocabulary
drift that caused every planned action to get silently stripped before.
"""

from __future__ import annotations


class GuardrailConfig:

    # ------------------------------------------------------------
    # Input limits
    # ------------------------------------------------------------

    MAX_EMAIL_BODY_LENGTH = 50_000
    MAX_SUBJECT_LENGTH = 500
    MAX_ATTACHMENT_SIZE_MB = 25
    MAX_ATTACHMENTS = 20
    MAX_EMAILS_PER_BATCH = 100

    # ------------------------------------------------------------
    # Planner limits
    # ------------------------------------------------------------

    MAX_ACTIONS_PER_EMAIL = 6

    # Must match agents/planner.py's ActionType Literal exactly.
    ALLOWED_ACTIONS = {
        "reply",
        "archive",
        "delete",
        "mark_read",
        "flag",
        "create_task",
        "schedule_meeting",
        "notify_slack",
        "forward",
        "do_nothing",
        "human_approval",
    }

    # Actions that must never run until a human has explicitly approved
    # this email. "reply"/"forward" send email; "delete" is destructive;
    # "schedule_meeting" commits an external calendar change.
    HUMAN_APPROVAL_ACTIONS = {
        "reply",
        "forward",
        "delete",
        "schedule_meeting",
    }

    # Central tool registry — enabled/approval/read-only status per action.
    # "human_approval" is a control action, not a tool call, so it's excluded.
    TOOL_REGISTRY = {
        "reply": {"enabled": True, "requires_approval": True, "read_only": False},
        "archive": {"enabled": True, "requires_approval": False, "read_only": False},
        "delete": {"enabled": True, "requires_approval": True, "read_only": False},
        "mark_read": {"enabled": True, "requires_approval": False, "read_only": False},
        "flag": {"enabled": True, "requires_approval": False, "read_only": False},
        "create_task": {"enabled": True, "requires_approval": False, "read_only": False},
        "schedule_meeting": {"enabled": True, "requires_approval": True, "read_only": False},
        "notify_slack": {"enabled": True, "requires_approval": False, "read_only": True},
        "forward": {"enabled": True, "requires_approval": True, "read_only": False},
        "do_nothing": {"enabled": True, "requires_approval": False, "read_only": True},
    }

    # ------------------------------------------------------------
    # Confidence thresholds (Classifier)
    # ------------------------------------------------------------

    HIGH_CONFIDENCE = 0.90
    REVIEW_CONFIDENCE = 0.70
    BLOCK_CONFIDENCE = 0.50
    MIN_CONFIDENCE = 0.70

    # ------------------------------------------------------------
    # Feature toggles
    # ------------------------------------------------------------

    ENABLE_PII_SCAN = True
    ENABLE_PROMPT_SCAN = True
    ENABLE_AUDIT = True

    REQUIRE_HUMAN_APPROVAL_FOR_SEND = True
    REQUIRE_HUMAN_APPROVAL_FOR_DELETE = True
    REQUIRE_HUMAN_APPROVAL_FOR_FORWARD = True

    READ_ONLY_MODE = False
