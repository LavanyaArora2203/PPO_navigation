


from datetime import date, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Task(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str = Field(..., min_length=1, max_length=100)
    description: str
    status: Literal["pending", "in_progress", "completed"] = "pending"
    due_date: date
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)




# ----------------------
# Pydantic Models
# ----------------------

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: str
    status: Literal["pending", "in_progress", "completed"] = "pending"
    due_date: date


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: Literal["pending", "in_progress", "completed"] | None = None
    due_date: date | None = None


