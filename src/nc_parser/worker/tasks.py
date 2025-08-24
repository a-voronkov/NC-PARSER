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
from nc_parser.core.worker_metrics import observe_task
from nc_parser.processing.captioning import caption_image_stub
from pathlib import Path
from structlog import get_logger


logger = get_logger(__name__)


@celery_app.task(name="nc_parser.process_file")
@observe_task("nc_parser.process_file")
def process_file(file_id: str) -> dict[str, Any]:
    """Process file and write a dummy result; placeholder for later phases."""
    # Update status: processing start
    write_status(UUID(file_id), status="processing", progress=0.1)
    input_path = get_uploaded_file_path(UUID(file_id))
    # Extra debug: log input path and list of files in uploads/<file_id>
    try:
        settings = get_settings()
        uploads_dir = settings.data_dir / "uploads" / file_id
        if uploads_dir.exists():
            files_list = [p.name for p in uploads_dir.iterdir() if p.is_file()]
        else:
            files_list = []
        # Debug-level to reduce noise in normal runs
        logger.debug("worker_input_path", file_id=file_id, input=str(input_path), uploads=str(uploads_dir), files=files_list)
    except Exception:
        pass
    # Debug: ensure artifacts dir is writable and visible
    try:
        settings = get_settings()
        if settings.ocr_debug_dump:
            art_dir = settings.data_dir / "artifacts" / file_id
            art_dir.mkdir(parents=True, exist_ok=True)
            # Write a small probe and copy original only when debug dump is enabled
            try:
                (art_dir / "probe.txt").write_text("ok", encoding="utf-8")
            except Exception:
                pass
            try:
                dest = art_dir / input_path.name
                dest.write_bytes(Path(input_path).read_bytes())
                logger.debug("worker_artifacts_copied", file_id=file_id, dest=str(dest))
            except Exception:
                pass
    except Exception:
        pass
    t0 = time.time()
    parsed = parse_document_to_text(input_path)
    t_parse = int((time.time() - t0) * 1000)
    # Optional captioning (stub): if enabled and input is image
    if get_settings().captioning_enabled and input_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".tiff"}:
        cap = caption_image_stub(input_path)
        parsed.pages.append({"index": len(parsed.pages), "text": cap.text})
    result = {
        "document_id": file_id,
        "document_description": "Auto-parsed document",
        "full_text": parsed.full_text,
        "pages": parsed.pages,
        "chunks": [],
        "processing_metrics": {"timings_ms": {"parse": t_parse}},
    }
    write_result(UUID(file_id), result)
    write_status(UUID(file_id), status="done", progress=1.0, timings_ms={"parse": float(t_parse)})
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


