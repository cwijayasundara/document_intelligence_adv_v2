"""Judge-model wrapper used by every synthesizer.

Thin layer over `evals.evaluators.llm_judge._base.structured_call` that adds:
- per-call cost accounting via `SynthCtx.cost_meter`
- abort-on-budget-exceeded
- a per-context concurrency semaphore
- a sidecar audit log of every prompt/response pair
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from .base import SynthCtx

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class BudgetExceeded(RuntimeError):
    """Raised when cumulative judge spend has reached the configured cap."""


# Rough $/call estimate — good enough to act as a stop, not for billing.
# Real cost is tracked from token counts where available; otherwise we fall
# back to a per-call constant.
_DEFAULT_CALL_USD = 0.02


def _audit_log_path() -> Path:
    base = Path(__file__).parent / ".synth_logs"
    base.mkdir(exist_ok=True)
    return base / f"audit_{time.strftime('%Y%m%d')}.jsonl"


def _log(record: dict[str, Any]) -> None:
    if os.environ.get("SYNTH_DISABLE_AUDIT_LOG"):
        return
    try:
        with _audit_log_path().open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, default=str) + "\n")
    except Exception as exc:  # noqa: BLE001
        logger.debug("audit-log write failed: %s", exc)


async def judge_call(
    *,
    ctx: SynthCtx,
    system: str,
    user: str,
    schema: type[T],
    purpose: str,
) -> T:
    """Run a structured judge call under the context's concurrency + cost budget.

    `purpose` is a short tag (e.g. "rag.generate", "rag.verify") used in the
    audit log so failures can be traced back to a specific synth step.
    """
    if ctx.cost_meter.exceeded():
        raise BudgetExceeded(
            f"max_cost_usd={ctx.cost_meter.max_cost_usd} reached after "
            f"{ctx.cost_meter.calls} calls (~${ctx.cost_meter.estimated_usd:.2f})"
        )

    from evals.evaluators.llm_judge._base import structured_call

    sem = ctx.get_semaphore()
    async with sem:
        started = time.time()
        try:
            result = await structured_call(system=system, user=user, schema=schema)
        except Exception as exc:
            _log({"purpose": purpose, "ok": False, "error": str(exc)})
            raise
        ctx.cost_meter.record(_DEFAULT_CALL_USD)
        _log({
            "purpose": purpose,
            "ok": True,
            "duration_s": round(time.time() - started, 3),
            "system_preview": system[:120],
            "user_preview": user[:200],
            "response": result.model_dump(),
        })
        return result
