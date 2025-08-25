### Phased implementation plan for the Document Processing Service (Unstructured + Donut + LLM)

This plan is derived from `initial_plan.pdf` and structured into phases with tasks, explicit exclusions, exit criteria, and checklists. Core technology choices are fixed in `docs/TECH_CHOICES.md` and referenced below.

## Phase 0 — Foundations and Project Setup
- Purpose: Prepare repo, dev environment, base container, GPU support, and scaffolding.
- Tasks:
  - Create repo structure: `api/`, `worker/`, `processing/`, `models/`, `storage/`, `configs/`, `scripts/`, `tests/`, `docker/`, `infra/`.
  - Define configuration schema (YAML/ENV) for: storage paths, OCR engine, model variants, GPU flags, retention TTL, concurrency.
  - Build base Dockerfile with CUDA, PyTorch, Unstructured, Donut/Transformers, PaddleOCR (primary) + Tesseract (fallback), FastAPI/uvicorn, Celery, psutil. See `docs/TECH_CHOICES.md`.
  - Implement health endpoints: `/healthz`, `/version`.
  - Add logging (structured JSON logs) and basic metrics collection stubs.
  - Write Makefile/scripts: build, run, test, format, download-models.
  - Define artifact layout under `/data`: `/uploads/`, `/artifacts/`, `/results/`, with UUID naming.
- Do not:
  - Train or fine-tune models.
  - Implement full pipeline logic.
  - Expose service publicly.
- Exit criteria:
  - Docker image builds with GPU runtime.
  - API boots; `/healthz` returns 200.
  - Import sanity: `unstructured`, `transformers`, `torch` load in container.
  - Write-access verified to `/data` subdirectories.
- Checklists:
  - Docker: CUDA base, NVIDIA runtime, pinned versions, non-root user, locales.
  - Python: locked dependencies, reproducible installs.
  - Security: disable telemetry, offline mirrors configurable.

## Phase 1 — Ingestion API and Job Orchestration
- Purpose: Upload endpoints, chunked upload, job queue, lifecycle.
- Tasks:
  - Endpoints: `POST /upload/init`, `POST /upload/chunk`, `POST /upload/complete`, `GET /status/{file_id}`, `GET /result/{file_id}`, `DELETE /file/{file_id}`.
  - Chunk assembler with ordering validation and optional checksums.
  - Storage under `/data/uploads/{uuid}` with TTL metadata.
  - Queue-backed worker (Celery + Redis); API enqueues and returns. See `docs/TECH_CHOICES.md`.
  - Idempotent uploads and safe reprocess.
- Do not:
  - Parse documents or load ML models yet.
  - Implement authentication (internal-only).
- Exit criteria:
  - Small-file single-shot and chunked upload flows pass.
  - Status transitions work; deletion purges all artifacts.
  - TTL scheduler stub present.
- Checklists:
  - Streaming, temp files, OOM-safe.
  - Standardized error schema.
  - Correlated logs for lifecycle events.

## Phase 2 — Document Parsing (Unstructured + OCR)
- Purpose: Convert raw files into page-ordered elements; attach metadata.
- Tasks:
  - Integrate Unstructured for PDF, DOCX, images, HTML.
  - OCR via PaddleOCR (default, GPU) with Tesseract (CPU) as fallback by `OCR_AGENT`. See `docs/TECH_CHOICES.md`.
  - Normalize elements: type, page, bboxes, language, confidence.
  - Preserve tables as HTML with parallel plain text.
  - Group by page; stable block IDs.
- Do not:
  - Call LLMs or Donut yet.
  - Caption images.
- Exit criteria:
  - Consistent elements for text PDFs, scans, and images.
  - Tables preserved; per-page text produced.
  - Baseline performance recorded.
- Checklists:
  - Text-layer detection before OCR.
  - Config toggles for OCR and limits.
  - Timing metrics collected.

