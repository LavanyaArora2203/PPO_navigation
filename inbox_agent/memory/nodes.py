"""
Memory Nodes

LangGraph-compatible node functions implementing the flow from
memory_management.txt:

    Planner Agent -> Retrieves Memory -> Generates Plan -> Executes Plan
    -> Memory Guard -> "Is there anything worth remembering?"
         NO  -> Finish
         YES -> Memory Manager -> Short-Term / Long-Term -> SQLite / Vector DB

Three node functions are provided:

    retrieve_memory_node   — call before/at the Planner Agent, populates
                              state["retrieved_memories"] for personalization
    memory_guard_node       — call after Executor, extracts MemoryCandidates
                              via the memory_extractor LLM and filters them
    memory_manager_node     — call after memory_guard_node, persists
                              approved candidates

`should_run_memory_manager(state)` is a routing predicate for graph.py's
conditional edge: if memory_guard_node found nothing worth storing, the
graph should go straight to END/Finish instead of calling memory_manager_node.

INTEGRATION NOTE: these nodes key everything off `state.get("user_id",
"default_user")`. EmailWorkflowState (state.py) doesn't declare a `user_id`
field yet — add one there for real multi-user deployments. Until then,
every run shares the "default_user" memory space.
"""

from __future__ import annotations

import logging

from agents.llm import llm
from agents.memory_extractor import parser, prompt
from state import EmailWorkflowState

from .extractor import MemoryCandidate
from .manager import MemoryManager

logger = logging.getLogger(__name__)

# Shared manager instance so short-term memory persists across node calls
# within a process (long-term is SQLite-backed regardless of instance).
memory_manager = MemoryManager()

# Runnable chain: prompt -> llm -> structured MemoryCandidate parser.
_extraction_chain = prompt | llm | parser


def _get_user_id(state: EmailWorkflowState) -> str:
    return state.get("user_id", "default_user")


# --------------------------------------------------------------------------
# 1. Retrieve Memory — runs at/before the Planner Agent
# --------------------------------------------------------------------------


def retrieve_memory_node(state: EmailWorkflowState) -> EmailWorkflowState:
    """
    Fetches all known memories for the current user so the Planner Agent can
    personalize its plan (e.g. known preferences, signature style, recurring
    workflow habits). Populates state["retrieved_memories"].

    NOTE: planner.py's prompt does not currently consume this field — wiring
    `state["retrieved_memories"]` into the planner's prompt context is a
    follow-up change to agents/planner.py, outside this file's scope.
    """
    user_id = _get_user_id(state)

    try:
        memories = memory_manager.retrieve(user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Memory retrieval failed for user %s: %s", user_id, exc)
        memories = []

    new_state = dict(state)
    new_state["retrieved_memories"] = memories
    return new_state


# --------------------------------------------------------------------------
# 2. Memory Guard — runs after Executor, decides what's worth remembering
# --------------------------------------------------------------------------


def _build_extraction_input(executed_item) -> str:
    """Assemble the text handed to the memory extraction LLM for one email."""
    email_info = executed_item.planned_email.prioritized_email.classified_email.email_info
    actions = executed_item.planned_email.action_plan.actions

    parts = [
        f"Email subject: {email_info.subject}",
        f"Email summary: {email_info.summary}",
        f"Actions taken: {', '.join(actions)}",
    ]

    if executed_item.pending_send is not None:
        parts.append(f"Drafted content: {executed_item.pending_send.body}")

    return "\n".join(parts)


def memory_guard_node(state: EmailWorkflowState) -> EmailWorkflowState:
    """
    For each executed email, asks the memory extraction LLM whether there's
    anything worth remembering (preferences, recurring contacts, workflow
    habits, etc.), then filters results through MemoryGuard.should_store()
    before they're allowed to reach memory_manager_node. Populates
    state["memory_candidates"] with only the approved candidates.
    """
    executed = state.get("executed_emails", [])
    candidates: list[MemoryCandidate] = []
    errors = list(state.get("errors", []))

    for item in executed:
        try:
            text = _build_extraction_input(item)
            candidate: MemoryCandidate = _extraction_chain.invoke({"text": text})

            if not candidate.should_store:
                continue

            if not memory_manager.guard.should_store(candidate.key, candidate.value):
                logger.info("MemoryGuard blocked candidate key=%s (sensitive)", candidate.key)
                continue

            candidates.append(candidate)

        except Exception as exc:  # noqa: BLE001
            errors.append(f"Memory extraction failed: {exc}")
            logger.warning("Memory extraction failed: %s", exc)

    new_state = dict(state)
    new_state["memory_candidates"] = candidates
    new_state["errors"] = errors
    return new_state


def should_run_memory_manager(state: EmailWorkflowState) -> bool:
    """Routing predicate for graph.py's conditional edge after memory_guard_node."""
    return bool(state.get("memory_candidates"))


# --------------------------------------------------------------------------
# 3. Memory Manager — runs only if memory_guard_node found something
# --------------------------------------------------------------------------


def memory_manager_node(state: EmailWorkflowState) -> EmailWorkflowState:
    """
    Persists each approved MemoryCandidate via MemoryManager, which routes
    to ShortTermMemory or LongTermMemory (SQLite) based on
    candidate.memory_type. Populates state["stored_memories"].
    """
    user_id = _get_user_id(state)
    candidates = state.get("memory_candidates", [])
    stored = []
    errors = list(state.get("errors", []))

    for candidate in candidates:
        try:
            record = memory_manager.store_candidate(candidate, user_id)
            if record is not None:
                stored.append(record)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Memory storage failed for key '{candidate.key}': {exc}")
            logger.warning("Memory storage failed: %s", exc)

    new_state = dict(state)
    new_state["stored_memories"] = stored
    new_state["errors"] = errors
    return new_state
