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
    """Standard document categories for classification evals."""
    return [
        {"id": "cat-lpa", "name": "Limited Partnership Agreement",
         "classification_criteria": "Contains fund name, GP, management fee, carried interest, etc."},
        {"id": "cat-sub", "name": "Subscription Agreement",
         "classification_criteria": "Capital commitment, investor representations, AML."},
        {"id": "cat-sl", "name": "Side Letter",
         "classification_criteria": "References main LPA, fee discounts, MFN clauses."},
        {"id": "cat-other", "name": "Other/Unclassified",
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
