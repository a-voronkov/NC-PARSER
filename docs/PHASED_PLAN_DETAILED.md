### Phased Implementation Plan — Detailed (Document Processing Service)

This document expands `docs/PHASED_PLAN.md` into atomic steps with explicit inputs, actions, commands, success criteria, self-tests, and fallback scenarios. It is designed so even a simple executor can follow it to a successful end result. It assumes a Python-based stack (FastAPI + Celery + Redis + Unstructured + PaddleOCR + Tesseract fallback + Transformers/Donut + optional vLLM for LLM).

---

## Global Rules

- Progress to the next phase only when all success criteria of the current phase are met.
- After any dependency or model change, re-run: container build → imports smoke test → linters → tests (unit/integration).
- Default policy: prefer latest stable/LTS images and libraries; pin and test for compatibility.
- Keep heavy artifacts out of git (`data/`, `models/`, `artifacts/`, `results/`).

---

## Phase 0 — Foundations and Project Setup (Detailed)

- Inputs
  - Linux host with Docker (and NVIDIA runtime for GPU), git.
  - This repository checked out.
- Actions
  1) Ensure `.gitignore` ignores `.env`, caches, data, models (already configured).
  2) Create `.env` from `.env.example` and fill minimal values.
  3) Create base multi-stage Dockerfile (CPU first). GPU support will be added after imports work.
  4) Add skeleton FastAPI app with `/healthz` and `/version` (later phases will expand).
  5) Add basic logging (structured JSON) and metrics stubs.
  6) Define `/data` layout: `/uploads`, `/artifacts`, `/results` (configurable via env).
  7) Add scripts or Make targets to build, run, test, format.
- Commands (self-check stubs; adapt once code exists)
  - Verify Docker works: `docker run --rm hello-world | cat`
  - Verify env: `test -f .env && echo ok`
- Success criteria
  - Docker builds a base image for the app (even if it only runs `--help`).
  - App boots in container and `/healthz` returns 200.
  - Write-access verified to `/data/*` inside container.
  - Python imports for `unstructured`, `transformers`, and `torch` succeed in container.
- Self-test procedure
  - Build: `docker build -t nc-parser:local . | cat`
  - Run: `docker run --rm -p 8080:8080 --env-file .env nc-parser:local --help | cat`
  - Exec import check (temporary): `docker run --rm nc-parser:local python - <<'PY'\nimport importlib;\nfor m in ["unstructured","transformers","torch"]:\n    print(m, '=>', bool(importlib.import_module(m)))\nPY`
- If something fails
  - Docker build fails: pin a simpler base (e.g., `python:3.12-slim`), retry; check network proxies and mirrors.
  - Import fails: install missing system libs (poppler, tesseract, libgl1, etc.), re-pin versions.

---

## Phase 1 — Ingestion API and Job Orchestration (Detailed)

- Inputs
  - Basic FastAPI skeleton with routing.
- Actions
  1) Implement endpoints:
     - `POST /upload/init` → returns `file_id` and upload token/URL (optional).
     - `POST /upload/chunk` → append chunk with ordering, checksum (optional).
     - `POST /upload/complete` → finalize file, validate size/checksum, enqueue processing job.
     - `GET /status/{file_id}` → returns current job state.
     - `GET /result/{file_id}` → streams final JSON or 404 if not ready.
     - `DELETE /file/{file_id}` → purge uploads + artifacts + results.
  2) Storage layout: `/data/uploads/{uuid}`; metadata file with size, checksum, timestamps.
  3) Queue/worker: Celery + Redis (broker+backend). API enqueues; worker processes.
  4) Idempotency: same file_id safe to re-init/overwrite after delete or TTL expiry.
- Commands
  - Start Redis (local): `docker run -d --name redis -p 6379:6379 redis:7-alpine`
  - Start app: `docker run --rm --env-file .env --network host nc-parser:local`
  - Smoke: `curl -f http://localhost:8080/healthz | cat`
  - Upload flow: use `curl -F file=@sample.pdf http://localhost:8080/upload/complete | cat` (single-shot path for small files) and then check status, result.
