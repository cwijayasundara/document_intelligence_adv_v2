#!/usr/bin/env bash
# Wrapper for the evals CLI. Works from any cwd in the repo.
#
# `uv run` anchors to the nearest pyproject.toml, which only exists under
# backend/. Running the CLI from the repo root without this wrapper uses the
# base Python interpreter (no deps, no sitecustomize) — every import fails.
# This script resolves that by running uv from backend/ and forwarding args.
#
# Usage:
#     ./evals.sh run --stage all
#     ./evals.sh run --stage rag --subset 3
#     ./evals.sh list-stages
#     ./evals.sh harvest-regressions
#     ./evals.sh sync-datasets

set -euo pipefail
cd "$(cd "$(dirname "$0")" && pwd)/backend"
exec uv run python -m evals.cli "$@"
