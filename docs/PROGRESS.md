# NC-PARSER — Progress & Checklists

This document tracks phase-wise progress against `docs/PHASED_PLAN.md` and `docs/PHASED_PLAN_DETAILED.md`.

## Phase 0 — Foundations and Project Setup
- [x] Repo structure scaffolded (`src/`, `tests/`, `scripts/`, `docker-compose.cpu.yml`)
- [x] Configuration schema via pydantic-settings; `settings.ensure_data_dirs()`
- [x] Base Dockerfile (CPU) with system deps (poppler, tesseract, libgl1, ghostscript)
- [x] Health endpoints `/healthz`, `/version`
- [x] Structured JSON logging (structlog)
- [x] Run scripts (bash/ps1)
- [x] Data layout `/data/{uploads,artifacts,results}`
- [ ] GPU base image and import check (planned later on GPU host)

Exit criteria: API boots; `/healthz` 200; write-access to `/data` — Achieved (CPU profile).

## Phase 1 — Ingestion API and Job Orchestration
- [x] Endpoints: `POST /upload`, `/upload/init`, `/upload/chunk`, `/upload/complete`
- [x] Endpoints: `GET /status/{file_id}`, `GET /result/{file_id}`, `DELETE /file/{file_id}`
- [x] Chunk assembler and single-shot flow
- [x] Storage layout under `/data/uploads/{uuid}` with metadata
- [x] Queue-backed worker (Celery + Redis), enqueue from API
- [ ] Idempotent uploads (baseline implemented; hardening pending)
- [x] TTL scheduler stub (Celery Beat hourly)

Exit criteria: Single-shot+chunked flows pass, status transitions, deletion — Achieved (e2e скрипт chunked-загрузки работает, статус/результат отдаются).

## Phase 2 — Document Parsing (CPU-first)
- [x] Text/Markdown/HTML парсинг
- [x] PDF (pdfminer.six) базовый текст
- [x] DOCX (python-docx)
- [x] Изображения через Tesseract OCR
- [ ] Таблицы как HTML + текст (в последующих итерациях)
- [ ] Метрики времени по шагам (добавить сбор)

Exit criteria: базовый парсинг для текстовых PDF, сканов и изображений — Частично достигнуто (PDF/MD/HTML/IMG/DOCX работают, таблицы/метрики в плане).

## Notes
- Local profile is CPU-only; OCR/Captioning/Donut/LLM toggles are off by default.
- Next: verify chunked flow with fixtures; implement TTL stub; improve status transitions (queued/processing/done).
