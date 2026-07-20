"""
Classifier Agent (LangGraph)
-----------------------------
Takes `EmailInfo` objects produced by the Email Understanding Agent and
classifies each into exactly one of a fixed set of categories, producing
`ClassifiedEmail` objects for the next agents in the pipeline (priority,
planner, responder).

SETUP
-----
    pip install --upgrade langgraph langchain-core langchain-anthropic pydantic
    export ANTHROPIC_API_KEY=...

Place this file alongside email_understanding_agent.py and gmail_unread_tool.py.

USAGE
-----
    from email_understanding_agent import run_email_understanding_agent
    from classifier_agent import run_classifier_agent

    understanding_result = run_email_understanding_agent(max_results=10)
    classified_result = run_classifier_agent(understanding_result["structured_emails"])

    for item in classified_result["classified_emails"]:
        print(item.classification.category, "-", item.email_info.subject)
"""

from __future__ import annotations

import json
from typing import List, Literal, TypedDict

from llm import llm
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from email_understanding import EmailInfo

# --------------------------------------------------------------------------
# Categories & structured output
# --------------------------------------------------------------------------

Category = Literal[
    "Work",
    "Personal",
    "Finance",
    "Promotion",
    "Spam",
    "Job",
    "Interview",
    "Newsletter",
    "Bills",
    "Shopping",
    "Social",
]

CATEGORY_DEFINITIONS = """\
- Work: professional/business correspondence, colleagues, projects, meetings, internal comms
- Personal: emails from friends/family, personal matters unrelated to work or finance
- Finance: banking, investments, statements, financial alerts (not recurring bills)
- Promotion: marketing/sales emails, discounts, ads from brands
- Spam: unsolicited, suspicious, phishing, or clearly unwanted junk mail
- Job: job applications, recruiter outreach, offer letters, application status updates
- Interview: interview scheduling, confirmations, or follow-ups tied to a specific hiring process
- Newsletter: subscribed digests, blog updates, curated content emails
- Bills: recurring payment due notices, utility/subscription/invoice bills
- Shopping: order confirmations, shipping/delivery updates, receipts from purchases
- Social: notifications from social networks, forums, or community platforms
"""


class Classification(BaseModel):
    category: Category
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the chosen category")
    reasoning: str = Field(description="One sentence explaining the classification")


class ClassifiedEmail(BaseModel):
    email_info: EmailInfo
    classification: Classification


# --------------------------------------------------------------------------
# Graph state
# --------------------------------------------------------------------------


class ClassifierState(TypedDict):
    emails: List[EmailInfo]
    classified_emails: List[ClassifiedEmail]
    errors: List[str]


# --------------------------------------------------------------------------
# LLM + node
# --------------------------------------------------------------------------

# _classifier_llm = ChatAnthropic(model="claude-sonnet-5", temperature=0)
_structured_classifier = llm.with_structured_output(Classification)

_CLASSIFICATION_PROMPT = """You are classifying an email into exactly one category.

Categories and definitions:
{definitions}

Rules:
- Choose exactly one category, the single best fit.
- If it's a recurring payment/utility notice, prefer "Bills" over "Finance".
- If it's an order/shipping/delivery/receipt, use "Shopping" even if payment is mentioned.
- If it relates to a specific interview process (scheduling, confirmation, feedback), use \
"Interview" over "Job".
- If it's a general job application/recruiter outreach without an interview being scheduled, \
use "Job".
- Use "Spam" only for unsolicited/suspicious/junk mail, not legitimate promotions you dislike.

Email details:
From: {sender}
Subject: {subject}
Summary: {summary}
Snippet: {snippet}
Contains links: {contains_links}
Mentioned entities: {entities}
Gmail labels: {labels}
"""


def classify_node(state: ClassifierState) -> ClassifierState:
    classified: List[ClassifiedEmail] = list(state.get("classified_emails", []))
    errors: List[str] = list(state.get("errors", []))

    for email_info in state.get("emails", []):
        try:
            classification = _structured_classifier.invoke(
                _CLASSIFICATION_PROMPT.format(
                    definitions=CATEGORY_DEFINITIONS,
                    sender=f"{email_info.sender.name or ''} <{email_info.sender.email}>",
                    subject=email_info.subject,
                    summary=email_info.summary,
                    snippet=email_info.snippet,
                    contains_links=email_info.contains_links,
                    entities=", ".join(email_info.mentioned_entities) or "none",
                    labels=", ".join(email_info.gmail_labels) or "none",
                )
            )
            classified.append(
                ClassifiedEmail(email_info=email_info, classification=classification)
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Classification failed for email {email_info.email_id}: {exc}")

    return {**state, "classified_emails": classified, "errors": errors}


# # --------------------------------------------------------------------------
# # Graph assembly
# # --------------------------------------------------------------------------


# def build_graph():
#     graph = StateGraph(ClassifierState)
#     graph.add_node("classify", classify_node)
#     graph.add_edge(START, "classify")
#     graph.add_edge("classify", END)
#     return graph.compile()


# classifier_graph = build_graph()


# def run_classifier_agent(emails: List[EmailInfo]) -> ClassifierState:
#     """Convenience entry point. Returns final state, including
#     `classified_emails: List[ClassifiedEmail]` ready for the priority agent."""
#     initial_state: ClassifierState = {
#         "emails": emails,
#         "classified_emails": [],
#         "errors": [],
#     }
#     return classifier_graph.invoke(initial_state)


# if __name__ == "__main__":
#     from email_understanding import run_email_understanding_agent

#     understanding_result = run_email_understanding_agent(max_results=5)
#     result = run_classifier_agent(understanding_result["structured_emails"])

#     print(
#         json.dumps(
#             [c.model_dump() for c in result["classified_emails"]], indent=2
#         )
#     )
#     if result["errors"]:
#         print("Errors:", result["errors"])