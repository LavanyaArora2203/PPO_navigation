# langgraph_agent/tools.py

import requests
from langchain_core.tools import tool

# BASE_URL = "http://localhost:8000"
from backend.main import *
from backend.schemas import *

# @tool
# def list_tasks_tool():
#     """List all tasks"""

#     r = requests.get(f"{BASE_URL}/tasks")
#     return r.json()


@tool
def create_task_tool(title: str, description: str):

    """Create a task"""

    task=TaskCreate(
        title=title,
        description=description,
        status='Pending',
    )
    return create_task(task)

@tool
def list_tasks_tool():
    return get_tasks()


@tool
def delete_task_tool(task_id: UUID):
    return delete_task(task_id)



@tool
def update_task_tool(
    task_id: UUID,
    title: str,
    description: str,
    status: str
):
    """
    Update an existing task.

    Args:
        task_id: ID of the task to update.
        title: Updated task title.
        description: Updated task description.
        status: Updated task status (e.g. Pending, In Progress, Completed).
    """

    task = TaskUpdate(
        title=title,
        description=description,
        status=status
    )

    result = update_task(task_id, task)

    return result