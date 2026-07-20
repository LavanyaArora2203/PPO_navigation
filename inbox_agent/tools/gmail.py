"""
LangChain tool: fetch unread Gmail messages.
How it works:

fetch_unread_emails(max_results=10, query=None, include_body=True) — searches is:unread, optionally combined with your own Gmail query filter (e.g. from:someone@x.com)
Returns a list of dicts: id, thread_id, sender, subject, date, snippet, and body (plain text)
Uses OAuth2 with a cached token.json so the agent doesn't need to re-auth every run
Read-only scope by default (gmail.readonly)

SETUP
-----
1. Enable the Gmail API in Google Cloud Console and create OAuth 2.0
   credentials (Desktop app), download as `credentials.json`.
2. Install dependencies:
       pip install --upgrade google-api-python-client google-auth-httplib2 \
           google-auth-oauthlib langchain langchain-core

3. First run will open a browser to authorize; a `token.json` is cached
   afterwards for subsequent runs (no re-auth needed until it expires
   or is revoked).

4. Scopes: this tool only requests read-only access
   (`gmail.readonly`). Widen SCOPES if you need to modify/send mail.

USAGE
-----
    from gmail import fetch_unread_emails

    agent_tools = [fetch_unread_emails]
    # e.g. bind to a LangChain agent / AgentExecutor as usual

Calling the tool directly:
    fetch_unread_emails.invoke({"max_results": 5})
"""

import base64
import os
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from langchain_core.tools import tool
from pydantic import BaseModel, Field

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS_PATH = os.environ.get("GMAIL_CREDENTIALS_PATH", "credentials.json")
TOKEN_PATH = os.environ.get("GMAIL_TOKEN_PATH", "token.json")


def _get_gmail_service():
    """Authenticate (using cached token if available) and return a Gmail API client."""
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _decode_snippet_body(payload) -> str:
    """Best-effort extraction of plain-text body from a Gmail message payload."""
    if not payload:
        return ""

    def _walk(part):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode(
                "utf-8", errors="replace"
            )
        for sub in part.get("parts", []) or []:
            result = _walk(sub)
            if result:
                return result
        return ""

    return _walk(payload)


class FetchUnreadEmailsInput(BaseModel):
    max_results: int = Field(
        default=10, description="Maximum number of unread emails to fetch (1-50)."
    )
    query: Optional[str] = Field(
        default=None,
        description=(
            "Optional additional Gmail search filter, combined with 'is:unread' "
            "(e.g. 'from:boss@company.com', 'subject:invoice')."
        ),
    )
    include_body: bool = Field(
        default=True, description="Whether to include the plain-text email body."
    )


@tool("fetch_unread_emails", args_schema=FetchUnreadEmailsInput)
def fetch_unread_emails(
    max_results: int = 10,
    query: Optional[str] = None,
    include_body: bool = True,
) -> List[dict]:
    """Fetch unread emails from the user's Gmail inbox.

    Returns a list of dicts with: id, thread_id, sender, subject, date,
    snippet, and (optionally) body.
    """
    max_results = max(1, min(max_results, 50))
    search_query = "is:unread" if not query else f"is:unread {query}"

    try:
        service = _get_gmail_service()
        results = (
            service.users()
            .messages()
            .list(userId="me", q=search_query, maxResults=max_results)
            .execute()
        )
        messages = results.get("messages", [])

        emails = []
        for msg_ref in messages:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=msg_ref["id"], format="full")
                .execute()
            )
            headers = {
                h["name"]: h["value"]
                for h in msg.get("payload", {}).get("headers", [])
            }
            entry = {
                "id": msg["id"],
                "thread_id": msg["threadId"],
                "sender": headers.get("From", ""),
                "subject": headers.get("Subject", "(no subject)"),
                "date": headers.get("Date", ""),
                "snippet": msg.get("snippet", ""),
            }
            if include_body:
                entry["body"] = _decode_snippet_body(msg.get("payload"))
            emails.append(entry)

        return emails

    except HttpError as error:
        return [{"error": f"Gmail API error: {error}"}]
    except FileNotFoundError:
        return [
            {
                "error": (
                    f"OAuth credentials file not found at '{CREDENTIALS_PATH}'. "
                    "See module docstring for setup instructions."
                )
            }
        ]


if __name__ == "__main__":
    # Quick manual test
    for email in fetch_unread_emails.invoke({"max_results": 5}):
        print(email)