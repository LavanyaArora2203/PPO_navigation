"""
Executor Agent (LangGraph)
----------------------------
Takes `PlannedEmail` objects (from the Planner Agent) and executes the
`action_plan.actions` sequence by calling the stub tools in tools.py.

SAFETY RULE: "reply" and "forward" are never executed automatically, because
both send an email out on the user's behalf. When either is encountered, the
executor drafts the outgoing content, logs it as `awaiting_approval`, and
STOPS processing further actions for that email. Nothing is actually sent
until a human calls `approve_and_send()` explicitly. An explicit
"human_approval" action in the sequence behaves the same way (stop + flag).

All other actions (archive, delete, mark_read, flag, create_task,
schedule_meeting, notify_slack) are executed directly since none of them
send anything out on the user's behalf.

SETUP
-----
    pip install --upgrade langgraph langchain-core pydantic

Place this file alongside tools.py and planner_agent.py (and the rest of the
pipeline files).

USAGE
-----
    from planner_agent import run_planner_agent
    from executor_agent import run_executor_agent, approve_and_send

    planned_result = run_planner_agent(prioritized_emails)
    executed_result = run_executor_agent(planned_result["planned_emails"])

    for item in executed_result["executed_emails"]:
        if item.requires_human_approval:
            print("NEEDS APPROVAL:", item.pending_send)
            # once a human approves:
            # approve_and_send(item.pending_send)
"""

from __future__ import annotations

import json
from typing import List, Literal, Optional, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

import tools
from planner import PlannedEmail

# --------------------------------------------------------------------------
# Structured output
# --------------------------------------------------------------------------

ExecutionStatus = Literal["success", "skipped", "awaiting_approval", "error"]


class ExecutionResult(BaseModel):
    action: str
    tool_name: Optional[str] = None
    status: ExecutionStatus
    details: dict = {}


class PendingSend(BaseModel):
    """An outbound email (reply or forward) drafted but not yet sent, awaiting approval."""

    kind: Literal["reply", "forward"]
    email_id: str
    thread_id: Optional[str] = None
    to: str
    subject: str
    body: str
    note: str = ""  # used for forward


class ExecutedEmail(BaseModel):
    planned_email: PlannedEmail
    execution_log: List[ExecutionResult] = []
    pending_send: Optional[PendingSend] = None
    requires_human_approval: bool = False


# --------------------------------------------------------------------------
# Graph state
# --------------------------------------------------------------------------


class ExecutorState(TypedDict):
    planned_emails: List[PlannedEmail]
    executed_emails: List[ExecutedEmail]
    errors: List[str]


# --------------------------------------------------------------------------
# Action -> tool dispatch
# --------------------------------------------------------------------------

OUTBOUND_ACTIONS = {"reply", "forward"}  # actions that send email and require approval


def _draft_reply(planned: PlannedEmail) -> PendingSend:
    email_info = planned.prioritized_email.classified_email.email_info
    return PendingSend(
        kind="reply",
        email_id=email_info.email_id,
        thread_id=email_info.thread_id,
        to=email_info.sender.email,
        subject=f"Re: {email_info.subject}",
        body=(
            f"[Draft reply — awaiting approval]\n\n"
            f"Regarding: {email_info.summary}\n\n"
            f"(Replace with actual generated reply content from a responder agent.)"
        ),
    )


def _draft_forward(planned: PlannedEmail) -> PendingSend:
    email_info = planned.prioritized_email.classified_email.email_info
    return PendingSend(
        kind="forward",
        email_id=email_info.email_id,
        thread_id=email_info.thread_id,
        to="",  # recipient not yet determined — human must fill this in on approval
        subject=f"Fwd: {email_info.subject}",
        body=email_info.body_text,
        note="Forward target not specified by planner — set `to` before approving.",
    )


def _run_tool_action(action: str, planned: PlannedEmail) -> ExecutionResult:
    """Execute a single non-outbound action by calling the matching tool in tools.py."""
    email_info = planned.prioritized_email.classified_email.email_info
    priority = planned.prioritized_email.priority
    category = planned.prioritized_email.classified_email.classification.category

    try:
        if action == "archive":
            result = tools.archive_email(email_id=email_info.email_id)
            return ExecutionResult(action=action, tool_name="archive_email", status="success", details=result)

        if action == "delete":
            result = tools.delete_email(email_id=email_info.email_id)
            return ExecutionResult(action=action, tool_name="delete_email", status="success", details=result)

        if action == "mark_read":
            result = tools.label_email(email_id=email_info.email_id, label="READ")
            return ExecutionResult(action=action, tool_name="label_email", status="success", details=result)

        if action == "flag":
            result = tools.label_email(email_id=email_info.email_id, label="FLAGGED")
            return ExecutionResult(action=action, tool_name="label_email", status="success", details=result)

        if action == "create_task":
            due_date = email_info.mentioned_dates_times[0] if email_info.mentioned_dates_times else None
            result = tools.create_notion_task(
                title=email_info.subject, description=email_info.summary, due_date=due_date
            )
            return ExecutionResult(action=action, tool_name="create_notion_task", status="success", details=result)

        if action == "schedule_meeting":
            when = email_info.mentioned_dates_times[0] if email_info.mentioned_dates_times else "TBD"
            result = tools.create_calendar_event(
                title=email_info.subject, when=when, attendees=[email_info.sender.email]
            )
            return ExecutionResult(
                action=action, tool_name="create_calendar_event", status="success", details=result
            )

        if action == "notify_slack":
            message = f"[{priority.level}] {category} email: '{email_info.subject}' from {email_info.sender.email}"
            result = tools.send_slack_message(channel="#email-alerts", message=message)
            return ExecutionResult(
                action=action, tool_name="send_slack_message", status="success", details=result
            )

        if action == "do_nothing":
            return ExecutionResult(action=action, status="skipped", details={"reason": "no action required"})

        return ExecutionResult(
            action=action, status="error", details={"reason": f"unrecognized action '{action}'"}
        )

    except Exception as exc:  # noqa: BLE001
        return ExecutionResult(action=action, status="error", details={"error": str(exc)})


