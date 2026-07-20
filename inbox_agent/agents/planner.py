"""
Planner Agent (LangGraph)
----------------------------
Takes `PrioritizedEmail` objects (from the Priority Agent) and decides the
ordered sequence of downstream actions each email should go through — it does
NOT perform any action itself. Output is consumed by an executor/orchestrator
that dispatches to the actual responder/calendar/task/slack/human-review
systems.

Output shape per email:
    {
        "actions": ["draft_reply" -> "reply", "calendar_event" -> "schedule_meeting", "human_approval"],
        "reasoning": "..."
    }

SETUP
-----
    pip install --upgrade langgraph langchain-core langchain-anthropic pydantic
    export ANTHROPIC_API_KEY=...

Place this file alongside email_understanding_agent.py, classifier_agent.py,
priority_agent.py, and gmail_unread_tool.py.

USAGE
-----
    from email_understanding_agent import run_email_understanding_agent
    from classifier_agent import run_classifier_agent
    from priority_agent import run_priority_agent
    from planner_agent import run_planner_agent

    understanding_result = run_email_understanding_agent(max_results=10)
    classified_result = run_classifier_agent(understanding_result["structured_emails"])
    priority_result = run_priority_agent(classified_result["classified_emails"])
    planned_result = run_planner_agent(priority_result["prioritized_emails"])

    for item in planned_result["planned_emails"]:
        print(item.action_plan.actions, "-", item.prioritized_email.classified_email.email_info.subject)
"""

from __future__ import annotations

import json
from typing import List, Literal, TypedDict

# from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from priority import PrioritizedEmail
from llm import llm

# --------------------------------------------------------------------------
# Action vocabulary & structured output
# --------------------------------------------------------------------------

ActionType = Literal[
    "reply",             # hand off to the responder agent to draft/send a reply
    "archive",           # no further action needed, archive it
    "delete",            # discard (spam/junk) — irreversible, guarded below
    "mark_read",         # mark read without archiving (still visible in inbox)
    "flag",              # flag/star for the user to revisit later
    "create_task",       # push an action item to a task tracker
    "schedule_meeting",  # create/update a calendar event from a date/time in the email
    "notify_slack",      # post a notification to Slack (e.g. urgent items)
    "forward",           # route the email to someone else
    "do_nothing",        # informational only, no action of any kind
    "human_approval",    # pause and route to a human before anything is sent/committed
]

ACTION_DEFINITIONS = """\
- reply: sender is waiting on a response; hand off to the responder agent to draft one
- archive: no further action needed but keep the email (routine notifications, completed items)
- delete: junk/spam that should be discarded outright
- mark_read: acknowledge without archiving (still worth keeping visible)
- flag: worth revisiting later, but not actionable right now
- create_task: a concrete task should be tracked (e.g. "pay bill", "review doc")
- schedule_meeting: the email references a meeting/event that should go on the calendar
- notify_slack: important enough that the user should get a real-time ping outside email
- forward: this should go to someone else, not be handled directly
- do_nothing: purely informational, no action of any kind, not even archiving
- human_approval: a human must review before any reply is sent or commitment is made
"""


class ActionPlan(BaseModel):
    actions: List[ActionType] = Field(
        description="Ordered sequence of actions to take on this email. Order matters — "
        "e.g. reply should be drafted before human_approval reviews it."
    )
    reasoning: str = Field(description="1-2 sentences explaining why this sequence was chosen")


class PlannedEmail(BaseModel):
    prioritized_email: PrioritizedEmail
    action_plan: ActionPlan


# --------------------------------------------------------------------------
# Graph state
# --------------------------------------------------------------------------


class PlannerState(TypedDict):
    prioritized_emails: List[PrioritizedEmail]
    planned_emails: List[PlannedEmail]
    errors: List[str]


# --------------------------------------------------------------------------
# LLM proposal node
# --------------------------------------------------------------------------

# _planner_llm = ChatAnthropic(model="claude-sonnet-5", temperature=0)
_structured_planner = llm.with_structured_output(ActionPlan)

_PLANNING_PROMPT = """You are deciding the sequence of actions an email-handling system should \
take for an email. You do not perform the actions — you only choose which ones happen and in \
what order.

Available actions:
{action_definitions}

Guidance:
- Choose the minimal sequence that actually handles the email — don't pad with unnecessary steps.
- do_nothing must be the only action if used (never combined with anything else).
- If a reply is warranted, "reply" comes before "human_approval" (draft first, then review).
- If the email references a specific meeting/interview/event with a date and needs the \
recipient's calendar updated, include "schedule_meeting".
- If the email is Urgent priority, prefer including "notify_slack" so the user doesn't miss it, \
in addition to whatever else is needed.
- If a concrete follow-up task is implied (not just "reply to this"), include "create_task".
- Never include "delete" unless the category is Spam or the content is clearly junk/malicious.
- "archive" and "mark_read" are for routine items with no further action required.

Context:
Category: {category}
Priority: {priority_level} ({priority_reasoning})
From: {sender}
Subject: {subject}
Summary: {summary}
Question present: {question_present}
Mentioned dates/times: {mentioned_dates_times}
"""


