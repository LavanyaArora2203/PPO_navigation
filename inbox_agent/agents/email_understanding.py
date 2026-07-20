"""
Email Understanding Agent (LangGraph)
--------------------------------------
Fetches unread Gmail messages via `fetch_unread_emails` (gmail_unread_tool.py)
and turns each raw message into a structured `EmailInfo` object that
downstream agents (classifier, priority, planner, responder) can consume
directly, without re-parsing raw email content.

SETUP
-----
    pip install --upgrade langgraph langchain-core langchain-anthropic pydantic

    export ANTHROPIC_API_KEY=...        # for the extraction LLM
    # + Gmail OAuth setup as described in gmail_unread_tool.py

Place this file in the same directory as gmail_unread_tool.py.

USAGE
-----
    from email_understanding_agent import run_email_understanding_agent

    result = run_email_understanding_agent(max_results=10)
    for email_info in result["structured_emails"]:
        print(email_info.model_dump())
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, TypedDict

from llm import llm
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from tools.gmail import fetch_unread_emails

# --------------------------------------------------------------------------
# Structured output schema — the contract handed to classifier / priority /
# planner / responder agents.
# --------------------------------------------------------------------------


class Attachment(BaseModel):
    filename: str
    mime_type: str
    size_bytes: Optional[int] = None


class Participant(BaseModel):
    name: Optional[str] = None
    email: str


class EmailInfo(BaseModel):
    # --- Identity / threading ---
    email_id: str
    thread_id: str
    is_reply: bool
    in_reply_to: Optional[str] = None
    thread_message_count: Optional[int] = None

    # --- Participants ---
    sender: Participant
    to: List[Participant] = []
    cc: List[Participant] = []

    # --- Core content ---
    subject: str
    date: str
    body_text: str
    snippet: str

    # --- Attachments ---
    has_attachments: bool
    attachments: List[Attachment] = []

    # --- Extracted signal ---
    summary: str
    detected_language: str
    contains_links: bool
    links: List[str] = []
    mentioned_dates_times: List[str] = []
    mentioned_entities: List[str] = []
    question_present: bool

    # --- Passthrough metadata ---
    gmail_labels: List[str] = []
    raw_headers: Dict[str, str] = {}


class EmailInfoExtraction(BaseModel):
    """Subset of EmailInfo that the LLM is responsible for deriving.
    (Identity/threading/participant/attachment fields are filled deterministically
    from the raw Gmail payload, not by the LLM, to avoid hallucination on facts
    we already have ground truth for.)
    """

    is_reply: bool
    body_text: str = Field(description="Cleaned body: quoted history and signature blocks stripped")
    summary: str = Field(description="1-2 sentence factual summary of what the email says or requests")
    detected_language: str = Field(description="ISO 639-1 code, e.g. 'en'")
    contains_links: bool
    links: List[str] = []
    mentioned_dates_times: List[str] = Field(
        default=[], description="Raw phrases like 'next Friday', '3pm EST', 'March 5th'"
    )
    mentioned_entities: List[str] = Field(
        default=[], description="People, organizations, or products named in the email"
    )
    question_present: bool = Field(description="Does the email directly ask something?")


# --------------------------------------------------------------------------
# Graph state
# --------------------------------------------------------------------------


class AgentState(TypedDict):
    max_results: int
    query: Optional[str]
    raw_emails: List[dict]
    structured_emails: List[EmailInfo]
    errors: List[str]


# --------------------------------------------------------------------------
# Nodes
# --------------------------------------------------------------------------


def fetch_emails_node(state: AgentState) -> AgentState:
    """Node 1: call the fetch_unread_emails tool."""
    raw = fetch_unread_emails.invoke(
        {
            "max_results": state.get("max_results", 10),
            "query": state.get("query"),
            "include_body": True,
        }
    )

    errors = list(state.get("errors", []))
    valid_emails = []
    for item in raw:
        if "error" in item:
            errors.append(item["error"])
        else:
            valid_emails.append(item)

    return {**state, "raw_emails": valid_emails, "errors": errors}


# _extractor_llm = ChatAnthropic(model="claude-sonnet-5", temperature=0)
_structured_extractor = llm.with_structured_output(EmailInfoExtraction)

_EXTRACTION_PROMPT = """You are extracting structured signal from a raw email so that \
downstream agents (classifier, priority, planner, responder) can act on it without re-reading \
the raw text. Be factual and literal — do not infer intent or urgency, only extract what the \
email actually contains.

