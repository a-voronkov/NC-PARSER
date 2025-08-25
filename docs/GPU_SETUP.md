# GPU Setup Guide (NVIDIA)

This guide explains how to run NC-PARSER on a server with an NVIDIA GPU.

## Prerequisites

- NVIDIA Driver installed on the host (sufficient for CUDA 12.x runtime).
- NVIDIA Container Toolkit installed and configured for Docker.
- Docker Engine / Docker Compose (v2).

References:
- NVIDIA drivers: https://docs.nvidia.com/datacenter/tesla/driver-installation/overview.html
- NVIDIA Container Toolkit: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html

## Verify GPU on the host

```bash
nvidia-smi
```

Should show the GPU model and driver version.

## Build and run (GPU profile)

We provide a GPU-ready image and compose profile:

```bash
# Enable captioning and select GPU backend (optional; default backend is blip2 placeholder)
export NC_CAPTIONING_ENABLED=true
export NC_CAPTION_BACKEND=blip2
export NC_CAPTION_DEVICE=cuda

# Start services
docker compose -f docker-compose.gpu.yml up -d --build

# Health check
curl -sf http://localhost:8080/healthz
```

Notes:
- The `Dockerfile.gpu` installs PyTorch CUDA (cu121) wheels and project extras `[gpu]` (transformers/accelerate/timm/xformers).
- Compose requests GPU via `deploy.resources.reservations.devices.capabilities: ["gpu"]`.
- Ensure the host has NVIDIA Container Toolkit so Docker can expose the GPU into containers.

## Environment variables (GPU related)

- `NC_CAPTIONING_ENABLED` — enable image captioning pipeline.
- `NC_CAPTION_BACKEND` — `stub|blip2|qwen_vl` (GPU-friendly backends: `blip2`/`qwen_vl`, both placeholder now).
- `NC_CAPTION_DEVICE` — `cuda|cpu` (default `cuda` in GPU profile).
- `NC_OCR_GPU` — `true|false` (enables OCR GPU hints; current OCR uses Tesseract CPU but we keep the flag for future backends).

## Minimal smoke test

1) Upload a file and wait for processing:
```bash
curl -sf -F file=@data/samples/formal_document.pdf http://localhost:8080/upload
# => {"file_id":"...","status":"queued"}
```
2) Poll status until `done` and verify caption metrics are present:
```bash
curl -sf http://localhost:8080/status/<FILE_ID> | jq
# Expect top-level "caption": {...}
```
3) Fetch result and verify top-level "caption":
```bash
curl -sf http://localhost:8080/result/<FILE_ID> | jq
```

## Troubleshooting

- If containers start but GPU is not visible:
  - Check `nvidia-smi` on host
  - Ensure NVIDIA Container Toolkit is installed and `/etc/docker/daemon.json` contains the necessary nvidia runtime configuration or that Compose is using the default toolkit integration.
- If Python fails to import torch with CUDA:
  - Verify that the image includes `torch` wheels built for `cu121` (we install from `https://download.pytorch.org/whl/cu121`).
  - Confirm that the host driver is recent enough for CUDA 12.x.

## Next steps

- Replace placeholder caption backends with real implementations (e.g., BLIP‑2 with accelerate on CUDA).
- Add model weight caching volumes and configuration.
- Add GPU metrics export (utilization/memory) to status once available.