def propose_actions_node(state: PlannerState) -> PlannerState:
    planned: List[PlannedEmail] = list(state.get("planned_emails", []))
    errors: List[str] = list(state.get("errors", []))

    for item in state.get("prioritized_emails", []):
        classified = item.classified_email
        email_info = classified.email_info
        try:
            action_plan = _structured_planner.invoke(
                _PLANNING_PROMPT.format(
                    action_definitions=ACTION_DEFINITIONS,
                    category=classified.classification.category,
                    priority_level=item.priority.level,
                    priority_reasoning=item.priority.reasoning,
                    sender=f"{email_info.sender.name or ''} <{email_info.sender.email}>",
                    subject=email_info.subject,
                    summary=email_info.summary,
                    question_present=email_info.question_present,
                    mentioned_dates_times=", ".join(email_info.mentioned_dates_times) or "none",
                )
            )
            planned.append(PlannedEmail(prioritized_email=item, action_plan=action_plan))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Planning failed for email {email_info.email_id}: {exc}")

    return {**state, "planned_emails": planned, "errors": errors}


# --------------------------------------------------------------------------
# Deterministic guardrail node — the LLM proposes, this enforces hard rules
# --------------------------------------------------------------------------


def _enforce_guardrails(planned: PlannedEmail) -> ActionPlan:
    classified = planned.prioritized_email.classified_email
    category = classified.classification.category
    confidence = classified.classification.confidence
    priority_level = planned.prioritized_email.priority.level
    actions = list(planned.action_plan.actions)
    reasoning = planned.action_plan.reasoning

    # Rule 1: high-confidence Spam is always just deleted — no LLM discretion on junk.
    if category == "Spam" and confidence >= 0.8:
        return ActionPlan(actions=["delete"], reasoning="High-confidence spam: auto-deleted.")

    # Rule 2: low-confidence delete is too risky — downgrade to flag + human_approval.
    if "delete" in actions and confidence < 0.8:
        actions = [a for a in actions if a != "delete"]
        if "flag" not in actions:
            actions.append("flag")
        if "human_approval" not in actions:
            actions.append("human_approval")
        reasoning += " (delete downgraded to flag+human_approval due to low classification confidence)"

    # Rule 3: do_nothing must be exclusive.
    if "do_nothing" in actions and len(actions) > 1:
        actions = ["do_nothing"]
        reasoning += " (do_nothing forced exclusive)"

    # Rule 4: Promotion/Newsletter/Social at Low priority never get reply/schedule_meeting/
    # notify_slack — those categories don't warrant interrupting the user or drafting replies.
    if category in ("Promotion", "Newsletter", "Social") and priority_level == "Low":
        blocked = {"reply", "schedule_meeting", "notify_slack", "human_approval"}
        filtered = [a for a in actions if a not in blocked]
        if filtered != actions:
            actions = filtered or ["archive"]
            reasoning += f" ({category} at Low priority: stripped reply/meeting/notify/approval actions)"

    # Rule 5: any reply on a stakes-bearing category must be human-reviewed first.
    if "reply" in actions and category in ("Finance", "Bills", "Job", "Interview"):
        if "human_approval" not in actions:
            actions.append("human_approval")
            reasoning += " (human_approval added: reply on a high-stakes category)"

    # Rule 6: human_approval, if present, must always be last.
    if "human_approval" in actions:
        actions = [a for a in actions if a != "human_approval"] + ["human_approval"]

    # Rule 7: never leave actions empty.
    if not actions:
        actions = ["do_nothing"]
        reasoning += " (fallback: no actions proposed, defaulted to do_nothing)"

    return ActionPlan(actions=actions, reasoning=reasoning)


def validate_actions_node(state: PlannerState) -> PlannerState:
    validated: List[PlannedEmail] = []
    for item in state.get("planned_emails", []):
        enforced_plan = _enforce_guardrails(item)
        validated.append(
            PlannedEmail(prioritized_email=item.prioritized_email, action_plan=enforced_plan)
        )
    return {**state, "planned_emails": validated}


# # --------------------------------------------------------------------------
# # Graph assembly
# # --------------------------------------------------------------------------


# def build_graph():
#     graph = StateGraph(PlannerState)
#     graph.add_node("propose_actions", propose_actions_node)
#     graph.add_node("validate_actions", validate_actions_node)

#     graph.add_edge(START, "propose_actions")
#     graph.add_edge("propose_actions", "validate_actions")
#     graph.add_edge("validate_actions", END)

#     return graph.compile()


# planner_graph = build_graph()


# def run_planner_agent(prioritized_emails: List[PrioritizedEmail]) -> PlannerState:
#     """Convenience entry point. Returns final state, including
#     `planned_emails: List[PlannedEmail]` (each with an `action_plan.actions` sequence)
#     ready for the executor/orchestrator to dispatch."""
#     initial_state: PlannerState = {
#         "prioritized_emails": prioritized_emails,
#         "planned_emails": [],
#         "errors": [],
#     }
#     return planner_graph.invoke(initial_state)


# if __name__ == "__main__":
#     from email_understanding_agent import run_email_understanding_agent
#     from classifier_agent import run_classifier_agent
#     from priority_agent import run_priority_agent

#     understanding_result = run_email_understanding_agent(max_results=5)
#     classified_result = run_classifier_agent(understanding_result["structured_emails"])
#     priority_result = run_priority_agent(classified_result["classified_emails"])
#     result = run_planner_agent(priority_result["prioritized_emails"])

#     print(json.dumps([p.model_dump() for p in result["planned_emails"]], indent=2))
#     if result["errors"]:
#         print("Errors:", result["errors"])