##state.py

from typing import Optional, TypedDict

from agents.email_understanding import EmailInfo
from agents.classifier import ClassifiedEmail
from agents.priority import PrioritizedEmail
from agents.planner import PlannedEmail
from agents.executor import ExecutedEmail


class EmailWorkflowState(TypedDict):
    """
    Shared LangGraph state for the complete Email Automation workflow.
    """

    # ============================================================
    # Workflow Configuration
    # ============================================================

    max_results: int
    query: Optional[str]

    # ============================================================
    # Gmail Fetch Tool Output
    # ============================================================

    raw_emails: list[dict]

    # ============================================================
    # Email Understanding Agent
    # ============================================================

    structured_emails: list[EmailInfo]

    # ============================================================
    # Classification Agent
    # ============================================================

    classified_emails: list[ClassifiedEmail]

    # ============================================================
    # Priority Agent
    # ============================================================

    prioritized_emails: list[PrioritizedEmail]

    # ============================================================
    # Planner Agent
    # ============================================================

    planned_emails: list[PlannedEmail]

    # ============================================================
    # Executor Agent
    # ============================================================

    executed_emails: list[ExecutedEmail]

    # ============================================================
    # Workflow Status
    # ============================================================

    errors: list[str]