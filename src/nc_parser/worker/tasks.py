from __future__ import annotations

from time import sleep
from typing import Any
from uuid import UUID

from nc_parser.processing.parser import parse_document_to_text
from nc_parser.storage.files import get_uploaded_file_path, write_result, write_status
from nc_parser.worker.app import celery_app
from nc_parser.core.settings import get_settings
from pathlib import Path
import time


@celery_app.task(name="nc_parser.process_file")
def process_file(file_id: str) -> dict[str, Any]:
    """Process file and write a dummy result; placeholder for later phases."""
    # Update status: processing start
    write_status(UUID(file_id), status="processing", progress=0.1)
    input_path = get_uploaded_file_path(UUID(file_id))
    parsed = parse_document_to_text(input_path)
    result = {
        "document_id": file_id,
        "document_description": "Auto-parsed document",
        "full_text": parsed.full_text,
        "pages": parsed.pages,
        "chunks": [],
        "processing_metrics": {"timings_ms": {"parse": 500}},
    }
    write_result(UUID(file_id), result)
    write_status(UUID(file_id), status="done", progress=1.0, timings_ms={"parse": 500})
    return result


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):  # type: ignore[no-untyped-def]
    sender.add_periodic_task(3600.0, cleanup_expired.s(), name="ttl_cleanup_hourly")


@celery_app.task(name="nc_parser.cleanup_expired")
def cleanup_expired() -> dict[str, Any]:
    settings = get_settings()
    base = settings.data_dir
    now = time.time()
    ttl = settings.retention_ttl_hours * 3600
    removed: list[str] = []
    uploads_dir = base / "uploads"
    if not uploads_dir.exists():
        return {"removed": removed}
    for dir_path in uploads_dir.iterdir():
        if not dir_path.is_dir():
            continue
        meta_path = dir_path / "meta.json"
        if not meta_path.exists():
            continue
        try:
            meta = UploadMeta.from_file(meta_path)  # type: ignore[name-defined]
            created = meta.created_ts or (meta_path.stat().st_mtime)
            if now - created > ttl:
                # delete corresponding folders
                from nc_parser.storage.files import delete_all
                delete_all(UUID(str(meta.file_id)))
                removed.append(str(meta.file_id))
        except Exception:
            continue
    return {"removed": removed}


