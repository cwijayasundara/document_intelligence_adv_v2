#!/usr/bin/env bash
# Wrapper for the ai_foundry_evals CLI. Mirrors evals.sh — runs uv from
# backend/ so deps resolve, then forwards args.
#
# Usage:
#     ./foundry_evals.sh safety --stage rag --subset 5
#     ./foundry_evals.sh agent --subset 5
#     ./foundry_evals.sh doc-retrieval --subset 10
#     ./foundry_evals.sh sim adversarial --scenario qa --n 50
#     ./foundry_evals.sh sim jailbreak --type indirect --n 30

set -euo pipefail
cd "$(cd "$(dirname "$0")" && pwd)/backend"
exec uv run python -m ai_foundry_evals.cli "$@"
