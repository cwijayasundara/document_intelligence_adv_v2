"""Direct (UPIA) and Indirect (XPIA) attack jailbreak simulators."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable

from ..settings import load_settings

logger = logging.getLogger(__name__)

_DATASETS_DIR = Path(__file__).resolve().parents[2] / "evals" / "datasets"


async def generate_indirect_attack(
    *,
    target: Callable[..., Awaitable[dict[str, Any]]] | None = None,
    n: int = 10,
    max_conversation_turns: int = 3,
    out_path: Path | None = None,
) -> Path:
    """XPIA: prompts injected into retrieved context."""
    from azure.ai.evaluation.simulator import IndirectAttackSimulator
    from azure.identity import DefaultAzureCredential

    if target is None:
        from ._target import default_rag_target as target  # noqa: PLW0127

    settings = load_settings()
    sim = IndirectAttackSimulator(
        azure_ai_project=settings.azure_ai_project,
        credential=DefaultAzureCredential(),
    )
    outputs = await sim(
        target=target,
        max_simulation_results=n,
        max_conversation_turns=max_conversation_turns,
    )

    out = out_path or (_DATASETS_DIR / "jailbreak_indirect.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(outputs, "to_json_lines"):
        out.write_text(outputs.to_json_lines())
    else:
        with out.open("w") as f:
            for row in outputs:
                f.write(json.dumps(row) + "\n")
    logger.info("wrote %d XPIA rows to %s", n, out)
    return out


async def generate_direct_attack(
    *,
    target: Callable[..., Awaitable[dict[str, Any]]] | None = None,
    scenario: str = "ADVERSARIAL_CONVERSATION",
    n: int = 10,
    max_conversation_turns: int = 3,
    out_path: Path | None = None,
) -> Path:
    """UPIA: prompts injected into the user turn. Output is a (baseline, jailbroken) pair."""
    from azure.ai.evaluation.simulator import AdversarialScenario, DirectAttackSimulator
    from azure.identity import DefaultAzureCredential

    if target is None:
        from ._target import default_rag_target as target  # noqa: PLW0127

    settings = load_settings()
    sim = DirectAttackSimulator(
        azure_ai_project=settings.azure_ai_project,
        credential=DefaultAzureCredential(),
    )
    outputs = await sim(
        target=target,
        scenario=getattr(AdversarialScenario, scenario),
        max_simulation_results=n,
        max_conversation_turns=max_conversation_turns,
    )

    out = out_path or (_DATASETS_DIR / "jailbreak_direct.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(outputs, (list, tuple)) and len(outputs) == 2:
        baseline, jailbroken = outputs
        with out.open("w") as f:
            for row in jailbroken:
                f.write(json.dumps({"variant": "jailbreak", **dict(row)}) + "\n")
            for row in baseline:
                f.write(json.dumps({"variant": "baseline", **dict(row)}) + "\n")
    elif hasattr(outputs, "to_json_lines"):
        out.write_text(outputs.to_json_lines())
    else:
        with out.open("w") as f:
            for row in outputs:
                f.write(json.dumps(row) + "\n")
    logger.info("wrote UPIA rows (n≈%d) to %s", n, out)
    return out
