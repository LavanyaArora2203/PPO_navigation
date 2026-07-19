# graph.py

from langgraph.graph import StateGraph, END
from backend.langraph_agents.state import AgentState
from backend.langraph_agents.router import *


builder = StateGraph(AgentState)

builder.add_node("tool", tool_node)
builder.add_node("response", response_node)

builder.set_entry_point("tool")

builder.add_conditional_edges(
    "tool",
    router,
    {
        "tool": "tool",
        "response": "response"
    }
)

builder.add_edge("response", END)

graph = builder.compile()