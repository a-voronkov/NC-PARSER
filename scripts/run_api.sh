#!/usr/bin/env bash
set -euo pipefail

HOST=${NC_APP_HOST:-0.0.0.0}
PORT=${NC_APP_PORT:-8080}

exec uvicorn nc_parser.api.main:app --host "$HOST" --port "$PORT"


