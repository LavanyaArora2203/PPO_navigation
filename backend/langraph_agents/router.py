# router.py

def router(state):

    text = state["user_input"].lower()

    if "create" in text or "add" in text:
        return "tool"

    if "update" in text or "edit" in text:
        return "tool"

    if "delete" in text or "remove" in text:
        return "tool"

    if "show" in text or "list" in text:
        return "tool"

    return "response"



from langgraph.prebuilt import ToolNode
from backend.langraph_agents.tools import *
from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="llama3.2:3b",      # or "qwen2.5:7b"
    temperature=0,
)




tools = [
    create_task_tool,
    update_task_tool,
    list_tasks_tool,
    delete_task_tool
]

llm = llm.bind_tools(tools)

tool_node = ToolNode(tools)

def response_node(state):

    return {
        "response": state["tool_result"]
    }

response = llm.invoke(
    "Create a task called Buy Milk"
)

print(response)