"""
Input Validation Guardrail

Runs immediately after Gmail fetch, before any agent sees the data.
Operates on state["raw_emails"]: list[dict] (the tool's raw output shape),
so no nested-model concerns apply here.

Responsibilities
----------------
1. Detect Gmail API errors
2. Validate batch size
3. Validate required fields
4. Normalize email fields
5. Remove malformed emails
6. Prevent duplicate email IDs
"""

from __future__ import annotations

import logging
from copy import deepcopy
from email.utils import parseaddr

from state import EmailWorkflowState

from .base import BaseGuardrail
from .config import GuardrailConfig
from .result import GuardDecision, GuardResult

logger = logging.getLogger(__name__)


class InputGuard(BaseGuardrail):

    name = "InputGuard"

    REQUIRED_FIELDS = ("id", "thread_id", "sender", "subject", "snippet", "body")

    def preprocess(self, state: EmailWorkflowState) -> EmailWorkflowState:
        """Normalize email fields before validation."""
        state = deepcopy(state)
        emails = state.get("raw_emails", [])

        for email in emails:
            display_name, address = parseaddr(email.get("sender", ""))
            email["sender_name"] = display_name
            email["sender_email"] = address.lower()

            subject = (email.get("subject", "") or "").strip() or "(No Subject)"
            if len(subject) > GuardrailConfig.MAX_SUBJECT_LENGTH:
                subject = subject[: GuardrailConfig.MAX_SUBJECT_LENGTH]
            email["subject"] = subject

            body = (email.get("body", "") or "").strip()
            snippet = (email.get("snippet", "") or "").strip()
            if not body:
                body = snippet
            if len(body) > GuardrailConfig.MAX_EMAIL_BODY_LENGTH:
                body = body[: GuardrailConfig.MAX_EMAIL_BODY_LENGTH]
            email["body"] = body

        return state

    def validate(self, state: EmailWorkflowState) -> GuardResult:
        emails = state.get("raw_emails", [])
        errors = list(state.get("errors", []))
        validated = []
        seen_ids = set()
        modified = False

        if len(emails) > GuardrailConfig.MAX_EMAILS_PER_BATCH:
            return GuardResult(
                decision=GuardDecision.BLOCK,
                passed=False,
                reason="Batch size exceeded.",
                guardrail_name=self.name,
            )

        for email in emails:
            try:
                if "error" in email:
                    return GuardResult(
                        decision=GuardDecision.BLOCK,
                        passed=False,
                        reason=email["error"],
                        guardrail_name=self.name,
                    )

                self._validate_required_fields(email)
                self._validate_email_id(email, seen_ids)
                self._validate_sender(email)

                validated.append(email)

            except Exception as exc:  # noqa: BLE001
                logger.warning(exc)
                errors.append(str(exc))
                modified = True

        new_state = deepcopy(state)
        new_state["raw_emails"] = validated
        new_state["errors"] = errors

        return GuardResult(
            decision=GuardDecision.MODIFY if modified else GuardDecision.ALLOW,
            passed=True,
            updated_state=new_state,
            reason="Validation completed.",
            metadata={
                "received": len(emails),
                "accepted": len(validated),
                "rejected": len(emails) - len(validated),
            },
            guardrail_name=self.name,
        )

    def _validate_required_fields(self, email: dict):
        for field in self.REQUIRED_FIELDS:
            if field not in email:
                raise ValueError(f"Missing field '{field}'")

    def _validate_email_id(self, email: dict, seen_ids: set):
        email_id = email["id"]
        if email_id in seen_ids:
            raise ValueError(f"Duplicate email id {email_id}")
        seen_ids.add(email_id)

    def _validate_sender(self, email: dict):
        if not email.get("sender_email", ""):
            raise ValueError("Invalid sender.")
