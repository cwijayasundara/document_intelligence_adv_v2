"""CLI entry point for the eval framework.

Subcommands:
    sync-datasets              Push golden JSONL files to LangSmith.
    harvest-regressions        Pull corrections memory → regression JSONL.
    run --stage STAGE [...]    Run an experiment for one stage.
    list-stages                Print stages + example counts.

Usage:
    uv run python -m evals.cli sync-datasets
    uv run python -m evals.cli run --stage extraction --subset 5
    uv run python -m evals.cli list-stages
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _load_env_files() -> None:
    """Load .env before subcommands touch os.environ.

    Precedence (highest wins): shell env > backend/.env > repo-root/.env.
    Matches how `src/config/settings.py` treats backend/.env as primary.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    here = Path(__file__).resolve()
    for candidate in (here.parents[1] / ".env", here.parents[2] / ".env"):
        if candidate.exists():
            load_dotenv(candidate, override=False)


_load_env_files()

DATASETS_DIR = Path(__file__).parent / "datasets"

STAGE_CHOICES = [
    "classification",
    "extraction",
    "summary",
    "rag",
    "sql",
    "agentic_rag",
    "pipeline",
    "all",
]


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    # Upstream libraries (openai/httpx transports, uvloop) occasionally drop
    # unclosed-transport ResourceWarnings during Ctrl-C or agent teardown. Our
    # own engine/session lifecycles are handled explicitly in _base.py, so
    # these are noise for the eval CLI — suppress to keep output readable.
    import warnings
    warnings.filterwarnings("ignore", category=ResourceWarning)


def _count_examples(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text().splitlines() if line.strip() and not line.startswith("#"))


def cmd_list_stages(_args: argparse.Namespace) -> int:
    from .dataset_sync import STAGE_TO_FILE

    print(f"{'stage':<16} {'examples':>10}  file")
    print(f"{'-' * 16} {'-' * 10}  {'-' * 40}")
    for stage, fname in STAGE_TO_FILE.items():
        count = _count_examples(DATASETS_DIR / fname)
        print(f"{stage:<16} {count:>10}  {fname}")
    return 0


def cmd_sync_datasets(_args: argparse.Namespace) -> int:
    from .dataset_sync import sync_all

    results = sync_all()
    for r in results:
        print(
            f"[sync] stage={r.stage:<14} total={r.examples_total:<4} "
            f"created={r.examples_created:<3} updated={r.examples_updated:<3} "
            f"unchanged={r.examples_unchanged}"
        )
    return 0


def cmd_harvest_regressions(_args: argparse.Namespace) -> int:
    from .regression_harvest import harvest

    count = asyncio.run(harvest())
    print(f"Harvested {count} corrections into regression_corrections.jsonl")
    return 0


def _load_runner(stage: str):
    """Dynamically import a runner module for the given stage.

    Uses a package-relative import so the CLI works whether it was invoked
    as `python -m evals.cli` (from backend/) or `python -m backend.evals.cli`
    (from the repo root).
    """
    import importlib

    relative = f".runners.run_{stage}"
    try:
        module = importlib.import_module(relative, package=__package__)
    except ModuleNotFoundError as exc:
        fq = f"{__package__}{relative}" if __package__ else relative.lstrip(".")
        print(
            f"[run] Runner for stage '{stage}' not implemented yet "
            f"(expected module {fq}). Error: {exc}",
            file=sys.stderr,
        )
        return None
    return getattr(module, "run_experiment", None)


def cmd_run(args: argparse.Namespace) -> int:
    stages = STAGE_CHOICES[:-1] if args.stage == "all" else [args.stage]
    any_failed = False
    summaries: list[dict[str, Any]] = []
    overall_start = time.time()
    for stage in stages:
        runner = _load_runner(stage)
        if runner is None:
            any_failed = True
            summaries.append({"stage": stage, "status": "NOT_IMPLEMENTED"})
            continue

        print(f"[run] stage={stage} subset={args.subset} model={args.model or 'default'}")
        try:
            result: dict[str, Any] = asyncio.run(
                runner(subset=args.subset, model=args.model, tags=args.tags),
            )
        except Exception as exc:  # noqa: BLE001 — surface any runner error.
            print(f"[run] stage={stage} FAILED: {exc}", file=sys.stderr)
            any_failed = True
            summaries.append({"stage": stage, "status": "FAILED", "error": str(exc)})
            continue

        # Runners return a dict-shaped ExperimentResult.
        print(f"[run] stage={stage} result={json.dumps(result, default=str)[:400]}")
        summaries.append({
            "stage": stage,
            "status": "OK",
            "run_id": result.get("run_id"),
            "total_examples": result.get("total_examples"),
            "duration_seconds": result.get("duration_seconds"),
            "summary_scores": result.get("summary_scores") or {},
        })

    if len(stages) > 1:
        _print_multi_stage_summary(summaries, elapsed=time.time() - overall_start)
    return 1 if any_failed else 0


def _print_multi_stage_summary(summaries: list[dict[str, Any]], *, elapsed: float) -> None:
    """Print a consolidated table after running multiple stages."""
    # Load the stage→primary-metric map so the headline column is meaningful.
    try:
        from src.api.routers.evals import _resolve_primary
    except Exception:  # noqa: BLE001 — fall back to no headline if imports fail.
        _resolve_primary = None  # type: ignore[assignment]

    print()
    print("=" * 78)
    print(f"{'stage':<14} {'status':<16} {'ex':>4} {'dur':>7}  primary")
    print("-" * 78)
    ok = failed = 0
    for s in summaries:
        status = s["status"]
        if status == "OK":
            ok += 1
        else:
            failed += 1
        examples = s.get("total_examples", "-")
        duration = s.get("duration_seconds")
        dur_str = f"{duration:.1f}s" if isinstance(duration, (int, float)) else "-"
        if status == "OK" and _resolve_primary is not None:
            metric_key, score = _resolve_primary(s["stage"], s.get("summary_scores"))
            headline = (
                f"{metric_key}={score:.3f}" if (metric_key and score is not None) else "no-metrics"
            )
        else:
            headline = s.get("error", "-")[:40]
        print(f"{s['stage']:<14} {status:<16} {examples!s:>4} {dur_str:>7}  {headline}")
    print("-" * 78)
    print(f"{ok} ok / {failed} failed  (total {elapsed:.1f}s)")
    print("=" * 78)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m evals.cli")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-stages", help="Print stages + example counts.").set_defaults(
        func=cmd_list_stages
    )

    sub.add_parser("sync-datasets", help="Push datasets to LangSmith.").set_defaults(
        func=cmd_sync_datasets
    )

    sub.add_parser(
        "harvest-regressions",
        help="Pull corrections memory → regression JSONL.",
    ).set_defaults(func=cmd_harvest_regressions)

    run_parser = sub.add_parser("run", help="Run an experiment for one stage.")
    run_parser.add_argument("--stage", required=True, choices=STAGE_CHOICES)
    run_parser.add_argument("--subset", type=int, default=None, help="Run on first N examples.")
    run_parser.add_argument("--model", default=None, help="Override production model.")
    run_parser.add_argument("--tags", nargs="*", default=None, help="Filter examples by tag.")
    run_parser.set_defaults(func=cmd_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
