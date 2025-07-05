# syntax=docker/dockerfile:1.5
FROM --platform=$TARGETPLATFORM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Workspace for AutoGen’s Docker executor
WORKDIR /workspace

# System deps
RUN apt-get update && \
    apt-get install -y build-essential git && \
    rm -rf /var/lib/apt/lists/*

# Python deps (CPU wheels)
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project
COPY . .
RUN uv sync --locked

# Optional: force PyTorch to skip MPS checks – avoids misleading warnings
ENV PYTORCH_ENABLE_MPS_FALLBACK=1

# Default run
CMD ["uv", "run", "main.py"]