From: {sender}
Subject: {subject}
Date: {date}
Snippet: {snippet}

Body:
{body}
"""


def extract_info_node(state: AgentState) -> AgentState:
    """Node 2: run LLM extraction over each raw email and assemble EmailInfo objects."""
    structured: List[EmailInfo] = list(state.get("structured_emails", []))
    errors = list(state.get("errors", []))

    for raw in state.get("raw_emails", []):
        try:
            extraction: EmailInfoExtraction = _structured_extractor.invoke(
                _EXTRACTION_PROMPT.format(
                    sender=raw.get("sender", ""),
                    subject=raw.get("subject", ""),
                    date=raw.get("date", ""),
                    snippet=raw.get("snippet", ""),
                    body=raw.get("body", "") or raw.get("snippet", ""),
                )
            )

            sender_email = raw.get("sender", "")
            sender_name = None
            if "<" in sender_email and ">" in sender_email:
                sender_name = sender_email.split("<")[0].strip().strip('"') or None
                sender_email = sender_email.split("<")[1].split(">")[0].strip()

            email_info = EmailInfo(
                email_id=raw["id"],
                thread_id=raw["thread_id"],
                is_reply=extraction.is_reply,
                in_reply_to=raw.get("in_reply_to"),
                thread_message_count=raw.get("thread_message_count"),
                sender=Participant(name=sender_name, email=sender_email),
                to=[],
                cc=[],
                subject=raw.get("subject", "(no subject)"),
                date=raw.get("date", ""),
                body_text=extraction.body_text,
                snippet=raw.get("snippet", ""),
                has_attachments=bool(raw.get("attachments")),
                attachments=[
                    Attachment(**a) for a in raw.get("attachments", [])
                ],
                summary=extraction.summary,
                detected_language=extraction.detected_language,
                contains_links=extraction.contains_links,
                links=extraction.links,
                mentioned_dates_times=extraction.mentioned_dates_times,
                mentioned_entities=extraction.mentioned_entities,
                question_present=extraction.question_present,
                gmail_labels=raw.get("labels", []),
                raw_headers=raw.get("headers", {}),
            )
            structured.append(email_info)

        except Exception as exc:  # noqa: BLE001
            errors.append(f"Extraction failed for email {raw.get('id')}: {exc}")

    return {**state, "structured_emails": structured, "errors": errors}


# # --------------------------------------------------------------------------
# # Graph assembly
# # --------------------------------------------------------------------------


# def build_graph():
#     graph = StateGraph(AgentState)
#     graph.add_node("fetch_emails", fetch_emails_node)
#     graph.add_node("extract_info", extract_info_node)

#     graph.add_edge(START, "fetch_emails")
#     graph.add_edge("fetch_emails", "extract_info")
#     graph.add_edge("extract_info", END)

#     return graph.compile()


# email_understanding_graph = build_graph()


# def run_email_understanding_agent(max_results: int = 10, query: Optional[str] = None) -> AgentState:
#     """Convenience entry point. Returns final graph state, including
#     `structured_emails: List[EmailInfo]` ready for classifier/priority/planner/responder."""
#     initial_state: AgentState = {
#         "max_results": max_results,
#         "query": query,
#         "raw_emails": [],
#         "structured_emails": [],
#         "errors": [],
#     }
#     return email_understanding_graph.invoke(initial_state)


# if __name__ == "__main__":
#     result = run_email_understanding_agent(max_results=5)
#     print(json.dumps([e.model_dump() for e in result["structured_emails"]], indent=2))
#     if result["errors"]:
#         print("Errors:", result["errors"])