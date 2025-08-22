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

## Progress & Checklists

See `docs/PROGRESS.md` for phase-wise progress against the plan.