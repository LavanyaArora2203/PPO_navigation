# langgraph_agent/state.py

from typing import TypedDict

class AgentState(TypedDict):
    user_input: str
    tool_result: str
    response: str