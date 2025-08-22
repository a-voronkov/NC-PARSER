from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from nc_parser import __version__
from nc_parser.core.settings import get_settings


router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/version")
def version() -> dict[str, str | None]:
    settings = get_settings()
    build_time = settings.build_time or datetime.now(timezone.utc).isoformat()
    return {
        "version": settings.build_version or __version__,
        "git_commit": settings.build_git_commit,
        "build_time": build_time,
    }


