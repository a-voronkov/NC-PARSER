from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional
from uuid import UUID, uuid4

from nc_parser.core.settings import get_settings


StatusLiteral = Literal["queued", "processing", "done", "failed"]


@dataclass
class UploadMeta:
    file_id: UUID
    filename: Optional[str] = None
    size_bytes: Optional[int] = None
    checksum: Optional[str] = None
    celery_task_id: Optional[str] = None
    chunks_received: list[int] | None = None
    created_ts: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_id": str(self.file_id),
            "filename": self.filename,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
            "celery_task_id": self.celery_task_id,
            "chunks_received": self.chunks_received or [],
            "created_ts": self.created_ts,
        }

    @staticmethod
    def from_file(path: Path) -> "UploadMeta":
        data = json.loads(path.read_text(encoding="utf-8"))
        return UploadMeta(
            file_id=UUID(data["file_id"]),
            filename=data.get("filename"),
            size_bytes=data.get("size_bytes"),
            checksum=data.get("checksum"),
            celery_task_id=data.get("celery_task_id"),
            chunks_received=list(data.get("chunks_received")) if data.get("chunks_received") else [],
            created_ts=data.get("created_ts"),
        )


def _base_paths(file_id: UUID) -> dict[str, Path]:
    settings = get_settings()
    base = settings.data_dir
    uploads = base / "uploads" / str(file_id)
    artifacts = base / "artifacts" / str(file_id)
    results = base / "results" / str(file_id)
    return {"uploads": uploads, "artifacts": artifacts, "results": results}


def _meta_path(file_id: UUID) -> Path:
    return _base_paths(file_id)["uploads"] / "meta.json"


def _status_path(file_id: UUID) -> Path:
    return _base_paths(file_id)["uploads"] / "status.json"


def init_upload(filename: Optional[str] = None, size_bytes: Optional[int] = None, checksum: Optional[str] = None) -> UUID:
    file_id = uuid4()
    paths = _base_paths(file_id)
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    (paths["uploads"] / "chunks").mkdir(parents=True, exist_ok=True)
    import time
    meta = UploadMeta(file_id=file_id, filename=filename, size_bytes=size_bytes, checksum=checksum, chunks_received=[], created_ts=time.time())
    _meta_path(file_id).write_text(json.dumps(meta.to_dict(), ensure_ascii=False), encoding="utf-8")
    return file_id


def append_chunk(file_id: UUID, index: int, data: bytes) -> None:
    paths = _base_paths(file_id)
    chunks_dir = paths["uploads"] / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    (chunks_dir / f"chunk_{index:08d}.part").write_bytes(data)
    # Update meta
    meta = UploadMeta.from_file(_meta_path(file_id))
    received = set(meta.chunks_received or [])
    received.add(index)
    meta.chunks_received = sorted(received)
    _meta_path(file_id).write_text(json.dumps(meta.to_dict(), ensure_ascii=False), encoding="utf-8")


def assemble_file(file_id: UUID) -> Path:
    paths = _base_paths(file_id)
    meta = UploadMeta.from_file(_meta_path(file_id))
    chunks_dir = paths["uploads"] / "chunks"
    output_path = paths["uploads"] / (meta.filename or "file.bin")
    indices = sorted(int(p.name.split("_")[1].split(".")[0]) for p in chunks_dir.glob("chunk_*.part"))
    # Ensure contiguous from 0..n
    if not indices:
        raise FileNotFoundError("No chunks found")
    if indices[0] != 0 or indices != list(range(indices[-1] + 1)):
        raise ValueError("Chunk indices are not contiguous from 0")
    with output_path.open("wb") as w:
        for idx in indices:
            w.write((chunks_dir / f"chunk_{idx:08d}.part").read_bytes())
    return output_path


def save_single_shot(file_bytes: bytes, filename: Optional[str]) -> UUID:
    file_id = init_upload(filename=filename, size_bytes=len(file_bytes))
    paths = _base_paths(file_id)
    out = paths["uploads"] / (filename or "file.bin")
    out.write_bytes(file_bytes)
    return file_id


def get_uploaded_file_path(file_id: UUID) -> Path:
    uploads_dir = _base_paths(file_id)["uploads"]
    # Prefer original filename if exists
    candidates = list(uploads_dir.glob("*.*")) + list(uploads_dir.glob("file.bin"))
    for c in candidates:
        if c.name != "meta.json" and c.is_file() and c.name != "chunks":
            return c
    raise FileNotFoundError("Uploaded file not found")


def save_celery_task_id(file_id: UUID, task_id: str) -> None:
    meta_path = _meta_path(file_id)
    meta = UploadMeta.from_file(meta_path)
    meta.celery_task_id = task_id
    meta_path.write_text(json.dumps(meta.to_dict(), ensure_ascii=False), encoding="utf-8")


def write_result(file_id: UUID, result: dict[str, Any]) -> Path:
    results_dir = _base_paths(file_id)["results"]
    results_dir.mkdir(parents=True, exist_ok=True)
    out = results_dir / "result.json"
    out.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return out


def read_result(file_id: UUID) -> dict[str, Any]:
    out = _base_paths(file_id)["results"] / "result.json"
    return json.loads(out.read_text(encoding="utf-8"))


def delete_all(file_id: UUID) -> None:
    for p in _base_paths(file_id).values():
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)


def write_status(
    file_id: UUID,
    status: str,
    progress: Optional[float] = None,
    error: Optional[str] = None,
    timings_ms: Optional[dict[str, float]] = None,
) -> None:
    payload: dict[str, Any] = {"file_id": str(file_id), "status": status}
    if progress is not None:
        payload["progress"] = max(0.0, min(1.0, float(progress)))
    if error is not None:
        payload["error"] = error
    if timings_ms:
        payload["timings_ms"] = timings_ms
    _status_path(file_id).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def read_status(file_id: UUID) -> dict[str, Any]:
    return json.loads(_status_path(file_id).read_text(encoding="utf-8"))


