from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_prefix="NC_", extra="ignore")

    # App
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8080)
    log_level: str = Field(default="INFO")

    # Storage
    data_dir: Path = Field(default=Path("data"))
    data_subdirs: List[str] = Field(default_factory=lambda: ["uploads", "artifacts", "results"])

    # Queue/Worker
    redis_url: str = Field(default="redis://localhost:6379/0")
    retention_ttl_hours: int = Field(default=168)  # 7 days

    # Features & OCR
    ocr_agent: str = Field(default="tesseract")  # paddle|tesseract
    ocr_gpu: bool = Field(default=False)
    captioning_enabled: bool = Field(default=False)
    donut_enabled: bool = Field(default=False)
    llm_enabled: bool = Field(default=False)

    # Build metadata (populated by CI or docker build args)
    build_version: str | None = Field(default=os.getenv("BUILD_VERSION"))
    build_git_commit: str | None = Field(default=os.getenv("BUILD_GIT_COMMIT"))
    build_time: str | None = Field(default=os.getenv("BUILD_TIME"))

    def ensure_data_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        for sub in self.data_subdirs:
            (self.data_dir / sub).mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()  # type: ignore[call-arg]


