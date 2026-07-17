from sqlalchemy import Column, String, Date, DateTime
from database import Base
from uuid import uuid4
from datetime import datetime


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title = Column(String(100), nullable=False)
    description = Column(String(500), nullable=False)
    status = Column(String(30), default="pending")
    due_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)