from __future__ import annotations

import time
from typing import Callable

from prometheus_client import Counter, Histogram, start_http_server


TASK_TOTAL = Counter(
    "celery_tasks_total",
    "Total Celery tasks by name and status",
    labelnames=("task", "status"),
)

TASK_DURATION = Histogram(
    "celery_task_duration_seconds",
    "Celery task duration in seconds",
    labelnames=("task",),
)


def start_worker_metrics_server(port: int) -> None:
    # Idempotent start
    try:
        start_http_server(port)
    except Exception:
        # If already started or port busy inside same process, ignore
        pass


def observe_task(task_name: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                TASK_TOTAL.labels(task=task_name, status="success").inc()
                return result
            except Exception:
                TASK_TOTAL.labels(task=task_name, status="failure").inc()
                raise
            finally:
                TASK_DURATION.labels(task=task_name).observe(time.perf_counter() - start)

        def sync_wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                TASK_TOTAL.labels(task=task_name, status="success").inc()
                return result
            except Exception:
                TASK_TOTAL.labels(task=task_name, status="failure").inc()
                raise
            finally:
                TASK_DURATION.labels(task=task_name).observe(time.perf_counter() - start)

        # Choose wrapper by coroutine nature
        return async_wrapper if callable(getattr(func, "__await__", None)) else sync_wrapper

    return decorator


