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
- POST `/upload/init`
- POST `/upload/chunk` (query: `file_id`, `index`, `checksum?`)
- POST `/upload/complete` (multipart single-shot or finalize by `file_id`)
- GET `/status/{file_id}`
- GET `/result/{file_id}`
- DELETE `/file/{file_id}`