def execute_actions_node(state: ExecutorState) -> ExecutorState:
    executed: List[ExecutedEmail] = list(state.get("executed_emails", []))
    errors: List[str] = list(state.get("errors", []))

    for planned in state.get("planned_emails", []):
        email_id = planned.prioritized_email.classified_email.email_info.email_id
        log: List[ExecutionResult] = []
        pending_send: Optional[PendingSend] = None
        requires_approval = False

        try:
            for action in planned.action_plan.actions:
                if action == "reply":
                    pending_send = _draft_reply(planned)
                    log.append(
                        ExecutionResult(
                            action=action, status="awaiting_approval",
                            details={"pending_send": pending_send.model_dump()},
                        )
                    )
                    requires_approval = True
                    break  # stop the sequence — nothing sends until approved

                if action == "forward":
                    pending_send = _draft_forward(planned)
                    log.append(
                        ExecutionResult(
                            action=action, status="awaiting_approval",
                            details={"pending_send": pending_send.model_dump()},
                        )
                    )
                    requires_approval = True
                    break

                if action == "human_approval":
                    log.append(
                        ExecutionResult(
                            action=action, status="awaiting_approval",
                            details={"reason": "planner flagged this email for human review"},
                        )
                    )
                    requires_approval = True
                    break

                log.append(_run_tool_action(action, planned))

            executed.append(
                ExecutedEmail(
                    planned_email=planned,
                    execution_log=log,
                    pending_send=pending_send,
                    requires_human_approval=requires_approval,
                )
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Execution failed for email {email_id}: {exc}")

    return {**state, "executed_emails": executed, "errors": errors}


# --------------------------------------------------------------------------
# Human approval gate — called externally, NOT part of the graph
# --------------------------------------------------------------------------


def approve_and_send(pending: PendingSend) -> ExecutionResult:
    """Call this only after a human has reviewed and approved a pending reply/forward.
    This is the one place reply_email() / forward_email() actually get invoked."""
    if pending.kind == "reply":
        result = tools.reply_email(
            email_id=pending.email_id, to=pending.to, subject=pending.subject,
            body=pending.body, thread_id=pending.thread_id,
        )
        return ExecutionResult(action="reply", tool_name="reply_email", status="success", details=result)

    if pending.kind == "forward":
        if not pending.to:
            return ExecutionResult(
                action="forward", status="error",
                details={"reason": "forward target ('to') was never set — cannot send"},
            )
        result = tools.forward_email(email_id=pending.email_id, to=pending.to, note=pending.note)
        return ExecutionResult(action="forward", tool_name="forward_email", status="success", details=result)

    return ExecutionResult(action="unknown", status="error", details={"reason": "unrecognized pending_send kind"})


def reject_send(pending: PendingSend, reason: str = "") -> ExecutionResult:
    """Call this if a human rejects a pending reply/forward instead of approving it."""
    return ExecutionResult(
        action=pending.kind, status="skipped", details={"reason": reason or "rejected by human reviewer"}
    )


# # --------------------------------------------------------------------------
# # Graph assembly
# # --------------------------------------------------------------------------


# def build_graph():
#     graph = StateGraph(ExecutorState)
#     graph.add_node("execute_actions", execute_actions_node)
#     graph.add_edge(START, "execute_actions")
#     graph.add_edge("execute_actions", END)
#     return graph.compile()


# executor_graph = build_graph()


# def run_executor_agent(planned_emails: List[PlannedEmail]) -> ExecutorState:
#     """Convenience entry point. Returns final state, including
#     `executed_emails: List[ExecutedEmail]`. Emails with `requires_human_approval=True`
#     have a `pending_send` that must go through `approve_and_send()` / `reject_send()`."""
#     initial_state: ExecutorState = {
#         "planned_emails": planned_emails,
#         "executed_emails": [],
#         "errors": [],
#     }
#     return executor_graph.invoke(initial_state)


# if __name__ == "__main__":
#     from email_understanding_agent import run_email_understanding_agent
#     from classifier_agent import run_classifier_agent
#     from priority_agent import run_priority_agent
#     from planner_agent import run_planner_agent

#     understanding_result = run_email_understanding_agent(max_results=5)
#     classified_result = run_classifier_agent(understanding_result["structured_emails"])
#     priority_result = run_priority_agent(classified_result["classified_emails"])
#     planned_result = run_planner_agent(priority_result["prioritized_emails"])
#     result = run_executor_agent(planned_result["planned_emails"])

#     print(json.dumps([e.model_dump() for e in result["executed_emails"]], indent=2))
#     if result["errors"]:
#         print("Errors:", result["errors"])