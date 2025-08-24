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
- [x] Старые/альтернативные форматы документов: DOC (binary), RTF, ODT — базовая поддержка (antiword/unrtf/striprtf/odfpy), требуется стабилизация
- [x] Таблицы: HTML + parallel plain-text для PDF/HTML/DOCX (база)
- [ ] Таблицы: RTF/DOC/ODT — улучшить эвристики, стабилизировать и покрыть тестами
- [x] «Fast‑fail» для битых/частично повреждённых PDF (эвристика EOF/страницы)
- [x] Нормализация/фильтрация: NBSP/минусы/контрольные символы, базовый фильтр шума UI/Word
- [x] Формальные документы: базовое извлечение ключевых полей (stub; расширение правил впереди)
- [x] Метрики времени: общая длительность parse_time_ms в `processing_metrics`
- [ ] Метрики времени: поэтапные (step-by-step) тайминги по операциям
- [ ] Здоровье ресурсов: surfaced‑сигналы OOM/ENOSPC в статус/метрики (см. Phase 7 Observability)

Exit criteria (Phase 2): базовый парсинг для текстовых PDF, сканов и изображений — почти достигнут. Для перехода дальше требуется: стабилизировать таблицы (особенно RTF/DOC/ODT) и их тесты, добавить поэтапные тайминги, усилить нормализацию, зафиксировать метрики/лимиты; здоровье ресурсов — в рамках Phase 7.

## Phase 3 — Visual Elements Description (Captioning)
- [x] Каркас captioning (stub) и интеграция по флагу
- [ ] BLIP-2 backend (GPU) — планируется на GPU-сервере
- [ ] Heuristics/батчинг/троттлинг

Readiness blockers (to start Phase 3 эффективно):
- [ ] Из Phase 2: стабильные элементы страниц (таблицы как HTML+plain), нормализованный текст
- [ ] Готовность окружения с GPU (образы/драйверы, доступ к весам BLIP‑2)
- [ ] Базовые метрики/тайминги для оценки накладных расходов captioning

## Notes
- Local profile is CPU-only; OCR/Captioning/Donut/LLM toggles are off by default.
- Next: закрыть хвосты Phase 2 (DOC/RTF/ODT, таблицы, тайминги/нормализация), затем включить GPU‑backend для BLIP‑2 и перейти к Phase 3.
