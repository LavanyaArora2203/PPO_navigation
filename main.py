from datetime import date
from typing import Dict, Literal
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from task_model import TaskCreate,TaskUpdate

app = FastAPI(title="Task Management API")


# ----------------------
# Pydantic Models
# ----------------------



class Task(TaskCreate):
    id: UUID


# ----------------------
# In-memory Database
# ----------------------

tasks_db: Dict[UUID, Task] = {}


# ----------------------
# Routes
# ----------------------

@app.get("/tasks", response_model=list[Task])
def get_tasks():
    """
    Get all tasks.
    """
    return list(tasks_db.values())


@app.post("/tasks", response_model=Task, status_code=201)
def create_task(task: TaskCreate):
    """
    Create a new task.
    """
    new_task = Task(
        id=uuid4(),
        **task.model_dump()
    )
    tasks_db[new_task.id] = new_task
    return new_task


@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: UUID, task: TaskUpdate):
    """
    Update an existing task.
    """
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")

    existing_task = tasks_db[task_id]

    updated_task = existing_task.model_copy(
        update=task.model_dump(exclude_unset=True)
    )

    tasks_db[task_id] = updated_task
    return updated_task


@app.delete("/tasks/{task_id}")
def delete_task(task_id: UUID):
    """
    Delete a task.
    """
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")

    del tasks_db[task_id]

    return {"message": "Task deleted successfully"}