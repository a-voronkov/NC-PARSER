from __future__ import annotations

import time
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.requests import Request
from starlette.responses import Response


REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    labelnames=("method", "path", "status"),
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    labelnames=("method", "path"),
)


async def metrics_endpoint(_: Request) -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

async def metrics_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    method = request.method.upper()
    path = request.url.path
    start = time.perf_counter()
    response: Response | None = None
    try:
        response = await call_next(request)
        return response
    finally:
        dur = time.perf_counter() - start
        REQUEST_LATENCY.labels(method=method, path=path).observe(dur)
        status_str = str(getattr(response, "status_code", 500))
        REQUEST_COUNT.labels(method=method, path=path, status=status_str).inc()


