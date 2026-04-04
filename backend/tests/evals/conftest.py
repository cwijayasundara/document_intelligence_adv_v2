"""Shared fixtures and configuration for agent evals.

Usage:
    uv run pytest tests/evals -v                    # Run all evals
    uv run pytest tests/evals -k classification      # By category
    uv run pytest tests/evals -k "rag and groundedness"  # Specific behavior

All eval runs are traced to LangSmith project 'pe-doc-intel-evals'.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

# Load .env for API keys (evals make real LLM calls)
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

# Ensure LangSmith tracing for evals
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
os.environ.setdefault("LANGCHAIN_PROJECT", "pe-doc-intel-evals")

DATASETS_DIR = Path(__file__).parent / "datasets"
GROUND_TRUTH_PATH = DATASETS_DIR / "ground_truth.json"


@pytest.fixture(scope="session")
def ground_truth() -> dict[str, Any]:
    """Load ground truth dataset."""
    with open(GROUND_TRUTH_PATH) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def lpa_document(ground_truth: dict) -> dict[str, Any]:
    """Get the main LPA Horizon document ground truth."""
    return ground_truth["documents"][0]


@pytest.fixture(scope="session")
def lpa_amendment(ground_truth: dict) -> dict[str, Any]:
    """Get the LPA amendment document ground truth."""
    return ground_truth["documents"][1]


@pytest.fixture(scope="session")
def lpa_parsed_content(lpa_document: dict) -> str:
    """Load parsed markdown content for the main LPA."""
    parsed_path = Path(lpa_document["parsed_path"])
    if not parsed_path.exists():
        # Try relative to backend dir
        parsed_path = Path("backend") / parsed_path
    if not parsed_path.exists():
        pytest.skip(f"Parsed file not found: {parsed_path}")
    return parsed_path.read_text()


@pytest.fixture(scope="session")
def categories() -> list[dict[str, Any]]:
    """Load categories — use DB if available, fallback to test data."""
    import uuid

    try:
        import asyncio
        import threading

        async def _load() -> list[dict[str, Any]]:
            from src.config.settings import get_settings
            from src.db.connection import get_session_factory, init_engine

            settings = get_settings()
            init_engine(settings.database_url, pool_size=2, max_overflow=1)
            factory = get_session_factory()
            async with factory() as session:
                from src.db.repositories.categories import CategoryRepository

                repo = CategoryRepository(session)
                cats = await repo.list_all()
                return [
                    {"id": c.id, "name": c.name, "classification_criteria": c.classification_criteria}
                    for c in cats
                ]

        result: list[dict[str, Any]] = []

        def _run() -> None:
            nonlocal result
            result = asyncio.run(_load())

        t = threading.Thread(target=_run)
        t.start()
        t.join(timeout=15)
        if result:
            return result
    except Exception:
        pass

    # Fallback
    return [
        {"id": uuid.uuid4(), "name": "Limited Partnership Agreement",
         "classification_criteria": "Contains fund name, GP, management fee, carried interest."},
        {"id": uuid.uuid4(), "name": "Subscription Agreement",
         "classification_criteria": "Capital commitment, investor representations."},
        {"id": uuid.uuid4(), "name": "Other/Unclassified",
         "classification_criteria": "Default for non-matching documents."},
    ]


class EvalMetrics:
    """Collect metrics for an eval run."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.start_time = time.time()
        self.metrics: dict[str, Any] = {}

    def record(self, key: str, value: Any) -> None:
        self.metrics[key] = value

    def finish(self) -> dict[str, Any]:
        elapsed = time.time() - self.start_time
        self.metrics["latency_seconds"] = round(elapsed, 2)
        return self.metrics


@pytest.fixture
def eval_metrics(request: pytest.FixtureRequest) -> EvalMetrics:
    """Create metrics tracker for the current eval."""
    return EvalMetrics(request.node.name)
