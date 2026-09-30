import time
from celery import Celery

CELERY_BROKER_URL="redis://127.0.0.1:6379/0"
CELERY_RESULT_BACKEND="redis://127.0.0.1:6379/0"

celery_app = Celery(
    "worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery_app.task(name="send_task_notification")
def send_task_notification(user_id: int, task_id: int, action: str):

    time.sleep(3) 
    print(f"[PUSH NOTIFICATION] Sent to User #{user_id}: Task #{task_id} was successfully {action}.")
    return True