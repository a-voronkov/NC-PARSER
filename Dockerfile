# syntax=docker/dockerfile:1.6

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      curl \
      ca-certificates \
      poppler-utils \
      tesseract-ocr \
      tesseract-ocr-eng \
      tesseract-ocr-rus \
      libgl1 \
      libglib2.0-0 \
      libsm6 libxrender1 libxext6 \
      ghostscript \
      fonts-dejavu \
      antiword \
      unrtf && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

EXPOSE 8080

ENV NC_APP_HOST=0.0.0.0 NC_APP_PORT=8080

CMD ["uvicorn", "nc_parser.api.main:app", "--host", "0.0.0.0", "--port", "8080"]


