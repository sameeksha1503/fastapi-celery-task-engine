import enum
from typing import Optional
from datetime import datetime,timezone
from sqlmodel import SQLModel, Field

class Status(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)

    title: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    status: Status = Field(default=Status.PENDING)
