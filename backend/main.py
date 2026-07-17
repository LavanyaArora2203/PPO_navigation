from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
import models

from database import Base, engine, get_db

from models import Task as TaskModel
from schemas import TaskCreate, TaskUpdate,Task

app = FastAPI()

# Create tables
Base.metadata.create_all(bind=engine)


@app.post("/tasks", response_model=Task)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    new_task = TaskModel(**task.model_dump())
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@app.get("/tasks", response_model=list[Task])
def get_tasks(db: Session = Depends(get_db)):
    """
    Get all tasks.
    """
    tasks = db.query(TaskModel).all()
    return tasks


@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: UUID, db: Session = Depends(get_db)):
    task = db.query(TaskModel).filter(Task.id == str(task_id)).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: UUID, task: TaskUpdate, db: Session = Depends(get_db)):
    """
    Update an existing task.
    """
    existing_task = db.query(TaskModel).filter(Task.id == str(task_id)).first()

    if not existing_task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = task.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(existing_task, key, value)

    db.commit()
    db.refresh(existing_task)

    return existing_task


@app.delete("/tasks/{task_id}")
def delete_task(task_id: UUID, db: Session = Depends(get_db)):
    """
    Delete a task.
    """
    task = db.query(TaskModel).filter(Task.id == str(task_id)).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()

    return {"message": "Task deleted successfully"}