## Phase 3 — Visual Elements Description (Captioning / Qwen-VL selectively)
- Purpose: Enrich non-text elements with descriptions.
- Tasks:
  - Extract per-image crops; pluggable caption backends (stub CPU now; BLIP-2/Qwen-VL planned).
  - Heuristics for when to use model; batching and caching; GPU throttling later.
  - Insert descriptions into page text and block metadata.
- Do not:
  - Caption every image blindly.
  - Duplicate descriptions excessively.
- Exit criteria:
  - Descriptions present for relevant images; backends switchable (stub now; real backends later).
  - Fallbacks work under GPU pressure (planned).
- Checklists:
  - Batch processing; caching; per-image timing and model names in metrics.

## Phase 4 — Donut for Structured Fields (Selective)
- Purpose: Extract structured fields for known templates; OCR-free fallback when helpful.
- Tasks:
  - Registry of doc-type → Donut model; heuristics for detection.
  - Parse Donut JSON; attach to `pages[i].structured_data`.
  - Reconcile Donut vs OCR text; provenance tags.
- Do not:
  - Force Donut on unknown types.
- Exit criteria:
  - Fields present for supported types; disagreements handled.
- Checklists:
  - Quantized weights; timeouts; error isolation per page.

## Phase 5 — LLM Analysis: Description, Q&A, Chunking
- Purpose: Produce document description, per-page Q&A, and RAG chunks.
- Tasks:
  - Use Qwen2.5-7B-Instruct (or similar) with long context and quantization via vLLM (prod GPU profile). See `docs/TECH_CHOICES.md`.
  - Summary prompt; page-focused Q&A with global context; strict JSON outputs.
  - Deterministic chunker (~200–300 words, with overlap) with page references.
  - Token accounting in metrics.
- Do not:
  - Invent facts; no LLM chunking.
- Exit criteria:
  - Accurate description; valid per-page Q&A JSON; chunk list ready.
- Checklists:
  - Context window guards; retry-on-invalid-JSON; low temperature.

## Phase 6 — Final JSON Assembly and Data Model
- Purpose: Merge outputs into final JSON schema.
- Tasks:
  - Schema with `document_id`, `document_description`, `full_text`, `pages[]`, `chunks[]`, `processing_metrics`.
- Do not:
  - Persist PII beyond TTL.
- Exit criteria:
  - JSON validates; streamed by `/result/{file_id}`; `/delete` purges.
- Checklists:
  - Robust serialization; optional fields only when present; deterministic key order if desired.

## Phase 7 — Performance, Scaling, and Cleanup
- Purpose: Meet performance and robustness targets; automatic cleanup.
- Tasks:
  - Quantized loading; serialize heavy calls; horizontal scale with queue.
  - TTL cleanup worker; Prometheus metrics; SLIs defined.
- Do not:
  - Run competing heavy inferences without guardrails.
- Exit criteria:
  - Benchmarks achieved; cleanup verified; alerts/metrics exposed.
- Checklists:
  - Stress tests; back-pressure; graceful shutdown.

## Phase 8 — Packaging, Documentation, and Handover
- Purpose: Operational docs and reproducible deployment.
- Tasks:
  - Docker Compose/K8s manifests; GPU runtime docs.
  - Configuration guide (OCR agents, model toggles, quantization, timeouts).
  - OpenAPI/Swagger; runbooks; security notes.
- Do not:
  - Publish publicly; include sensitive samples.
- Exit criteria:
  - One-command local run; docs accurate.
- Checklists:
  - Versioning, changelog, third-party licenses.

### Phase transition rules
- Progress only after all exit criteria are met.
- Fix blockers within the phase; do not defer.
- Model/engine changes after Phase 5 require revalidation of Phases 2–6.
- Security/privacy blockers halt progression until resolved.

### Global exclusions
- No external cloud inference; local-only models.
- No authentication scope (internal network assumed).
- No training/fine-tuning pipelines.
- No vector DB or RAG query service (only chunk preparation).
- No multi-agent orchestration beyond explicit pipeline.

### Repo hygiene additions
- Provide `.env.example`; include `.env` in `.gitignore`.
- Before each commit, review what should be ignored (artifacts, caches, datasets, model weights, secrets).
