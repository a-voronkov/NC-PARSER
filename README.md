# NC-PARSER

- See the high-level phased plan in `docs/PHASED_PLAN.md`.
- See the detailed execution plan with self-tests in `docs/PHASED_PLAN_DETAILED.md`.
- See technical choices and versioning policy in `docs/TECH_CHOICES.md`.
- API specification: `docs/api/openapi.yaml` and preview instructions in `docs/api/README.md`.
- Copy `.env.example` to `.env` and adjust values before running locally.

## Run (CPU profile) with Docker Compose

Requires Docker Desktop.

```
docker compose -f docker-compose.cpu.yml up -d --build
curl -sf http://localhost:8080/healthz
```

Services:
- API: FastAPI on port 8080
- Redis: 6379
- Worker: Celery worker
- Beat: Celery beat (runs TTL cleanup hourly)

Env flags (see `.env.example`):
- `NC_RETENTION_TTL_HOURS` — TTL for uploads/results cleanup (default 168)

E2E scripts:
- Chunked upload (PowerShell): `scripts/e2e_chunk_upload.ps1`

## Local run (without Docker)

```
# API
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_api.ps1
# or bash
bash scripts/run_api.sh
```

## Data cleanup

Use PowerShell helper:

```
# Dry-run (preview):
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/clean_data.ps1 -DryRun

# Delete all (uploads, artifacts, results):
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/clean_data.ps1 -Force

# Delete only older than N days:
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/clean_data.ps1 -OlderThanDays 7 -Force

# Select subdirs:
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/clean_data.ps1 -Uploads -Force
```

The script respects `NC_DATA_DIR` if set; otherwise uses `data/`.

## Reference-based verification (offline)

Quick check that current parser output matches `.reference` sidecar files under `data/samples`:

```
python scripts/offline_check_references.py  # scans data/samples by default
```

It prints a summary (`TOTAL/OK/FAIL`) and writes brief `*.diff.txt` files next to sources for failed cases.

## Reference-based verification (API)

With the API running on `http://localhost:8080`:

```
# Generate reference files from current outputs (one-time, optional)
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/gen_references.ps1

# Compare API outputs with existing .reference
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check_references.ps1
```

`check_references.ps1` uploads each sample, waits for processing, fetches results, and compares `full_text` to `expected_full_text` from the `.reference` files.

## Progress & Checklists

See `docs/PROGRESS.md` for phase-wise progress against the plan.