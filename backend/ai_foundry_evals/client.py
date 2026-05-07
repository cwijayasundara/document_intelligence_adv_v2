"""Lazy Azure SDK clients.

Imports azure-ai-projects only when called so the rest of the package stays
importable on machines that don't have the optional `foundry` extra installed.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from .settings import load_settings


@lru_cache(maxsize=1)
def get_project_client() -> Any:
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    s = load_settings()
    return AIProjectClient(
        endpoint=s.project_endpoint,
        credential=DefaultAzureCredential(),
    )


def get_evals_client() -> Any:
    """OpenAI-shaped client for Foundry's `client.evals.*` API."""
    return get_project_client().get_openai_client()