- Success criteria
  - Both single-shot and chunked uploads succeed for small files.
  - Status transitions reflect queue processing lifecycle.
  - Deleting a file purges all artifacts on disk.
- Self-test
  - Upload a tiny file (<1MB) and confirm status/result endpoints.
  - Restart API; ensure idempotency and no orphaned temp files.
- If fails
  - Validate directory permissions, free disk space, and chunk ordering logic.

---

## Phase 2 — Document Parsing (Unstructured + OCR) (Detailed)

- Inputs
  - Worker skeleton and storage in place.
- Actions
  1) Integrate Unstructured for PDFs, images, DOCX, HTML.
  2) Add OCR agents:
     - Default: PaddleOCR (GPU if available, else CPU).
     - Fallback: Tesseract (CPU) when Paddle unavailable or fails.
  3) Detect text layer first; route pages without text to OCR.
  4) Normalize elements: type, page, bbox, language, confidence.
  5) Preserve tables as HTML plus parallel plain text.
  6) Emit per-page elements with stable block IDs.
  7) Toggle via env: `OCR_AGENT=paddle|tesseract`, `OCR_GPU=true|false`, `OCR_LANGS`, limits.
- Commands
  - Import smoke inside container: `python -c "import unstructured; import paddleocr; import pytesseract; print('ok')"`
  - Run worker on fixtures: `docker exec <worker> python scripts/run_on_fixture.py data/samples/*.pdf`
- Success criteria
  - Text PDFs, scans, and images yield consistent elements.
  - Tables preserved; per-page text available.
  - Baseline throughput recorded (docs/min, p95 latency per page).
- Self-test
  - Prepare 3 fixtures: text PDF, scanned PDF, image set; compare outputs are stable and annotated with confidences.
- If fails
  - Switch OCR agent; refine language packs; ensure CUDA availability when expected; check `TESSDATA_PREFIX` for Tesseract.

---

## Phase 3 — Visual Elements Description (Captioning) (Detailed)

- Inputs
  - Elements with image regions.
- Actions
  1) Crop per-image regions; create a pluggable captioning interface.
  2) Backends: BLIP-2 (default), optional Qwen2-VL for higher quality.
  3) Heuristics: caption only relevant images (diagrams, charts), not decorative.
  4) GPU throttling and batching.
  5) Attach descriptions to page text and block metadata.
- Commands
  - Caption smoke: process a sample with and without captions; compare runtime and output.
- Success criteria
  - Relevant images have useful descriptions; clear provenance (backend and model name).
- Self-test
  - Ensure caching avoids re-captioning identical crops; validate timing metrics per image.
- If fails
  - Reduce max size; lower batch; switch to CPU; fallback to simpler model.

---

## Phase 4 — Donut for Structured Fields (Selective) (Detailed)

- Inputs
  - Document type heuristics or simple registry mapping.
- Actions
  1) Maintain registry: doc_type → Donut model.
  2) Parse Donut JSON outputs; place under `pages[i].structured_data`.
  3) Reconcile Donut-extracted fields with OCR text; annotate disagreements with provenance.
  4) Timeouts, quantized weights, and per-page error isolation.
- Commands
  - Parse known templates (e.g., invoice); verify stable fields across runs.
- Success criteria
  - Supported types yield fields; unknown types skipped safely.
- Self-test
  - Force timeouts and verify graceful degradation without crashing workers.
- If fails
  - Try smaller Donut variant; relax heuristic thresholds; cache intermediate features.

---

## Phase 5 — LLM Analysis: Description, Q&A, Chunking (Detailed)

- Inputs
  - Clean per-page elements and optional captions.
- Actions
  1) LLM runner via vLLM (preferred) or local inference pipeline.
  2) Summary prompt, page-focused Q&A with global context, deterministic chunker (200–300 words, overlap).
  3) Strict JSON schema; retry on invalid JSON; low temperature; token accounting.
  4) Model suggestion: Qwen2.5-7B-Instruct (or equivalent long-context instruct model).
- Commands
  - JSON validation: run the pipeline on a small doc; ensure parsable outputs; measure tokens.
