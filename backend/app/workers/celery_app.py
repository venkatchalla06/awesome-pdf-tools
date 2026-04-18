from celery import Celery
from celery.schedules import crontab
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "pdfkit",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.tasks.merge",
        "app.workers.tasks.split",
        "app.workers.tasks.compress",
        "app.workers.tasks.rotate",
        "app.workers.tasks.watermark",
        "app.workers.tasks.protect",
        "app.workers.tasks.page_numbers",
        "app.workers.tasks.ocr",
        "app.workers.tasks.convert",
        "app.workers.tasks.ai_tasks",
        "app.workers.tasks.page_ops",
        "app.workers.tasks.cleanup",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.tasks.ocr.*": {"queue": "ocr"},
        "app.workers.tasks.ai_tasks.*": {"queue": "ai"},
        "app.workers.tasks.*": {"queue": "default"},
    },
    beat_schedule={
        "cleanup-expired-files": {
            "task": "app.workers.tasks.cleanup.delete_expired",
            "schedule": crontab(minute=0),
        }
    },
)
