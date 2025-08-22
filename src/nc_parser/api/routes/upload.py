from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, Request
from fastapi.responses import JSONResponse

from nc_parser.storage import files as storage
from nc_parser.worker.app import celery_app


router = APIRouter()


@router.post("/upload")
async def upload_single(file: UploadFile = File(...), filename: Optional[str] = None) -> JSONResponse:
    data = await file.read()
    file_id = storage.save_single_shot(data, filename or file.filename)
    storage.write_status(file_id, status="queued", progress=0.0)
    task = celery_app.send_task("nc_parser.process_file", args=[str(file_id)])
    storage.save_celery_task_id(file_id, task.id)
    return JSONResponse({"file_id": str(file_id), "status": "queued"})


@router.post("/upload/init")
def upload_init(payload: dict | None = None) -> JSONResponse:
    filename = (payload or {}).get("filename") if payload else None
    size_bytes = (payload or {}).get("size_bytes") if payload else None
    checksum = (payload or {}).get("checksum") if payload else None
    file_id = storage.init_upload(filename=filename, size_bytes=size_bytes, checksum=checksum)
    storage.write_status(file_id, status="queued", progress=0.0)
    return JSONResponse({"file_id": str(file_id)})


@router.post("/upload/chunk")
async def upload_chunk(
    request: Request,
    file_id: UUID = Query(...),
    index: int = Query(..., ge=0),
) -> JSONResponse:
    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="Empty chunk body")
    storage.append_chunk(file_id, index, data)
    return JSONResponse(status_code=204, content=None)


@router.post("/upload/complete")
async def upload_complete(
    file_id: UUID | None = Query(default=None), file: UploadFile | None = File(default=None)
) -> JSONResponse:
    if file is not None:
        data = await file.read()
        file_id2 = storage.save_single_shot(data, file.filename)
        storage.write_status(file_id2, status="queued", progress=0.0)
        task = celery_app.send_task("nc_parser.process_file", args=[str(file_id2)])
        storage.save_celery_task_id(file_id2, task.id)
        return JSONResponse({"file_id": str(file_id2), "status": "queued"})
    if file_id is None:
        raise HTTPException(status_code=400, detail="file_id or file must be provided")
    storage.assemble_file(file_id)
    storage.write_status(file_id, status="queued", progress=0.0)
    task = celery_app.send_task("nc_parser.process_file", args=[str(file_id)])
    storage.save_celery_task_id(file_id, task.id)
    return JSONResponse({"file_id": str(file_id), "status": "queued"})


@router.get("/status/{file_id}")
def status(file_id: UUID) -> JSONResponse:
    # If we have result on disk, it's done
    try:
        storage.read_result(file_id)
        try:
            st = storage.read_status(file_id)
            st.update({"file_id": str(file_id), "status": "done", "progress": 1.0})
            return JSONResponse(st)
        except Exception:
            return JSONResponse({"file_id": str(file_id), "status": "done", "progress": 1.0})
    except FileNotFoundError:
        pass
    # Else try to read celery task id and ask celery
    try:
        meta = storage.UploadMeta.from_file(storage._meta_path(file_id))  # type: ignore[attr-defined]
        if meta.celery_task_id:
            async_result = celery_app.AsyncResult(meta.celery_task_id)
            st = async_result.status.lower()
            # Map Celery states to our enum
            mapped = {
                "pending": "queued",
                "received": "processing",
                "started": "processing",
                "retry": "processing",
                "success": "done",
                "failure": "failed",
                "revoked": "failed",
            }.get(st, "processing")
            try:
                st = storage.read_status(file_id)
                st.update({"file_id": str(file_id), "status": mapped})
                return JSONResponse(st)
            except Exception:
                return JSONResponse({"file_id": str(file_id), "status": mapped})
    except Exception:
        pass
    try:
        st = storage.read_status(file_id)
        st.update({"file_id": str(file_id)})
        return JSONResponse(st)
    except Exception:
        return JSONResponse({"file_id": str(file_id), "status": "processing"})


@router.get("/result/{file_id}")
def result(file_id: UUID) -> JSONResponse:
    try:
        data = storage.read_result(file_id)
        return JSONResponse(data)
    except FileNotFoundError:
        return JSONResponse(status_code=202, content=None)


@router.delete("/file/{file_id}")
def delete_file(file_id: UUID) -> JSONResponse:
    storage.delete_all(file_id)
    return JSONResponse(status_code=204, content=None)


