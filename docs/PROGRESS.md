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
- [x] Бэкенд-интерфейс + кэш (CPU-friendly, stub/blip2-stub/qwen-vl-stub)
- [x] Батч‑капшенинг с кэшем, вставка в pages и метрики (model, cache_hits)
- [x] Эвристики отбора: min size, max images per doc, аспект‑ratio, энтропия
- [ ] Троттлинг/пулы по backends (конкурентность)
- [ ] BLIP-2 backend (GPU) — планируется на GPU-сервере

Readiness blockers (to start Phase 3 эффективно):
- [ ] Из Phase 2: стабильные элементы страниц (таблицы как HTML+plain), нормализованный текст — база есть, ведём стабилизацию RTF/DOC/ODT
- [ ] Готовность окружения с GPU (образы/драйверы, доступ к весам BLIP‑2)
- [x] Базовые метрики/тайминги для оценки накладных расходов captioning — добавлены (pdf_caption_ms/docx_caption_ms, caption metrics)

## Notes
- Local profile is CPU-only; OCR/Captioning/Donut/LLM toggles are off by default.
- Next: закрыть хвосты Phase 2 (DOC/RTF/ODT, таблицы, тайминги/нормализация), затем включить GPU‑backend для BLIP‑2 и перейти к Phase 3.

## Snapshot — CPU + Captioning(stub) — 2025‑08‑25

- **Запуск профиля (CPU) с captioning stub**:
  - Переменные окружения:
    - `NC_CAPTIONING_ENABLED=true`
    - `NC_CAPTION_BACKEND=stub`
  - Команда запуска: `docker compose -f docker-compose.cpu.yml up -d --build`

- **Быстрая API‑проверка (scripts/check_references.ps1)**
  - Итог: `TOTAL=19 OK=1 FAIL=18`

- **Оффлайн‑проверка (scripts/offline_check_references.py)**
  - Итог: `TOTAL=19 OK=2 FAIL=17`

- **Примеры image_caption (из `data/results/**/result.json`)**

```text
FILE_ID=0ad34803-7413-42ec-ae70-b691beace000
caption_metrics={"count":16,"cache_hits":0,"processed":16,"model":"stub"}
image_caption=Image 600x777, mode=RGB

FILE_ID=2a02af68-2d24-4fc7-bf4e-d672ae84d4bf
caption_metrics={"count":1,"cache_hits":1,"processed":0,"model":"stub"}
image_caption=Image 2480x3508, mode=RGB

FILE_ID=3bce217e-0a50-4422-87d2-987a0efd4614
caption_metrics={"count":4,"cache_hits":4,"processed":0,"model":"stub"}
image_caption=Image 339x194, mode=RGB

FILE_ID=f5879dd3-71a6-4dde-ba99-c75f5b768085
caption_metrics={"count":4,"cache_hits":0,"processed":4,"model":"stub"}
image_caption=Image 287x153, mode=RGB
```

- **Метрики `processing_metrics.caption` (примеры)**

```json
{ "count": 16, "cache_hits": 16, "processed": 0,  "model": "stub" }
{ "count":  2, "cache_hits":  0, "processed": 2,  "model": "stub" }
{ "count":  1, "cache_hits":  1, "processed": 0,  "model": "stub" }
{ "count":  1, "cache_hits":  0, "processed": 1,  "model": "stub" }
```

Примечание: капшены добавляются как элементы страниц с типом `image_caption`, а агрегированные метрики капшенинга пишутся в `processing_metrics.caption` у итогового `result.json`. Модель — `stub`; кэширование активно по умолчанию.