- Success criteria
  - Accurate document description; valid per-page Q&A JSON; finalized chunk list.
- Self-test
  - Inject malformed outputs in a test to confirm retry works and caps at safe attempts.
- If fails
  - Reduce prompt complexity; increase context overlap; switch to a smaller model or CPU profile as needed.

---

## Phase 6 — Final JSON Assembly and Data Model (Detailed)

- Inputs
  - Outputs from Phases 2–5.
- Actions
  1) Define schema: `document_id`, `document_description`, `full_text`, `pages[]`, `chunks[]`, `processing_metrics`.
  2) Provide stable ordering and deterministic key order when serialized (optional).
  3) Stream results via `GET /result/{file_id}`.
  4) Ensure PII not persisted beyond TTL.
- Commands
  - JSON schema validation tests; golden sample fixtures for regressions.
- Success criteria
  - JSON validates and is retrievable via API; delete purges all related files.
- Self-test
  - Round-trip: upload → status → result → delete → confirm 404 and no files on disk.
- If fails
  - Fix serialization edge-cases; handle optional fields; guard against `None`/NaN.

---

## Phase 7 — Performance, Scaling, and Cleanup (Detailed)

- Inputs
  - A functioning pipeline end-to-end.
- Actions
  1) Quantize heavy models; serialize heavy calls; apply concurrency limits.
  2) Horizontal scale via queue; back-pressure and graceful shutdown.
  3) TTL cleanup worker; Prometheus metrics (request latency, OCR time, model ids, token counts).
- Commands
  - k6 smoke: run 5–10 RPS for key endpoints with thresholds (p95 < target).
- Success criteria
  - Benchmarks hit; cleanup verified; metrics exposed.
- Self-test
  - Kill worker mid-job; ensure retry and idempotency; check no leaks.
- If fails
  - Add batch size/cooldowns; adjust process memory limits; add indices to storage if used.

---

## Phase 8 — Packaging, Documentation, and Handover (Detailed)

- Inputs
  - Working service.
- Actions
  1) Provide Docker Compose or K8s manifests (GPU runtime notes).
  2) Configuration guide for OCR agents, model toggles, quantization, timeouts.
  3) OpenAPI/Swagger, runbooks, and security notes.
  4) SBOM and image scanning in CI; non-root container user.
- Commands
  - `trivy image` scan; `syft` SBOM; OpenAPI served at `/docs`.
- Success criteria
  - One-command local run; accurate docs.
- Self-test
  - New developer can follow README to run end-to-end.
- If fails
  - Patch docs and scripts until friction-free.

---

## Versioning and Compatibility — How to stay on latest stable safely

- Lookup latest stable versions (examples)
  - Python packages (uv preferred):
    - `uv sync --upgrade`
    - `uv pip index versions <package> | head -n 30 | cat`
  - PyTorch (CUDA):
    - Check `https://pytorch.org/get-started/locally/` for the correct `--index-url` matching CUDA 12.x.
  - Unstructured / PaddleOCR / Transformers:
    - Use `uv add <pkg>@latest && uv lock && uv sync`, then run import smoke tests.
- Compatibility test after any bump
  1) Rebuild image.
  2) Run import smoke for `unstructured`, `paddleocr`, `pytesseract`, `transformers`, `torch`.
  3) Run minimal fixtures through the worker; compare outputs to golden samples.
  4) If a package breaks, pin to previous minor, open an issue, and document in `CHANGELOG.md`.

---

## Observability and Security — Baseline requirements

- Structured JSON logs with correlation ids for uploads/jobs.
- Prometheus metrics for API and worker: latency, throughput, queue depth, OCR and model timings.
- Security: non-root containers, minimal capabilities, `readOnlyRootFilesystem` when possible, dependency and image scans (Trivy), SBOM (Syft), secret scanning in CI.

---

## Acceptance Criteria (Go/No-Go)

- Phase-wise success criteria met and verified.
- Container image builds and starts; imports succeed; healthz 200.
- Upload → process → result → delete lifecycle green on fixtures.
- Linters/tests pass; performance smoke meets baseline; image scan shows no CRITICAL vulnerabilities.