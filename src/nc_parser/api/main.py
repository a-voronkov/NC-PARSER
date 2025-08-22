from __future__ import annotations

import logging

from fastapi import FastAPI

from nc_parser.api.routes.health import router as health_router
from nc_parser.api.routes.upload import router as upload_router
from nc_parser.core.logging import setup_structlog
from nc_parser.core.settings import get_settings
from nc_parser.core.metrics import metrics_endpoint, metrics_middleware


def create_app() -> FastAPI:
    settings = get_settings()
    setup_structlog(settings.log_level)

    app = FastAPI(title="NC-PARSER API", version="0.1.0")
    app.add_route("/metrics", metrics_endpoint, methods=["GET"])  # Prometheus scrape
    app.middleware("http")(metrics_middleware)

    # Ensure data directories exist on startup
    @app.on_event("startup")
    def _on_startup() -> None:  # noqa: D401
        settings.ensure_data_dirs()
        logging.getLogger(__name__).info("App started", extra={"data_dir": str(settings.data_dir)})

    # Routers
    app.include_router(health_router)
    app.include_router(upload_router)

    return app


app = create_app()


