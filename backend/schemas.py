from pydantic import BaseModel
from datetime import date, datetime
from uuid import UUID


class TaskCreate(BaseModel):
    title: str
    description: str
    status: str
    due_date: date


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    due_date: date | None = None


class Task(BaseModel):
    id: UUID
    title: str
    description: str
    status: str
    due_date: date
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }