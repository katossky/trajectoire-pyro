# syntax=docker/dockerfile:1.5
FROM --platform=$TARGETPLATFORM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Workspace for AutoGen’s Docker executor
WORKDIR /workspace

# System deps
RUN apt-get update && \
    apt-get install -y build-essential git && \
    rm -rf /var/lib/apt/lists/*

RUN git config --global --add --bool push.autoSetupRemote true

# Python deps (CPU wheels)
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project
COPY . .
# for deployment
# RUN uv sync --locked
# for developement (editable install)
RUN uv pip install -e .

# Optional: force PyTorch to skip MPS checks – avoids misleading warnings
ENV PYTORCH_ENABLE_MPS_FALLBACK=1

# Default run
ENTRYPOINT ["uv", "run", "--"]
CMD ["smoke"]
