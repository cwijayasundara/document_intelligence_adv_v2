"""Generate adversarial datasets via Azure's AdversarialSimulator.

Maps a friendly scenario name to the SDK enum and writes the simulator's
output (already in OpenAI message + ground-truth shape) to JSONL under
`backend/evals/datasets/`.

Region-bound: East US 2, France Central, UK South, Sweden Central.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Awaitable, Callable

from ..settings import load_settings

logger = logging.getLogger(__name__)

_DATASETS_DIR = Path(__file__).resolve().parents[2] / "evals" / "datasets"

SCENARIO_MAP: dict[str, str] = {
    "qa": "ADVERSARIAL_QA",
    "conversation": "ADVERSARIAL_CONVERSATION",
    "summarization": "ADVERSARIAL_SUMMARIZATION",
    "search": "ADVERSARIAL_SEARCH",
    "rewrite": "ADVERSARIAL_REWRITE",
    "content_gen_ungrounded": "ADVERSARIAL_CONTENT_GEN_UNGROUNDED",
    "content_gen_grounded": "ADVERSARIAL_CONTENT_GEN_GROUNDED",
    "protected_material": "ADVERSARIAL_PROTECTED_MATERIAL",
}


async def generate_adversarial(
    *,
    scenario: str,
    target: Callable[..., Awaitable[dict[str, Any]]] | None = None,
    n: int = 10,
    max_conversation_turns: int = 1,
    out_path: Path | None = None,
    seed: int | None = None,
) -> Path:
    """Run AdversarialSimulator and persist outputs to JSONL."""
    from azure.ai.evaluation.simulator import AdversarialScenario, AdversarialSimulator
    from azure.identity import DefaultAzureCredential

    enum_name = SCENARIO_MAP.get(scenario)
    if enum_name is None:
        raise ValueError(f"unknown scenario {scenario!r}; valid: {sorted(SCENARIO_MAP)}")

    if target is None:
        from ._target import default_rag_target as target  # noqa: PLW0127

    settings = load_settings()
    sim = AdversarialSimulator(
        credential=DefaultAzureCredential(),
        azure_ai_project=settings.azure_ai_project,
    )

    kwargs: dict[str, Any] = {
        "scenario": getattr(AdversarialScenario, enum_name),
        "target": target,
        "max_simulation_results": n,
        "max_conversation_turns": max_conversation_turns,
    }
    if seed is not None:
        kwargs["randomization_seed"] = seed

    outputs = await sim(**kwargs)

    out = out_path or (_DATASETS_DIR / f"adversarial_{scenario}.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(outputs, "to_eval_qr_json_lines") and max_conversation_turns == 1:
        out.write_text(outputs.to_eval_qr_json_lines())
    else:
        out.write_text(outputs.to_json_lines())
    logger.info("wrote %d adversarial rows to %s", n, out)
    return out
