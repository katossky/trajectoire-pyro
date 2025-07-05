# syntax=docker/dockerfile:1.5
FROM --platform=linux/arm64 python:3.11-slim

# System deps
RUN apt-get update && \
    apt-get install -y build-essential git && \
    rm -rf /var/lib/apt/lists/*

# Python deps (CPU wheels)
RUN pip install uv

RUN uv init trajectoire-pyro

RUN uv add torch pyro-ppl pandas

# Optional: force PyTorch to skip MPS checks – avoids misleading warnings
ENV PYTORCH_ENABLE_MPS_FALLBACK=1

# Workspace for AutoGen’s Docker executor
WORKDIR /workspace
