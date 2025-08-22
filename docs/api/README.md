# NC-PARSER API Docs

- Spec: `openapi.yaml` (OpenAPI 3.1)
- Preview options:
  - VS Code: OpenAPI extension preview
  - Redocly CLI: `npx @redocly/cli preview-docs openapi.yaml`
  - Swagger UI (docker): `docker run -p 8081:8080 -e SWAGGER_JSON=/spec/openapi.yaml -v $(pwd):/spec swaggerapi/swagger-ui`

## Validate the spec

- Redocly lint:
```bash
npx @redocly/cli lint openapi.yaml | cat
```
- Spectral lint:
```bash
npx @stoplight/spectral lint openapi.yaml | cat
```

## Endpoints (summary)

- GET `/healthz`
- GET `/version`
- POST `/upload` (single-shot multipart)
- POST `/upload/init`
- POST `/upload/chunk` (query: `file_id`, `index`, `checksum?`)
- POST `/upload/complete` (finalize by `file_id` or single-shot with file)
- GET `/status/{file_id}`
- GET `/result/{file_id}`
- DELETE `/file/{file_id}`

## Examples

- Single-shot:
```bash
curl -f -F file=@sample.pdf http://localhost:8080/upload | jq
```
- Chunked:
```bash
FILE_ID=$(curl -sf -X POST http://localhost:8080/upload/init -H 'Content-Type: application/json' -d '{"filename":"sample.pdf","size_bytes":123}' | jq -r .file_id)
# For each chunk i:
curl -sf --data-binary @chunk_0.bin "http://localhost:8080/upload/chunk?file_id=$FILE_ID&index=0&checksum=..."
# Complete:
curl -sf -X POST "http://localhost:8080/upload/complete?file_id=$FILE_ID" | jq
```