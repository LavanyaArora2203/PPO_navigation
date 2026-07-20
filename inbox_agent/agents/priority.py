"""
Priority Agent (LangGraph)
----------------------------
Takes `ClassifiedEmail` objects produced by the Classifier Agent and assigns
a priority level (Urgent / High / Medium / Low) with reasoning, producing
`PrioritizedEmail` objects for the next agents (planner, responder).

SETUP
-----
    pip install --upgrade langgraph langchain-core langchain-anthropic pydantic
    export ANTHROPIC_API_KEY=...

Place this file alongside email_understanding_agent.py, classifier_agent.py,
and gmail_unread_tool.py.

USAGE
-----
    from email_understanding_agent import run_email_understanding_agent
    from classifier_agent import run_classifier_agent
    from priority_agent import run_priority_agent

    understanding_result = run_email_understanding_agent(max_results=10)
    classified_result = run_classifier_agent(understanding_result["structured_emails"])
    priority_result = run_priority_agent(classified_result["classified_emails"])

    for item in priority_result["prioritized_emails"]:
        print(item.priority.level, "-", item.classified_email.email_info.subject)
"""

from __future__ import annotations

import json
from typing import List, Literal, TypedDict

# from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from llm import llm

from classifier import ClassifiedEmail

# --------------------------------------------------------------------------
# Structured output
# --------------------------------------------------------------------------

PriorityLevel = Literal["Urgent", "High", "Medium", "Low"]

PRIORITY_DEFINITIONS = """\
- Urgent: needs action today or has an explicit near-term deadline/time-sensitive event \
(e.g. "reply by EOD", a meeting in the next few hours, a payment due imminently, an active \
incident). Ignoring it has real, immediate consequences.
- High: needs action soon (within the next few days), or is important even without a hard \
deadline (e.g. a manager's request, an interview invite, a bill due this week).
- Medium: worth addressing but not time-critical (e.g. an FYI from a colleague, a non-urgent \
question, a routine notification that may need a reply eventually).
- Low: informational only, no action needed, or safe to ignore/batch-review later \
(e.g. newsletters, promotions, social notifications, spam).
"""


class Priority(BaseModel):
    level: PriorityLevel
    reasoning: str = Field(description="1-2 sentences explaining why this priority was assigned")
    requires_reply: bool = Field(
        description="True if the sender expects or requests a response from the recipient; otherwise False."
    )


class PrioritizedEmail(BaseModel):
    classified_email: ClassifiedEmail
    priority: Priority


# --------------------------------------------------------------------------
# Graph state
# --------------------------------------------------------------------------


class PriorityState(TypedDict):
    classified_emails: List[ClassifiedEmail]
    prioritized_emails: List[PrioritizedEmail]
    errors: List[str]


# --------------------------------------------------------------------------
# LLM + node
# --------------------------------------------------------------------------

# _priority_llm = ChatAnthropic(model="claude-sonnet-5", temperature=0)
_structured_priority = llm.with_structured_output(Priority)

_PRIORITY_PROMPT = """You are assigning a priority level to an email so a human can triage their inbox efficiently.

Priority levels and definitions:
{definitions}

Your tasks are:

1. Assign one priority level.
2. Explain your reasoning in 1-2 sentences.
3. Determine whether this email requires a reply.

Rules for requires_reply:

Return true if:
- the sender explicitly asks a question
- the sender requests information
- the sender asks the recipient to perform an action
- the sender requests confirmation
- the sender schedules or proposes a meeting
- the sender is expecting a response

Return false if:
- the email is informational only
- newsletters
- promotions
- receipts
- shipping notifications
- system notifications
- no response is expected

Priority guidance:

- Base the decision on actual urgency signals in the content (deadlines, explicit asks,
time-sensitive events), not just the category.

- Category is a strong prior but not absolute.

- Bills/Finance items are Urgent only if the due date is imminent.

- Interview/Job items are High by default.

- If the email explicitly asks a direct question or requests a reply,
that usually implies requires_reply = true.

Email details:

Category: {category}
From: {sender}
Subject: {subject}
Summary: {summary}
Question present: {question_present}
Mentioned dates/times: {mentioned_dates_times}
Gmail labels: {labels}
"""

def prioritize_node(state: PriorityState) -> PriorityState:
    prioritized: List[PrioritizedEmail] = list(state.get("prioritized_emails", []))
    errors: List[str] = list(state.get("errors", []))

    for item in state.get("classified_emails", []):
        email_info = item.email_info
        try:
            priority = _structured_priority.invoke(
                _PRIORITY_PROMPT.format(
                    definitions=PRIORITY_DEFINITIONS,
                    category=item.classification.category,
                    sender=f"{email_info.sender.name or ''} <{email_info.sender.email}>",
                    subject=email_info.subject,
                    summary=email_info.summary,
                    question_present=email_info.question_present,
                    mentioned_dates_times=", ".join(email_info.mentioned_dates_times) or "none",
                    labels=", ".join(email_info.gmail_labels) or "none",
                )
            )
            prioritized.append(PrioritizedEmail(classified_email=item, priority=priority))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Prioritization failed for email {email_info.email_id}: {exc}")

    return {**state, "prioritized_emails": prioritized, "errors": errors}


# # --------------------------------------------------------------------------
# # Graph assembly
# # --------------------------------------------------------------------------


# def build_graph():
#     graph = StateGraph(PriorityState)
#     graph.add_node("prioritize", prioritize_node)
#     graph.add_edge(START, "prioritize")
#     graph.add_edge("prioritize", END)
#     return graph.compile()


# priority_graph = build_graph()


# def run_priority_agent(classified_emails: List[ClassifiedEmail]) -> PriorityState:
#     """Convenience entry point. Returns final state, including
#     `prioritized_emails: List[PrioritizedEmail]` ready for the planner agent."""
#     initial_state: PriorityState = {
#         "classified_emails": classified_emails,
#         "prioritized_emails": [],
#         "errors": [],
#     }
#     return priority_graph.invoke(initial_state)


# if __name__ == "__main__":
#     from email_understanding_agent import run_email_understanding_agent
#     from classifier_agent import run_classifier_agent

#     understanding_result = run_email_understanding_agent(max_results=5)
#     classified_result = run_classifier_agent(understanding_result["structured_emails"])
#     result = run_priority_agent(classified_result["classified_emails"])

#     print(
#         json.dumps(
#             [p.model_dump() for p in result["prioritized_emails"]], indent=2
#         )
#     )
#     if result["errors"]:
#         print("Errors:", result["errors"])