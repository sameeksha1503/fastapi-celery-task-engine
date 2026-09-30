from pydantic import BaseModel
from typing import Optional
from ..models.tasks import Status

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None

class TaskRead(BaseModel):
    id:int
    user_id:int
    title: str
    description: Optional[str] = None
    status: Status

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[Status] = None
    user_id: Optional[int] = None

