### Technical Choices — NC-PARSER

This document consolidates technology selections, versioning policy, and compatibility guidance for the Document Processing Service.

---

## Language and Runtime

- Primary: Python (recommended: 3.12.x; consider 3.13 only if all deps compatible).
- Process model: API (FastAPI + Uvicorn) and Worker (Celery + Redis).

## Core Libraries

- API: FastAPI (modern async web framework), Uvicorn (ASGI server).
- Queue/Worker: Celery (broker and result backend via Redis).
- Parsing: Unstructured (multi-format), PDF processing stack (poppler-utils),
  OCR: PaddleOCR (default; GPU-capable), Tesseract (fallback).
- Vision/LLM: Transformers (Hugging Face), Donut for layout/structured fields,
  optional vLLM for serving local instruct models (e.g., Qwen2.5-7B-Instruct).

## Containers and Base Images

- CPU-only dev image: `python:3.12-slim` with required system deps (poppler, tesseract, libgl1, fonts).
- GPU runtime: NVIDIA CUDA 12.x runtime base (e.g., `nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04`) plus Python layer or official PyTorch image matching CUDA.
- Best practice: multi-stage build (builder → runtime), non-root user, minimal size, cache wheels.

## System Dependencies (apt)

- poppler-utils, tesseract-ocr (+ language packs), libgl1, libglib2.0-0, libsm6, libxrender1, libxext6, fonts (e.g., `fonts-dejavu`), `ghostscript` for some PDF workflows.

## Python Packaging and Tooling

- Package/lock: `uv` (preferred) or `pip-tools`.
- Quality: ruff (lint), black (format), mypy (types), pytest (+ pytest-cov) for tests.

## Model and Data Policy

- Models and large artifacts are not stored in git. Download at runtime or via `scripts/download-models`.
- Provide toggles for OCR, captioning, Donut, and LLM; default to conservative settings for dev.

---

## Version Policy

- Prefer latest stable/LTS minor versions; pin exact versions in lockfile.
- Allow automatic patch updates via Renovate/Dependabot.
- After any bump:
  1) Rebuild images
  2) Import smoke tests (torch, transformers, unstructured, paddleocr, pytesseract)
  3) Run fixtures through pipeline and compare against golden outputs
  4) If breakage: pin to last known-good, open an issue, document in `CHANGELOG.md`

### How to find the latest stable versions

- Python (uv):
  - `uv sync --upgrade`
  - `uv pip index versions <package> | head -n 30 | cat`
- PyTorch + CUDA:
  - Follow `https://pytorch.org/get-started/locally/` for correct `pip` extra index matching CUDA 12.x.
- Transformers / Unstructured / PaddleOCR:
  - `uv add <pkg>@latest && uv lock && uv sync` in a branch; run smoke tests.

---

## Observability and Security Choices

- Logs: structured JSON with request/job correlation ids.
- Metrics: Prometheus client for API and worker, include timings for OCR and model inference.
- Tracing: OpenTelemetry (optional for internal deployments).
- Container security: non-root, minimal capabilities; Trivy image scans; SBOM via Syft.

---

## Compatibility Notes

- GPU: ensure driver and container CUDA versions are compatible; verify with `nvidia-smi` and torch CUDA check (`torch.cuda.is_available()`).
- OCR: Tesseract requires proper `TESSDATA_PREFIX`; PaddleOCR requires paddlepaddle (GPU/CPU variant) alignment.
- PDF stack: poppler-utils must be installed for Unstructured PDF processing flows.
