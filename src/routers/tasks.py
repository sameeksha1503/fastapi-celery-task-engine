from http.client import HTTPException
import json
from typing import List
from fastapi import APIRouter, Depends, status,Response
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from ..worker.celery import send_task_notification

from ..database import get_db
from ..redis import redis_client
from ..models.tasks import Task
from ..schemas.tasks import TaskCreate,TaskRead,TaskUpdate
from ..worker import celery

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# Mock current user for testing
async def get_current_user_id() -> int:
    return 1

#-------------------------------------------------------------
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_db),
    author_id: int = Depends(get_current_user_id)
):
    
    new_task = Task(**task.model_dump(), user_id=author_id)
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    try:
        await redis_client.delete(f"tasks_user_{author_id}")
    except Exception as e:
        print(f"Redis cache delete failed: {e}")

    try:
        send_task_notification.delay(
            user_id=author_id, 
            task_id=new_task.id, 
            action="created"
        )
    except Exception as e:
        print(f"Celery dispatch failed: {e}")

    return new_task

#--------------------------------------------------------------------------

@router.get("/", response_model=List[TaskRead])
async def get_tasks(
    response: Response,
    db: AsyncSession = Depends(get_db),
    author_id: int = Depends(get_current_user_id)
):
    cache_key = f"tasks_user_{author_id}"
    cached_tasks = await redis_client.get(cache_key)
    if cached_tasks:
        response.headers["X-Data-Source"] = "redis"
        return json.loads(cached_tasks)

    tasks = (await db.exec(select(Task).where(Task.user_id == author_id))).all()
    tasks_json = [task.model_dump(mode="json") for task in tasks]

    await redis_client.setex(cache_key, 60, json.dumps(tasks_json))
    
    response.headers["X-Data-Source"] = "database"
    return tasks

#-----------------------------------------------------------------------------------------

@router.get("/{task_id}", response_model=TaskRead)
async def get_task_by_id(
    task_id: int,
    response: Response,
    db: AsyncSession = Depends(get_db),
    author_id: int = Depends(get_current_user_id)
):
    
    cache_key = f"task_{task_id}"

    #cache hit
    cached_task = await redis_client.get(cache_key)
    if cached_task:
        task_data = json.loads(cached_task)
        if task_data["user_id"] != author_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        response.headers["X-Data-Source"] = "redis"
        return task_data

    # 2. Cache Miss
    task = (await db.exec(select(Task).where(Task.id == task_id, Task.user_id == author_id))).one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    await redis_client.setex(cache_key, 60, task.model_dump_json())

    response.headers["X-Data-Source"] = "database"
    return task

#-------------------------------------------------------------------------------------------------

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_by_id(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    author_id: int = Depends(get_current_user_id)
):

    task = (await db.exec(select(Task).where(Task.id == task_id, Task.user_id == author_id))).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Task not found or access denied"
        )

    await db.delete(task)
    await db.commit()

    await redis_client.delete(f"task_{task_id}")
    await redis_client.delete(f"tasks_user_{author_id}")

    send_task_notification.delay(user_id=author_id, task_id=task_id, action="deleted")
    
    return None

#-----------------------------------------------------------------------------------------

@router.patch("/{task_id}", response_model=TaskRead)
async def update_task_patch(
    task_id: int,
    updated_task: TaskUpdate,
    response: Response,                
    db: AsyncSession = Depends(get_db),  
    author_id: int = Depends(get_current_user_id)
):

    task = (await db.exec(select(Task).where(Task.id == task_id,Task.user_id == author_id))).one_or_none()

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,  detail="Task not found")

    updated_data = updated_task.model_dump(exclude_unset=True)
    for key, value in updated_data.items():
        setattr(task, key, value)

    await db.commit()
    await db.refresh(task)

    await redis_client.delete(f"task_{task_id}")
    await redis_client.delete(f"tasks_user_{author_id}")

    return task