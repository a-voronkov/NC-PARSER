from __future__ import annotations

from celery import Celery

from nc_parser.core.settings import get_settings
from nc_parser.core.worker_metrics import start_worker_metrics_server


def create_celery() -> Celery:
    settings = get_settings()
    # Start Prometheus metrics server for worker
    start_worker_metrics_server(settings.worker_metrics_port)
    app = Celery(
        "nc_parser",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=["nc_parser.worker.tasks"],
    )
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
    )
    return app


celery_app = create_celery()


